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

    if current_app.config["READ_ONLY"]:
        raise click.ClickException(
            "The tracking worker writes to the database, so it can't run read only (READ_ONLY is set)")

    run_worker()


@click.command("publish_db")
@click.argument("output_path")
@click.option("--all-runs",
              is_flag=True,
              help="Also keep the runs that didn't complete (failed, cancelled or still processing)")
def publish_db_command(output_path, all_runs):
    """Write a copy of the database for a read only server: a single file, not in WAL mode, with only the
    completed runs unless --all-runs is given"""
    summary = db.publish_db(output_path, completed_runs_only=not all_runs)
    click.echo(
        f"Published {summary['runs']} runs, {summary['draws']} draws and {summary['shots']} shots "
        f"({summary['bytes'] / 1e6:.0f} MB) to {output_path}")


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
