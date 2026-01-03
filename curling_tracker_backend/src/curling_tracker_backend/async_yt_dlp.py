import yt_dlp
import asyncio
import functools
from concurrent.futures import ProcessPoolExecutor


def _download_helper(url, output_path, start_time=None, end_time=None):
    ydl_opts = {
        'outtmpl': output_path,
        'merge_output_format': 'mp4',
    }

    if start_time is not None and end_time is not None:
        ydl_opts['download_ranges'] = yt_dlp.utils.download_range_func(
            None, [(start_time, end_time)])

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        return ydl.download(url)


async def download_video(url, output_path, start_time=None, end_time=None):
    loop = asyncio.get_running_loop()
    with ProcessPoolExecutor() as exc:
        return await loop.run_in_executor(
            exc,
            functools.partial(_download_helper,
                              url=url,
                              output_path=output_path,
                              start_time=start_time,
                              end_time=end_time))
