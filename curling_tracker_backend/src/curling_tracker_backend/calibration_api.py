from flask import (Blueprint, request, jsonify, current_app)

import uuid
import math
import sqlite3
from typing import Dict, List, Optional, Tuple
import numpy as np
import logging
import curling_tracker_backend.db_helper as db_helper
from curling_tracker_backend.db import query_db, db_transaction
import curling_tracker_backend.util.camera_utilities as camera_utilities
from curling_tracker_backend.util.sheet_coordinates import SHEET_COORDINATES
import curling_tracker_backend.util.async_yt_dlp as async_yt_dlp
import cv2
import base64
import tempfile
import os
import curling_tracker_backend.util.curling_shot_tracker as shot_tracker
import curling_tracker_backend.flask_util as flask_util

logger = logging.getLogger(__name__)
bp = Blueprint("calibration_api", __name__, url_prefix="/api")

# Minimum number of point pairs needed to calibrate a camera from a single view
MIN_CALIBRATION_POINTS = 6
# Minimum number of shared points needed to compute a homography between two cameras
MIN_HOMOGRAPHY_POINTS = 4


@bp.route("/camera_setup_headers", methods=["GET"])
def camera_setup_headers():
    logger.info(f"Processing camera setup headers request.")

    if request.method == "GET":
        camera_setups = query_db(
            "SELECT setup_id, setup_name FROM CameraSetups")

        return jsonify([{
            "setup_id": setup[0],
            "setup_name": setup[1]
        } for setup in camera_setups])
    else:
        return jsonify({"error": "Method not allowed"}), 405


@bp.route("/camera_setup", methods=["POST", "GET"])
def camera_setup():
    if request.method == "GET":
        setup_id = request.args.get("setup_id", None)

        logger.info(f"Processing camera_setup GET request: {setup_id=}")

        if setup_id is None:
            return jsonify({"error": "setup_id is required"}), 400
        setup = query_db("SELECT * FROM CameraSetups WHERE setup_id = ?",
                         [setup_id],
                         one=True)
        if setup is None:
            return jsonify({"error": "Camera Setup not found"}), 404

        rows = query_db(
            f"SELECT {db_helper.CAMERA_COLUMNS} FROM Cameras WHERE setup_id = ?",
            [setup_id],
        )
        cameras = {row[0]: db_helper.camera_from_row(row) for row in rows}
        for camera, reference_id in cameras.values():
            if reference_id in cameras:
                camera.reference_camera = cameras[reference_id][0]

        camera_list = []
        for row in rows:
            camera, reference_id = cameras[row[0]]
            camera_list.append({
                "camera_id": row[0],
                "camera_name": camera.name,
                "camera_type": row[8],
                "corner1": camera.corner1.tolist(),
                "corner2": camera.corner2.tolist(),
                **_camera_calibration_json(camera, reference_id),
            })
        return jsonify({
            "setup_id": setup[0],
            "setup_name": setup[1],
            "cameras": camera_list
        })

    elif request.method == "POST":
        data = request.get_json()
        setup_name = data.get("setup_name", "Unnamed Setup")
        setup_id = data.get("setup_id", None)

        logger.info(
            f"Processing camera_setup POST request: {setup_id=} {setup_name=}")

        if setup_id is None:
            setup_id = str(uuid.uuid4())
            query_db(
                "INSERT INTO CameraSetups (setup_id, setup_name) VALUES (?, ?)",
                [setup_id, setup_name],
            )
        else:
            query_db(
                "UPDATE CameraSetups SET setup_name = ? WHERE setup_id = ?",
                [setup_name, setup_id],
            )

        # Update cameras in place so camera ids (and their calibration points) stay stable
        with db_transaction() as conn:
            existing_cameras = {
                row[0]: row
                for row in conn.execute(
                    "SELECT camera_id, corner1, corner2 FROM Cameras WHERE setup_id = ?",
                    [setup_id]).fetchall()
            }

            kept_camera_ids = set()
            for camera in data.get("cameras", []):
                camera_id = camera.get("camera_id", None)
                camera_name = camera.get("camera_name", "Unnamed Camera")
                corner1 = np.array(camera.get("corner1", [0, 0]))
                corner2 = np.array(camera.get("corner2", [0, 0]))
                camera_type = camera.get("camera_type", "unknown")

                if camera_id in existing_cameras:
                    kept_camera_ids.add(camera_id)
                    conn.execute(
                        "UPDATE Cameras SET camera_name = ?, camera_type = ?, corner1 = ?, corner2 = ? WHERE camera_id = ?",
                        [
                            camera_name, camera_type, corner1, corner2,
                            camera_id
                        ],
                    )

                    # The image points are relative to the corners, so a change requires a recalibration
                    _, old_corner1, old_corner2 = existing_cameras[camera_id]
                    if not (np.array_equal(old_corner1, corner1)
                            and np.array_equal(old_corner2, corner2)):
                        _recalibrate_camera(conn, camera_id)
                else:
                    conn.execute(
                        "INSERT INTO Cameras (camera_id, setup_id, camera_name, camera_type, corner1, corner2) VALUES (?, ?, ?, ?, ?, ?)",
                        [
                            str(uuid.uuid4()), setup_id, camera_name,
                            camera_type, corner1, corner2
                        ],
                    )

            for camera_id in existing_cameras.keys() - kept_camera_ids:
                # Cameras using the deleted camera as a reference lose their homography
                conn.execute(
                    "UPDATE Cameras SET reference_camera_id = NULL, homography = NULL WHERE reference_camera_id = ?",
                    [camera_id])
                conn.execute(
                    "DELETE FROM CalibrationPoints WHERE camera_id = ?",
                    [camera_id])
                conn.execute("DELETE FROM Cameras WHERE camera_id = ?",
                             [camera_id])

        return jsonify({"setup_id": setup_id})


