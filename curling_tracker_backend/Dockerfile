# Use an official Python runtime as a base image. It is pinned by digest because Docker Hub republishes
# the 3.11-slim tag with OS updates, and a new base image invalidates the cache of every layer after it
# (including the large pip installs). To update it, change the digest deliberately.
FROM python:3.11-slim@sha256:da047cb8f9d1d98e5c070f5300ba9f7274e33b8fc0e5be5ed88740aed1b95ba9 AS curling-backend-base

# Set the working directory in the container
WORKDIR /app

# Install system dependencies

RUN apt update && apt install -y libgl1-mesa-dev libglib2.0-0 ffmpeg zip curl

RUN curl -fsSL https://deno.land/install.sh > deno_install.sh
RUN sh ./deno_install.sh -y
RUN rm ./deno_install.sh
ENV DENO_INSTALL="/root/.deno"
ENV PATH="$DENO_INSTALL/bin:$PATH"

# Copy the requirements file into the container and install dependencies
COPY requirements_base.txt .
RUN pip install --no-cache-dir -r requirements_base.txt

FROM curling-backend-base AS curling-backend

# Set the working directory in the container
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY . .

# Install the application in editable mode
RUN pip install -e .

# Expose the port the app runs on
EXPOSE 5000

# Command to run the application
CMD ["flask", "run", "--host=0.0.0.0"]
