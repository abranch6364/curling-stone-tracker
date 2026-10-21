import os
import yt_dlp
import asyncio
import functools
from concurrent.futures import ProcessPoolExecutor
import cv2


def download_video_sync(url,
                        output_path,
                        start_time=None,
                        end_time=None,
                        file_stem=None,
                        video_format='bestvideo/best',
                        progress_hook=None):
    """Download a video, or part of one.

    Args:
        url (str): The video to download
        output_path (str): The file to download to, or with file_stem, the folder to download into
        start_time (float, optional): The start (s) of the part of the video to download, with end_time.
            Defaults to the whole video.
        end_time (float, optional): The end (s) of the part of the video to download
        file_stem (str, optional): The name of the file without its extension, which yt-dlp then picks
            for the format downloaded. Without it, output_path is the file.
        video_format (str, optional): The yt-dlp format to download. Defaults to the best video and audio,
            merged into an mp4.
        progress_hook (Callable[[dict], None], optional): Called with yt-dlp's progress updates

    Returns:
        str: The path of the downloaded file
    """
    ydl_opts = {
        'outtmpl':
        os.path.join(output_path, file_stem +
                     '.%(ext)s') if file_stem is not None else output_path,
        'merge_output_format':
        'mp4',
        'format':
        video_format,
        'progress_hooks': [progress_hook] if progress_hook is not None else [],
    }

    if start_time is not None and end_time is not None:
        ydl_opts['download_ranges'] = yt_dlp.utils.download_range_func(
            None, [(start_time, end_time)])

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return ydl.prepare_filename(info)


def video_info_sync(url):
    """Get the title and date of a video from its metadata, without downloading it.

    Args:
        url (str): The video

    Returns:
        dict: The video's title, date (YYYY-MM-DD) and, for a recorded live stream, the time the stream
            started (unix time, otherwise None). A normal upload only has the time it was uploaded, which
            isn't when it was recorded.
    """
    with yt_dlp.YoutubeDL({'quiet': True, 'skip_download': True}) as ydl:
        info = ydl.extract_info(url, download=False)

    was_live = info.get('was_live') or info.get('live_status') == 'was_live'
    date = info.get('release_date') or info.get('upload_date')

    return {
        'title': info.get('title'),
        'date': f"{date[:4]}-{date[4:6]}-{date[6:]}" if date else None,
        'start_timestamp': info.get('release_timestamp') if was_live else None,
    }


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
