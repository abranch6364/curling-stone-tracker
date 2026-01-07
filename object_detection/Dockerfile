# Use an official Python runtime as a base image
FROM python:3.11-slim

WORKDIR /object_detection

# Install system dependencies
RUN apt update && apt install -y libgl1-mesa-dev libglib2.0-0 ffmpeg

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
	pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["/bin/bash"]