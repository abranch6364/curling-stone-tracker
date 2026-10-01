from curling_tracker_backend.db import query_db
import curling_tracker_backend.util.curling_shot_tracker as shot_tracker
import curling_tracker_backend.util.camera_utilities as camera_utilities
import sqlite3
import numpy as np
import uuid
from typing import Dict, List, Optional, Tuple


CAMERA_COLUMNS = "camera_id, camera_name, corner1, corner2, camera_matrix, distortion_coefficients, rotation_vectors, translation_vectors, camera_type, calibration_method, reference_camera_id, homography"


def camera_from_row(row) -> Tuple[camera_utilities.Camera, Optional[str]]:
    """Build a camera from a row selected with CAMERA_COLUMNS.

    Returns:
        Tuple[camera_utilities.Camera, Optional[str]]: The camera (without its reference camera attached)
            and the id of its reference camera.
    """
    camera = camera_utilities.Camera(
        row[1],
        row[2],
        row[3],
        row[4],
        row[5],
        row[6],
        row[7],
        camera_utilities.CameraType(row[8]),
        calibration_method=camera_utilities.CalibrationMethod(row[9]),
        homography=row[11],
    )
    return camera, row[10]


def get_setup_from_db(setup_id: str):
    db_setup = query_db(
        "SELECT setup_name FROM CameraSetups WHERE setup_id = ?", [setup_id],
        one=True)

    db_cameras = query_db(
        f"SELECT {CAMERA_COLUMNS} FROM Cameras WHERE setup_id = ?",
        [setup_id],
    )

    cameras_by_id = {}
    reference_ids = {}
    for row in db_cameras:
        camera, reference_id = camera_from_row(row)
        cameras_by_id[row[0]] = camera
        reference_ids[row[0]] = reference_id

    # Reference cameras are always in the same setup
    for camera_id, camera in cameras_by_id.items():
        camera.reference_camera = cameras_by_id.get(reference_ids[camera_id])

    return shot_tracker.CameraSetup(setup_id, db_setup[0],
                                    list(cameras_by_id.values()))


def get_camera_from_db(camera_id: str,
                       conn: Optional[sqlite3.Connection] = None):
    """Get a camera, with its reference camera attached if it has one.

    Args:
        camera_id (str): The camera to get
        conn (Optional[sqlite3.Connection]): An open connection to read through, so uncommitted
            changes in a transaction are visible. Defaults to None which opens a new connection.
    """
    query = f"SELECT {CAMERA_COLUMNS} FROM Cameras WHERE camera_id = ?"
    if conn is None:
        db_camera = query_db(query, [camera_id], one=True)
    else:
        db_camera = conn.execute(query, [camera_id]).fetchone()

    if db_camera is None:
        return None

    camera, reference_id = camera_from_row(db_camera)
    if reference_id is not None:
        # Reference cameras always use a full calibration, so they have no reference of their own
        camera.reference_camera = get_camera_from_db(reference_id, conn)

    return camera


def _calibration_point_row_to_dict(row) -> Dict:
    return {
        "point_id": row[0],
        "name": row[1],
        "image_point": [row[2], row[3]],
        "world_point": [row[4], row[5], row[6]],
    }


def get_calibration_points(
        camera_id: str,
        conn: Optional[sqlite3.Connection] = None) -> List[Dict]:
    """Get the calibration points stored for a camera.

    Args:
        camera_id (str): The camera to get points for
        conn (Optional[sqlite3.Connection]): An open connection to read through, so uncommitted
            changes in a transaction are visible. Defaults to None which opens a new connection.

    Returns:
        List[Dict]: The points as dicts with point_id, name, image_point and world_point
    """
    query = "SELECT point_id, name, image_x, image_y, world_x, world_y, world_z FROM CalibrationPoints WHERE camera_id = ? ORDER BY rowid"
    if conn is None:
        rows = query_db(query, [camera_id])
    else:
        rows = conn.execute(query, [camera_id]).fetchall()

    return [_calibration_point_row_to_dict(row) for row in rows]


def replace_calibration_points(conn: sqlite3.Connection, camera_id: str,
                               points: List[Dict]):
    """Replace all of the calibration points stored for a camera.

    Args:
        conn (sqlite3.Connection): The connection (transaction) to write through
        camera_id (str): The camera to replace points for
        points (List[Dict]): The new points as dicts with name, image_point and world_point
    """
    conn.execute("DELETE FROM CalibrationPoints WHERE camera_id = ?",
                 [camera_id])
    for point in points:
        conn.execute(
            "INSERT INTO CalibrationPoints (point_id, camera_id, name, image_x, image_y, world_x, world_y, world_z) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [
                str(uuid.uuid4()), camera_id, point["name"],
                *point["image_point"], *point["world_point"]
            ],
        )


def set_camera_calibration(conn: sqlite3.Connection, camera_id: str,
                           camera: Optional[camera_utilities.Camera]):
    """Store the calibration for a camera.

    Args:
        conn (sqlite3.Connection): The connection (transaction) to write through
        camera_id (str): The camera to update
        camera (Optional[camera_utilities.Camera]): The calibrated camera, or None to clear the calibration
    """
    if camera is None:
        args = [None, None, None, None, camera_id]
    else:
        args = [
            camera.camera_matrix, camera.distortion_coefficients,
            camera.rotation_vectors, camera.translation_vectors, camera_id
        ]

    conn.execute(
        "UPDATE Cameras SET camera_matrix = ?, distortion_coefficients = ?, rotation_vectors = ?, translation_vectors = ? WHERE camera_id = ?",
        args,
    )


def set_camera_homography(conn: sqlite3.Connection, camera_id: str,
                          homography: Optional[np.ndarray]):
    """Store the homography of a camera.

    Args:
        conn (sqlite3.Connection): The connection (transaction) to write through
        camera_id (str): The camera to update
        homography (Optional[np.ndarray]): The homography, or None to clear it
    """
    conn.execute("UPDATE Cameras SET homography = ? WHERE camera_id = ?",
                 [homography, camera_id])
