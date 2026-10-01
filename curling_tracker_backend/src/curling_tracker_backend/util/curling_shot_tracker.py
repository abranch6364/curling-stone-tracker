from dataclasses import dataclass
from enum import Enum
import enum
import os
from typing import Generator, Iterator, List, Optional, Tuple
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

# Standard deviation (ft) of a stone's position measured from a camera
MEASUREMENT_STD_FEET = 0.25
# Standard deviation (ft) of a measured position between the hog lines, where the cameras' calibrations
# are least accurate
MEASUREMENT_STD_BETWEEN_HOGS_FEET = 1.0
# Stones whose centres come within this distance (ft) are treated as colliding. A stone is about
# 0.96 ft across, with some margin for position error.
COLLISION_DISTANCE_FEET = 1.5
# Standard deviation of the sudden change in velocity (ft/s) and acceleration (ft/s^2) a collision can
# cause, used so the smoother doesn't spread a collision's effect over the time before it
COLLISION_VELOCITY_STD = 5.0
COLLISION_ACCELERATION_STD = 5.0
# Detections whose box is within this many pixels of the image edge are partly outside the image
CLIPPED_BOX_MARGIN_PIXELS = 2
# Longest time a stone can go undetected and still have its two tracks merged
MAX_TRACK_GAP_SECONDS = 6.0
# Speed (ft/s) above which a track that ends is treated as a moving stone when merging
MERGE_MOVING_SPEED = 1.0
# Furthest (ft) a moving stone's next track can start from its line of travel
MERGE_MAX_SIDEWAYS_OFFSET = 2.0
# Furthest (ft) a stone at rest's next track can start from where it was
MERGE_MAX_RESTING_OFFSET = 1.0


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
    clipped: bool = False

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

    def __init__(self, filter_timestep, stones=None):
        # A shared default list would carry stones over between tracking runs
        self.stones: List[Stone] = stones if stones is not None else []
        self.filter_timestep = filter_timestep

    def get_filtered_state(self,
                           num_detections_threshold: int = 5,
                           velocity_threshold: float = 50.0):
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
                if detection.overlapping or detection.clipped:
                    continue

                # Ignore stones beyond the back lines (e.g. waiting by the hack), they are out of play
                if not (SHEET_COORDINATES["home_back_center_12"][1] <=
                        detection.sheet_coordinates[1] <=
                        SHEET_COORDINATES["away_back_center_12"][1]):
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

    def is_clipped(self, detection, image: np.ndarray) -> bool:
        """Check if a detection touches the edge of the image. Part of the stone is then outside the
        image, so the box (and the sheet position computed from it) is wrong.
        """
        x, y, width, height = detection.image_coordinates
        image_height, image_width = image.shape[:2]
        margin = CLIPPED_BOX_MARGIN_PIXELS

        return (x <= margin or y <= margin
                or x + width >= image_width - 1 - margin
                or y + height >= image_height - 1 - margin)

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
            stone.clipped = self.is_clipped(stone, image)

        return stones


def measurement_noise(position: Tuple[float, float]) -> np.ndarray:
    """The measurement noise covariance of a stone position measured at a point on the sheet.

    Args:
        position (Tuple[float, float]): The measured sheet position

    Returns:
        np.ndarray: The 2x2 measurement noise covariance
    """
    hog_line = SHEET_COORDINATES["away_middle_hog"][1]
    std = (MEASUREMENT_STD_BETWEEN_HOGS_FEET
           if abs(position[1]) < hog_line else MEASUREMENT_STD_FEET)
    return np.eye(2) * std**2


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
        self.state_history = [self.filter.x.copy()]
        self.covariance_history = [self.filter.P.copy()]
        self.measurement_history = [(initial_time, tuple(initial_position))]
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
        filter.F, filter.Q = cls.motion_model(dt)

        #Measurement function
        filter.H = np.array([[1., 0., 0., 0., 0., 0.],
                             [0., 1., 0., 0., 0., 0.]])

        #Covariance matrix
        filter.P = np.eye(6) * 10
        filter.P[0, 0] = 0.25
        filter.P[1, 1] = 0.25

        filter.R = np.eye(2) * MEASUREMENT_STD_FEET**2

        return filter

    @staticmethod
    def motion_model(dt: float) -> Tuple[np.ndarray, np.ndarray]:
        """The constant acceleration motion model of a stone's filter.

        Args:
            dt (float): The timestep of the model

        Returns:
            Tuple[np.ndarray, np.ndarray]: The state transition matrix F and process noise Q
        """
        f_x = [1., 0., dt, 0., 0.5 * dt**2, 0.]
        f_y = [0., 1., 0., dt, 0., 0.5 * dt**2]
        f_vx = [0., 0., 1., 0., dt, 0.]
        f_vy = [0., 0., 0., 1., 0., dt]
        f_ax = [0., 0., 0., 0., 1., 0.]
        f_ay = [0., 0., 0., 0., 0., 1.]
        F = np.array([f_x, f_y, f_vx, f_vy, f_ax, f_ay])

        Q = Q_discrete_white_noise(dim=2,
                                   dt=dt,
                                   var=0.1,
                                   block_size=3,
                                   order_by_dim=False)
        return F, Q

    def update_active_status(self, current_time: float):
        if current_time - self.last_measurement_time > 1.0:
            self.active = False

    def add_measurement(self, position: Tuple[float, float], time: float):
        if self.last_measurement_time is None or time > self.last_measurement_time:
            self.num_frames_visible += 1

        self.filter.update([position[0], position[1]],
                           R=measurement_noise(position))
        self.measurement_history.append((time, tuple(position[:2])))
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
            self.state_history.append(self.filter.x.copy())
            self.covariance_history.append(self.filter.P.copy())

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
            "position_covariance_history":
            [covariance[:2, :2].tolist() for covariance in self.covariance_history],
        }


