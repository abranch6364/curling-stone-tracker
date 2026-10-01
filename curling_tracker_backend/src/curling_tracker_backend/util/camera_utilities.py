from __future__ import annotations

from typing import List, Optional, Tuple
import numpy as np
from dataclasses import dataclass
from enum import Enum
import cv2 as cv


class CameraType(str, Enum):
    TOP_DOWN = "top_down"
    ANGLED = "angled"


class CalibrationMethod(str, Enum):
    FULL = "full"
    HOMOGRAPHY = "homography"


class CalibrationError(ValueError):
    """Raised when a camera is missing the calibration needed for a conversion."""


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
        calibration_method (CalibrationMethod): Whether this camera uses its own full calibration or
            a homography into the image of a reference camera.
        homography (Optional[np.ndarray]): For a homography camera, the 3x3 matrix mapping this camera's
            pixels to the reference camera's undistorted pixels.
        reference_camera (Optional[Camera]): For a homography camera, the fully calibrated camera the
            homography maps into.
    """

    name: str
    corner1: np.ndarray
    corner2: np.ndarray
    camera_matrix: np.ndarray
    distortion_coefficients: np.ndarray
    rotation_vectors: np.ndarray
    translation_vectors: np.ndarray
    camera_type: CameraType
    calibration_method: CalibrationMethod = CalibrationMethod.FULL
    homography: Optional[np.ndarray] = None
    reference_camera: Optional[Camera] = None

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


def is_calibrated(camera: Camera) -> bool:
    """Check if a camera has what it needs to convert between image and world coordinates.

    Args:
        camera (Camera): The camera to check

    Returns:
        bool: True if the camera can be used for coordinate conversions.
    """
    if camera.calibration_method == CalibrationMethod.HOMOGRAPHY:
        return (camera.homography is not None
                and camera.reference_camera is not None
                and camera.reference_camera.calibration_method
                == CalibrationMethod.FULL
                and is_calibrated(camera.reference_camera))

    return camera.camera_matrix is not None


def _check_calibrated(camera: Camera):
    """Raise a CalibrationError describing why a camera can't be used for conversions."""
    if camera.calibration_method == CalibrationMethod.HOMOGRAPHY:
        # Check the reference first since its calibration is needed to compute the homography
        if camera.reference_camera is None:
            raise CalibrationError(
                f"Camera {camera.name} does not have a reference camera")
        if not is_calibrated(camera.reference_camera):
            raise CalibrationError(
                f"Reference camera {camera.reference_camera.name} of camera {camera.name} is not calibrated"
            )
        if camera.homography is None:
            raise CalibrationError(
                f"Camera {camera.name} does not have a homography")
    elif camera.camera_matrix is None:
        raise CalibrationError(f"Camera {camera.name} is not calibrated")


def world_to_image_coordinates(camera: Camera,
                               points_3d: np.ndarray) -> np.ndarray:
    """Project 3d points in the world frame into the cameras 2d image frame in pixel coordinates

    Args:
        camera (Camera): The camera to project the points onto.
        points_3d (np.ndarray): The points to project into image coordinates

    Returns:
        np.ndarray: The points_3d array as 2d image coordinates.
    """
    _check_calibrated(camera)

    if camera.calibration_method == CalibrationMethod.HOMOGRAPHY:
        # The homography maps into the reference camera's undistorted pixels, so project without distortion
        reference = camera.reference_camera
        reference_points, _ = cv.projectPoints(
            np.asarray(points_3d, dtype="float64"),
            reference.rotation_vectors,
            reference.translation_vectors,
            reference.camera_matrix,
            None,
        )
        return cv.perspectiveTransform(reference_points,
                                       np.linalg.inv(camera.homography))

    projected_points, _ = cv.projectPoints(
        points_3d,
        camera.rotation_vectors,
        camera.translation_vectors,
        camera.camera_matrix,
        camera.distortion_coefficients,
    )
    return projected_points


