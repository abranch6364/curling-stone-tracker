from dataclasses import dataclass
from typing import Tuple

from matplotlib.pyplot import gray
import cv2 as cv
import numpy as np  
import sheet_coordinates as sheet
import curling_sheet_plotting as sheet_plot

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
    image_coords['left_tee_8'] = (56,143)
    image_coords['left_tee_4'] = (93,142)
    image_coords['right_tee_12'] = (235,143)
    image_coords['right_tee_8'] = (202,141)
    image_coords['right_tee_4'] = (165,141)
    image_coords['top_center_12'] = (130,266)
    image_coords['top_center_8'] = (130,226)
    image_coords['top_center_4'] = (130,182)
    image_coords['back_center_12'] = (127,18)
    image_coords['back_center_8'] = (128,57)
    image_coords['back_center_4'] = (129,98)

    image_coords['left_back_corner'] = (5,26)
    image_coords['right_back_corner'] = (252,25)

    image_shape = list(image.shape[0:2][::-1])

    imgpoints = []
    objpoints = []
    for k,v in image_coords.items():
        imgpoints.append(v)
        coord = sheet.COORDINATES["side_a"][k]
        objpoints.append(sheet.COORDINATES["side_a"][k])

    imgpoints = np.array([imgpoints])
    objpoints = np.array([objpoints])
    imgpoints = imgpoints.astype('float32')
    objpoints = objpoints.astype('float32')

    ret, camera_mat, distortion, rotation_vecs, translation_vecs = cv.calibrateCamera(objpoints, imgpoints, image_shape, None, None)
    camera = Camera(camera_mat, distortion, rotation_vecs[0], translation_vecs[0])

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

def output_undistorted_image(camera: Camera, image: np.ndarray) -> np.ndarray:
    image_shape = list(image.shape[0:2][::-1])
    newcameramtx, roi = cv.getOptimalNewCameraMatrix(camera.camera_matrix, camera.distortion_coefficients, image_shape, 1.0, image_shape)
    undistorted_image = cv.undistort(image, camera.camera_matrix, camera.distortion_coefficients, None, newcameramtx)
    return undistorted_image

def main():
    image_path = 'data/example_sheet.png'
    image = cv.imread(image_path)

    camera = create_camera()

    undistort_test = np.array([(142,290),(144,160),(129,492)])

    undistort_test = undistort_test.astype('float32')
    sheet_coords = image_to_sheet_coordinates(camera, undistort_test)

    fig, ax = plt.subplots()
    sheet_plot.plot_sheet_side_a(fig, ax)
    sheet_plot.set_sheet_plot_limits(ax)
    sheet_plot.plot_stones(ax, sheet_coords, color='green')
    plt.show()

    cv.imwrite('data/example_sheet_undistorted.png', output_undistorted_image(camera, image))

if __name__ == "__main__":
    main()