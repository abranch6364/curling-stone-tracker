from dataclasses import dataclass
from typing import Tuple

from matplotlib.pyplot import gray
import cv2 as cv
import numpy as np  
import sheet_coordinates as sheet

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

def main():
    image_path = 'data/example_sheet.png'
    image = cv.imread(image_path)

    image_coords = {}
    image_coords['middle_hog'] = (126,507)
    image_coords['left_hog'] = (21,503)
    image_coords['right_hog'] = (232,499)

    image_coords['pin'] = (122,131)
    image_coords['left_tee_12'] = (15,135)
    image_coords['left_tee_8'] = (49,134)
    image_coords['left_tee_4'] = (87,132)
    image_coords['right_tee_12'] = (131,133)
    image_coords['right_tee_8'] = (197,132)
    image_coords['right_tee_4'] = (159,131)
    image_coords['top_center_12'] = (123,258)
    image_coords['top_center_8'] = (123,217)
    image_coords['top_center_4'] = (122,173)
    image_coords['back_center_12'] = (122,8)
    image_coords['back_center_8'] = (122,47)
    image_coords['back_center_4'] = (122,90)

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

    pin = np.array([sheet.COORDINATES["side_a"]["pin"]])
    pin = pin.astype('float32')

    left = np.array([sheet.COORDINATES["side_a"]["left_tee_12"]])
    left = left.astype('float32')

    left_hog = np.array([sheet.COORDINATES["side_a"]["left_hog"]])
    left_hog = left_hog.astype('float32')

    print(project_points(camera, pin))
    print(project_points(camera, left))
    print(project_points(camera, left_hog))

     # Project 3D points to image plane
    print("Error in projection : \n", ret)
   # print("\nCamera matrix : \n", camera_mat)
   # print("\nDistortion coefficients : \n", distortion)
   # print("\nRotation vector : \n", rotation_vecs)
   # print("\nTranslation vector : \n", translation_vecs)

    newcameramtx, roi = cv.getOptimalNewCameraMatrix(camera.camera_matrix, camera.distortion_coefficients, image_shape, 1.0, image_shape)
    dst = cv.undistort(image, camera.camera_matrix, camera.distortion_coefficients, None, newcameramtx)
    
    # crop the image
  #  x, y, w, h = roi
  #  dst = dst[y:y+h, x:x+w]
    cv.imwrite('data/example_sheet_undistorted.png', dst)

def project_points(camera: Camera, points_3d: np.ndarray) -> np.ndarray:
    projected_points, _ = cv.projectPoints(points_3d, camera.rotation_vectors, camera.translation_vectors, camera.camera_matrix, camera.distortion_coefficients)
    return projected_points

if __name__ == "__main__":
    main()