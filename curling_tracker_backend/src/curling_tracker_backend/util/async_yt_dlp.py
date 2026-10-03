import os
import yt_dlp
import asyncio
import functools
from concurrent.futures import ProcessPoolExecutor
import cv2


def download_video_sync(url, output_path, start_time=None, end_time=None):
    ydl_opts = {
        'outtmpl': output_path,
        'merge_output_format': 'mp4',
        'format': 'bestvideo+bestaudio/best',
    }

    if start_time is not None and end_time is not None:
        ydl_opts['download_ranges'] = yt_dlp.utils.download_range_func(
            None, [(start_time, end_time)])

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        return ydl.download(url)


def download_full_video_sync(url, output_folder, file_stem, progress_hook=None):
    """Download the video stream (no audio) of a whole video.

    Args:
        url (str): The video to download
        output_folder (str): The folder to download into
        file_stem (str): The name of the downloaded file, without its extension
        progress_hook (Callable[[dict], None], optional): Called with yt-dlp's progress updates

    Returns:
        str: The name of the downloaded file in output_folder
    """
    ydl_opts = {
        'outtmpl': os.path.join(output_folder, file_stem + '.%(ext)s'),
        # Same video stream the camera setups were calibrated on, without the audio to merge
        'format': 'bestvideo/best',
        'progress_hooks': [progress_hook] if progress_hook is not None else [],
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return os.path.basename(ydl.prepare_filename(info))


async def download_video(url, output_path, start_time=None, end_time=None):
    loop = asyncio.get_running_loop()
    with ProcessPoolExecutor() as exc:
        return await loop.run_in_executor(
            exc,
            functools.partial(download_video_sync,
                              url=url,
                              output_path=output_path,
                              start_time=start_time,
                              end_time=end_time))


def download_frame_sync(url, timestamp_seconds):
    timestamp_ms = int(timestamp_seconds * 1000)

    # 1. Get the direct stream URL
    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'socket_timeout': 10,
        'extract_flat': False,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(url, download=False)
        stream_url = info_dict.get('url', None)

    if stream_url:
        # 2. Open the video stream
        print("OpenCV Video Backends:", cv2.videoio_registry.getBackends())
        cap = cv2.VideoCapture(stream_url, cv2.CAP_FFMPEG)

        # 3. Jump to the timestamp (in milliseconds)
        cap.set(cv2.CAP_PROP_POS_MSEC, timestamp_ms)

        # 4. Read the frame at that timestamp
        success, frame = cap.read()
        cap.release()

        if success:
            return frame
    else:
        print("Stream URL Not Valid.")
    return None


async def download_frame(url, timestamp_seconds):
    loop = asyncio.get_running_loop()
    with ProcessPoolExecutor() as exc:
        return await loop.run_in_executor(
            exc,
            functools.partial(download_frame_sync,
                              url=url,
                              timestamp_seconds=timestamp_seconds))
