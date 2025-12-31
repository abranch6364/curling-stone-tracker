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
import numpy as np
from curling_tracker_backend.util.curling_shot_tracker import StoneDetector, image_to_sheet_coordinates, undistort_image
import math

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

@bp.route('/camera_setup_headers', methods=['GET'])
def camera_setup_headers():
    if request.method == 'GET':
        camera_setups = query_db('SELECT setup_id, setup_name FROM CameraSetups')

        return jsonify([{"setup_id": setup[0], "setup_name": setup[1]} for setup in camera_setups])
    else:
        return jsonify({"error": "Method not allowed"}), 405

@bp.route('/camera_setup', methods=['POST', 'GET'])
def camera_setup():
    if request.method == 'GET':
        setup_id = request.args.get('setup_id', None)
        if setup_id is None:
            return jsonify({"error": "setup_id is required"}), 400
        setup = query_db('SELECT * FROM CameraSetups WHERE setup_id = ?', [setup_id], one=True)
        if setup is None:
            return jsonify({"error": "Camera Setup not found"}), 404
        
        cameras = query_db('SELECT camera_id, camera_name, corner1, corner2, camera_matrix, distortion_coefficients, rotation_vectors, translation_vectors FROM Cameras WHERE setup_id = ?', [setup_id])
        camera_list = []
        for camera in cameras:
            camera_list.append({
                "camera_id": camera[0],
                "camera_name": camera[1],
                "corner1": camera[2].tolist(),
                "corner2": camera[3].tolist(),
                "camera_matrix": camera[4].tolist() if camera[4] is not None else None,
                "distortion_coefficients": camera[5].tolist() if camera[5] is not None else None,
                "rotation_vectors": camera[6].tolist() if camera[6] is not None else None,
                "translation_vectors": camera[7].tolist() if camera[7] is not None else None,
            })
        return jsonify({
            "setup_id": setup[0],
            "setup_name": setup[1],
            "cameras": camera_list
        })

    elif request.method == 'POST':
        data = request.get_json()
        setup_name = data.get('setup_name', "Unnamed Setup")
        setup_id = data.get('setup_id', None)

        if setup_id is None:
            setup_id = str(uuid.uuid4())
            query_db('INSERT INTO CameraSetups (setup_id, setup_name) VALUES (?, ?)', [setup_id, setup_name])
        else:
            query_db('UPDATE CameraSetups SET setup_name = ? WHERE setup_id = ?', [setup_name, setup_id])

        #Replace existing cameras for this setup
        query_db('DELETE FROM Cameras WHERE setup_id = ?', [setup_id])
        for camera in data.get('cameras', []):
            camera_id = str(uuid.uuid4())
            camera_name = camera.get('camera_name', 'Unnamed Camera')
            corner1 = np.array(camera.get('corner1', [0,0]))
            corner2 = np.array(camera.get('corner2', [0,0]))
            query_db('INSERT INTO Cameras (camera_id, setup_id, camera_name, corner1, corner2) VALUES (?, ?, ?, ?, ?)', [camera_id, setup_id, camera_name, corner1, corner2])
        return jsonify({"setup_id": setup_id})


@bp.route('/camera_calibration', methods=['POST'])
def camera_calibration():
    return_data = {}
    if request.method == 'POST':
        data = request.get_json()

        processed_image_points = []
        processed_world_points = []

        camera_id = request.json.get('camera_id', None)
        image_points = request.json.get('image_points', None)
        world_points = request.json.get('world_points', None)
        image_shape = request.json.get('image_shape', None)
        print("image points:", image_points, flush=True)
        print("world_points:", world_points, flush=True)
        print("image_shape:", image_shape, flush=True)

        if image_points is None or world_points is None or image_shape is None or camera_id is None:
            return jsonify({"error": "camera_id, image_points, world_points, and image_shape are required"}), 400
        
        for k in data['image_points'].keys():
            if k in data['world_points']:
                processed_world_points.append(tuple(data['world_points'][k]))
                processed_image_points.append(tuple(data['image_points'][k]))

        camera = curling_camera.create_camera(
            processed_image_points,
            processed_world_points,
            image_shape)

        if query_db('SELECT * FROM Cameras WHERE camera_id = ?', [camera_id], one=True) is None:
            return jsonify({"error": "camera_id not found"}), 400

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

        setup_id = request.form.get('setup_id', None)
        if setup_id is None:
            return jsonify({"error": "setup_id is required"}), 400


        if file and os.path.splitext(file.filename)[1] in ['.jpg', '.jpeg', '.png']:
            if os.path.exists(current_app.config['UPLOAD_FOLDER']) == False:
                os.makedirs(current_app.config['UPLOAD_FOLDER'])

            filename = secure_filename(file.filename)
            full_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            file.save(full_path)
        else:
            return jsonify({"error": "Invalid file format"}), 400

        #Get cameras from database
        cameras = query_db('SELECT corner1, corner2, camera_matrix, distortion_coefficients, rotation_vectors, translation_vectors FROM Cameras WHERE setup_id = ?', [setup_id])
        
        #Load image
        image = cv.imread(full_path)

        #Format results to return
        ret_stones = []
        for camera in cameras:
            camera_obj = curling_camera.Camera(camera[2], 
                                               camera[3], 
                                               camera[4], 
                                               camera[5])
            corner1 = camera[0]
            corner2 = camera[1]
            x = min(corner1[0], corner2[0])
            y = min(corner1[1], corner2[1])
            width = abs(corner1[0] - corner2[0])
            height = abs(corner1[1] - corner2[1])

            #Split image for this camera
            split_image = image[y:(y+height), x:(x+width)]

            #Detect stones
            stone_detector = StoneDetector(os.path.join(current_app.root_path, 'model/top_down_stone_detector.pt'))
            stones = stone_detector.detect_stones(split_image)   

            #Add stones to list
            if len(stones['green']) != 0:
                green_sheet_coords = image_to_sheet_coordinates(camera_obj, stones['green'])

                for image_coords, sheet_coords in zip(stones['green'], green_sheet_coords):
                    ret_stones.append({"color": "green", "image_coordinates": image_coords.tolist(), "sheet_coordinates": sheet_coords.tolist()})

            if len(stones['yellow']) != 0:
                yellow_sheet_coords = image_to_sheet_coordinates(camera_obj, stones['yellow'])

                for image_coords, sheet_coords in zip(stones['yellow'], yellow_sheet_coords):
                    ret_stones.append({"color": "yellow", "image_coordinates": image_coords.tolist(), "sheet_coordinates": sheet_coords.tolist()})

        #Clean up
        if os.path.exists(full_path):
            os.remove(full_path)

        return jsonify({"stones": ret_stones})

@bp.route('/sheet_coordinates', methods=['GET'])
def sheet_coordinates():
    return jsonify(SHEET_COORDINATES)