def bhattacharyya_distance_gaussian(mu1: np.ndarray, mu2: np.ndarray,
                                    cov1: np.ndarray,
                                    cov2: np.ndarray) -> float:
    """Calculate the Bhattacharyya distance between two Gaussian distributions.
    
    Args:
        mu1 (np.ndarray): Mean of the first distribution.
        mu2 (np.ndarray): Mean of the second distribution.
        cov1 (np.ndarray): Covariance of the first distribution.
        cov2 (np.ndarray): Covariance of the second distribution.

    Returns:
        float: The Bhattacharyya distance between the two distributions.
    """
    cov_avg = (cov1 + cov2) / 2
    inv_cov_avg = np.linalg.inv(cov_avg)

    diff_mu = mu1 - mu2
    term1 = 0.125 * diff_mu.T @ inv_cov_avg @ diff_mu

    det_cov1 = np.linalg.det(cov1)
    det_cov2 = np.linalg.det(cov2)
    det_cov_avg = np.linalg.det(cov_avg)

    term2 = 0.5 * np.log(det_cov_avg / np.sqrt(det_cov1 * det_cov2))

    return term1 + term2


def _last_measurement_index(stone: Stone) -> int:
    """The index into a stone's histories of its last measurement."""
    return max(i for i, t in enumerate(stone.time_history)
               if t <= stone.last_measurement_time)


def _track_merge_cost(earlier: Stone, later: Stone) -> Optional[float]:
    """Check if a later track can be the continuation of an earlier one, using how a curling stone
    moves rather than the filter's prediction. Positions far from the calibration points (e.g. near
    the centre line) can be several feet off, which makes long predictions unreliable.

    A moving stone keeps going the same way and only slows down, so the later track has to start
    ahead of it, close to its line of travel, at an average speed no higher than its last speed.
    A stone at rest has to reappear where it was.

    Returns:
        Optional[float]: The distance in feet from where the later track was expected to start, or
            None if it can't be a continuation.
    """
    end_time, end_position = earlier.measurement_history[-1]
    start_time, start_position = later.measurement_history[0]
    gap = start_time - end_time

    end_velocity = earlier.state_history[_last_measurement_index(earlier)][2:4]
    end_speed = float(np.linalg.norm(end_velocity))
    offset = np.asarray(start_position[:2]) - np.asarray(end_position[:2])

    if end_speed <= MERGE_MOVING_SPEED:
        distance = float(np.linalg.norm(offset))
        return distance if distance <= MERGE_MAX_RESTING_OFFSET else None

    direction = end_velocity / end_speed
    along = float(offset @ direction)
    sideways = float(np.linalg.norm(offset - along * direction))
    if along <= 0.0 or sideways > MERGE_MAX_SIDEWAYS_OFFSET or along / gap > end_speed:
        return None

    return sideways


def _merge_tracks(earlier: Stone, later: Stone):
    """Merge a later track into an earlier one. The gap between them is filled in by smooth_track."""
    # Keep the earlier track up to its last measurement, dropping the predictions after it
    keep = _last_measurement_index(earlier) + 1
    for name in [
            "position_history", "velocity_history", "acceleration_history",
            "time_history", "state_history", "covariance_history"
    ]:
        setattr(earlier, name,
                getattr(earlier, name)[:keep] + getattr(later, name))

    earlier.measurement_history = sorted(earlier.measurement_history +
                                         later.measurement_history,
                                         key=lambda m: m[0])
    earlier.num_frames_visible += later.num_frames_visible
    earlier.last_measurement_time = later.last_measurement_time
    earlier.active = later.active
    earlier.filter = later.filter


