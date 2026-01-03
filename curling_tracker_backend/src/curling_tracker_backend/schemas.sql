CREATE TABLE IF NOT EXISTS CameraSetups (
    setup_id TEXT PRIMARY KEY,
    setup_name TEXT
);

CREATE TABLE IF NOT EXISTS Cameras (
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
);

CREATE TABLE IF NOT EXISTS Videos (
    video_id TEXT PRIMARY KEY,
    url TEXT,
    filename TEXT,
    start_seconds INTEGER,
    duration INTEGER
);