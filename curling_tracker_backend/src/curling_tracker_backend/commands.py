import click
import curling_tracker_backend.db as db
import shutil

from flask import (current_app)


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