def find_collisions(stones: List[Stone],
                    timestep: float) -> dict[int, List[float]]:
    """Find when stones collide, as the times their tracks come closest while within
    COLLISION_DISTANCE_FEET of each other.

    Args:
        stones (List[Stone]): The tracked stones
        timestep (float): The timestep the stones were tracked at

    Returns:
        dict[int, List[float]]: The collision times of each stone, keyed by its index in stones.
    """
    collisions = {index: [] for index in range(len(stones))}

    def positions_at(stone: Stone, times: np.ndarray) -> np.ndarray:
        return np.stack([
            np.interp(times, stone.time_history,
                      [p[axis] for p in stone.position_history])
            for axis in range(2)
        ],
                        axis=1)

    for i, first in enumerate(stones):
        for j in range(i + 1, len(stones)):
            second = stones[j]
            start = max(first.time_history[0], second.time_history[0])
            end = min(first.time_history[-1], second.time_history[-1])
            if end <= start:
                continue

            times = np.arange(start, end + timestep / 2, timestep)
            distances = np.linalg.norm(
                positions_at(first, times) - positions_at(second, times),
                axis=1)

            # Each run of times within the collision distance is one collision, at its closest point
            close = distances <= COLLISION_DISTANCE_FEET
            run_start = None
            for k in range(len(times) + 1):
                if k < len(times) and close[k]:
                    run_start = k if run_start is None else run_start
                elif run_start is not None:
                    closest = run_start + int(np.argmin(distances[run_start:k]))
                    collisions[i].append(float(times[closest]))
                    collisions[j].append(float(times[closest]))
                    logger.info(
                        f"Collision between {first.color.name} and {second.color.name} stones at {times[closest]:.1f}s"
                    )
                    run_start = None

    return collisions


def smooth_track(stone: Stone,
                 timestep: float,
                 collision_times: List[float] = ()):
    """Replace a stone's history with a Kalman filter run over all of its measurements followed by an
    RTS smoother. Each point then uses the measurements after it as well as before it, which removes
    the filter's lag and jitter and fills any gaps (e.g. from merged tracks) using both sides.

    Args:
        stone (Stone): The stone to smooth
        timestep (float): The timestep the stone was tracked at
        collision_times (List[float], optional): Times the stone collided with another. Its velocity
            can change suddenly there, rather than the smoother easing into the change beforehand.
    """
    start_time = stone.time_history[0]
    end_time = stone.time_history[-1]

    def step_of(time: float) -> int:
        return int(round((time - start_time) / timestep))

    measurements_by_step = {}
    for time, position in stone.measurement_history:
        measurements_by_step.setdefault(step_of(time), []).append(position)

    collision_steps = {step_of(time) for time in collision_times}
    collision_noise = np.diag([
        0.0, 0.0, COLLISION_VELOCITY_STD**2, COLLISION_VELOCITY_STD**2,
        COLLISION_ACCELERATION_STD**2, COLLISION_ACCELERATION_STD**2
    ])

    kalman_filter = Stone.create_stone_filter(
        stone.measurement_history[0][1], timestep)
    states, covariances, process_noises = [], [], []
    for step in range(step_of(end_time) + 1):
        # The process noise used to step into this point, larger where a collision can change the motion
        process_noise = kalman_filter.Q + (collision_noise if step
                                           in collision_steps else 0.0)
        if step > 0:
            kalman_filter.predict(Q=process_noise)
        for position in measurements_by_step.get(step, []):
            kalman_filter.update([position[0], position[1]],
                                 R=measurement_noise(position))
        states.append(kalman_filter.x.copy())
        covariances.append(kalman_filter.P.copy())
        process_noises.append(process_noise)
    smoothed_states, smoothed_covariances, _, _ = kalman_filter.rts_smoother(
        np.array(states), np.array(covariances), Qs=np.array(process_noises))

    stone.time_history = [
        start_time + step * timestep for step in range(len(smoothed_states))
    ]
    stone.position_history = [(x[0], x[1]) for x in smoothed_states]
    stone.velocity_history = [(x[2], x[3]) for x in smoothed_states]
    stone.acceleration_history = [(x[4], x[5]) for x in smoothed_states]
    stone.state_history = list(smoothed_states)
    stone.covariance_history = list(smoothed_covariances)


def merge_track_gaps(stones: List[Stone],
                     timestep: float,
                     max_gap: float = MAX_TRACK_GAP_SECONDS) -> List[Stone]:
    """Merge tracks of the same stone that were split because it went undetected for a while.

    Args:
        stones (List[Stone]): The tracked stones
        timestep (float): The timestep the stones were tracked at
        max_gap (float, optional): The longest gap in seconds to merge across.

    Returns:
        List[Stone]: The stones with split tracks merged.
    """
    stones = list(stones)
    while True:
        # Merge the most likely pair first, then look again since merging changes the candidates
        best = None
        for earlier in stones:
            for later in stones:
                if earlier is later or earlier.color != later.color:
                    continue

                gap = later.measurement_history[0][
                    0] - earlier.last_measurement_time
                if not (timestep / 2 < gap <= max_gap):
                    continue

                cost = _track_merge_cost(earlier, later)
                if cost is not None and (best is None or cost < best[0]):
                    best = (cost, earlier, later)

        if best is None:
            return stones

        cost, earlier, later = best
        logger.info(
            f"Merging {earlier.color.name} track ending at {earlier.last_measurement_time:.1f}s with track starting at {later.measurement_history[0][0]:.1f}s ({cost=:.2f})"
        )
        _merge_tracks(earlier, later)
        stones.remove(later)


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

    state.stones = merge_track_gaps(state.stones, second_interval)
    collisions = find_collisions(state.stones, second_interval)
    for index, stone in enumerate(state.stones):
        smooth_track(stone, second_interval, collisions[index])

    return TrackingResults(state.get_filtered_state(), detection_times,
                           mosaic_detections)
