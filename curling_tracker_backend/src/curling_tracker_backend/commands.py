import click
import curling_tracker_backend.db as db

@click.command('initdb')
def init_db_command():
    db.init_db()

@click.command('cleardb')
def clear_db_command():
    db.clear_db()