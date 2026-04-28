#!/bin/bash

set -euo pipefail

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

if ! docker compose version >/dev/null 2>&1; then
    echo "ERROR: Docker Compose v2 is not available."
    exit 1
fi

# 2. Ensure local directories/files for Docker volumes are valid
echo "Ensuring local log directory exists..."
mkdir -p logs

if [ -e .dropbox.token ] && [ ! -f .dropbox.token ]; then
    echo "ERROR: .dropbox.token exists but is not a regular file."
    echo "Remove that path before deploying; Docker Compose expects a file there."
    exit 1
fi

if [ ! -e .dropbox.token ]; then
    touch .dropbox.token
fi

# 3. Update the REMREC_IMAGE_TAG in the .env file
echo "Updating REMREC_IMAGE_TAG in .env..."
# Use a temporary file for sed to be compatible with more systems
if grep -q "^REMREC_IMAGE_TAG=" .env; then
    sed -i'' -e "s/^REMREC_IMAGE_TAG=.*$/REMREC_IMAGE_TAG=${IMAGE_TAG}/g" .env
else
    printf '\nREMREC_IMAGE_TAG=%s\n' "${IMAGE_TAG}" >> .env
fi


# 4. Pull the latest image
echo "Pulling Docker image: kokogen/remrec:${IMAGE_TAG}..."
docker compose pull app

# 5. Start the service
echo "Starting Docker container in detached mode..."
docker compose up -d --no-build --remove-orphans app

echo ""
echo "--- Local Deployment Finished ---"
echo "Service is running in the background."
echo "Use 'docker compose logs -f' to view logs."
echo "Use 'docker compose down' to stop the service."
