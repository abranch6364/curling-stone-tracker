from flask import (
    Blueprint, current_app, request, jsonify, redirect, flash, app, url_for
)

from curling_tracker_backend.db import query_db

import uuid
import curling_tracker_backend.curling_camera as curling_camera
from curling_tracker_backend.sheet_coordinates import SHEET_COORDINATES
from werkzeug.utils import secure_filename
import os
import cv2 as cv

from curling_tracker_backend.util.curling_shot_tracker import StoneDetector, image_to_sheet_coordinates, undistort_image

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
    return_data = {}
    if request.method == 'GET':
        camera_id = request.args.get('camera_id', None)
        if camera_id is None:
            return jsonify({"error": "camera_id is required"}), 400
        camera = query_db('SELECT * FROM Cameras WHERE camera_id = ?', [camera_id], one=True)
        
        if camera is None:
            print("Camera not found for camera_id:", camera_id)
            return jsonify({"error": "Camera not found"}), 404
        return_data = {
            "camera_id": camera[0],
            "camera_matrix": camera[1].tolist(),
            "distortion_coefficients": camera[2].tolist(),
            "rotation_vectors": camera[3].tolist(),
            "translation_vectors": camera[4].tolist()
        }

    elif request.method == 'POST':
        data = request.get_json()

        processed_image_points = []
        processed_world_points = []

        image_points = request.json.get('image_points', None)
        world_points = request.json.get('world_points', None)
        image_shape = request.json.get('image_shape', None)
        image_shape = image_shape[::-1]
        print("image points:", image_points)
        print("world_points:", world_points)
        print("image_shape:", image_shape)

        if image_points is None or world_points is None or image_shape is None:
            return jsonify({"error": "image_points, world_points, and image_shape are required"}), 400
        
        for k in data['image_points'].keys():
            if k in data['world_points']:
                processed_world_points.append(tuple(data['world_points'][k]))
                processed_image_points.append(tuple(data['image_points'][k]))

        camera = curling_camera.create_camera(
            processed_image_points,
            processed_world_points,
            image_shape)

        camera_id = request.json.get('camera_id', None)

        if camera_id is None or query_db('SELECT * FROM Cameras WHERE camera_id = ?', [camera_id], one=True) is None:
            camera_id = str(uuid.uuid4())
            print("Storing calibration for camera_id:", camera_id)
            print(query_db('INSERT INTO Cameras (camera_id, camera_matrix, distortion_coefficients, rotation_vectors, translation_vectors) VALUES (?, ?, ?, ?, ?)',
                    args=[camera_id,
                            camera.camera_matrix,
                            camera.distortion_coefficients,
                            camera.rotation_vectors,
                            camera.translation_vectors]))
        else:
            query_db('UPDATE Cameras SET camera_matrix = ?, distortion_coefficients = ?, rotation_vectors = ?, translation_vectors = ? WHERE camera_id = ?',
                    args=[camera.camera_matrix,
                            camera.distortion_coefficients,
                            camera.rotation_vectors,
                            camera.translation_vectors,
                            camera_id])

        return_data = {"camera_id": camera_id,
                        "camera_matrix": camera.camera_matrix.tolist(),
                        "distortion_coefficients": camera.distortion_coefficients.tolist(),
                        "rotation_vectors": camera.rotation_vectors.tolist(),
                        "translation_vectors": camera.translation_vectors.tolist()}

    return jsonify(return_data)

@bp.route('/detect_stones', methods=['POST'])
def detect_stones():
    if request.method == 'POST':
        if 'file' not in request.files:
            return jsonify({"error": "No image in request"}), 400
        file = request.files['file']
        if file and os.path.splitext(file.filename)[1] in ['.jpg', '.jpeg', '.png']:
            if os.path.exists(current_app.config['UPLOAD_FOLDER']) == False:
                os.makedirs(current_app.config['UPLOAD_FOLDER'])

            filename = secure_filename(file.filename)
            full_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            file.save(full_path)
        else:
            return jsonify({"error": "Invalid file format"}), 400

        #Get camera calibration data from database
        camera_id = request.form.get('camera_id', None)
        if camera_id is None:
            return jsonify({"error": "camera_id is required"}), 400
        camera = query_db('SELECT * FROM Cameras WHERE camera_id = ?', [camera_id], one=True)
        if camera is None:
            return jsonify({"error": "Camera not found"}), 404

        camera = curling_camera.Camera(camera['camera_matrix'], 
                                       camera['distortion_coefficients'], 
                                       camera['rotation_vectors'], 
                                       camera['translation_vectors'])

        #load and undistort image
        image = cv.imread(full_path)

        #Detect stones
        stone_detector = StoneDetector(os.path.join(current_app.root_path, 'model/top_down_stone_detector.pt'))
        stones = stone_detector.detect_stones(image)   


        #Format results to return
        ret_stones = []

        if len(stones['green']) != 0:
            green_sheet_coords = image_to_sheet_coordinates(camera, stones['green'])

            for image_coords, sheet_coords in zip(stones['green'], green_sheet_coords):
                ret_stones.append({"color": "green", "image_coordinates": image_coords.tolist(), "sheet_coordinates": sheet_coords.tolist()})

        if len(stones['yellow']) != 0:
            yellow_sheet_coords = image_to_sheet_coordinates(camera, stones['yellow'])

            for image_coords, sheet_coords in zip(stones['yellow'], yellow_sheet_coords):
                ret_stones.append({"color": "yellow", "image_coordinates": image_coords.tolist(), "sheet_coordinates": sheet_coords.tolist()})

        #Clean up
        if os.path.exists(full_path):
            os.remove(full_path)

        return jsonify({"stones": ret_stones})

@bp.route('/sheet_coordinates', methods=['GET'])
def sheet_coordinates():
    return jsonify(SHEET_COORDINATES)
