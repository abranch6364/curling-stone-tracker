# Curling Game Tracker

Track curling stones from video for game analysis. This repository contains both a Flask API for all the logic and a React frontend as a UI.

## Setup and Installation

### CUDA

The Flask API can use CUDA to accelerate the object detector. If you have an CUDA supported NVIDIA GPU available, make sure the latest NVIDIA drivers are installed to enable this.

### Development Environment Setup

Docker containers are used to provide a consistant development environment. Two docker containers are used, one for the React frontend and one for the Flask backend. To start the development environment run the following from the root of this repository:

`docker compose up --build --watch`

Navigate to `localhost:3000` to view the webapp.

The watch option enables syncing of files on the host machine into the docker container, where the Flask and React apps will reload with the updates files. The build options ensures that the latest versions of the files are updated in the image. Without this, if a new container is started, the files will be the same as they were when the image was last built as the synced files do not persist into new containers. If this causes difficulties in the development process we might switch to just using bind mounts for the development containers.

## Contributing

Although the interest is appreciated, we are currently not accepting external contributions.
