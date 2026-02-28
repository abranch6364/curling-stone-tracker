# Use an official Python runtime as a base image
FROM python:3.11-slim AS curling-backend-base

# Set the working directory in the container
WORKDIR /app

# Install system dependencies
RUN apt update && apt install -y libgl1-mesa-dev libglib2.0-0 ffmpeg zip curl

RUN curl -fsSL https://deno.land/install.sh > deno_install.sh
RUN sh ./deno_install.sh -y
RUN rm ./deno_install.sh

# Copy the requirements file into the container and install dependencies
COPY requirements_base.txt .
RUN pip install --no-cache-dir -r requirements_base.txt


FROM curling-backend-base AS curling-backend

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
