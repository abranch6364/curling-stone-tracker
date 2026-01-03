from typing import Tuple
import cv2 as cv
import numpy as np


def split_stream_frame(
    image: np.ndarray
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
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
