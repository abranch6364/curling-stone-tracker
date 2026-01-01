from typing import Tuple
import cv2 as cv
import numpy as np

def split_stream_frame(image:np.ndarray) -> Tuple[np.ndarray,np.ndarray,np.ndarray,np.ndarray]:
    """Split a frame from the RCC stream into the single camera components.

    Args:
        image (np.ndarray): The image to split

    Returns:
        Tuple[np.ndarray,np.ndarray,np.ndarray,np.andarrayrray]: The resulting split images.
    """

    #Create slices to use later. These are row,column slices
    top_down_a_slice = np.s_[30:549, 833:1090]
    top_down_b_slice = np.s_[549:1049, 833:1090]
    angled_a_slice = np.s_[0:image.shape[0], 1089:image.shape[1]]
    angled_b_slice = np.s_[0:image.shape[0], 0:831]

    top_down_a = image[top_down_a_slice]
    top_down_b = image[top_down_b_slice]

    angled_a = image[angled_a_slice]
    angled_b = image[angled_b_slice]

    return top_down_a, top_down_b, angled_a, angled_b

def extract_images_from_video(video_path:str, second_interval:int=1, start_second:int=0) -> np.ndarray:
    """Generator for extracting frames from a video.

    Args:
        video_path (str): The path to the video to extract frames from
        second_interval (int, optional): The interval in seconds between frames to yield. Defaults to 1.
        start_second (int, optional): The time in the video to start yielding frames at. Defaults to 0.

    Yields:
        np.ndarray: An array containing the next frame from the video
    """
    cap = cv.VideoCapture(video_path)
    fps = cap.get(cv.CAP_PROP_FPS)
    frame_interval = int(fps * second_interval)
    start_frame = int(fps * start_second)

    cap.set(cv.CAP_PROP_POS_FRAMES, start_frame)
    current_frame = start_frame

    total_seconds = cap.get(cv.CAP_PROP_FRAME_COUNT) / fps

    while cap.isOpened():
        cap.set(cv.CAP_PROP_POS_FRAMES, current_frame)
        ret, frame = cap.read()
        if not ret:
            break

        yield current_frame, frame
        current_frame += frame_interval
        print(f"Extracted frame at {current_frame/fps:.2f} seconds / {total_seconds:.2f} seconds", end='\r')

    cap.release()