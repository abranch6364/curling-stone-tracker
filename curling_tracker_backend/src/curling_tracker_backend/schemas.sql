CREATE TABLE IF NOT EXISTS CameraSetups (
    setup_id TEXT PRIMARY KEY,
    setup_name TEXT
);

CREATE TABLE IF NOT EXISTS Cameras (
    camera_id TEXT PRIMARY KEY,
    setup_id TEXT,
    camera_name TEXT,
    camera_type TEXT,
    corner1 MATRIX,
    corner2 MATRIX,
    camera_matrix MATRIX,
    distortion_coefficients MATRIX,
    rotation_vectors MATRIX,
    translation_vectors MATRIX,
    calibration_method TEXT NOT NULL DEFAULT 'full',
    reference_camera_id TEXT,
    homography MATRIX,

    FOREIGN KEY (setup_id) REFERENCES CameraSetups(setup_id)
);

CREATE TABLE IF NOT EXISTS Videos (
    video_id TEXT PRIMARY KEY,
    url TEXT,
    filename TEXT,
    start_seconds INTEGER,
    duration INTEGER
);

CREATE TABLE IF NOT EXISTS CalibrationPoints (
    point_id TEXT PRIMARY KEY,
    camera_id TEXT NOT NULL,
    name TEXT,
    image_x REAL NOT NULL,
    image_y REAL NOT NULL,
    world_x REAL NOT NULL,
    world_y REAL NOT NULL,
    world_z REAL NOT NULL,

    FOREIGN KEY (camera_id) REFERENCES Cameras(camera_id),
    UNIQUE (camera_id, name)
);

CREATE TABLE IF NOT EXISTS TrackingRuns (
    run_id TEXT PRIMARY KEY,
    url TEXT NOT NULL,
    setup_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued',
    progress REAL NOT NULL DEFAULT 0,
    message TEXT,
    error TEXT,
    video_filename TEXT,
    video_duration REAL,
    video_title TEXT,
    -- The date of the video as YYYY-MM-DD
    video_date TEXT,
    -- For a recorded live stream, when the stream started (unix time)
    video_start_timestamp REAL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (setup_id) REFERENCES CameraSetups(setup_id)
);

CREATE TABLE IF NOT EXISTS Games (
    game_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    game_number INTEGER NOT NULL,
    start_seconds REAL,
    end_seconds REAL,

    FOREIGN KEY (run_id) REFERENCES TrackingRuns(run_id)
);

CREATE TABLE IF NOT EXISTS Ends (
    end_id TEXT PRIMARY KEY,
    game_id TEXT NOT NULL,
    end_number INTEGER NOT NULL,
    direction TEXT,
    complete INTEGER NOT NULL DEFAULT 0,
    start_seconds REAL,
    end_seconds REAL,

    FOREIGN KEY (game_id) REFERENCES Games(game_id)
);

CREATE TABLE IF NOT EXISTS Shots (
    shot_id TEXT PRIMARY KEY,
    end_id TEXT NOT NULL,
    shot_number INTEGER NOT NULL,
    color TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    start_seconds REAL,
    end_seconds REAL,

    FOREIGN KEY (end_id) REFERENCES Ends(end_id)
);

CREATE TABLE IF NOT EXISTS ShotStones (
    stone_id TEXT PRIMARY KEY,
    shot_id TEXT NOT NULL,
    color TEXT,
    time_history MATRIX,
    state_history MATRIX,
    position_covariance_history MATRIX,

    FOREIGN KEY (shot_id) REFERENCES Shots(shot_id)
);
