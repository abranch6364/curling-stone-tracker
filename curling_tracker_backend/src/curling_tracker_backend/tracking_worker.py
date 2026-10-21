"""Background worker that tracks whole videos, run with `flask tracking_worker`.

Runs are queued in the TrackingRuns table by the API. Each run is downloaded once, scanned at a coarse
interval to split it into games, ends and shots, and then each shot is tracked at the full rate. Progress
is written to the run so the UI can show it. A run interrupted by a restart is picked up again, skipping
the stages (and shots) it already finished.
"""
import logging
import os
import time
import uuid

import numpy as np
from flask import current_app

import curling_tracker_backend.db_helper as db_helper
import curling_tracker_backend.util.async_yt_dlp as async_yt_dlp
import curling_tracker_backend.util.curling_shot_tracker as shot_tracker
import curling_tracker_backend.util.video_segmentation as segmentation
from curling_tracker_backend.db import db_transaction, init_db, query_db

logger = logging.getLogger(__name__)

# Time (s) between checks for a queued run
POLL_INTERVAL_SECONDS = 5.0
# Shortest time (s) between writes of a run's progress
PROGRESS_INTERVAL_SECONDS = 2.0
# Share of a run's progress given to each stage
DOWNLOAD_PROGRESS = (0.0, 0.15)
SCAN_PROGRESS = (0.15, 0.45)
TRACK_PROGRESS = (0.45, 1.0)

RUNNING_STATUSES = ("downloading", "scanning", "tracking")


class RunCancelled(Exception):
    """Raised when the run being processed was cancelled through the API."""


def format_seconds(seconds: float) -> str:
    seconds = int(seconds)
    return f"{seconds // 3600}:{seconds // 60 % 60:02d}:{seconds % 60:02d}"


class ProgressReporter:
    """Writes a run's status, progress and message, at most every PROGRESS_INTERVAL_SECONDS unless forced.
    Each write also checks if the run was cancelled, and raises RunCancelled if it was."""

    def __init__(self, run_id: str):
        self.run_id = run_id
        self.last_write = 0.0

    def stage(self, status: str, progress: float, message: str):
        self.write(progress, message, status=status, force=True)

    def write(self,
              progress: float,
              message: str,
              status: str = None,
              force: bool = False):
        now = time.monotonic()
        if not force and now - self.last_write < PROGRESS_INTERVAL_SECONDS:
            return
        self.last_write = now

        with db_transaction() as conn:
            updated = conn.execute(
                "UPDATE TrackingRuns SET status = COALESCE(?, status), progress = ?, message = ?, updated_at = CURRENT_TIMESTAMP WHERE run_id = ? AND status != 'cancelled'",
                [status, progress, message, self.run_id]).rowcount
        if updated == 0:
            raise RunCancelled()


def stage_progress(stage: tuple, fraction: float) -> float:
    start, end = stage
    return start + (end - start) * min(max(fraction, 0.0), 1.0)


def download_stage(run, reporter: ProgressReporter) -> str:
    """Download the run's video, unless it already was. Returns the path to the video."""
    download_folder = current_app.config["YOUTUBE_DOWNLOADS_FOLDER"]
    if run["video_filename"] is not None:
        video_path = os.path.join(download_folder, run["video_filename"])
        if os.path.exists(video_path):
            logger.info(f"Reusing downloaded video {video_path}")
            return video_path

    reporter.stage("downloading", DOWNLOAD_PROGRESS[0], "Downloading video")
    os.makedirs(download_folder, exist_ok=True)

    def progress_hook(update: dict):
        if update.get("status") != "downloading":
            return
        total = update.get("total_bytes") or update.get("total_bytes_estimate")
        downloaded = update.get("downloaded_bytes", 0)
        if total:
            reporter.write(
                stage_progress(DOWNLOAD_PROGRESS, downloaded / total),
                f"Downloading video {downloaded / 1e6:.0f} / {total / 1e6:.0f} MB"
            )

    filename = async_yt_dlp.download_full_video_sync(run["url"],
                                                     download_folder,
                                                     f"run_{run['run_id']}",
                                                     progress_hook)
    video_path = os.path.join(download_folder, filename)
    video = shot_tracker.CurlingVideo(video_path)
    query_db(
        "UPDATE TrackingRuns SET video_filename = ?, video_duration = ? WHERE run_id = ?",
        [filename, video.num_frames / video.fps, run["run_id"]])
    return video_path


