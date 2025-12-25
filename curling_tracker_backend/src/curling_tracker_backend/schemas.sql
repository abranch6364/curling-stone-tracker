CREATE TABLE Cameras (
    camera_id TEXT PRIMARY KEY,
    camera_matrix MATRIX,
    distortion_coefficients MATRIX,
    rotation_vectors MATRIX,
    translation_vectors MATRIX
);