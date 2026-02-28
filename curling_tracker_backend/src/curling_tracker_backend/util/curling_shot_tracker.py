from dataclasses import dataclass
from enum import Enum
import os
from typing import Generator, Iterator, List, Tuple
import scipy
from ultralytics import YOLO
import logging
import cv2 as cv
import numpy as np
import base64
from filterpy.kalman import KalmanFilter
from filterpy.common import Q_discrete_white_noise

logger = logging.getLogger(__name__)


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


@dataclass
class CameraSetup:
    id: str
    name: str
    cameras: List[Camera]


@dataclass
class StoneDetection:
    color: str
    image_coordinates: Tuple[float, float, float, float]
    sheet_coordinates: Tuple[float, float, float]

    def dict_for_json(self) -> dict:
        return {
            "color": self.color,
            "image_coordinates": self.image_coordinates,
            "sheet_coordinates": self.sheet_coordinates,
        }


@dataclass
class MosaicStoneDetections:
    images: dict[str, np.ndarray]
    detections: dict[str, List[StoneDetection]]

    def dict_for_json(self) -> dict:
        encoded_images = {}
        for camera_name, image in self.images.items():
            _, buffer = cv.imencode('.png', image)
            png_as_text = base64.b64encode(buffer).decode('utf-8')
            encoded_images[camera_name] = png_as_text

        return {
            "images": encoded_images,
            "detections": {
                camera_name:
                [detection.dict_for_json() for detection in detections]
                for camera_name, detections in self.detections.items()
            },
        }


class GameState:

    def __init__(self, filter_timestep):
        self.stones: List[Stone] = []
        self.filter_timestep = filter_timestep

    def update_stones(self, timestamp: float):
        for stone in self.stones:
            stone.update_filter(timestamp)

    def add_stone_detections(self, new_detections: MosaicStoneDetections,
                             timestamp: float):
        all_detections = []
        for camera_detections in new_detections.detections.values():
            for detection in camera_detections:
                all_detections.append(detection)

        if len(self.stones) == 0:
            for detection in all_detections:
                self.stones.append(
                    Stone(detection.color, detection.sheet_coordinates,
                          timestamp, self.filter_timestep))
            return

        if len(all_detections) == 0:
            return

        matrix = []
        for val1 in self.stones:
            if not val1.active:
                new_row = [1000001.0] * len(all_detections)
                matrix.append(new_row)
                continue

            new_row = []
            for val2 in all_detections:
                if val1.color != val2.color:
                    new_row.append(1000001.0)
                else:
                    dist = distance(val2.sheet_coordinates,
                                    val1.get_latest_position())
                    if dist > 2.0:
                        dist = 1000001.0
                    new_row.append(dist)

            matrix.append(new_row)
        matrix = np.array(matrix)

        best_idxs = scipy.optimize.linear_sum_assignment(matrix)

        remaining_detections = set(range(len(all_detections)))
        for r, c in zip(*best_idxs):
            if matrix[r][c] >= 1000000.0:
                continue

            self.stones[r].add_measurement(all_detections[c].sheet_coordinates,
                                           timestamp)
            remaining_detections.remove(c)

        for idx in remaining_detections:
            self.stones.append(
                Stone(all_detections[idx].color,
                      all_detections[idx].sheet_coordinates, timestamp,
                      self.filter_timestep))

    def dict_for_json(self) -> dict:
        return {
            "stones": [stone.dict_for_json() for stone in self.stones],
        }


@dataclass
class TrackingResults:
    state: GameState
    mosaic_detection_times: List[float]
    mosaic_detections: List[MosaicStoneDetections]

    def dict_for_json(self) -> dict:
        return {
            "state":
            self.state.dict_for_json(),
            "mosaic_detections": [
                detection.dict_for_json()
                for detection in self.mosaic_detections
            ],
            "mosaic_detection_times":
            self.mosaic_detection_times,
        }


