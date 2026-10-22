from flask import Blueprint, request, jsonify
import logging
import uuid

from curling_tracker_backend.db import db_transaction, query_db

logger = logging.getLogger(__name__)
bp = Blueprint("tracking_runs_api", __name__, url_prefix="/api")

RUN_COLUMNS = "run_id, url, setup_id, status, progress, message, error, video_duration, video_title, video_date, video_start_timestamp, created_at, updated_at"


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


@bp.route("/games", methods=["GET"])
def games():
    """Every game (draw) found in every run, newest run first."""
    games = query_db("""SELECT Games.game_id, Games.game_number, Games.start_seconds, Games.end_seconds,
            TrackingRuns.run_id, TrackingRuns.url, TrackingRuns.status AS run_status,
            TrackingRuns.created_at AS run_created_at, TrackingRuns.video_title, TrackingRuns.video_date, TrackingRuns.video_start_timestamp,
            (SELECT setup_name FROM CameraSetups WHERE CameraSetups.setup_id = TrackingRuns.setup_id) AS setup_name,
            (SELECT COUNT(*) FROM Ends WHERE Ends.game_id = Games.game_id) AS num_ends,
            (SELECT COUNT(*) FROM Shots JOIN Ends ON Shots.end_id = Ends.end_id
                WHERE Ends.game_id = Games.game_id) AS num_shots,
            (SELECT COUNT(*) FROM Shots JOIN Ends ON Shots.end_id = Ends.end_id
                WHERE Ends.game_id = Games.game_id AND Shots.status = 'tracked') AS num_tracked_shots
        FROM Games JOIN TrackingRuns ON Games.run_id = TrackingRuns.run_id
        ORDER BY TrackingRuns.created_at DESC, Games.game_number""")

    return jsonify([_run_to_dict(game) for game in games])


@bp.route("/games/<game_id>", methods=["GET"])
def game(game_id):
    """A game (draw) with its ends and their shots."""
    game = query_db(
        """SELECT Games.game_id, Games.game_number, Games.start_seconds, Games.end_seconds,
                  TrackingRuns.run_id, TrackingRuns.url, TrackingRuns.status AS run_status, TrackingRuns.video_title, TrackingRuns.video_date, TrackingRuns.video_start_timestamp
           FROM Games JOIN TrackingRuns ON Games.run_id = TrackingRuns.run_id WHERE Games.game_id = ?""",
        [game_id],
        one=True)
    if game is None:
        return jsonify({"error": "Game not found"}), 404

    ends = query_db(
        "SELECT end_id, end_number, direction, complete, start_seconds, end_seconds FROM Ends WHERE game_id = ? ORDER BY end_number",
        [game_id])
    shots = query_db(
        """SELECT Shots.shot_id, Shots.end_id, Shots.shot_number, Shots.color, Shots.status, Shots.start_seconds, Shots.end_seconds,
                  Shots.back_line_to_hog_seconds, Shots.hog_to_hog_seconds
           FROM Shots JOIN Ends ON Shots.end_id = Ends.end_id WHERE Ends.game_id = ? ORDER BY Shots.shot_number""",
        [game_id])

    shots_by_end = {}
    for shot in shots:
        shots_by_end.setdefault(shot["end_id"], []).append(_run_to_dict(shot))

    result = _run_to_dict(game)
    result["ends"] = []
    for end in ends:
        end_dict = _run_to_dict(end)
        end_dict["complete"] = bool(end_dict["complete"])
        end_dict["shots"] = shots_by_end.get(end["end_id"], [])
        result["ends"].append(end_dict)

    return jsonify(result)


@bp.route("/shots/<shot_id>", methods=["GET"])
def shot(shot_id):
    shot = query_db(
        """SELECT Shots.shot_id, Shots.shot_number, Shots.color, Shots.status, Shots.start_seconds, Shots.end_seconds,
                  Shots.back_line_to_hog_seconds, Shots.hog_to_hog_seconds, Ends.end_number, Ends.direction, Games.game_id, Games.game_number, Games.run_id, TrackingRuns.url
           FROM Shots JOIN Ends ON Shots.end_id = Ends.end_id JOIN Games ON Ends.game_id = Games.game_id
           JOIN TrackingRuns ON Games.run_id = TrackingRuns.run_id
           WHERE Shots.shot_id = ?""", [shot_id],
        one=True)
    if shot is None:
        return jsonify({"error": "Shot not found"}), 404

    stones = query_db(
        "SELECT color, time_history, state_history, position_covariance_history FROM ShotStones WHERE shot_id = ?",
        [shot_id])

    # The order the game's shots were played in, for moving to the previous or next one
    game_shot_ids = [
        row["shot_id"] for row in query_db(
            """SELECT Shots.shot_id FROM Shots JOIN Ends ON Shots.end_id = Ends.end_id
               WHERE Ends.game_id = ? AND Shots.status = 'tracked'
               ORDER BY Ends.end_number, Shots.shot_number""",
            [shot["game_id"]])
    ]
    index = game_shot_ids.index(shot_id) if shot_id in game_shot_ids else None

    result = _run_to_dict(shot)
    result["previous_shot_id"] = game_shot_ids[
        index - 1] if index is not None and index > 0 else None
    result["next_shot_id"] = game_shot_ids[
        index +
        1] if index is not None and index + 1 < len(game_shot_ids) else None
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
