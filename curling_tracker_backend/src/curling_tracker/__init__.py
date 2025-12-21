import os

from flask import Flask

def create_app():
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)

    app.config.from_mapping(
        DATABASE=os.path.join(app.instance_path, 'database.db'),
        UPLOAD_FOLDER = 'uploads'
    )
    app.json.sort_keys = False

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    from . import db
    db.init_app(app)

    from .commands import init_db_command, clear_db_command
    app.cli.add_command(clear_db_command)
    app.cli.add_command(init_db_command)

    from . import api
    app.register_blueprint(api.bp)

    with app.test_request_context():
        for rule in app.url_map.iter_rules():
            print(f"Endpoint: {rule.endpoint} | Methods: {','.join(rule.methods)} | Rule: {rule.rule}")

    return app
