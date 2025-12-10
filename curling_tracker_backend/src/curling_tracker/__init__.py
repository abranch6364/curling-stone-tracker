import os

from flask import Flask, redirect

import curling_tracker.db as db
import click

def create_app():
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        DATABASE=os.path.join(app.instance_path, 'database.db')
    )
    app.json.sort_keys = False

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    from . import db
    db.init_app(app)

    from .commands import init_db_command
    app.cli.add_command(init_db_command)

    from . import api
    app.register_blueprint(api.bp)

    return app
