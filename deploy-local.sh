#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# --- Configuration ---
# Get the Docker image tag. Argument takes precedence.
if [ -z "$1" ]; then
    echo "Usage: $0 <docker_image_tag>"
    echo "Please provide the Docker image tag to deploy."
    exit 1
fi
IMAGE_TAG="$1"

echo "--- Deploying Locally ---"
echo "Image Tag to Deploy: ${IMAGE_TAG}"

# 1. Check for required files
if [ ! -f .env ]; then
    echo "ERROR: .env file not found."
    echo "Please copy .env.example to .env and fill in your secrets before running."
    exit 1
fi

if [ ! -f docker-compose.yml ]; then
    echo "ERROR: docker-compose.yml not found. Please ensure it exists in the project root."
    exit 1
fi

# 2. Ensure local files for Docker volumes exist
echo "Ensuring local log and token files exist..."
touch app.log
touch .dropbox.token

# 3. Update the REMREC_IMAGE_TAG in the .env file
echo "Updating REMREC_IMAGE_TAG in .env..."
# Use a temporary file for sed to be compatible with more systems
sed -i'' -e "s/^REMREC_IMAGE_TAG=.*$/REMREC_IMAGE_TAG=${IMAGE_TAG}/g" .env


# 4. Pull the latest image
echo "Pulling Docker image: kokogen/remrec:${IMAGE_TAG}..."
docker-compose pull

# 5. Start the service
echo "Starting Docker container in detached mode..."
docker-compose up -d --remove-orphans

echo ""
echo "--- Local Deployment Finished ---"
echo "Service is running in the background."
echo "Use 'docker-compose logs -f' to view logs."
echo "Use 'docker-compose down' to stop the service."
