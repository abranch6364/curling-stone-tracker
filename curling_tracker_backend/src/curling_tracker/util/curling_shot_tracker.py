from dataclasses import dataclass
from typing import Tuple
import munkres
from ultralytics import YOLO

from matplotlib.pyplot import gray
import cv2 as cv
import numpy as np  
import curling_tracker.sheet_coordinates as sheet
import curling_tracker.util.curling_sheet_plotting as sheet_plot
import curling_tracker.util.curling_image_processing as cip
import matplotlib.pyplot as plt

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

def create_camera():
    image_path = 'data/example_sheet.png'
    image = cv.imread(image_path)

    image_coords = {}
    image_coords['middle_hog'] = (130,507)
    image_coords['left_hog'] = (27,502)
    image_coords['right_hog'] = (233,500)

    image_coords['pin'] = (129,140)
    image_coords['left_tee_12'] = (22,144)
    image_coords['left_tee_8'] = (55,142)
    image_coords['left_tee_4'] = (93,140)
    image_coords['right_tee_12'] = (235,141)
    image_coords['right_tee_8'] = (202,140)
    image_coords['right_tee_4'] = (165,141)
    image_coords['top_center_12'] = (130,266)
    image_coords['top_center_8'] = (130,226)
    image_coords['top_center_4'] = (130,182)
    image_coords['back_center_12'] = (127,18)
    image_coords['back_center_8'] = (128,56)
    image_coords['back_center_4'] = (129,98)

    image_coords['left_backline_corner'] = (-2,24)
    image_coords['right_backline_corner'] = (259,24)

    image_shape = list(image.shape[0:2][::-1])
    print("IMAGE SHAPE : ", image_shape)

    imgpoints = []
    objpoints = []
    for k,v in image_coords.items():
        imgpoints.append(v)
        coord = sheet.SHEET_COORDINATES["side_a"][k]
        objpoints.append(sheet.SHEET_COORDINATES["side_a"][k])

    print("imgpoints : ", imgpoints)
    print("objpoints : ", objpoints)

    imgpoints = np.array([imgpoints])
    objpoints = np.array([objpoints])
    imgpoints = imgpoints.astype('float32')
    objpoints = objpoints.astype('float32')

    ret, camera_mat, distortion, rotation_vecs, translation_vecs = cv.calibrateCamera(objpoints, imgpoints, image_shape, None, None)
    camera = Camera(camera_mat, distortion, rotation_vecs[0], translation_vecs[0])

    print("Camera Matrix : \n", camera.camera_matrix)
    print("Error in projection : \n", ret)

    return camera

def sheet_to_image_coordinates(camera: Camera, points_3d: np.ndarray) -> np.ndarray:
    projected_points, _ = cv.projectPoints(points_3d, camera.rotation_vectors, camera.translation_vectors, camera.camera_matrix, camera.distortion_coefficients)
    return projected_points

def image_to_sheet_coordinates(camera: Camera, image_points: np.ndarray) -> np.ndarray:
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
    image_shape = list(image.shape[0:2][::-1])
    newcameramtx, roi = cv.getOptimalNewCameraMatrix(camera.camera_matrix, camera.distortion_coefficients, image_shape, 1.0, image_shape)
    undistorted_image = cv.undistort(image, camera.camera_matrix, camera.distortion_coefficients, None, newcameramtx)
    return undistorted_image

class StoneDetector:
    def __init__(self, model_path: str):
        self.model = YOLO(model_path)

    def detect_stones(self, image) -> dict:
        stones = {}
        stones['green'] = []
        stones['yellow'] = []

        results = self.model.predict(source=image, save=False, save_txt=False, conf=0.5)
        for result in results:
            for box in result.boxes:
                x1, y1, x2, y2 = box.xyxy[0]
                x_center = int((x1 + x2) / 2)
                y_center = int((y1 + y2) / 2)
                class_id = int(box.cls[0])
                if class_id == 0:
                    stones['green'].append((x_center, y_center))
                elif class_id == 1:
                    stones['yellow'].append((x_center, y_center))

        stones['green'] = np.array(stones['green'])
        stones['yellow'] = np.array(stones['yellow'])
        stones['green'] = stones['green'].astype('float32')
        stones['yellow'] = stones['yellow'].astype('float32')

        return stones

def distance(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    return np.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

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

def main():
    #image_path = 'data/example_sheet_stones2.png'
    #image = cv.imread(image_path)

    #video_path = 'C:\\Users\\abran\\Desktop\\curling_videos\\full_example_video.mp4'
    #cap = cv.VideoCapture(video_path)
    camera = create_camera()
    
    game = GameState()
    stone_detector = StoneDetector('./curling_tracker_backend/src/curling_tracker/model/top_down_stone_detector.pt') 

    #start_frame = (43*60 + 53) * cap.get(cv.CAP_PROP_FPS)
    #end_frame = (44*60 + 7) * cap.get(cv.CAP_PROP_FPS)

    start_frame = (2*3600 + 36*60 + 38) * cap.get(cv.CAP_PROP_FPS)
    end_frame = (2*3600 + 36*60 + 49) * cap.get(cv.CAP_PROP_FPS)

    cap.set(cv.CAP_PROP_POS_FRAMES, start_frame)

    frame_count = 0
    frame_interval = 1
    print("Starting processing video...")
    while cap.isOpened():
        ret, frame = cap.read()

        if not ret or cap.get(cv.CAP_PROP_POS_FRAMES) > end_frame:
            print("End of video or error reading frame.")
            break

        if frame_count % frame_interval != 0:
            frame_count += 1
            continue

        top_down_a, top_down_b, angled_a, angled_b = cip.split_stream_frame(frame)
        image = top_down_a
        undistorted_image = undistort_image(camera, image)

        stones = stone_detector.detect_stones(undistorted_image)   

        green_stones = stones['green']
        yellow_stones = stones['yellow']

        green_sheet_coords = image_to_sheet_coordinates(camera, green_stones)
        yellow_sheet_coords = image_to_sheet_coordinates(camera, yellow_stones)

        stone_positions = {'green': [(p[0], p[1]) for p in green_sheet_coords],
                           'yellow': [(p[0], p[1]) for p in yellow_sheet_coords]}

        game.add_stone_detections(stone_positions)
        frame_count += 1


    fig, ax = plt.subplots()
    sheet_plot.plot_sheet_side_a(fig, ax)
    sheet_plot.set_sheet_plot_limits(ax)
    for rock in game.rocks:
        if len(rock.position_history) > 50:
            sheet_plot.plot_stone(ax, rock.get_latest_position(), rock.position_history, color=rock.color)

    plt.show()

def new_stone_test():
    game = GameState()
    game.add_stone_detections({'green': [(0.0, 0.0), (5.0, 5.0)],
                             'yellow': [(2.0, 2.0)]})
    
    game.add_stone_detections({'green': [(0.5, 0.5), (5.5, 5.5)],
                             'yellow': [(2.5, 2.5)]})
    
    game.add_stone_detections({'green': [(0.75, 0.75), (5.75, 5.75)],
                            'yellow': [(2.75, 2.75), (10.0, 10.0)]})

    game.add_stone_detections({'green': [(0.75, 0.75), (5.75, 5.75)],
                            'yellow': [(10.5, 10.5)]})

    game.add_stone_detections({'green': [],
                            'yellow': []})

    for rock in game.rocks:
        print(f"Rock color: {rock.color}, Position history: {rock.position_history}")

if __name__ == "__main__":
    main()