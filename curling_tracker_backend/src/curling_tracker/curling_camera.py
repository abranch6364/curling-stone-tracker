import cv2 as cv
import numpy as np  
from dataclasses import dataclass
from typing import Tuple, List

@dataclass
class ImageCoordinates:
    sheet_coords : Tuple[float, float]
    image_coords : Tuple[int, int]

@dataclass
class Camera:
    camera_matrix : np.ndarray
    distortion_coefficients : np.ndarray
    rotation_vectors : np.ndarray
    translation_vectors : np.ndarray

def create_camera(image_points: List[Tuple[int, int]], 
                  world_points: List[Tuple[float, float, float]], 
                  image_shape: Tuple[int, int]) -> Camera:
    image_points = np.array([image_points])
    world_points = np.array([world_points])
    image_points = image_points.astype('float32')
    world_points = world_points.astype('float32')

    _, camera_mat, distortion, rotation_vecs, translation_vecs = cv.calibrateCamera(world_points, image_points, image_shape, None, None)
    camera = Camera(camera_mat, distortion, rotation_vecs[0], translation_vecs[0])

    return camera
