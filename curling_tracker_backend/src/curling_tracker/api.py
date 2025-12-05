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
    camera = curling_camera.create_camera(
        data['image_points'],
        data['world_points'],
        data['image_shape'])

    return jsonify({"message": "Data received successfully!"})

@bp.route('/sheet_coordinates', methods=['GET'])
def sheet_coordinates():
    print(SHEET_COORDINATES)
    return jsonify(SHEET_COORDINATES)
