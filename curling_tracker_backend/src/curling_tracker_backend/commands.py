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
