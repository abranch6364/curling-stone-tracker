CREATE TABLE Cameras (
    camera_id TEXT PRIMARY KEY,
    camera_matrix BLOB,
    distortion_coefficients BLOB,
    rotation_vectors BLOB,
    translation_vectors BLOB
);