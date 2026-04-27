#!/bin/bash

set -euo pipefail

usage() {
    cat <<'EOF'
Usage: ./e2e-local.sh [options]

Runs a local one-shot live E2E workflow in Docker.

Options:
  --provider dropbox|gdrive     Override STORAGE_PROVIDER for this run.
  --image-tag TAG               Override REMREC_IMAGE_TAG without editing .env.
  --pull                        Pull the configured image instead of building locally.
  --no-build                    Skip docker compose build.
  -h, --help                    Show this help.

Default behavior builds the local image and runs:
  python -m src.main --run-once
EOF
}

PROVIDER=""
IMAGE_TAG=""
PULL_IMAGE=0
SKIP_BUILD=0

while [ "$#" -gt 0 ]; do
    case "$1" in
        --provider)
            PROVIDER="${2:-}"
            shift 2
            ;;
        --image-tag)
            IMAGE_TAG="${2:-}"
            shift 2
            ;;
        --pull)
            PULL_IMAGE=1
            shift
            ;;
        --no-build)
            SKIP_BUILD=1
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "ERROR: Unknown option: $1" >&2
            usage
            exit 2
            ;;
    esac
done

if [ -n "$PROVIDER" ] && [ "$PROVIDER" != "dropbox" ] && [ "$PROVIDER" != "gdrive" ]; then
    echo "ERROR: --provider must be either 'dropbox' or 'gdrive'." >&2
    exit 2
fi

if [ ! -f .env ]; then
    echo "ERROR: .env file not found." >&2
    echo "Create it from .env.example and fill in live credentials before running E2E." >&2
    exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
    echo "ERROR: Docker Compose v2 is not available." >&2
    exit 1
fi

get_env_value() {
    local key="$1"
    awk -v key="$key" '
        index($0, key "=") == 1 {
            value = substr($0, length(key) + 2)
            gsub(/^"|"$/, "", value)
            print value
            exit
        }
    ' .env
}

CONFIGURED_PROVIDER="${PROVIDER:-$(get_env_value STORAGE_PROVIDER)}"
CONFIGURED_PROVIDER="${CONFIGURED_PROVIDER:-dropbox}"

if [ "$CONFIGURED_PROVIDER" = "dropbox" ]; then
    DROPBOX_SOURCE_DIR_VALUE="$(get_env_value DROPBOX_SOURCE_DIR)"
    if [ -z "$DROPBOX_SOURCE_DIR_VALUE" ]; then
        echo "WARN: DROPBOX_SOURCE_DIR is empty, so Dropbox root will be scanned." >&2
        echo "This is expected for reMarkable exports, but make sure only intended PDFs are present." >&2
    fi
fi

mkdir -p logs
touch app.log

if [ -e .dropbox.token ] && [ ! -f .dropbox.token ]; then
    echo "WARN: .dropbox.token exists but is not a file. DROPBOX_REFRESH_TOKEN from .env must be present for Dropbox runs." >&2
fi

env_args=()
run_args=()

if [ -n "$IMAGE_TAG" ]; then
    env_args+=("REMREC_IMAGE_TAG=$IMAGE_TAG")
fi

if [ -n "$PROVIDER" ]; then
    run_args+=("-e" "STORAGE_PROVIDER=$PROVIDER")
fi

run_with_env() {
    if [ "${#env_args[@]}" -gt 0 ]; then
        env "${env_args[@]}" "$@"
    else
        "$@"
    fi
}

echo "--- Local E2E ---"
echo "Provider: $CONFIGURED_PROVIDER"
if [ -n "$IMAGE_TAG" ]; then
    echo "Image tag override: $IMAGE_TAG"
fi

if [ "$PULL_IMAGE" -eq 1 ]; then
    echo "Pulling Docker image..."
    run_with_env docker compose pull app
elif [ "$SKIP_BUILD" -eq 0 ]; then
    echo "Building local Docker image..."
    run_with_env docker compose build app
else
    echo "Skipping build."
fi

echo "Running one-shot workflow..."
if [ "${#run_args[@]}" -gt 0 ]; then
    run_with_env docker compose run --rm "${run_args[@]}" app python -m src.main --run-once
else
    run_with_env docker compose run --rm app python -m src.main --run-once
fi

echo "--- Local E2E finished successfully ---"
