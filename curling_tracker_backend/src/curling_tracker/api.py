from flask import (
    Blueprint, request, jsonify
)

from curling_tracker.db import query_db

import uuid
import curling_tracker.curling_camera as curling_camera
from curling_tracker.sheet_coordinates import SHEET_COORDINATES

bp = Blueprint('api', __name__, url_prefix='/api')

@bp.route("/")
def home():
    return "Hello, World!"

@bp.route('/camera_ids', methods=['GET'])
def camera_ids():
    if request.method == 'GET':
        cameras = query_db('SELECT camera_id FROM Cameras')
        print("getting camera_id:", cameras)

        return jsonify([camera[0] for camera in cameras])
    else:
        return jsonify({"error": "Method not allowed"}), 405

@bp.route('/camera_calibration', methods=['POST', 'GET'])
def camera_calibration():
    if request.method == 'GET':
        camera_id = request.args.get('camera_id', None)
        if camera_id is None:
            return jsonify({"error": "camera_id is required"}), 400
        camera = query_db('SELECT * FROM Cameras WHERE camera_id = ?', [camera_id], one=True)
        if camera is None:
            return jsonify({"error": "Camera not found"}), 404

        return_data = {
            "camera_id": camera[0],
            "camera_matrix": camera[1],
            "distortion_coefficients": camera[2],
            "rotation_vectors": camera[3],
            "translation_vectors": camera[4]
        }

    elif request.method == 'POST':
        data = request.get_json()

        processed_image_points = []
        processed_world_points = []

        image_points = request.json.get('image_points', None)
        world_points = request.json.get('world_points', None)
        image_shape = request.json.get('image_shape', None)

        if image_points is None or world_points is None or image_shape is None:
            return jsonify({"error": "image_points, world_points, and image_shape are required"}), 400
        
        for k in data['image_points'].keys():
            if k in data['world_points']:
                processed_world_points.append(tuple(data['world_points'][k]))
                processed_image_points.append(tuple(data['image_points'][k]))

        camera = curling_camera.create_camera(
            processed_image_points,
            processed_world_points,
            data['image_shape'])

        camera_id = request.json.get('camera_id', None)

        if camera_id is None or query_db('SELECT * FROM Cameras WHERE camera_id = ?', [camera_id], one=True) is None:
            camera_id = str(uuid.uuid4())
            print("Storing calibration for camera_id:", camera_id)
            print(query_db('INSERT INTO Cameras (camera_id, camera_matrix, distortion_coefficients, rotation_vectors, translation_vectors) VALUES (?, ?, ?, ?, ?)',
                    args=[camera_id,
                            camera.camera_matrix.dumps(),
                            camera.distortion_coefficients.dumps(),
                            camera.rotation_vectors.dumps(),
                            camera.translation_vectors.dumps()]))
        else:
            query_db('UPDATE Cameras SET camera_matrix = ?, distortion_coefficients = ?, rotation_vectors = ?, translation_vectors = ? WHERE camera_id = ?',
                    args=[camera.camera_matrix.dumps(),
                            camera.distortion_coefficients.dumps(),
                            camera.rotation_vectors.dumps(),
                            camera.translation_vectors.dumps(),
                            camera_id])

        return_data = {"camera_id": camera_id,
                        "camera_matrix": camera.camera_matrix.tolist(),
                        "distortion_coefficients": camera.distortion_coefficients.tolist(),
                        "rotation_vectors": camera.rotation_vectors.tolist(),
                        "translation_vectors": camera.translation_vectors.tolist()}

    return jsonify(return_data)

@bp.route('/sheet_coordinates', methods=['GET'])
def sheet_coordinates():
    return jsonify(SHEET_COORDINATES)
