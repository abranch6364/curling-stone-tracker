from dataclasses import dataclass
from typing import Generator, Iterator, List, Tuple
import scipy
from ultralytics import YOLO
import logging
import cv2 as cv
import numpy as np

logger = logging.getLogger(__name__)


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

    corner1: np.ndarray
    corner2: np.ndarray
    camera_matrix: np.ndarray
    distortion_coefficients: np.ndarray
    rotation_vectors: np.ndarray
    translation_vectors: np.ndarray

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


@dataclass
class CameraSetup:
    id: str
    name: str
    cameras: List[Camera]


class CurlingVideo:

    def __init__(self, video_path: str):
        self.video_path = video_path

        cap = cv.VideoCapture(self.video_path)
        self.fps = cap.get(cv.CAP_PROP_FPS)
        cap.release()

    def frame_generator(
            self,
            second_interval: float = 1.0,
            start_second: float = 0.0) -> Generator[np.ndarray, None, None]:
        """Generator for extracting frames from a video.

        Args:
            video_path (str): The path to the video to extract frames from
            second_interval (int, optional): The interval in seconds between frames to yield. Defaults to 1.
            start_second (int, optional): The time in the video to start yielding frames at. Defaults to 0.

        Yields:
            np.ndarray: An array containing the next frame from the video
        """

        cap = cv.VideoCapture(self.video_path)
        frame_interval = int(self.fps * second_interval)
        start_frame = int(self.fps * start_second)

        cap.set(cv.CAP_PROP_POS_FRAMES, start_frame)
        current_frame = start_frame

        while cap.isOpened():
            cap.set(cv.CAP_PROP_POS_FRAMES, current_frame)
            ret, frame = cap.read()
            if not ret:
                break

            yield current_frame, frame
            current_frame += frame_interval

        cap.release()


def create_camera(
    image_points: List[Tuple[int, int]],
    world_points: List[Tuple[float, float, float]],
    image_shape: Tuple[int, int],
) -> Camera:
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
    image_points = image_points.astype("float32")
    world_points = world_points.astype("float32")

    _, camera_mat, distortion, rotation_vecs, translation_vecs = cv.calibrateCamera(
        world_points, image_points, image_shape, None, None)
    camera = Camera(camera_mat, distortion, rotation_vecs[0],
                    translation_vecs[0])

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