class CurlingVideo:

    def __init__(self, video_path: str):
        self.video_path = video_path

        cap = cv.VideoCapture(self.video_path)
        self.fps = cap.get(cv.CAP_PROP_FPS)
        self.num_frames = int(cap.get(cv.CAP_PROP_FRAME_COUNT))
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

    return camera_mat, distortion, rotation_vecs[0], translation_vecs[0]


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


class StoneDetector:
    """
    A class for detecting curling stones in images using a YOLO model and converting to world coordinates.
    """

    def __init__(self, model_path: str):
        self.model = YOLO(model_path)

    def detect_stones(self, camera: Camera,
                      image: np.ndarray) -> List[StoneDetection]:
        """Detect curling stones in an image and return their position in world coordinates

        Args:
            camera (Camera): The camera that the image came from.
            image (np.ndarray): The image to detect stones in.

        Returns:
            List: The resulting list of stone locations.
        """
        stone_centers = {}
        stone_centers["green"] = []
        stone_centers["yellow"] = []

        stone_boxes = {}
        stone_boxes["green"] = []
        stone_boxes["yellow"] = []
        results = self.model.predict(source=image,
                                     save=False,
                                     save_txt=False,
                                     conf=0.75,
                                     verbose=False)
        for result in results:
            for box in result.boxes:
                x1, y1, x2, y2 = box.xyxy[0]
                x_center = int((x1 + x2) / 2)
                y_center = int((y1 + y2) / 2)
                width = int(x2 - x1)
                height = int(y2 - y1)
                class_id = int(box.cls[0])
                if class_id == 0:
                    stone_centers["green"].append((x_center, y_center))
                    stone_boxes["green"].append(
                        (int(x1), int(y1), width, height))
                elif class_id == 1:
                    stone_centers["yellow"].append((x_center, y_center))
                    stone_boxes["yellow"].append(
                        (int(x1), int(y1), width, height))

        stone_centers["green"] = np.array(stone_centers["green"])
        stone_centers["yellow"] = np.array(stone_centers["yellow"])
        stone_centers["green"] = stone_centers["green"].astype("float32")
        stone_centers["yellow"] = stone_centers["yellow"].astype("float32")

        stones = []
        # Add stones to list
        if len(stone_centers["green"]) != 0:
            green_sheet_coords = image_to_sheet_coordinates(
                camera, stone_centers["green"])

            for image_coords, sheet_coords in zip(stone_boxes["green"],
                                                  green_sheet_coords):
                stones.append(
                    StoneDetection("green", image_coords,
                                   sheet_coords.tolist()))

        if len(stone_centers["yellow"]) != 0:
            yellow_sheet_coords = image_to_sheet_coordinates(
                camera, stone_centers["yellow"])

            for image_coords, sheet_coords in zip(stone_boxes["yellow"],
                                                  yellow_sheet_coords):
                stones.append(
                    StoneDetection("yellow", image_coords,
                                   sheet_coords.tolist()))
        return stones


