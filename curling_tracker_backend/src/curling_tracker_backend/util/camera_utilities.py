from typing import List, Tuple
import numpy as np
from dataclasses import dataclass
from enum import Enum
import cv2 as cv


class CameraType(str, Enum):
    TOP_DOWN = "top_down"
    ANGLED = "angled"


@dataclass
class Camera:
    """Stores the defining components of a camera.

    Attributes:
        name (str): The name of this camera
        corner1 (np.ndarray): The x,y pixel coordinates of the first corner of this camera in a mosaic image.
        corner2 (np.ndarray): The x,y pixel coorindates of the 2nd opposite corner of this camrea in a mosaic image.
        camera_matrix (np.ndarray): The camera matrix for this camera
        distortion_coefficients (np.ndarray): The distortion coefficients for this camera
        rotation_vectors (np.ndarray): The rotation vector for this camrea.
        translation_vectors (np.ndarray): The translation vector for this camera.
        camera_type (CameraType): The type of this camera (top down or angled)
    """

    name: str
    corner1: np.ndarray
    corner2: np.ndarray
    camera_matrix: np.ndarray
    distortion_coefficients: np.ndarray
    rotation_vectors: np.ndarray
    translation_vectors: np.ndarray
    camera_type: CameraType

    def extract_image(self, image: np.ndarray) -> np.ndarray:
        """Extract the sub-image corresponding to this camera from a mosaic image.

        Args:
            image (np.ndarray): The mosaic image

        Returns:
            np.ndarray: The extracted image for this camera.
        """
        x = min(self.corner1[0], self.corner2[0])
        y = min(self.corner1[1], self.corner2[1])
        width = abs(self.corner1[0] - self.corner2[0])
        height = abs(self.corner1[1] - self.corner2[1])

        return image[y:(y + height), x:(x + width)]


def world_to_image_coordinates(camera: Camera,
                               points_3d: np.ndarray) -> np.ndarray:
    """Project 3d points in the world frame into the cameras 2d image frame in pixel coordinates

    Args:
        camera (Camera): The camera to project the points onto.
        points_3d (np.ndarray): The points to project into image coordinates

    Returns:
        np.ndarray: The points_3d array as 2d image coordinates.
    """
    projected_points, _ = cv.projectPoints(
        points_3d,
        camera.rotation_vectors,
        camera.translation_vectors,
        camera.camera_matrix,
        camera.distortion_coefficients,
    )
    return projected_points


def image_to_world_coordinates(camera: Camera,
                               image_points: np.ndarray) -> np.ndarray:
    """Convert image pixel coordinates inot world coordinates with the z-axis == 0. i.e. on the sheet.

    Args:
        camera (Camera): The camera that the image points are from
        image_points (np.ndarray): The image points to convert

    Returns:
        np.ndarray: The resulting world points.
    """
    image_points = np.expand_dims(image_points, axis=1)
    undistorted_points = cv.undistortPoints(
        image_points,
        camera.camera_matrix,
        camera.distortion_coefficients,
        P=camera.camera_matrix,
    )

    rmat, _ = cv.Rodrigues(camera.rotation_vectors)
    extrinsic_mat = np.hstack((rmat, camera.translation_vectors))
    projection_mat = camera.camera_matrix @ extrinsic_mat
    homography_mat = projection_mat[:, [0, 1, 3]]
    inv_homography_mat = np.linalg.inv(homography_mat)

    sheet_points = []
    for p in undistorted_points:
        point3d_homogeneous = np.array([p[0][0], p[0][1], 1.0])
        world_point_homogeneous = inv_homography_mat @ point3d_homogeneous
        world_point_homogeneous /= world_point_homogeneous[2]
        sheet_points.append(
            (world_point_homogeneous[0], world_point_homogeneous[1], 0.0))

    return np.array(sheet_points)


def undistort_image(camera: Camera, image: np.ndarray) -> np.ndarray:
    """Undistort an image based on camera calibartion data

    Args:
        camera (Camera): The camera to use for undistorting
        image (np.ndarray): The image to undistort

    Returns:
        np.ndarray: The resulting undistorted image.
    """
    image_shape = list(image.shape[0:2][::-1])
    newcameramtx, roi = cv.getOptimalNewCameraMatrix(
        camera.camera_matrix,
        camera.distortion_coefficients,
        image_shape,
        1.0,
        image_shape,
    )
    undistorted_image = cv.undistort(image, camera.camera_matrix,
                                     camera.distortion_coefficients, None,
                                     newcameramtx)
    return undistorted_image


def create_camera(
    image_points: List[Tuple[int, int]],
    world_points: List[Tuple[float, float, float]], image_shape: Tuple[int,
                                                                       int]
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Create a calibrated camera from corresponding pixel coordinates and world coordinates.

    Args:
        image_points (List[Tuple[int, int]]): The pixel coordinates in the image.
        world_points (List[Tuple[float, float, float]]): The corresponding world points.
        image_shape (Tuple[int, int]): The shape of the image

    Returns:
        Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]: The camera matrix, distortion coefficients, rotation vectors, and translation vectors for the calibrated camera.
        
    """
    image_points = np.array([image_points])
    world_points = np.array([world_points])
    image_points = image_points.astype("float32")
    world_points = world_points.astype("float32")

    _, camera_mat, distortion, rotation_vecs, translation_vecs = cv.calibrateCamera(
        world_points, image_points, image_shape, None, None)

    return Camera("", np.array, np.array, camera_mat, distortion,
                  rotation_vecs[0], translation_vecs[0], CameraType.ANGLED)