def _camera_calibration_json(camera: camera_utilities.Camera,
                             reference_camera_id: Optional[str]) -> Dict:
    """The calibration fields of a camera for a JSON response."""

    def to_list(matrix):
        return matrix.tolist() if matrix is not None else None

    return {
        "calibration_method": camera.calibration_method.value,
        "reference_camera_id": reference_camera_id,
        "calibrated": camera_utilities.is_calibrated(camera),
        "camera_matrix": to_list(camera.camera_matrix),
        "distortion_coefficients": to_list(camera.distortion_coefficients),
        "rotation_vectors": to_list(camera.rotation_vectors),
        "translation_vectors": to_list(camera.translation_vectors),
        "homography": to_list(camera.homography),
    }


def _compute_full_calibration(conn: sqlite3.Connection,
                              camera_id: str) -> Optional[str]:
    """Compute and store the full calibration of a camera from its calibration points.
    The calibration is cleared if it cannot be computed.

    Returns:
        Optional[str]: None, or the reason the camera could not be calibrated.
    """
    points = db_helper.get_calibration_points(camera_id, conn)
    corner1, corner2 = conn.execute(
        "SELECT corner1, corner2 FROM Cameras WHERE camera_id = ?",
        [camera_id]).fetchone()
    image_shape = tuple(int(v) for v in np.abs(corner1 - corner2))

    camera = None
    error = None
    if len(points) < MIN_CALIBRATION_POINTS:
        error = f"At least {MIN_CALIBRATION_POINTS} points are required to calibrate, got {len(points)}"
    elif image_shape[0] <= 0 or image_shape[1] <= 0:
        error = "The camera corners do not define an image area"
    else:
        try:
            camera = camera_utilities.create_camera(
                [tuple(p["image_point"]) for p in points],
                [tuple(p["world_point"]) for p in points], image_shape)
        except cv2.error as e:
            logger.warning(f"Calibration failed for {camera_id=}: {e}")
            error = f"Calibration failed: {e}"

    db_helper.set_camera_calibration(conn, camera_id, camera)
    db_helper.set_camera_homography(conn, camera_id, None)
    return error


def _compute_homography(conn: sqlite3.Connection, camera_id: str,
                        reference_camera_id: Optional[str]) -> Optional[str]:
    """Compute and store the homography of a camera into its reference camera from the calibration
    points both cameras have with the same name. The homography is cleared if it cannot be computed.

    Returns:
        Optional[str]: None, or the reason the homography could not be computed.
    """
    # A homography camera only uses the calibration of its reference
    db_helper.set_camera_calibration(conn, camera_id, None)

    homography = None
    error = None
    reference = (db_helper.get_camera_from_db(reference_camera_id, conn)
                 if reference_camera_id is not None else None)
    if reference is None:
        error = "No reference camera is set"
    else:
        image_points = {
            p["name"]: p["image_point"]
            for p in db_helper.get_calibration_points(camera_id, conn)
            if p["name"] is not None
        }
        reference_points = {
            p["name"]: p["image_point"]
            for p in db_helper.get_calibration_points(reference_camera_id,
                                                      conn)
            if p["name"] is not None
        }
        shared_names = [n for n in image_points if n in reference_points]

        if len(shared_names) < MIN_HOMOGRAPHY_POINTS:
            error = f"At least {MIN_HOMOGRAPHY_POINTS} points shared with reference camera {reference.name} are required, got {len(shared_names)}"
        else:
            try:
                homography = camera_utilities.create_homography(
                    [image_points[n] for n in shared_names], reference,
                    [reference_points[n] for n in shared_names])
            except (camera_utilities.CalibrationError, cv2.error) as e:
                logger.warning(f"Homography failed for {camera_id=}: {e}")
                error = str(e)

    db_helper.set_camera_homography(conn, camera_id, homography)
    return error


