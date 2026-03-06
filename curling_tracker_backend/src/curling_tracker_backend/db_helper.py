from curling_tracker_backend.db import query_db
import curling_tracker_backend.util.curling_shot_tracker as shot_tracker


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
        camera = shot_tracker.Camera(c[0], c[1], c[2], c[3], c[4], c[5], c[6],
                                     shot_tracker.CameraType(c[7]))
        cameras.append(camera)

    return shot_tracker.CameraSetup(setup_id, db_setup[0], cameras)


def get_camera_from_db(camera_id: str):
    db_camera = query_db(
        "SELECT camera_name, corner1, corner2, camera_matrix, distortion_coefficients, rotation_vectors, translation_vectors, camera_type FROM Cameras WHERE camera_id = ?",
        [camera_id],
        one=True,
    )

    return shot_tracker.Camera(db_camera[0], db_camera[1], db_camera[2],
                               db_camera[3], db_camera[4], db_camera[5],
                               db_camera[6],
                               shot_tracker.CameraType(db_camera[7]))
