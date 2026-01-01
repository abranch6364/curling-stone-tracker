import click
import curling_tracker_backend.db as db


@click.command("initdb")
def init_db_command():
    """Create the tables in the database."""
    db.init_db()


@click.command("cleardb")
def clear_db_command():
    """A command to clear the entires in the database and recreate the empty Tables"""
    db.clear_db()
