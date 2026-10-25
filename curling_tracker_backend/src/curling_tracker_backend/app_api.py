"""Endpoints that don't need the stone tracking, so a read only server can serve them without loading it."""
from flask import Blueprint, current_app, jsonify
import logging

from curling_tracker_backend.util.sheet_coordinates import SHEET_COORDINATES

logger = logging.getLogger(__name__)
bp = Blueprint("app_api", __name__, url_prefix="/api")


@bp.route("/config", methods=["GET"])
def config():
    """How the server is set up, so the frontend can match it."""
    return jsonify({"read_only": current_app.config["READ_ONLY"]})


@bp.route("/calibration_coordinates", methods=["GET"])
def sheet_coordinates():
    logger.info(f"Processing calibration_coordinates request.")
    return jsonify(SHEET_COORDINATES)
