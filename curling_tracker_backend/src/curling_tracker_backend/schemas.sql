CREATE TABLE CameraSetups (
    setup_id TEXT PRIMARY KEY,
    setup_name TEXT
)  IF NOT EXISTS CameraSetups;

CREATE TABLE Cameras (
    camera_id TEXT PRIMARY KEY,
    setup_id TEXT,
    camera_name TEXT,
    corner1 MATRIX,
    corner2 MATRIX,
    camera_matrix MATRIX,
    distortion_coefficients MATRIX,
    rotation_vectors MATRIX,
    translation_vectors MATRIX,

    FOREIGN KEY (setup_id) REFERENCES CameraSetups(setup_id)
) IF NOT EXISTS Cameras;

CREATE TABLE VideoTracking (
    tracking_id TEXT PRIMARY KEY,
    link TEXT,
    start_seconds FLOAT,
    duration FLOAT,
    percent_complete FLOAT,
)  IF NOT EXISTS VideoTracking;

CREATE TABLE Rocks (
    rock_id TEXT PRIMARY KEY,
    color TEXT,
    positions MATRIX,
    time MATRIX,

    FOREIGN KEY (tracking_id) REFERENCES VideoTracking(tracking_id)
)  IF NOT EXISTS Rocks;