def _undistort_points(camera: Camera, image_points: np.ndarray) -> np.ndarray:
    """Remove lens distortion from pixel coordinates, keeping them in pixel units.

    Args:
        camera (Camera): The fully calibrated camera the image points are from
        image_points (np.ndarray): The Nx2 image points to undistort

    Returns:
        np.ndarray: The Nx2 undistorted image points.
    """
    image_points = np.asarray(image_points, dtype="float64").reshape(-1, 1, 2)
    undistorted_points = cv.undistortPoints(
        image_points,
        camera.camera_matrix,
        camera.distortion_coefficients,
        P=camera.camera_matrix,
    )
    return undistorted_points.reshape(-1, 2)


def _undistorted_image_to_world(camera: Camera,
                                undistorted_points: np.ndarray) -> np.ndarray:
    """Convert undistorted pixel coordinates into world coordinates on the sheet (z == 0).

    Args:
        camera (Camera): The fully calibrated camera the image points are from
        undistorted_points (np.ndarray): The Nx2 undistorted image points

    Returns:
        np.ndarray: The Nx3 world points.
    """
    rmat, _ = cv.Rodrigues(camera.rotation_vectors)
    extrinsic_mat = np.hstack((rmat, camera.translation_vectors))
    projection_mat = camera.camera_matrix @ extrinsic_mat
    homography_mat = projection_mat[:, [0, 1, 3]]
    inv_homography_mat = np.linalg.inv(homography_mat)

    sheet_points = []
    for p in np.asarray(undistorted_points).reshape(-1, 2):
        point3d_homogeneous = np.array([p[0], p[1], 1.0])
        world_point_homogeneous = inv_homography_mat @ point3d_homogeneous
        world_point_homogeneous /= world_point_homogeneous[2]
        sheet_points.append(
            (world_point_homogeneous[0], world_point_homogeneous[1], 0.0))

    return np.array(sheet_points)


def image_to_world_coordinates(camera: Camera,
                               image_points: np.ndarray) -> np.ndarray:
    """Convert image pixel coordinates inot world coordinates with the z-axis == 0. i.e. on the sheet.
    Uses the camera's full calibration, or its homography into the reference camera followed by the
    reference camera's calibration.

    Args:
        camera (Camera): The camera that the image points are from
        image_points (np.ndarray): The image points to convert

    Raises:
        CalibrationError: If the camera (or its reference camera) is not calibrated.

    Returns:
        np.ndarray: The resulting world points.
    """
    _check_calibrated(camera)

    image_points = np.asarray(image_points, dtype="float64").reshape(-1, 1, 2)

    if camera.calibration_method == CalibrationMethod.HOMOGRAPHY:
        # The homography outputs undistorted reference pixels, so no undistortion is needed
        reference_points = cv.perspectiveTransform(image_points,
                                                   camera.homography)
        return _undistorted_image_to_world(camera.reference_camera,
                                           reference_points)

    return _undistorted_image_to_world(camera,
                                       _undistort_points(camera, image_points))


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


def create_homography(image_points: List[Tuple[float, float]],
                      reference_camera: Camera,
                      reference_image_points: List[Tuple[float, float]]
                      ) -> np.ndarray:
    """Create a homography from a camera's pixels to the undistorted pixels of a calibrated reference camera.

    Args:
        image_points (List[Tuple[float, float]]): The pixel coordinates in this camera's image.
        reference_camera (Camera): The fully calibrated reference camera.
        reference_image_points (List[Tuple[float, float]]): The pixel coordinates of the same points in the
            reference camera's image.

    Raises:
        CalibrationError: If the reference camera is not calibrated or no homography could be found.

    Returns:
        np.ndarray: The 3x3 homography matrix.
    """
    if (reference_camera.calibration_method != CalibrationMethod.FULL
            or not is_calibrated(reference_camera)):
        raise CalibrationError(
            f"Reference camera {reference_camera.name} is not calibrated")

    undistorted_reference_points = _undistort_points(reference_camera,
                                                     reference_image_points)
    homography, _ = cv.findHomography(
        np.asarray(image_points, dtype="float64").reshape(-1, 2),
        undistorted_reference_points, 0)

    if homography is None:
        raise CalibrationError("A homography could not be computed")

    return homography
