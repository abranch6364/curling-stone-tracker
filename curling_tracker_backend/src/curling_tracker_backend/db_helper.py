from curling_tracker_backend.db import query_db
import curling_tracker_backend.curling_shot_tracker as shot_tracker


async def get_setup_from_db(setup_id: str):
    db_setup = await query_db(
        "SELECT setup_name FROM CameraSetups WHERE setup_id = ?", [setup_id],
        one=True)

    db_cameras = await query_db(
        "SELECT corner1, corner2, camera_matrix, distortion_coefficients, rotation_vectors, translation_vectors FROM Cameras WHERE setup_id = ?",
        [setup_id],
    )

    cameras = []
    for c in db_cameras:
        camera = shot_tracker.Camera(c[0], c[1], c[2], c[3], c[4], c[5])
        cameras.append(camera)

    return shot_tracker.CameraSetup(setup_id, db_setup[0], cameras)
