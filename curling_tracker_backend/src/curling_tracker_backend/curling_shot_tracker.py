from dataclasses import dataclass
from typing import List, Tuple
import munkres
from ultralytics import YOLO

import cv2 as cv
import numpy as np  

@dataclass
class Camera:
    """Stores the defining components of a camera.

    Attributes:
        corner1 (np.ndarray): The x,y pixel coordinates of the first corner of this camera in a mosaic image.
        corner2 (np.ndarray): The x,y pixel coorindates of the 2nd opposite corner of this camrea in a mosaic image.
        camera_matrix (np.ndarray): The camera matrix for this camera
        distortion_coefficients (np.ndarray): The distortion coefficients for this camera
        rotation_vectors (np.ndarray): The rotation vector for this camrea.
        translation_vectors (np.ndarray): The translation vector for this camera.
    """

    corner1 : np.ndarray
    corner2 : np.ndarray
    camera_matrix : np.ndarray
    distortion_coefficients : np.ndarray
    rotation_vectors : np.ndarray
    translation_vectors : np.ndarray

    def extract_image(self, image : np.ndarray) -> np.ndarray:
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

        return image[y:(y+height), x:(x+width)]

def create_camera(image_points: List[Tuple[int, int]], 
                  world_points: List[Tuple[float, float, float]], 
                  image_shape: Tuple[int, int]) -> Camera:
    """Create a calibrated camera from corresponding pixel coordinates and world coordinates.

    Args:
        image_points (List[Tuple[int, int]]): The pixel coordinates in the image.
        world_points (List[Tuple[float, float, float]]): The corresponding world points.
        image_shape (Tuple[int, int]): The shape of the image

    Returns:
        Camera: The resulting calibrated camera.
    """
    image_points = np.array([image_points])
    world_points = np.array([world_points])
    image_points = image_points.astype('float32')
    world_points = world_points.astype('float32')

    _, camera_mat, distortion, rotation_vecs, translation_vecs = cv.calibrateCamera(world_points, image_points, image_shape, None, None)
    camera = Camera(camera_mat, distortion, rotation_vecs[0], translation_vecs[0])

    return camera

