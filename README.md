# Remarkable Recognizer

A containerized Python application that automates the process of converting handwritten notes from a reMarkable tablet into text-based PDFs. The workflow is designed to be robust, autonomous, and easy to deploy.

The application watches a specified Dropbox folder for new PDF exports, processes each one using a Gemini-based AI model for handwriting recognition (OCR), and uploads a searchable, text-based PDF back to a different Dropbox folder.

## Features

- **Automated OCR**: Converts handwritten notes from PDF images into structured text.
- **Dropbox Integration**: Seamlessly uses Dropbox for both input and output of files.
- **AI-Powered**: Leverages large vision models (like Gemini) for high-accuracy handwriting recognition.
- **Containerized**: Packaged with Docker and Docker Compose for easy, one-command deployment.
- **Continuous & On-Demand**: Runs as a continuous service that watches for files and will support on-demand single runs for debugging.
- **Robust Error Handling**:
    - Distinguishes between transient (network) and permanent (bad file) errors.
    - Automatically quarantines files that fail processing into a `/failed_files` folder.
- **Configurable**: Key parameters like DPI, folder paths, and API keys are managed via an environment file.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)

## Configuration

The application is configured using environment variables. Secret variables are managed via GitHub Secrets in the CI/CD pipeline and should *not* be in your local `.env` file.

1.  **Create/Update a `.env` file**:
    The `.env` file is now part of version control and contains non-secret application settings. Ensure your local `.env` is up-to-date with the latest version from the repository.

2.  **GitHub Secrets**:
    The following secret variables must be configured in your GitHub repository's `Settings > Secrets and variables > Actions`:
    *   `DROPBOX_APP_KEY`
    *   `DROPBOX_APP_SECRET`
    *   `OPENAI_API_KEY`
    *   `DOCKER_USERNAME` (Your Docker Hub username)
    *   `DOCKER_HUB_ACCESS_TOKEN` (A Personal Access Token for Docker Hub with push/pull access)
    
3.  **Generate a Dropbox Refresh Token**:
    You can generate your refresh token by running the application with a special command. This interactive process will guide you through authenticating with Dropbox in your browser and will then automatically save the refresh token to `.dropbox.token` on your local machine. This `.dropbox.token` file is automatically mounted into the container.
    
    ```shell
    docker-compose run --rm app python auth.py
    ```
    Follow the prompts:
    *   The script will print a URL. Copy and paste it into your browser.
    *   Authorize in Browser: Click "Allow".
    *   Copy the FULL URL from your browser's address bar.
    *   Paste the full redirect URL back into your terminal.
    
    The token will be saved to `./.dropbox.token`.

## Usage

All commands should be run from the root of the project directory.

### Automated CI/CD: Build and Publish Docker Image (GitHub Actions)

The Docker image is now automatically built and pushed to Docker Hub by a GitHub Actions workflow.

-   **Trigger:** The workflow runs automatically only when a new version tag (e.g., `v1.2.3`) is pushed to any branch.
-   **Workflow File:** `.github/workflows/build-and-push.yml`
-   **Image Naming:** The image is tagged intelligently based on the Git tag.
-   **Secrets:** Docker Hub credentials and API keys are securely managed via GitHub Secrets.

To trigger a build and push:
1.  Create and push a new Git tag (e.g., `git tag v1.0.0 && git push origin v1.0.0`).
    *Note: Pushing to the `github-actions` branch will no longer trigger a build.*

### Running in Production (Continuous Mode)

To deploy the application on your server, first ensure that the `.env` file on the server specifies the correct image tag (e.g., `REMREC_IMAGE_TAG=v1.0.0`).

Then, pull the latest image and start the service in the background. The application runs in a continuous loop, watching for new files.

```shell
docker-compose pull
docker-compose up -d
```

### Viewing Logs

To see the live output of the application:

```shell
docker-compose logs -f
```

### Running a One-Time Task (Debug Mode)

To process all files in the source folder immediately, without waiting for the loop, run the following command. This is useful for debugging or manual runs.

```shell
docker-compose run --rm app python main.py --run-once
```
- `run`: Executes a one-off command in a service container.
- `--rm`: Automatically removes the container after the command completes.

### Stopping the Application

To stop the application and remove the container:

```shell
docker-compose down
```

## Project Structure

- `main.py`: The main orchestrator that schedules and triggers the workflow.
- `processing.py`: Contains the core logic for processing a single file.
- `dbox.py`: A client class for interacting with the Dropbox API.
- `recognition.py`: Handles the API call to the AI model for OCR.
- `pdf_utils.py`: Utility for creating text-based PDFs.
- `config.py`: Loads and provides all configuration from the environment.
- `exceptions.py`: Defines custom exceptions for error handling.
- `Dockerfile`: Defines the application's container image.
- `docker-compose.yml`: Defines how to run the application service.

## Testing

This project uses `pytest` for unit and integration testing. Mocks are heavily used to isolate services and test logic independently of external APIs (Dropbox, OpenAI).

The tests are located in the `tests/` directory.

### Running Tests

To run the complete test suite, execute the following command from the project root:

```bash
.venv/bin/pytest -v
```