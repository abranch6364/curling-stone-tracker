from flask import (
    Blueprint,
    request,
    jsonify,
)

import uuid
import numpy as np
import logging
import curling_tracker_backend.db_helper as db_helper
from curling_tracker_backend.db import query_db
import curling_tracker_backend.util.curling_shot_tracker as shot_tracker
from curling_tracker_backend.util.sheet_coordinates import SHEET_COORDINATES

logger = logging.getLogger(__name__)
bp = Blueprint("calibration_api", __name__, url_prefix="/api")


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

        cameras = query_db(
            "SELECT camera_id, camera_name, camera_type, corner1, corner2, camera_matrix, distortion_coefficients, rotation_vectors, translation_vectors FROM Cameras WHERE setup_id = ?",
            [setup_id],
        )
        camera_list = []
        for camera in cameras:
            camera_list.append({
                "camera_id":
                camera[0],
                "camera_name":
                camera[1],
                "camera_type":
                camera[2],
                "corner1":
                camera[3].tolist(),
                "corner2":
                camera[4].tolist(),
                "camera_matrix":
                (camera[5].tolist() if camera[5] is not None else None),
                "distortion_coefficients":
                (camera[6].tolist() if camera[6] is not None else None),
                "rotation_vectors":
                (camera[7].tolist() if camera[7] is not None else None),
                "translation_vectors":
                (camera[8].tolist() if camera[8] is not None else None),
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

        # Replace existing cameras for this setup
        query_db("DELETE FROM Cameras WHERE setup_id = ?", [setup_id])
        for camera in data.get("cameras", []):
            camera_id = str(uuid.uuid4())
            camera_name = camera.get("camera_name", "Unnamed Camera")
            corner1 = np.array(camera.get("corner1", [0, 0]))
            corner2 = np.array(camera.get("corner2", [0, 0]))
            camera_type = camera.get("camera_type", "unknown")
            query_db(
                "INSERT INTO Cameras (camera_id, setup_id, camera_name, camera_type, corner1, corner2) VALUES (?, ?, ?, ?, ?, ?)",
                [
                    camera_id, setup_id, camera_name, camera_type, corner1,
                    corner2
                ],
            )
        return jsonify({"setup_id": setup_id})


@bp.route("/camera_calibration", methods=["POST"])
def camera_calibration():
    return_data = {}
    if request.method == "POST":
        data = request.get_json()

        camera_id = request.json.get("camera_id", None)
        image_points = request.json.get("image_points", None)
        world_points = request.json.get("world_points", None)
        image_shape = request.json.get("image_shape", None)

        logger.info(
            f"Processing camera_calibration POST request: {camera_id=}")

        if (image_points is None or world_points is None or image_shape is None
                or camera_id is None):
            return (
                jsonify({
                    "error":
                    "camera_id, image_points, world_points, and image_shape are required"
                }),
                400,
            )

        processed_image_points = []
        processed_world_points = []
        for k in data["image_points"].keys():
            if k in data["world_points"]:
                processed_world_points.append(tuple(data["world_points"][k]))
                processed_image_points.append(tuple(data["image_points"][k]))

        db_camera = query_db(
            "SELECT camera_id FROM Cameras WHERE camera_id = ?", [camera_id],
            one=True)
        if (db_camera is None):
            return jsonify({"error": "camera_id not found"}), 400

        logger.info(f"{image_shape=}")
        camera_mat, distortion, rotation_vecs, translation_vecs = shot_tracker.create_camera(
            processed_image_points, processed_world_points, image_shape)

        query_db(
            "UPDATE Cameras SET camera_matrix = ?, distortion_coefficients = ?, rotation_vectors = ?, translation_vectors = ? WHERE camera_id = ?",
            args=[
                camera_mat,
                distortion,
                rotation_vecs,
                translation_vecs,
                camera_id,
            ],
        )

        return_data = {
            "camera_id": camera_id,
            "camera_matrix": camera_mat.tolist(),
            "distortion_coefficients": distortion.tolist(),
            "rotation_vectors": rotation_vecs.tolist(),
            "translation_vectors": translation_vecs.tolist(),
        }

    return jsonify(return_data)


@bp.route("/image_to_sheet_coordinates", methods=["POST"])
def image_to_sheet_coordinates():
    logger.info(f"Processing image_to_sheet_coordinates request.")
    camera_id = request.json.get("camera_id", None)
    image_points = request.json.get("image_points", None)

    if camera_id is None or image_points is None:
        return jsonify({"error":
                        "camera_id and image_points are required"}), 400

    camera = db_helper.get_camera_from_db(camera_id)

    if len(image_points) != 2:
        return jsonify(
            {"error": "image_points must be a list of 2 coordinates"}), 400

    sheet_coords = shot_tracker.image_to_sheet_coordinates(
        camera, np.array(image_points, dtype="float32")).tolist()

    return jsonify(sheet_coords[0])


@bp.route("/calibration_coordinates", methods=["GET"])
def sheet_coordinates():
    logger.info(f"Processing calibration_coordinates request.")
    return jsonify(SHEET_COORDINATES)
