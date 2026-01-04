#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# --- Configuration ---
# IMPORTANT: Replace these with your actual Synology details
SYNOLOGY_USER="koko"
SYNOLOGY_HOST="192.168.0.249"
REMOTE_PROJECT_PATH="/volume1/docker/remrec" # Path to your project on Synology (where docker-compose.yml and .env are)
REMOTE_LOG_FILE_PATH="${REMOTE_PROJECT_PATH}/app.log" # Path to the app.log file on Synology
REMOTE_TOKEN_FILE_PATH="${REMOTE_PROJECT_PATH}/.dropbox.token" # Path to the Dropbox token file on Synology

# Get the Docker image tag from the .env file
IMAGE_TAG=$(grep '^REMREC_IMAGE_TAG=' .env | cut -d '=' -f2)
if [ -z "$IMAGE_TAG" ]; then
    echo "REMREC_IMAGE_TAG not found or is empty in the .env file."
    exit 1
fi

echo "--- Deploying Docker Image to Synology ---"
echo "Target Synology: ${SYNOLOGY_USER}@${SYNOLOGY_HOST}"
echo "Remote Project Path: ${REMOTE_PROJECT_PATH}"
echo "Image Tag to Deploy: ${IMAGE_TAG}"

# Check if local .env file exists
if [ ! -f .env ]; then
    echo "Local .env file not found. Please ensure it exists in the project root."
    exit 1
fi

echo "Copying local .env file to Synology..."
cat .env | ssh -p 22222 "${SYNOLOGY_USER}@${SYNOLOGY_HOST}" "cat > ${REMOTE_PROJECT_PATH}/.env"
echo ".env file copied successfully."

# Check if local docker-compose.yml file exists
if [ ! -f docker-compose.yml ]; then
    echo "Local docker-compose.yml file not found. Please ensure it exists in the project root."
    exit 1
fi

echo "Copying local docker-compose.yml file to Synology..."
cat docker-compose.yml | ssh -p 22222 "${SYNOLOGY_USER}@${SYNOLOGY_HOST}" "cat > ${REMOTE_PROJECT_PATH}/docker-compose.yml"
echo "docker-compose.yml file copied successfully."

# --- SSH Commands to execute on Synology ---
SSH_COMMANDS=$(cat <<EOF
    set -e

    echo "Changing to remote project directory: ${REMOTE_PROJECT_PATH}"
    cd "${REMOTE_PROJECT_PATH}"

    echo "Ensuring log file exists on remote: ${REMOTE_LOG_FILE_PATH}"
    touch "${REMOTE_LOG_FILE_PATH}"

    echo "Ensuring token file exists on remote: ${REMOTE_TOKEN_FILE_PATH}"
    touch "${REMOTE_TOKEN_FILE_PATH}"

    # Determine the correct docker-compose command
    DOCKER_COMPOSE_CMD=""
    if command -v docker-compose &> /dev/null; then
        DOCKER_COMPOSE_CMD="docker-compose"
    elif command -v docker &> /dev/null && docker compose version &> /dev/null; then
        DOCKER_COMPOSE_CMD="docker compose"
    elif [ -f "/usr/local/bin/docker-compose" ]; then
        DOCKER_COMPOSE_CMD="/usr/local/bin/docker-compose"
    elif [ -f "/var/packages/Docker/target/usr/bin/docker-compose" ]; then
        DOCKER_COMPOSE_CMD="/var/packages/Docker/target/usr/bin/docker-compose"
    else
        echo "Error: docker-compose command not found on Synology." >&2
        exit 1
    fi
    echo "Using docker-compose command: \${DOCKER_COMPOSE_CMD}"

    # The .env file is now the single source of truth, so no update is needed here.
    # The correct REMREC_IMAGE_TAG is already in the .env file copied from local.

    echo "Pulling Docker image..."
    sudo \${DOCKER_COMPOSE_CMD} pull

    echo "Restarting Docker containers..."
    sudo \${DOCKER_COMPOSE_CMD} up -d --remove-orphans

    echo "Deployment to Synology complete."
EOF
)

# Execute SSH commands
ssh -t -p 22222 "${SYNOLOGY_USER}@${SYNOLOGY_HOST}" "${SSH_COMMANDS}"

echo ""
echo "--- Deployment Script Finished ---"
echo "Please ensure you have replaced placeholder values in deploy.sh with your actual Synology details."
