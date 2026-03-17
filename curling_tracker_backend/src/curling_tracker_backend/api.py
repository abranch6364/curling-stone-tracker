from flask import (
    Blueprint,
    current_app,
    request,
    jsonify,
    redirect,
    flash,
    app,
    url_for,
)

import uuid
from werkzeug.utils import secure_filename
import os
import cv2 as cv
import numpy as np
import logging
import hashlib
import curling_tracker_backend.db_helper as db_helper
import curling_tracker_backend.util.async_yt_dlp as async_yt_dlp
from curling_tracker_backend.db import query_db
import curling_tracker_backend.util.curling_shot_tracker as shot_tracker
from curling_tracker_backend.util.sheet_coordinates import SHEET_COORDINATES

logger = logging.getLogger(__name__)
bp = Blueprint("api", __name__, url_prefix="/api")


@bp.route("/video_tracking_headers", methods=["GET"])
def video_tracking_headers():
    logger.info(f"Processing video_tracking_headers request.")

    tracking_headers = query_db(
        "SELECT tracking_id, link, stream_date, start_seconds, duration, percent_complete FROM VideoTracking"
    )

    return jsonify([{
        "tracking_id": header[0],
        "link": header[1],
        "stream_date": header[2],
        "start_seconds": header[3],
        "duration": header[4],
        "percent_complete": header[5]
    } for header in tracking_headers])


@bp.route("/request_video_tracking", methods=["POST"])
async def request_video_tracking():
    url = request.json.get("url", None)
    start_seconds = request.json.get("start_seconds", None)
    duration = request.json.get("duration", None)
    setup_id = request.json.get("setup_id", None)
    include_images = request.json.get("include_images", False)

    logger.info(
        f"Processing video tracking request: {url=} {start_seconds=} {duration=} {setup_id=}"
    )

    if url is None or start_seconds is None or duration is None or setup_id is None:
        return jsonify({
            "error":
            "url, start_seconds, duration, and setup_id is required"
        }), 400

    db_video = query_db(
        "SELECT filename FROM Videos WHERE url = ? AND start_seconds = ? AND duration = ?",
        [url, start_seconds, duration],
        one=True)

    if db_video is not None:
        output_file = os.path.join(
            current_app.config["YOUTUBE_DOWNLOADS_FOLDER"], db_video[0])
        logger.info(f"Using cached video {db_video[0]} for tracking.")
    else:
        logger.info(f"Downloading video for tracking.")
        if not os.path.exists(current_app.config["YOUTUBE_DOWNLOADS_FOLDER"]):
            os.makedirs(current_app.config["YOUTUBE_DOWNLOADS_FOLDER"])

        video_id = str(uuid.uuid4())
        output_file = os.path.join(
            current_app.config["YOUTUBE_DOWNLOADS_FOLDER"], video_id + ".mp4")
        await async_yt_dlp.download_video(url,
                                          output_file,
                                          start_time=start_seconds,
                                          end_time=start_seconds + duration)
        query_db(
            "INSERT INTO Videos (video_id, url, start_seconds, duration, filename) VALUES (?, ?, ?, ?, ?)",
            [video_id, url, start_seconds, duration, video_id + ".mp4"])

        logger.info(f"Inserted video record into database: {video_id=}")

    camera_setup = db_helper.get_setup_from_db(setup_id)

    stone_detectors = shot_tracker.get_stone_detectors(
        os.path.join(current_app.root_path, "model/"))
    video = shot_tracker.CurlingVideo(output_file)

    logger.info(f"Starting video stone tracking...")
    tracking_results = shot_tracker.video_stone_tracker(
        camera_setup, video, stone_detectors, image_save_interval=1.0)

    logger.info(f"Finished video stone tracking.")

    return jsonify(tracking_results.dict_for_json())


@bp.route("/detect_stones", methods=["POST"])
def detect_stones():
    if "file" not in request.files:
        return jsonify({"error": "No image in request"}), 400
    file = request.files["file"]

    setup_id = request.form.get("setup_id", None)
    if setup_id is None:
        return jsonify({"error": "setup_id is required"}), 400

    logger.info(f"Processing detect_stones request: {setup_id=}")

    if file and os.path.splitext(
            file.filename)[1] in [".jpg", ".jpeg", ".png"]:
        if os.path.exists(current_app.config["UPLOAD_FOLDER"]) == False:
            os.makedirs(current_app.config["UPLOAD_FOLDER"])

        filename = secure_filename(file.filename)
        full_path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
        file.save(full_path)
    else:
        return jsonify({"error": "Invalid file format"}), 400

    camera_setup = db_helper.get_setup_from_db(setup_id)

    image = cv.imread(full_path)

    stone_detector = shot_tracker.StoneDetector(
        os.path.join(current_app.root_path,
                     "model/top_down_stone_detector.pt"))

    all_detections = shot_tracker.mosaic_image_detect_stones(
        camera_setup, image, stone_detector)

    stones = []
    for _, detections in all_detections.detections.items():
        for detection in detections:
            stones.append(detection.dict_for_json())

    # Clean up
    if os.path.exists(full_path):
        os.remove(full_path)

    return jsonify({"stones": stones})


@bp.route("/dataset_headers", methods=["GET"])
def dataset_headers():
    logger.info(f"Processing dataset_headers request.")

    datasets = []
    for dataset_name, _ in current_app.config["DATASETS"].items():
        datasets.append({
            "name": dataset_name,
        })

    return jsonify(datasets)


@bp.route("/add_image_to_dataset", methods=["POST"])
def add_to_dataset():

    if "file" not in request.files:
        return jsonify({"message": "No image in request"}), 400
    file = request.files["file"]
    dataset_name = request.form.get("dataset_name", None)

    logger.info(f"Processing add_to_dataset request: {dataset_name=}")

    if dataset_name not in current_app.config["DATASETS"]:
        return jsonify({"message": "Invalid dataset name"}), 400

    if file and os.path.splitext(file.filename)[1] in [".png"]:
        dataset_folder = current_app.config["DATASETS"][dataset_name]["folder"]
        dataset_path = os.path.join(current_app.config["BASE_DATASETS_PATH"],
                                    dataset_folder)
        if not os.path.exists(dataset_path):
            return jsonify({"message":
                            "Dataset does not exist on server"}), 400

        filename = secure_filename(file.filename)
        filename = os.path.splitext(filename)[0] + "_" + str(
            uuid.uuid4()) + os.path.splitext(filename)[1]
        full_path = os.path.join(dataset_path, filename)

        # Calculate hash of uploaded image
        file.seek(0)
        file_content = file.read()
        file_hash = hashlib.sha256(file_content).digest()
        file.seek(0)

        logger.info(f"Calculated file hash: {file_hash}")

        dataset_table = current_app.config["DATASETS"][dataset_name][
            "dataset_table"]

        # Check if file with same hash already exists in dataset
        existing_image = query_db(
            f"SELECT file_path FROM {dataset_table} WHERE file_hash = ?",
            [file_hash],
            one=True,
            db_name="datasets")

        if existing_image:
            return jsonify({
                "message": "Image already exists in dataset",
                "filename": filename
            }), 400

        file.save(full_path)

        # Insert into dataset database
        query_db(
            f"INSERT INTO {dataset_table} (file_hash, file_path) VALUES (?, ?)",
            [file_hash, filename],
            db_name="datasets")

        logger.info(f"Added image to dataset: {filename}")

        return jsonify({
            "message": "Image added to dataset",
            "filename": filename
        }), 201
    else:
        return jsonify({"error": "Invalid file format"}), 400
