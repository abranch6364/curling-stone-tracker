CREATE TABLE Cameras (
    camera_id TEXT PRIMARY KEY,
    setup_id TEXT FOREIGN KEY REFERENCES CameraSetups(setup_id),
    camera_name TEXT,
    camera_matrix MATRIX,
    distortion_coefficients MATRIX,
    rotation_vectors MATRIX,
    translation_vectors MATRIX
);

CREATE TABLE CameraSetups (
    setup_id TEXT PRIMARY KEY,
    setup_name TEXT
);