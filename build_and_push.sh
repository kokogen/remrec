#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# --- Configuration ---
DOCKER_USERNAME="kokogen" # Replace with your Docker Hub username
IMAGE_NAME="remrec"       # The name of your Docker image
# Default tag is 'latest' if no argument is provided
IMAGE_TAG=${1:-latest}

FULL_IMAGE_NAME="${DOCKER_USERNAME}/${IMAGE_NAME}:${IMAGE_TAG}"

echo "--- Building and Pushing Docker Image ---"
echo "Docker Hub Username: ${DOCKER_USERNAME}"
echo "Image Name: ${IMAGE_NAME}"
echo "Image Tag: ${IMAGE_TAG}"
echo "Full Image Name: ${FULL_IMAGE_NAME}"

# 1. Log in to Docker Hub
echo ""
echo "Attempting to log in to Docker Hub..."
docker login

# Check if login was successful
if [ $? -ne 0 ]; then
    echo "Docker login failed. Please ensure you have correct credentials."
    exit 1
fi
echo "Successfully logged in to Docker Hub."

# 2. Build the Docker image
echo ""
echo "Building Docker image: ${FULL_IMAGE_NAME}..."
# Assuming Dockerfile is in the current directory (project root)
docker build -t "${FULL_IMAGE_NAME}" .

# Check if build was successful
if [ $? -ne 0 ]; then
    echo "Docker image build failed."
    exit 1
fi
echo "Docker image built successfully."

# 3. Push the Docker image to Docker Hub
echo ""
echo "Pushing Docker image: ${FULL_IMAGE_NAME} to Docker Hub..."
docker push "${FULL_IMAGE_NAME}"

# Check if push was successful
if [ $? -ne 0 ]; then
    echo "Docker image push failed."
    exit 1
fi
echo "Docker image pushed successfully to Docker Hub."

echo ""
echo "--- Script Finished ---"
echo "To deploy this image on your server, ensure your .env file has REMREC_IMAGE_TAG=${IMAGE_TAG}"
echo "and then run 'docker-compose pull' followed by 'docker-compose up -d'."
