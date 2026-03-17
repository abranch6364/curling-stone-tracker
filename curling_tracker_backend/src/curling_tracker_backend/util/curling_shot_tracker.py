from dataclasses import dataclass
from enum import Enum
import enum
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

from curling_tracker_backend.util.sheet_coordinates import SHEET_COORDINATES
import curling_tracker_backend.util.camera_utilities as camera_utilities

logger = logging.getLogger(__name__)


class StoneClass(enum.Enum):
    BLUE = 0
    GREEN = 1
    RED = 2
    YELLOW = 3


@dataclass
class CameraSetup:
    id: str
    name: str
    cameras: List[camera_utilities.Camera]


@dataclass
class StoneDetection:
    color: StoneClass
    image_coordinates: Tuple[float, float, float, float]
    sheet_coordinates: Tuple[float, float, float]
    overlapping: bool

    def dict_for_json(self) -> dict:
        return {
            "color": self.color.name.lower(),
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

    def __init__(self, filter_timestep, stones=[]):
        self.stones: List[Stone] = stones
        self.filter_timestep = filter_timestep

    def get_filtered_state(self,
                           num_detections_threshold: int = 5,
                           velocity_threshold: float = 5.0):
        filtered_stones = []

        for stone in self.stones:
            if stone.num_frames_visible < num_detections_threshold:
                continue
            if stone.get_max_velocity() > velocity_threshold:
                continue
            filtered_stones.append(stone)

        return GameState(self.filter_timestep, stones=filtered_stones)

    def update_stones(self, timestamp: float):
        for stone in self.stones:
            stone.update_filter(timestamp)

    def add_stone_detections(self, new_detections: MosaicStoneDetections,
                             timestamp: float):
        for camera_detections in new_detections.detections.values():
            filtered_detections = []

            for detection in camera_detections:
                if detection.overlapping:
                    continue

                if not (SHEET_COORDINATES["away_middle_hog"][1] <=
                        detection.sheet_coordinates[1] <=
                        SHEET_COORDINATES["away_back_center_12"][1]
                        or SHEET_COORDINATES["home_back_center_12"][1] <=
                        detection.sheet_coordinates[1] <=
                        SHEET_COORDINATES["home_middle_hog"][1]):
                    continue

                filtered_detections.append(detection)

            if len(self.stones) == 0:
                for detection in filtered_detections:
                    self.stones.append(
                        Stone(detection.color, detection.sheet_coordinates,
                              timestamp, self.filter_timestep))
                continue

            if len(filtered_detections) == 0:
                continue

            matrix = []
            for val1 in self.stones:
                if not val1.active:
                    new_row = [1000001.0] * len(filtered_detections)
                    matrix.append(new_row)
                    continue

                new_row = []
                for val2 in filtered_detections:
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

            remaining_detections = set(range(len(filtered_detections)))
            for r, c in zip(*best_idxs):
                if matrix[r][c] >= 1000000.0:
                    continue

                self.stones[r].add_measurement(
                    filtered_detections[c].sheet_coordinates, timestamp)
                remaining_detections.remove(c)

            for idx in remaining_detections:
                self.stones.append(
                    Stone(filtered_detections[idx].color,
                          filtered_detections[idx].sheet_coordinates,
                          timestamp, self.filter_timestep))

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


def distance(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    """Find the distance between two points

    Args:
        p1 (Tuple[float, float]): Point 1
        p2 (Tuple[float, float]): Point 2

    Returns:
        float: The distance between the points
    """
    return np.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)


class StoneDetector:
    """
    A class for detecting curling stones in images using a YOLO model and converting to world coordinates.
    """

    def __init__(self, model_path: str):
        self.model = YOLO(model_path)

    def is_overlapping(self, detection, all_detections):
        x, y, width, height = detection.image_coordinates

        for other in all_detections:
            if other is detection:
                continue

            ox, oy, owidth, oheight = other.image_coordinates

            overlap_x = not (x + width <= ox or x >= ox + owidth)
            overlap_y = not (y + height <= oy or y >= oy + oheight)

            if overlap_x and overlap_y:
                return True

        return False

    def convert_to_sheet_coords(
        self, camera: camera_utilities.Camera,
        image_coords: List[Tuple[float, float, float, float]]
    ) -> List[Tuple[float, float, float]]:

        if camera.camera_type == camera_utilities.CameraType.ANGLED:
            pixel_coords = []
            for coord in image_coords:
                x, y, width, height = coord
                pixel_x = x + width / 2
                pixel_y = y + height
                pixel_coords.append((pixel_x, pixel_y))

            pixel_coords = np.array(pixel_coords, dtype="float32")

            sheet_coords = camera_utilities.image_to_world_coordinates(
                camera, pixel_coords)

            #The angled camera uses the center base of the stone to convert to sheet coordinates
            #since it is on the ice. Shift that away from the camera by half a stone diameter.
            #sheet_coords[:, 1] += np.sign(sheet_coords[:, 1]) * 0.479

            return [tuple(coord) for coord in sheet_coords]

        elif camera.camera_type == camera_utilities.CameraType.TOP_DOWN:
            pixel_coords = []
            for coord in image_coords:
                x, y, width, height = coord
                center_x = x + width / 2
                center_y = y + height / 2
                pixel_coords.append((center_x, center_y))

            pixel_coords = np.array(pixel_coords, dtype="float32")

            sheet_coords = camera_utilities.image_to_world_coordinates(
                camera, pixel_coords)
            return [tuple(coord) for coord in sheet_coords]

        return []

    def detect_stones(self, camera: camera_utilities.Camera,
                      image: np.ndarray) -> List[StoneDetection]:
        """Detect curling stones in an image and return their position in world coordinates

        Args:
            camera (Camera): The camera that the image came from.
            image (np.ndarray): The image to detect stones in.

        Returns:
            List: The resulting list of stone locations.
        """
        stone_boxes = {}
        stone_boxes[StoneClass.GREEN] = []
        stone_boxes[StoneClass.YELLOW] = []
        results = self.model.predict(source=image,
                                     save=False,
                                     save_txt=False,
                                     conf=0.75,
                                     verbose=False)
        for result in results:
            for box in result.boxes:
                x1, y1, x2, y2 = box.xyxy[0]
                width = int(x2 - x1)
                height = int(y2 - y1)
                class_id = StoneClass(int(box.cls[0]))
                stone_boxes[class_id].append((int(x1), int(y1), width, height))

        stones = []
        # Add stones to list
        if len(stone_boxes[StoneClass.GREEN]) != 0:
            green_sheet_coords = self.convert_to_sheet_coords(
                camera, stone_boxes[StoneClass.GREEN])

            for image_coords, sheet_coords in zip(
                    stone_boxes[StoneClass.GREEN], green_sheet_coords):
                stones.append(
                    StoneDetection(StoneClass.GREEN, image_coords,
                                   sheet_coords, False))

        if len(stone_boxes[StoneClass.YELLOW]) != 0:
            yellow_sheet_coords = self.convert_to_sheet_coords(
                camera, stone_boxes[StoneClass.YELLOW])

            for image_coords, sheet_coords in zip(
                    stone_boxes[StoneClass.YELLOW], yellow_sheet_coords):
                stones.append(
                    StoneDetection(StoneClass.YELLOW, image_coords,
                                   sheet_coords, False))

        #Update the overlapping check now that we have all the detections
        for stone in stones:
            stone.overlapping = self.is_overlapping(stone, stones)

        return stones


class Stone:

    def __init__(self, color: StoneClass, initial_position: Tuple[float,
                                                                  float],
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
        self.num_frames_visible = 0

    def get_max_velocity(self):
        if len(self.velocity_history) == 0:
            return 0.0
        return max(np.sqrt(v[0]**2 + v[1]**2) for v in self.velocity_history)

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
        if self.last_measurement_time is None or time > self.last_measurement_time:
            self.num_frames_visible += 1

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
            "color": self.color.name.lower(),
            "position_history": self.position_history,
            "velocity_history": self.velocity_history,
            "acceleration_history": self.acceleration_history,
            "time_history": self.time_history,
        }


def mosaic_image_detect_stones(
    camera_setup: CameraSetup, image: np.ndarray,
    stone_detectors: dict[camera_utilities.CameraType, StoneDetector]
) -> MosaicStoneDetections:
    all_detections = MosaicStoneDetections({}, {})

    for i, camera in enumerate(camera_setup.cameras):
        # Split image for this camera
        split_image = camera.extract_image(image)
        detections = stone_detectors[camera.camera_type].detect_stones(
            camera, split_image)

        all_detections.images[camera.name] = split_image
        all_detections.detections[camera.name] = detections

    return all_detections


def get_stone_detectors(
        model_dir: str) -> dict[camera_utilities.CameraType, StoneDetector]:
    detectors = {}
    detectors[camera_utilities.CameraType.TOP_DOWN] = StoneDetector(
        os.path.join(model_dir, "top_down_stone_detector.pt"))
    detectors[camera_utilities.CameraType.ANGLED] = StoneDetector(
        os.path.join(model_dir, "angled_stone_detector.pt"))

    return detectors


def video_stone_tracker(camera_setup: CameraSetup,
                        video: CurlingVideo,
                        stone_detectors: dict[camera_utilities.CameraType,
                                              StoneDetector],
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

    return TrackingResults(state.get_filtered_state(), detection_times,
                           mosaic_detections)