def distance(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    """Find the distance between two points

    Args:
        p1 (Tuple[float, float]): Point 1
        p2 (Tuple[float, float]): Point 2

    Returns:
        float: The distance between the points
    """
    return np.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

def sheet_to_image_coordinates(camera: Camera, points_3d: np.ndarray) -> np.ndarray:
    """Project 3d points in the world frame into the cameras 2d image frame in pixel coordinates

    Args:
        camera (Camera): The camera to project the points onto.
        points_3d (np.ndarray): The points to project into image coordinates

    Returns:
        np.ndarray: The points_3d array as 2d image coordinates.
    """
    projected_points, _ = cv.projectPoints(points_3d, camera.rotation_vectors, camera.translation_vectors, camera.camera_matrix, camera.distortion_coefficients)
    return projected_points

def image_to_sheet_coordinates(camera: Camera, image_points: np.ndarray) -> np.ndarray:
    """Convert image pixel coordinates inot world coordinates with the z-axis == 0. i.e. on the sheet.

    Args:
        camera (Camera): The camera that the image points are from
        image_points (np.ndarray): The image points to convert

    Returns:
        np.ndarray: The resulting world points.
    """
    image_points = np.expand_dims(image_points, axis=1)
    undistorted_points = cv.undistortPoints(image_points, camera.camera_matrix, camera.distortion_coefficients, P=camera.camera_matrix)

    rmat, _ = cv.Rodrigues(camera.rotation_vectors)
    extrinsic_mat = np.hstack((rmat, camera.translation_vectors))
    projection_mat = camera.camera_matrix @ extrinsic_mat
    homography_mat = projection_mat[:, [0,1,3]]
    inv_homography_mat = np.linalg.inv(homography_mat)

    sheet_points = []
    for p in undistorted_points:
        point3d_homogeneous = np.array([p[0][0], p[0][1], 1.0])
        world_point_homogeneous = inv_homography_mat @ point3d_homogeneous
        world_point_homogeneous /= world_point_homogeneous[2]
        sheet_points.append((world_point_homogeneous[0], world_point_homogeneous[1], 0.0))

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
    newcameramtx, roi = cv.getOptimalNewCameraMatrix(camera.camera_matrix, camera.distortion_coefficients, image_shape, 1.0, image_shape)
    undistorted_image = cv.undistort(image, camera.camera_matrix, camera.distortion_coefficients, None, newcameramtx)
    return undistorted_image

class StoneDetector:
    """
    A class for detecting curling stones in images using a YOLO model and converting to world coordinates.
    """
    def __init__(self, model_path: str):
        self.model = YOLO(model_path)

    def detect_stones(self, camera:Camera, image:np.ndarray) -> List:
        """Detect curling stones in an image and return their position in world coordinates

        Args:
            camera (Camera): The camera that the image came from.
            image (np.ndarray): The image to detect stones in.

        Returns:
            List: The resulting list of stone locations.
        """
        stone_positions = {}
        stone_positions['green'] = []
        stone_positions['yellow'] = []

        results = self.model.predict(source=image, save=False, save_txt=False, conf=0.5)
        for result in results:
            for box in result.boxes:
                x1, y1, x2, y2 = box.xyxy[0]
                x_center = int((x1 + x2) / 2)
                y_center = int((y1 + y2) / 2)
                class_id = int(box.cls[0])
                if class_id == 0:
                    stone_positions['green'].append((x_center, y_center))
                elif class_id == 1:
                    stone_positions['yellow'].append((x_center, y_center))

        stone_positions['green'] = np.array(stone_positions['green'])
        stone_positions['yellow'] = np.array(stone_positions['yellow'])
        stone_positions['green'] = stone_positions['green'].astype('float32')
        stone_positions['yellow'] = stone_positions['yellow'].astype('float32')

        stones = []
        #Add stones to list
        if len(stone_positions['green']) != 0:
            green_sheet_coords = image_to_sheet_coordinates(camera, stone_positions['green'])

            for image_coords, sheet_coords in zip(stone_positions['green'], green_sheet_coords):
                stones.append({"color": "green", "image_coordinates": image_coords.tolist(), "sheet_coordinates": sheet_coords.tolist()})

        if len(stone_positions['yellow']) != 0:
            yellow_sheet_coords = image_to_sheet_coordinates(camera, stone_positions['yellow'])

            for image_coords, sheet_coords in zip(stone_positions['yellow'], yellow_sheet_coords):
                stones.append({"color": "yellow", "image_coordinates": image_coords.tolist(), "sheet_coordinates": sheet_coords.tolist()})
        return stones

class Rock:
    def __init__(self, color: str, initial_position: Tuple[float, float]):
        self.color = color
        self.position_history = [initial_position]

    def update_position(self, new_position: Tuple[float, float]):
        self.position_history.append(new_position)

    def get_latest_position(self) -> Tuple[float, float]:
        return self.position_history[-1]

class GameState:
    def __init__(self):
        self.rocks = []

    def add_stone_detections(self, stone_positions: dict):
        detected_rocks = []
        for color in ['green', 'yellow']:
            for pos in stone_positions[color]:
                detected_rocks.append(Rock(color, pos))
        matrix = []
        for i, val1 in enumerate(self.rocks):
            for j, val2 in enumerate(detected_rocks):        
                if len(matrix) < i+1:
                    matrix.append([])
                if len(matrix[i]) < j+1:
                    matrix[i].append([])
                if val1.color != val2.color:
                    matrix[i][j] = float('inf')
                else:
                    matrix[i][j] = distance(val2.get_latest_position(), val1.get_latest_position())

        if len(matrix) == 0:
            self.rocks.extend(detected_rocks)
            return

        new_rocks = []
        m = munkres.Munkres()
        best_idxs = m.compute(matrix)
        
        remaining_rocks = set(range(len(detected_rocks)))
        for (r, c) in best_idxs:
            self.rocks[r].update_position(detected_rocks[c].get_latest_position())
            remaining_rocks.remove(c)

        for idx in remaining_rocks:
            new_rocks.append(detected_rocks[idx])

        self.rocks.extend(new_rocks)