def _recalibrate_camera(conn: sqlite3.Connection,
                        camera_id: str) -> Optional[str]:
    """Recompute and store the calibration of a camera from its stored calibration points, using its
    calibration method. Cameras that use it as a reference are recomputed too.

    Args:
        conn (sqlite3.Connection): The connection (transaction) to read and write through
        camera_id (str): The camera to recalibrate

    Returns:
        Optional[str]: None, or the reason the camera could not be calibrated.
    """
    method, reference_camera_id = conn.execute(
        "SELECT calibration_method, reference_camera_id FROM Cameras WHERE camera_id = ?",
        [camera_id]).fetchone()

    if method == camera_utilities.CalibrationMethod.HOMOGRAPHY:
        error = _compute_homography(conn, camera_id, reference_camera_id)
    else:
        error = _compute_full_calibration(conn, camera_id)

        # Homographies map into this camera's undistorted image, so they depend on its calibration
        dependents = conn.execute(
            "SELECT camera_id FROM Cameras WHERE reference_camera_id = ?",
            [camera_id]).fetchall()
        for (dependent_id, ) in dependents:
            _compute_homography(conn, dependent_id, camera_id)

    logger.info(f"Camera calibration updated for {camera_id=}: {error=}")
    return error


def _set_calibration_method(conn: sqlite3.Connection, camera_id: str,
                            method: str,
                            reference_camera_id: Optional[str]
                            ) -> Optional[str]:
    """Validate and store the calibration method of a camera.

    Returns:
        Optional[str]: None, or an error message if the method is invalid.
    """
    try:
        method = camera_utilities.CalibrationMethod(method)
    except ValueError:
        return f"Unknown calibration_method {method}"

    if method == camera_utilities.CalibrationMethod.FULL:
        conn.execute(
            "UPDATE Cameras SET calibration_method = ?, reference_camera_id = NULL, homography = NULL WHERE camera_id = ?",
            [method.value, camera_id])
        return None

    if reference_camera_id is None:
        return "reference_camera_id is required for a homography calibration"
    if reference_camera_id == camera_id:
        return "A camera cannot be its own reference camera"

    setup_id, = conn.execute(
        "SELECT setup_id FROM Cameras WHERE camera_id = ?",
        [camera_id]).fetchone()
    reference = conn.execute(
        "SELECT setup_id, calibration_method FROM Cameras WHERE camera_id = ?",
        [reference_camera_id]).fetchone()
    if reference is None or reference[0] != setup_id:
        return "The reference camera must be in the same camera setup"
    if reference[1] != camera_utilities.CalibrationMethod.FULL:
        return "The reference camera must use a full calibration"

    dependent = conn.execute(
        "SELECT camera_name FROM Cameras WHERE reference_camera_id = ?",
        [camera_id]).fetchone()
    if dependent is not None:
        return f"Camera {dependent[0]} uses this camera as its reference, so it must use a full calibration"

    conn.execute(
        "UPDATE Cameras SET calibration_method = ?, reference_camera_id = ? WHERE camera_id = ?",
        [method.value, reference_camera_id, camera_id])
    return None


def _is_coordinate(value, length: int) -> bool:
    return (isinstance(value, (list, tuple)) and len(value) == length and all(
        isinstance(v, (int,
                       float)) and not isinstance(v, bool) and math.isfinite(v)
        for v in value))


def _parse_calibration_points(
        raw_points) -> Tuple[Optional[List[Dict]], Optional[str]]:
    """Validate the calibration points of a request and fill in the world points of named points.

    Returns:
        Tuple[Optional[List[Dict]], Optional[str]]: The points and None, or None and an error message.
    """
    if not isinstance(raw_points, list):
        return None, "points must be a list"

    points = []
    names = set()
    for raw_point in raw_points:
        if not isinstance(raw_point, dict):
            return None, "each point must be an object"

        name = raw_point.get("name", None)
        image_point = raw_point.get("image_point", None)
        if not _is_coordinate(image_point, 2):
            return None, f"image_point must be [x, y] for point {name}"

        if name is not None:
            if name not in SHEET_COORDINATES:
                return None, f"Unknown point name {name}"
            if name in names:
                return None, f"Duplicate point name {name}"
            names.add(name)
            world_point = list(SHEET_COORDINATES[name])
        else:
            world_point = raw_point.get("world_point", None)
            if not _is_coordinate(world_point, 3):
                return None, "world_point must be [x, y, z] for unnamed points"

        points.append({
            "name": name,
            "image_point": image_point,
            "world_point": world_point
        })

    return points, None


