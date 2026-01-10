import os
import logging.config
from flask import Flask
import yaml


def create_app():
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)

    with open(os.path.join(app.root_path, "config/logging.yaml"), 'r') as f:
        logger_config = yaml.safe_load(f.read())
        logging.config.dictConfig(logger_config)
    logger = logging.getLogger(__name__)
    logger.info("Starting Curling Tracker Backend Flask App...")

    app.config.from_mapping(
        DATABASE=os.path.join(app.instance_path, "database.db"),
        UPLOAD_FOLDER=os.path.join(app.instance_path, "uploads"),
        YOUTUBE_DOWNLOADS_FOLDER=os.path.join(app.instance_path,
                                              "youtube_downloads"),
        DATASETS_DATABASE="/datasets/datasets_database.db")

    app.config.from_pyfile("config.py", silent=True)

    app.json.sort_keys = False

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    ###
    # Setup the database
    ###
    from . import db

    db.init_app(app)

    ###
    # Setup the commands
    ###
    from .commands import init_db_command, clear_db_command, clear_videos_command, rebuild_datasets_command

    app.cli.add_command(clear_db_command)
    app.cli.add_command(init_db_command)
    app.cli.add_command(clear_videos_command)
    app.cli.add_command(rebuild_datasets_command)

    ###
    # Setup blueprints
    ###
    from . import api

    app.register_blueprint(api.bp)

    ###
    # Output flask app endpoint info
    ###
    with app.test_request_context():
        for rule in app.url_map.iter_rules():
            logger.info(
                f"Endpoint: {rule.endpoint} | Methods: {','.join(rule.methods)} | Rule: {rule.rule}"
            )
    return app
