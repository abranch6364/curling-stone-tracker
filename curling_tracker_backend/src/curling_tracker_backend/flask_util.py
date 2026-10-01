from curling_tracker_backend.db import query_db
import os
import logging
import curling_tracker_backend.util.async_yt_dlp as async_yt_dlp
import uuid

logger = logging.getLogger(__name__)


async def get_video(video_url,
                    download_folder,
                    start_seconds=None,
                    duration=None):
    db_video = query_db(
        "SELECT filename FROM Videos WHERE url = ? AND start_seconds = ? AND duration = ?",
        [video_url, start_seconds, duration],
        one=True)

    if db_video is not None:
        output_file = os.path.join(download_folder, db_video[0])
        logger.info(f"Using cached video {db_video[0]} for tracking.")
    else:
        logger.info(f"Downloading video for tracking.")
        if not os.path.exists(download_folder):
            os.makedirs(download_folder)

        video_id = str(uuid.uuid4())
        output_file = os.path.join(download_folder, video_id + ".mp4")
        await async_yt_dlp.download_video(video_url,
                                          output_file,
                                          start_time=start_seconds,
                                          end_time=start_seconds + duration)
        query_db(
            "INSERT INTO Videos (video_id, url, start_seconds, duration, filename) VALUES (?, ?, ?, ?, ?)",
            [video_id, video_url, start_seconds, duration, video_id + ".mp4"])

        logger.info(f"Inserted video record into database: {video_id=}")
    return output_file