@bp.route("/calibration_points", methods=["GET", "PUT"])
def calibration_points():
    if request.method == "GET":
        camera_id = request.args.get("camera_id", None)
        raw_points = None
    else:
        data = request.get_json()
        camera_id = data.get("camera_id", None)
        raw_points = data.get("points", None)
        calibration_method = data.get("calibration_method", None)
        reference_camera_id = data.get("reference_camera_id", None)

    logger.info(
        f"Processing calibration_points {request.method} request: {camera_id=}"
    )

    if camera_id is None:
        return jsonify({"error": "camera_id is required"}), 400

    db_camera = query_db("SELECT camera_id FROM Cameras WHERE camera_id = ?",
                         [camera_id],
                         one=True)
    if db_camera is None:
        return jsonify({"error": "camera_id not found"}), 404

    if request.method == "GET":
        return jsonify({
            "camera_id": camera_id,
            "points": db_helper.get_calibration_points(camera_id)
        })

    points, error = _parse_calibration_points(raw_points)
    if error is not None:
        return jsonify({"error": error}), 400

    # The calibration always matches the stored points, so redo it whenever they change
    with db_transaction() as conn:
        if calibration_method is not None:
            error = _set_calibration_method(conn, camera_id,
                                            calibration_method,
                                            reference_camera_id)
            if error is not None:
                conn.rollback()
                return jsonify({"error": error}), 400

        db_helper.replace_calibration_points(conn, camera_id, points)
        calibration_error = _recalibrate_camera(conn, camera_id)
        stored_points = db_helper.get_calibration_points(camera_id, conn)
        camera = db_helper.get_camera_from_db(camera_id, conn)
        reference_camera_id, = conn.execute(
            "SELECT reference_camera_id FROM Cameras WHERE camera_id = ?",
            [camera_id]).fetchone()

    return jsonify({
        "camera_id": camera_id,
        "points": stored_points,
        "calibration_error": calibration_error,
        **_camera_calibration_json(camera, reference_camera_id),
    })


@bp.route("/image_to_sheet_coordinates", methods=["POST"])
def image_to_sheet_coordinates():
    logger.info(f"Processing image_to_sheet_coordinates request.")
    camera_id = request.json.get("camera_id", None)
    image_points = request.json.get("image_points", None)

    if camera_id is None or image_points is None:
        return jsonify({"error":
                        "camera_id and image_points are required"}), 400

    camera = db_helper.get_camera_from_db(camera_id)
    if camera is None:
        return jsonify({"error": "camera_id not found"}), 400

    if len(image_points) != 2:
        return jsonify(
            {"error": "image_points must be a list of 2 coordinates"}), 400

    try:
        sheet_coords = camera_utilities.image_to_world_coordinates(
            camera, np.array(image_points, dtype="float32")).tolist()
    except camera_utilities.CalibrationError as e:
        return jsonify({"error": str(e)}), 400

    return jsonify(sheet_coords[0])


@bp.route("/calibration_coordinates", methods=["GET"])
def sheet_coordinates():
    logger.info(f"Processing calibration_coordinates request.")
    return jsonify(SHEET_COORDINATES)


@bp.route("/video_frame", methods=["GET"])
async def get_video_frame():
    video_url = request.args.get("video_url", None)
    timestamp = request.args.get("timestamp", None)

    logger.info(
        f"Processing video_frame GET request: {video_url=}, {timestamp=}")

    if video_url is None or timestamp is None:
        return jsonify({"error": "video_url and timestamp are required"}), 400

    timestamp = int(timestamp)
    frame = None
    with tempfile.TemporaryDirectory() as temp_dir:
        file_path = os.path.join(temp_dir, "my_output.mp4")

        await async_yt_dlp.download_video(video_url,
                                          file_path,
                                          start_time=timestamp,
                                          end_time=timestamp + 10)
        video = shot_tracker.CurlingVideo(video_path=file_path)

        for f_num, f in video.frame_generator():
            frame = f
            break

    if frame is None:
        return jsonify({"error": "Failed to retrieve frame from URL."}), 400

    success, buffer = cv2.imencode('.png', frame)

    if success:
        b64_frame = base64.b64encode(buffer).decode('utf-8')
        return jsonify({"frame": b64_frame})

    else:
        return jsonify({"error": "Failed to encode frame in base64"}), 400