def scan_stage(run_id: str, camera_setup: shot_tracker.CameraSetup,
               video: shot_tracker.CurlingVideo, stone_detectors,
               reporter: ProgressReporter):
    """Detect the in-play stones across the whole video at a coarse interval, split it into games, ends
    and shots and store them, with every shot pending."""
    duration = video.num_frames / video.fps
    reporter.stage("scanning", SCAN_PROGRESS[0], "Scanning video")

    max_batch_images = current_app.config["DETECTION_BATCH_IMAGES"]
    frame_batches = shot_tracker.batched_frames(
        video.frame_generator(
            second_interval=segmentation.SCAN_INTERVAL_SECONDS),
        shot_tracker.get_frame_batch_size(camera_setup, max_batch_images))

    frames = []
    for batch in frame_batches:
        mosaic_detections = shot_tracker.batch_mosaic_detect_stones(
            camera_setup, [frame for _, frame in batch], stone_detectors)

        for (frame_index, _), mosaic_detection in zip(batch,
                                                      mosaic_detections):
            stones = []
            for detections in mosaic_detection.detections.values():
                for detection in shot_tracker.in_play_detections(detections):
                    stones.append((detection.color.name.lower(),
                                   float(detection.sheet_coordinates[0]),
                                   float(detection.sheet_coordinates[1])))
            frames.append(
                segmentation.ScanFrame(float(frame_index) / video.fps, stones))

        frame_time = frames[-1].time
        reporter.write(
            stage_progress(SCAN_PROGRESS, frame_time / duration),
            f"Scanning {format_seconds(frame_time)} / {format_seconds(duration)}"
        )

    games = segmentation.segment_video(frames)
    with db_transaction() as conn:
        for game_number, game in enumerate(games, start=1):
            game_id = str(uuid.uuid4())
            conn.execute(
                "INSERT INTO Games (game_id, run_id, game_number, start_seconds, end_seconds) VALUES (?, ?, ?, ?, ?)",
                [
                    game_id, run_id, game_number, game.start_seconds,
                    game.end_seconds
                ])
            for end_number, end in enumerate(game.ends, start=1):
                end_id = str(uuid.uuid4())
                conn.execute(
                    "INSERT INTO Ends (end_id, game_id, end_number, direction, complete, start_seconds, end_seconds) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    [
                        end_id, game_id, end_number, end.direction,
                        int(end.complete), end.start_seconds, end.end_seconds
                    ])
                for shot_number, shot in enumerate(end.shots, start=1):
                    conn.execute(
                        "INSERT INTO Shots (shot_id, end_id, shot_number, color, status, start_seconds, end_seconds) VALUES (?, ?, ?, ?, 'pending', ?, ?)",
                        [
                            str(uuid.uuid4()), end_id, shot_number, shot.color,
                            shot.start_seconds, shot.end_seconds
                        ])

    logger.info(f"Found {len(games)} games in run {run_id}")


def trim_stone(stone: shot_tracker.Stone, start: float):
    """Drop the part of a stone's history before a time."""
    keep = [i for i, t in enumerate(stone.time_history) if t >= start]
    for name in [
            "position_history", "velocity_history", "acceleration_history",
            "time_history", "state_history", "covariance_history"
    ]:
        history = getattr(stone, name)
        setattr(stone, name, [history[i] for i in keep])


def track_shot(shot, camera_setup: shot_tracker.CameraSetup,
               video: shot_tracker.CurlingVideo, stone_detectors):
    """Track one shot and store its stones."""
    results = shot_tracker.video_stone_tracker(
        camera_setup,
        video,
        stone_detectors,
        start_second=shot["start_seconds"],
        end_second=shot["end_seconds"],
        max_batch_images=current_app.config["DETECTION_BATCH_IMAGES"])
    stones = results.state.stones

    start, delivered = segmentation.trim_start_time(stones, shot["direction"],
                                                    shot["start_seconds"])
    for stone in stones:
        trim_stone(stone, start)
    stones = [stone for stone in stones if stone.time_history]
    color = shot["color"]
    if delivered is not None:
        color = results.state.stones[delivered].color.name.lower()

    with db_transaction() as conn:
        conn.execute("DELETE FROM ShotStones WHERE shot_id = ?",
                     [shot["shot_id"]])
        for stone in stones:
            conn.execute(
                "INSERT INTO ShotStones (stone_id, shot_id, color, time_history, state_history, position_covariance_history) VALUES (?, ?, ?, ?, ?, ?)",
                [
                    str(uuid.uuid4()), shot["shot_id"],
                    stone.color.name.lower(),
                    np.array(stone.time_history, dtype=float),
                    np.array(stone.state_history, dtype=float),
                    np.array([
                        covariance[:2, :2]
                        for covariance in stone.covariance_history
                    ],
                             dtype=float)
                ])
        conn.execute(
            "UPDATE Shots SET status = 'tracked', color = ?, start_seconds = ? WHERE shot_id = ?",
            [color, start, shot["shot_id"]])


def track_stage(run_id: str, camera_setup: shot_tracker.CameraSetup,
                video: shot_tracker.CurlingVideo, stone_detectors,
                reporter: ProgressReporter):
    """Track every shot of the run that hasn't been tracked yet."""
    shots = query_db(
        """SELECT Shots.shot_id, Shots.status, Shots.color, Shots.start_seconds, Shots.end_seconds, Ends.direction
           FROM Shots JOIN Ends ON Shots.end_id = Ends.end_id JOIN Games ON Ends.game_id = Games.game_id
           WHERE Games.run_id = ? ORDER BY Shots.start_seconds""", [run_id])

    reporter.stage("tracking", TRACK_PROGRESS[0], "Tracking shots")
    for index, shot in enumerate(shots):
        reporter.write(stage_progress(TRACK_PROGRESS, index / len(shots)),
                       f"Tracking shot {index + 1} / {len(shots)}",
                       force=True)
        if shot["status"] == "tracked":
            continue

        try:
            track_shot(shot, camera_setup, video, stone_detectors)
        except Exception:
            logger.exception(f"Failed to track shot {shot['shot_id']}")
            query_db("UPDATE Shots SET status = 'failed' WHERE shot_id = ?",
                     [shot["shot_id"]])


