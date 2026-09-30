from curling_tracker_backend.db import query_db
import curling_tracker_backend.util.curling_shot_tracker as shot_tracker
import curling_tracker_backend.util.camera_utilities as camera_utilities
import sqlite3
import uuid
from typing import Dict, List, Optional


def get_setup_from_db(setup_id: str):
    db_setup = query_db(
        "SELECT setup_name FROM CameraSetups WHERE setup_id = ?", [setup_id],
        one=True)

    db_cameras = query_db(
        "SELECT camera_name, corner1, corner2, camera_matrix, distortion_coefficients, rotation_vectors, translation_vectors, camera_type FROM Cameras WHERE setup_id = ?",
        [setup_id],
    )

    cameras = []
    for c in db_cameras:
        camera = camera_utilities.Camera(c[0], c[1], c[2], c[3], c[4],
                                         c[5], c[6],
                                         camera_utilities.CameraType(c[7]))
        cameras.append(camera)

    return shot_tracker.CameraSetup(setup_id, db_setup[0], cameras)


def get_camera_from_db(camera_id: str):
    db_camera = query_db(
        "SELECT camera_name, corner1, corner2, camera_matrix, distortion_coefficients, rotation_vectors, translation_vectors, camera_type FROM Cameras WHERE camera_id = ?",
        [camera_id],
        one=True,
    )

    if db_camera is None:
        return None

    return camera_utilities.Camera(db_camera[0], db_camera[1], db_camera[2],
                                   db_camera[3], db_camera[4], db_camera[5],
                                   db_camera[6],
                                   camera_utilities.CameraType(db_camera[7]))


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
