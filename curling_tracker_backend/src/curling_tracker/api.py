from flask import (
    Blueprint, request, jsonify
)

from curling_tracker.db import query_db

import curling_tracker.curling_camera as curling_camera
from curling_tracker.sheet_coordinates import SHEET_COORDINATES

bp = Blueprint('api', __name__, url_prefix='/api')

@bp.route("/")
def home():
    return "Hello, World!"

@bp.route('/camera_calibration', methods=['POST'])
def camera_calibration():
    data = request.get_json()

    print("Calibrating camera with data:", data)

    processed_image_points = []
    processed_world_points = []
    for k in data['image_points'].keys():
        if k in data['world_points']:
            processed_world_points.append(tuple(data['world_points'][k]))
            processed_image_points.append(tuple(data['image_points'][k]))

    camera = curling_camera.create_camera(
        processed_image_points,
        processed_world_points,
        data['image_shape'])
    
    return_data = {"camera_matrix": camera.camera_matrix.tolist(),
                   "distortion_coefficients": camera.distortion_coefficients.tolist(),
                   "rotation_vectors": camera.rotation_vectors.tolist(),
                   "translation_vectors": camera.translation_vectors.tolist()}

    print("Calibration result:", return_data)
    return jsonify(return_data)

@bp.route('/sheet_coordinates', methods=['GET'])
def sheet_coordinates():
    return jsonify(SHEET_COORDINATES)
