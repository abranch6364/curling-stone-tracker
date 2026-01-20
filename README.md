# Curling Game Tracker

Automatically track curling stones from youtube videos for game analysis.

## Usage

### Multi-Camera Setup
It is common for curling streams to use multiple cameras mosaiced together to provide context of the entire ice sheet to the viewer. This webapp allows the user to define a new camera setup from the video stream by identifying the different camera views in the mosaiced image. The user can then calibrate the cameras by selecting known landmarks on the curling sheet for each camera view.

### Youtube Video Tracking
Video tracking of the curling stones can be done directly from a youtube video by providing a URL and a camera setup to use, a start time, and a duration. The video will automatically be analyzed and the stone positions over the requested time will be returned and plotted ona digitial curling sheet. Along side that is be a subset of frames from the video for reference. The different camera views will be fused to track stones over the entire visible area of the curling sheet.

## Implementation

This is implemented as a webapp, with a React frontend and a Flask backend.

## Setup and Installation

### CUDA

The Flask API can use CUDA to accelerate the object detector. If you have an CUDA supported NVIDIA GPU available, make sure the latest NVIDIA drivers are installed to enable this.

### Development Environment Setup

Docker containers are used to provide a consistant development environment. Two docker containers are used, one for the React frontend and one for the Flask backend. To start the development environment run the following from the root of this repository:

`docker compose up --build --watch`

Navigate to `localhost:3000` to view the webapp.

The watch option enables syncing of files on the host machine into the docker container, where the Flask and React apps will reload with the updates files. The build options ensures that the latest versions of the files are updated in the image. Without this, if a new container is started, the files will be the same as they were when the image was last built as the synced files do not persist into new containers. If this causes difficulties in the development process we might switch to just using bind mounts for the development containers.

## ML Pipeline

An ML pipeline is setup to facilitate the collecting of new images for the different datasets, labelling those images, and re-training the ML models on the updated datasets. This is a local pipeline in that it does not use any cloud storage for the dataset or compute for training.

### Datasets
Datasets are stored in a Docker Volume. This volume can then be mounted as needed in multiple Docker containers to access the dataset. Each dataset is stored in separate folders in the volume. The datasets only consist of the dataset files with no labels. They are not yet split into train/test/validation sets. When new images are added to these folders the data labeling software automatically recognizes the new data and can be used to label it.

The curling stone datasets should only include single camera images. It is common that club curling streams provide a mosaic of images from different cameras. These should be split into single camera views before adding to the respective datasets. Currently we have the two following datasets:

- `curling_stone_top_down`: Curling stones labelled with bounding boxes from images with a top down view.
- `curling_stone_angle`: Curling stones with bounding boxes from images with an angled view.

### Data Collection
The curling tracking webapp provides a tool for adding new images to the dataset. When doing video tracking a subset of the images from the video are shown and can be added to datasets. To do this, the backend Flask API provides an endpoint for adding a new file to a specific dataset at `api/add_image_to_dataset`. A database is used to store a SHA256 hash of each file in each dataset to easily know if the image already exists, if it exists it is rejected. This database is stored on the Docker volume as well.

Tools are also provided to generate images to add to datasets from youtube videos directly and to add those images to the dataset. Specifically in scripts folder of the `curling_tracking_backend` package.

`curling_video_to_images.py`: Downloads and parses a youtube video to generate images for datasets. The backend api must be running.

`add_folder_to_dataset.py`: Adds a folder of images to a dataset via the backend api. The backend api must be running.


### Data Labelling
Data labelling is done with [Label Studio](https://labelstud.io/). A docker compose file is provided to start a Docker container running Label Studio and mount the Docker volume with the dataset into that container. Label Studio should then be setup to sync with local storage to access the dataset for labelling.

### Model Training
Model training is done in a Docker container as well. The Dockerfile and compose coniguration are provided. The results from the model training are stored in a bind mounted volume so they are available on the host machine. A tensorboard Docker container is also started with the same bind mounting to track the training process. Two scripts are provided


Pull the labelled dataset from Label Studio and splits it into train/test/validation datasets. The Label Studio Docker container must be active to do this.

`prep_top_down_dataset.sh`

Starts a new training run for the dataset.

`train_top_down_dataset.sh`

Hyperparameter tuning and model testing scripts are also provided. These example shell scripts are all for a specific dataset, but are easily adapted for different datasets.

## Contributing

Although the interest is appreciated, we are currently not accepting external contributions.



