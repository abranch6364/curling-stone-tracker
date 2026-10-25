import os
import logging.config
from flask import Flask, jsonify, request
import yaml

# The endpoints a read only server serves: everything the Draws tab reads, and nothing that writes, downloads
# or needs the stone detectors
READ_ONLY_ENDPOINTS = {
    "static",
    "app_api.config",
    "app_api.sheet_coordinates",
    "tracking_runs_api.games",
    "tracking_runs_api.game",
    "tracking_runs_api.shot",
    "tracking_runs_api.tracking_runs",
}


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
        YOUTUBE_DOWNLOADS_FOLDER=os.path.join(app.instance_path,
                                              "youtube_downloads"),
        DATASETS_DATABASE="/datasets/datasets_database.db")

    app.config.from_pyfile(os.path.join(app.root_path, "config.py"))

    # A read only server only serves the draws that were tracked, e.g. on a host the database is published
    # to. Set with the READ_ONLY environment variable.
    app.config["READ_ONLY"] = os.environ.get("READ_ONLY", "false").strip().lower() in ("1", "true", "yes")
    if app.config["READ_ONLY"]:
        logger.info("Running read only")

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
    from .commands import init_db_command, clear_db_command, clear_videos_command, rebuild_datasets_command, tracking_worker_command, publish_db_command

    app.cli.add_command(clear_db_command)
    app.cli.add_command(init_db_command)
    app.cli.add_command(clear_videos_command)
    app.cli.add_command(rebuild_datasets_command)
    app.cli.add_command(tracking_worker_command)
    app.cli.add_command(publish_db_command)

    ###
    # Setup blueprints
    ###
    from . import app_api
    from . import tracking_runs_api

    app.register_blueprint(app_api.bp)
    app.register_blueprint(tracking_runs_api.bp)

    # These import the stone tracking (PyTorch, ultralytics, OpenCV, yt-dlp), which a read only server
    # doesn't need, so it doesn't load them
    if not app.config["READ_ONLY"]:
        from . import api
        from . import calibration_api

        app.register_blueprint(api.bp)
        app.register_blueprint(calibration_api.bp)

    @app.before_request
    def only_read_draws_when_read_only():
        # Unknown routes have no endpoint and get their usual 404
        if app.config["READ_ONLY"] and request.endpoint is not None and request.endpoint not in READ_ONLY_ENDPOINTS:
            return jsonify({"error": "This server is read only"}), 403

    ###
    # Output flask app endpoint info
    ###
    with app.test_request_context():
        for rule in app.url_map.iter_rules():
            logger.info(
                f"Endpoint: {rule.endpoint} | Methods: {','.join(rule.methods)} | Rule: {rule.rule}"
            )
    return app