class Stone:

    def __init__(self, color: str, initial_position: Tuple[float, float],
                 initial_time: float, filter_timestep: float):
        self.color = color
        self.filter_timestep = filter_timestep
        self.filter = self.create_stone_filter(initial_position,
                                               filter_timestep)
        self.position_history = [initial_position]
        self.velocity_history = [(0.0, 0.0)]
        self.acceleration_history = [(0.0, 0.0)]
        self.time_history = [initial_time]
        self.last_measurement_time = initial_time
        self.active = True

    @classmethod
    def create_stone_filter(cls, initial_position, dt):
        #x = [x,y,vx,vy,ax,ay]
        filter = KalmanFilter(dim_x=6, dim_z=2)

        #initial value
        filter.x = np.array(
            [initial_position[0], initial_position[1], 0., 0., 0., 0.])

        #Transition function
        f_x = [1., 0., dt, 0., 0.5 * dt**2, 0.]
        f_y = [0., 1., 0., dt, 0., 0.5 * dt**2]
        f_vx = [0., 0., 1., 0., dt, 0.]
        f_vy = [0., 0., 0., 1., 0., dt]
        f_ax = [0., 0., 0., 0., 1., 0.]
        f_ay = [0., 0., 0., 0., 0., 1.]
        filter.F = np.array([f_x, f_y, f_vx, f_vy, f_ax, f_ay])

        #Measurement function
        filter.H = np.array([[1., 0., 0., 0., 0., 0.],
                             [0., 1., 0., 0., 0., 0.]])

        #Covariance matrix
        filter.P = np.eye(6) * 10
        filter.P[0, 0] = 0.25
        filter.P[1, 1] = 0.25

        filter.R = np.eye(2) * 0.25

        filter.Q = Q_discrete_white_noise(dim=2,
                                          dt=dt,
                                          var=0.1,
                                          block_size=3,
                                          order_by_dim=False)

        return filter

    def update_active_status(self, current_time: float):
        if current_time - self.last_measurement_time > 1.0:
            self.active = False

    def add_measurement(self, position: Tuple[float, float], time: float):
        self.filter.update([position[0], position[1]])
        self.last_measurement_time = time
        self.active = True

    def update_filter(self, time: float):
        self.update_active_status(time)
        if self.active:
            self.filter.predict()
            self.position_history.append((self.filter.x[0], self.filter.x[1]))
            self.velocity_history.append((self.filter.x[2], self.filter.x[3]))
            self.acceleration_history.append(
                (self.filter.x[4], self.filter.x[5]))
            self.time_history.append(time)

    def get_latest_position(self) -> Tuple[float, float]:
        return self.position_history[-1]

    def get_latest_time(self) -> float:
        return self.time_history[-1]

    def dict_for_json(self) -> dict:
        return {
            "color": self.color,
            "position_history": self.position_history,
            "velocity_history": self.velocity_history,
            "acceleration_history": self.acceleration_history,
            "time_history": self.time_history,
        }


def mosaic_image_detect_stones(
        camera_setup: CameraSetup, image: np.ndarray,
        stone_detectors: dict[CameraType,
                              StoneDetector]) -> MosaicStoneDetections:
    all_detections = MosaicStoneDetections({}, {})

    for i, camera in enumerate(camera_setup.cameras):
        # Split image for this camera
        split_image = camera.extract_image(image)
        detections = stone_detectors[camera.camera_type].detect_stones(
            camera, split_image)

        all_detections.images[camera.name] = split_image
        all_detections.detections[camera.name] = detections

    return all_detections


def get_stone_detectors(model_dir: str) -> dict[CameraType, StoneDetector]:
    detectors = {}
    detectors[CameraType.TOP_DOWN] = StoneDetector(
        os.path.join(model_dir, "top_down_stone_detector.pt"))
    detectors[CameraType.ANGLED] = StoneDetector(
        os.path.join(model_dir, "angled_stone_detector.pt"))

    return detectors


def video_stone_tracker(camera_setup: CameraSetup,
                        video: CurlingVideo,
                        stone_detectors: dict[CameraType, StoneDetector],
                        image_save_interval: float = -1.0) -> TrackingResults:

    second_interval = 0.1

    state = GameState(second_interval)
    detection_times = []
    mosaic_detections = []

    for frame_index, frame in video.frame_generator(
            second_interval=second_interval):
        frame_time = float(frame_index) / video.fps

        mosaic_detection = mosaic_image_detect_stones(camera_setup, frame,
                                                      stone_detectors)
        if image_save_interval > 0.0:
            if len(detection_times) == 0:
                detection_times.append(frame_time)
                mosaic_detections.append(mosaic_detection)
            else:
                last_saved_time = detection_times[-1]
                if frame_time - last_saved_time >= image_save_interval:
                    detection_times.append(frame_time)
                    mosaic_detections.append(mosaic_detection)

        state.add_stone_detections(mosaic_detection, frame_time)
        state.update_stones(frame_time)

    return TrackingResults(state, detection_times, mosaic_detections)