def summary_message(run_id: str) -> str:
    counts = query_db(
        """SELECT COUNT(DISTINCT Games.game_id), COUNT(DISTINCT Ends.end_id), COUNT(Shots.shot_id)
           FROM Games LEFT JOIN Ends ON Ends.game_id = Games.game_id LEFT JOIN Shots ON Shots.end_id = Ends.end_id
           WHERE Games.run_id = ?""", [run_id],
        one=True)
    return f"{counts[0]} games, {counts[1]} ends, {counts[2]} shots"


def store_video_info(run_id: str, url: str):
    """Store the title and date of a run's video. The run doesn't need them, so failing is only logged."""
    try:
        info = async_yt_dlp.video_info_sync(url)
    except Exception:
        logger.warning(f"Failed to get the video info for run {run_id}", exc_info=True)
        return

    query_db(
        "UPDATE TrackingRuns SET video_title = ?, video_date = ?, video_start_timestamp = ? WHERE run_id = ?",
        [info["title"], info["date"], info["start_timestamp"], run_id])


def process_run(run, stone_detectors):
    run_id = run["run_id"]
    reporter = ProgressReporter(run_id)
    video_path = None

    try:
        with db_transaction() as conn:
            camera_setup = db_helper.get_setup_from_db(conn, run["setup_id"])

        if run["video_date"] is None:
            store_video_info(run_id, run["url"])

        video_path = download_stage(run, reporter)
        video = shot_tracker.CurlingVideo(video_path)

        scanned = query_db("SELECT 1 FROM Games WHERE run_id = ? LIMIT 1",
                           [run_id],
                           one=True)
        if scanned is None:
            scan_stage(run_id, camera_setup, video, stone_detectors, reporter)

        track_stage(run_id, camera_setup, video, stone_detectors, reporter)
        reporter.stage("complete", 1.0, summary_message(run_id))
        logger.info(f"Finished tracking run {run_id}")
    except Exception as e:
        cancelled = query_db(
            "SELECT 1 FROM TrackingRuns WHERE run_id = ? AND status = 'cancelled'",
            [run_id],
            one=True)
        # Cancelling can also surface as another error, e.g. from inside the download
        if isinstance(e, RunCancelled) or cancelled is not None:
            logger.info(f"Tracking run {run_id} was cancelled")
        else:
            logger.exception(f"Tracking run {run_id} failed")
            query_db(
                "UPDATE TrackingRuns SET status = 'failed', error = ?, updated_at = CURRENT_TIMESTAMP WHERE run_id = ?",
                [str(e), run_id])
    finally:
        remove_run_files(run_id)


def remove_run_files(run_id: str):
    """Delete a run's downloaded video, including a partial download."""
    download_folder = current_app.config["YOUTUBE_DOWNLOADS_FOLDER"]
    if not os.path.exists(download_folder):
        return
    for filename in os.listdir(download_folder):
        if filename.startswith(f"run_{run_id}."):
            os.remove(os.path.join(download_folder, filename))


def claim_next_run():
    """Claim the oldest queued run, or return None if there isn't one."""
    run = query_db(
        "SELECT run_id FROM TrackingRuns WHERE status = 'queued' ORDER BY created_at LIMIT 1",
        one=True)
    if run is None:
        return None

    with db_transaction() as conn:
        claimed = conn.execute(
            "UPDATE TrackingRuns SET status = 'downloading', progress = 0, message = 'Starting', error = NULL, updated_at = CURRENT_TIMESTAMP WHERE run_id = ? AND status = 'queued'",
            [run["run_id"]]).rowcount
        if claimed == 0:
            return None
        return conn.execute(
            "SELECT run_id, url, setup_id, video_filename, video_date FROM TrackingRuns WHERE run_id = ?",
            [run["run_id"]]).fetchone()


def run_worker():
    init_db()

    # Runs that were in progress when the worker stopped are picked up again
    query_db(
        f"UPDATE TrackingRuns SET status = 'queued' WHERE status IN ({', '.join('?' * len(RUNNING_STATUSES))})",
        RUNNING_STATUSES)

    # Clean up the downloads of runs that were cancelled while the worker wasn't running
    for run in query_db(
            "SELECT run_id FROM TrackingRuns WHERE status IN ('cancelled', 'failed', 'complete')"
    ):
        remove_run_files(run["run_id"])

    stone_detectors = shot_tracker.get_stone_detectors(
        os.path.join(current_app.root_path, "model/"))
    logger.info("Tracking worker started")

    while True:
        run = claim_next_run()
        if run is None:
            time.sleep(POLL_INTERVAL_SECONDS)
            continue

        logger.info(f"Processing tracking run {run['run_id']}: {run['url']}")
        process_run(run, stone_detectors)
