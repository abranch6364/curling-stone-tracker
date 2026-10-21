import click
import curling_tracker_backend.db as db
import shutil
import os
import hashlib
import logging

from flask import (current_app)

logger = logging.getLogger(__name__)


@click.command("initdb")
def init_db_command():
    """Create the tables in the database."""
    db.init_db()


@click.command("cleardb")
def clear_db_command():
    """A command to clear the entires in the database and recreate the empty Tables"""
    db.clear_db()


@click.command("clear_videos")
def clear_videos_command():
    """A command to clear the the videos in the database and from the server"""

    db.query_db("DELETE FROM Videos")
    shutil.rmtree(current_app.config["YOUTUBE_DOWNLOADS_FOLDER"])


@click.command("tracking_worker")
def tracking_worker_command():
    """Run the worker that tracks queued full video runs"""
    from curling_tracker_backend.tracking_worker import run_worker

    run_worker()


@click.command("backfill_video_info")
def backfill_video_info_command():
    """Get the title and date of the videos of runs that don't have them"""
    from curling_tracker_backend.tracking_worker import store_video_info

    for run in db.query_db(
            "SELECT run_id, url FROM TrackingRuns WHERE video_date IS NULL"):
        logger.info(f"Getting the video info for run {run['run_id']}")
        store_video_info(run["run_id"], run["url"])


@click.command("backfill_split_times")
def backfill_split_times_command():
    """Work out the back line to hog and hog to hog times of shots from their stored stone tracks"""
    from types import SimpleNamespace
    import curling_tracker_backend.util.video_segmentation as segmentation

    shots = db.query_db(
        """SELECT Shots.shot_id, Ends.direction FROM Shots JOIN Ends ON Shots.end_id = Ends.end_id
           WHERE Shots.status = 'tracked'""")
    for shot in shots:
        stones = [
            SimpleNamespace(time_history=list(stone["time_history"]),
                            position_history=stone["state_history"][:, 0:2].tolist(),
                            velocity_history=stone["state_history"][:, 2:4].tolist())
            for stone in db.query_db(
                "SELECT time_history, state_history FROM ShotStones WHERE shot_id = ?",
                [shot["shot_id"]])
        ]
        delivered = segmentation.find_delivered_stone(stones, shot["direction"])
        times = (None, None) if delivered is None else segmentation.split_times(
            stones[delivered], shot["direction"])
        db.query_db(
            "UPDATE Shots SET back_line_to_hog_seconds = ?, hog_to_hog_seconds = ? WHERE shot_id = ?",
            [*times, shot["shot_id"]])
    logger.info(f"Worked out the split times of {len(shots)} shots")


@click.command("rebuild_datasets")
def rebuild_datasets_command():
    """A command to rebuild the TopDownDataset table from the files in the dataset folder"""

    dataset_db = db.get_db(db_name="datasets")
    with current_app.open_resource("dataset_schemas.sql") as f:
        dataset_db.executescript(f.read().decode("utf8"))
    dataset_db.close()

    for dataset_name, dataset in current_app.config["DATASETS"].items():
        logger.info(
            f"Rebuilding dataset: {dataset_name} with files from folder: {dataset['folder']} into database table: {dataset['dataset_table']}"
        )
        db.query_db(f"DELETE FROM {dataset['dataset_table']}",
                    db_name="datasets")
        dataset_path = os.path.join(current_app.config["BASE_DATASETS_PATH"],
                                    dataset['folder'])
        for file_name in os.listdir(dataset_path):
            file_path = os.path.join(dataset_path, file_name)
            with open(file_path, "rb") as f:
                file_data = f.read()
                file_hash = hashlib.sha256(file_data).digest()
                db.query_db(
                    f"INSERT INTO {dataset['dataset_table']} (file_hash, file_path) VALUES (?, ?)",
                    (file_hash, file_path),
                    db_name="datasets")
