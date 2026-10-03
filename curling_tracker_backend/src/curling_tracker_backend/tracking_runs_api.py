from flask import Blueprint, request, jsonify
import logging
import uuid

from curling_tracker_backend.db import db_transaction, query_db

logger = logging.getLogger(__name__)
bp = Blueprint("tracking_runs_api", __name__, url_prefix="/api")

RUN_COLUMNS = "run_id, url, setup_id, status, progress, message, error, video_duration, created_at, updated_at"


def _run_to_dict(row) -> dict:
    return {key: row[key] for key in row.keys()}


@bp.route("/tracking_runs", methods=["POST"])
def create_tracking_run():
    url = (request.json.get("url") or "").strip()
    setup_id = request.json.get("setup_id", None)

    logger.info(f"Processing create tracking run request: {url=} {setup_id=}")

    if url == "" or setup_id is None:
        return jsonify({"error": "url and setup_id are required"}), 400

    setup = query_db("SELECT 1 FROM CameraSetups WHERE setup_id = ?",
                     [setup_id],
                     one=True)
    if setup is None:
        return jsonify({"error": "Camera setup not found"}), 404

    # The worker picks up queued runs, so this returns straight away
    run_id = str(uuid.uuid4())
    query_db(
        "INSERT INTO TrackingRuns (run_id, url, setup_id, status, message) VALUES (?, ?, ?, 'queued', 'Waiting for the worker')",
        [run_id, url, setup_id])

    return jsonify({"run_id": run_id}), 201


@bp.route("/tracking_runs", methods=["GET"])
def tracking_runs():
    runs = query_db(f"""SELECT {RUN_COLUMNS},
            (SELECT setup_name FROM CameraSetups WHERE CameraSetups.setup_id = TrackingRuns.setup_id) AS setup_name,
            (SELECT COUNT(*) FROM Games WHERE Games.run_id = TrackingRuns.run_id) AS num_games,
            (SELECT COUNT(*) FROM Shots JOIN Ends ON Shots.end_id = Ends.end_id JOIN Games ON Ends.game_id = Games.game_id
                WHERE Games.run_id = TrackingRuns.run_id) AS num_shots
        FROM TrackingRuns ORDER BY created_at DESC""")

    return jsonify([_run_to_dict(run) for run in runs])


@bp.route("/tracking_runs/<run_id>/cancel", methods=["POST"])
def cancel_tracking_run(run_id):
    logger.info(f"Processing cancel tracking run request: {run_id=}")

    # The worker sees the status on its next progress update and stops the run
    with db_transaction() as conn:
        cancelled = conn.execute(
            "UPDATE TrackingRuns SET status = 'cancelled', message = 'Cancelled', updated_at = CURRENT_TIMESTAMP WHERE run_id = ? AND status NOT IN ('complete', 'failed', 'cancelled')",
            [run_id]).rowcount
        exists = conn.execute("SELECT 1 FROM TrackingRuns WHERE run_id = ?",
                              [run_id]).fetchone()

    if exists is None:
        return jsonify({"error": "Tracking run not found"}), 404
    if cancelled == 0:
        return jsonify({"error": "The tracking run has already finished"}), 409
    return jsonify({"run_id": run_id})


@bp.route("/tracking_runs/<run_id>", methods=["GET"])
def tracking_run(run_id):
    run = query_db(f"SELECT {RUN_COLUMNS} FROM TrackingRuns WHERE run_id = ?",
                   [run_id],
                   one=True)
    if run is None:
        return jsonify({"error": "Tracking run not found"}), 404

    games = query_db(
        "SELECT game_id, game_number, start_seconds, end_seconds FROM Games WHERE run_id = ? ORDER BY game_number",
        [run_id])
    ends = query_db(
        """SELECT Ends.end_id, Ends.game_id, Ends.end_number, Ends.direction, Ends.complete, Ends.start_seconds, Ends.end_seconds
           FROM Ends JOIN Games ON Ends.game_id = Games.game_id WHERE Games.run_id = ? ORDER BY Ends.end_number""",
        [run_id])
    shots = query_db(
        """SELECT Shots.shot_id, Shots.end_id, Shots.shot_number, Shots.color, Shots.status, Shots.start_seconds, Shots.end_seconds
           FROM Shots JOIN Ends ON Shots.end_id = Ends.end_id JOIN Games ON Ends.game_id = Games.game_id
           WHERE Games.run_id = ? ORDER BY Shots.shot_number""", [run_id])

    shots_by_end = {}
    for shot in shots:
        shots_by_end.setdefault(shot["end_id"], []).append(_run_to_dict(shot))

    ends_by_game = {}
    for end in ends:
        end_dict = _run_to_dict(end)
        end_dict["complete"] = bool(end_dict["complete"])
        end_dict["shots"] = shots_by_end.get(end["end_id"], [])
        ends_by_game.setdefault(end["game_id"], []).append(end_dict)

    result = _run_to_dict(run)
    result["games"] = []
    for game in games:
        game_dict = _run_to_dict(game)
        game_dict["ends"] = ends_by_game.get(game["game_id"], [])
        result["games"].append(game_dict)

    return jsonify(result)


@bp.route("/shots/<shot_id>", methods=["GET"])
def shot(shot_id):
    shot = query_db(
        """SELECT Shots.shot_id, Shots.shot_number, Shots.color, Shots.status, Shots.start_seconds, Shots.end_seconds,
                  Ends.end_number, Ends.direction, Games.game_number, Games.run_id, TrackingRuns.url
           FROM Shots JOIN Ends ON Shots.end_id = Ends.end_id JOIN Games ON Ends.game_id = Games.game_id
           JOIN TrackingRuns ON Games.run_id = TrackingRuns.run_id
           WHERE Shots.shot_id = ?""", [shot_id],
        one=True)
    if shot is None:
        return jsonify({"error": "Shot not found"}), 404

    stones = query_db(
        "SELECT color, time_history, state_history, position_covariance_history FROM ShotStones WHERE shot_id = ?",
        [shot_id])

    # The order shots were played in, for moving to the previous or next one
    run_shot_ids = [
        row["shot_id"] for row in query_db(
            """SELECT Shots.shot_id FROM Shots JOIN Ends ON Shots.end_id = Ends.end_id
               JOIN Games ON Ends.game_id = Games.game_id
               WHERE Games.run_id = ? AND Shots.status = 'tracked'
               ORDER BY Games.game_number, Ends.end_number, Shots.shot_number""",
            [shot["run_id"]])
    ]
    index = run_shot_ids.index(shot_id) if shot_id in run_shot_ids else None

    result = _run_to_dict(shot)
    result["previous_shot_id"] = run_shot_ids[
        index - 1] if index is not None and index > 0 else None
    result["next_shot_id"] = run_shot_ids[
        index +
        1] if index is not None and index + 1 < len(run_shot_ids) else None
    # The same shape as Stone.dict_for_json, so the sheet plot can draw it
    result["state"] = {
        "stones": [{
            "color":
            stone["color"],
            "position_history":
            stone["state_history"][:, 0:2].tolist(),
            "velocity_history":
            stone["state_history"][:, 2:4].tolist(),
            "acceleration_history":
            stone["state_history"][:, 4:6].tolist(),
            "time_history":
            stone["time_history"].tolist(),
            "position_covariance_history":
            stone["position_covariance_history"].tolist(),
        } for stone in stones]
    }

    return jsonify(result)
