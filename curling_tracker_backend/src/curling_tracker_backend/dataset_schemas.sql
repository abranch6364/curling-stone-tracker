CREATE TABLE IF NOT EXISTS CurlingStoneTopDownDataset (
    file_hash BLOB PRIMARY KEY,
    file_path TEXT
);

CREATE TABLE IF NOT EXISTS CurlingStoneAngledDataset (
    file_hash BLOB PRIMARY KEY,
    file_path TEXT
);