def sheet_to_image_coordinates(camera: Camera,
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


def image_to_sheet_coordinates(camera: Camera,
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


class SingleCameraStoneDetector:
    """
    A class for detecting curling stones in images using a YOLO model and converting to world coordinates.
    """

    def __init__(self, model_path: str):
        self.model = YOLO(model_path)

    def detect_stones(self, camera: Camera, image: np.ndarray) -> List:
        """Detect curling stones in an image and return their position in world coordinates

        Args:
            camera (Camera): The camera that the image came from.
            image (np.ndarray): The image to detect stones in.

        Returns:
            List: The resulting list of stone locations.
        """
        stone_positions = {}
        stone_positions["green"] = []
        stone_positions["yellow"] = []

        results = self.model.predict(source=image,
                                     save=False,
                                     save_txt=False,
                                     conf=0.65,
                                     verbose=False)
        for result in results:
            for box in result.boxes:
                x1, y1, x2, y2 = box.xyxy[0]
                x_center = int((x1 + x2) / 2)
                y_center = int((y1 + y2) / 2)
                class_id = int(box.cls[0])
                if class_id == 0:
                    stone_positions["green"].append((x_center, y_center))
                elif class_id == 1:
                    stone_positions["yellow"].append((x_center, y_center))

        stone_positions["green"] = np.array(stone_positions["green"])
        stone_positions["yellow"] = np.array(stone_positions["yellow"])
        stone_positions["green"] = stone_positions["green"].astype("float32")
        stone_positions["yellow"] = stone_positions["yellow"].astype("float32")

        stones = []
        # Add stones to list
        if len(stone_positions["green"]) != 0:
            green_sheet_coords = image_to_sheet_coordinates(
                camera, stone_positions["green"])

            for image_coords, sheet_coords in zip(stone_positions["green"],
                                                  green_sheet_coords):
                stones.append({
                    "color": "green",
                    "image_coordinates": image_coords.tolist(),
                    "sheet_coordinates": sheet_coords.tolist(),
                })

        if len(stone_positions["yellow"]) != 0:
            yellow_sheet_coords = image_to_sheet_coordinates(
                camera, stone_positions["yellow"])

            for image_coords, sheet_coords in zip(stone_positions["yellow"],
                                                  yellow_sheet_coords):
                stones.append({
                    "color": "yellow",
                    "image_coordinates": image_coords.tolist(),
                    "sheet_coordinates": sheet_coords.tolist(),
                })
        return stones


class Stone:

    def __init__(self,
                 color: str,
                 initial_position: Tuple[float, float] = None,
                 initial_time: float = None):
        self.color = color
        if initial_position is not None and initial_time is not None:
            self.position_history = [initial_position]
            self.time_history = [initial_time]
        else:
            self.position_history = []
            self.time_history = []

    def update_position(self, new_position: Tuple[float, float],
                        new_time: float):
        self.position_history.append(new_position)
        self.time_history.append(new_time)

    def get_latest_position(self) -> Tuple[float, float]:
        return self.position_history[-1]

    def get_latest_time(self) -> float:
        return self.time_history[-1]

    def to_dict(self) -> dict:
        return {
            "color": self.color,
            "position_history": self.position_history,
            "time_history": self.time_history,
        }


class GameState:

    def __init__(self):
        self.stones = []

    def add_stone_detections(self, new_detections, timestamp: float):
        detected_rocks = []
        for detection in new_detections:
            detected_rocks.append(
                Stone(detection["color"], detection["sheet_coordinates"],
                      timestamp))

        if len(self.stones) == 0:
            self.stones.extend(detected_rocks)
            return

        if len(detected_rocks) == 0:
            return

        matrix = []
        for val1 in self.stones:
            new_row = []
            for val2 in detected_rocks:
                if val1.color != val2.color:
                    new_row.append(10000000.0)
                else:
                    dist = distance(val2.get_latest_position(),
                                    val1.get_latest_position())
                    if dist > 2.0:
                        dist = 1000000.0
                    new_row.append(dist)

            matrix.append(new_row)
        matrix = np.array(matrix)

        new_rocks = []
        best_idxs = scipy.optimize.linear_sum_assignment(matrix)

        remaining_rocks = set(range(len(detected_rocks)))
        for r, c in zip(*best_idxs):
            if matrix[r][c] >= 1000000.0:
                continue

            self.stones[r].update_position(
                detected_rocks[c].get_latest_position(), timestamp)
            remaining_rocks.remove(c)

        for idx in remaining_rocks:
            pos = detected_rocks[idx].get_latest_position()

        self.stones.extend(new_rocks)

    def to_dict(self) -> dict:
        return {
            "stones": [stone.to_dict() for stone in self.stones],
        }


def mosaic_image_track_stones(camera_setup: CameraSetup, image: np.ndarray,
                              stone_detector: SingleCameraStoneDetector):
    stones = []

    for i, camera in enumerate(camera_setup.cameras):
        # Split image for this camera
        split_image = camera.extract_image(image)

        # Detect stones
        stones.extend(stone_detector.detect_stones(camera, split_image))

    return stones


def video_stone_tracker(camera_setup: CameraSetup, video: CurlingVideo,
                        stone_detector: SingleCameraStoneDetector):

    state = GameState()
    for frame_index, frame in video.frame_generator(second_interval=0.1):
        frame_stones = mosaic_image_track_stones(camera_setup, frame,
                                                 stone_detector)

        state.add_stone_detections(frame_stones,
                                   float(frame_index) / video.fps)
    return state
