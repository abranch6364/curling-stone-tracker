CREATE TABLE CameraSetups (
    setup_id TEXT PRIMARY KEY,
    setup_name TEXT
);

CREATE TABLE Cameras (
    camera_id TEXT PRIMARY KEY,
    setup_id TEXT,
    camera_name TEXT,
    FOREIGN KEY (setup_id) REFERENCES CameraSetups(setup_id)
);

CREATE TABLE CameraCalibrations (
    camera_id TEXT PRIMARY KEY,
    camera_matrix MATRIX,
    distortion_coefficients MATRIX,
    rotation_vectors MATRIX,
    translation_vectors MATRIX
);