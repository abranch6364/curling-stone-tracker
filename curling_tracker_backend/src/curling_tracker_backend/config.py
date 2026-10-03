BASE_DATASETS_PATH = "/datasets"
DATASETS = {
    "curling_top_down": {
        "folder": "curling_stone_top_down_dataset",
        "dataset_table": "CurlingStoneTopDownDataset",
    },
    "curling_angled": {
        "folder": "curling_stone_angled_dataset",
        "dataset_table": "CurlingStoneAngledDataset",
    }
}

# Largest number of camera images run through a stone detector at once. Frames are detected in groups,
# with as many frames per batch as fit for each camera type (the top down and angled cameras use different
# models). Lower this if the GPU runs out of memory.
DETECTION_BATCH_IMAGES = 16
