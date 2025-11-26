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

The application is configured using environment variables.

1.  **Create a `.env` file**:
    Copy the provided example file to a new file named `.env`.
    ```shell
    cp .env.example .env
    ```

2.  **Fill in the `.env` file**:
    Open the `.env` file and provide your credentials and settings.

    - `DROPBOX_APP_KEY` & `DROPBOX_APP_SECRET`:
        - Go to the [Dropbox App Console](https://www.dropbox.com/developers/apps).
        - Create a new app with "Scoped access".
        - Ensure your app has the following permissions: `files.content.write`, `files.content.read`, `files.metadata.read`.
        - Find the "App key" and "App secret" in your app's **Settings** tab.

    - `DROPBOX_REFRESH_TOKEN`:
        - This is a long-lived token that you only need to generate once. See the section below.

    - `OPENAI_API_KEY`:
        - Get this from your AI provider's dashboard (e.g., [OpenAI API Keys](https://platform.openai.com/api-keys)).

    - `OPENAI_BASE_URL`:
        - The base URL for the recognition API. If you are using a proxy, enter it here. For connecting directly to OpenAI, use `https://api.openai.com/v1`.

### How to Get a Dropbox Refresh Token

You can generate your refresh token by running the application with a special command. This interactive process will guide you through authenticating with Dropbox in your browser and will then automatically save the refresh token for you.

1.  **Run the authorization utility**:
    ```shell
    docker-compose run --rm app python auth.py
    ```
2.  **Follow the prompts**: The script will print a URL. Copy and paste it into your browser.
3.  **Authorize in Browser**: The script will open a browser window asking you to authorize your Dropbox app. Click "Allow".
4.  **Token is Saved**: The script will automatically receive the token and save it to a file (`.dropbox.token`) that is read by the main application. You do not need to manually copy it into your `.env` file.

## Usage

All commands should be run from the root of the project directory.

### Development Workflow: Build and Publish Docker Image

When working on the application, you'll build and publish the Docker image to Docker Hub from your local development machine. This image will then be pulled by the deployment server.

1.  **Log in to Docker Hub:**
    Ensure you are logged into Docker Hub on your development machine:
    ```bash
    docker login
    ```
    (You may need to run `docker logout` first if you encounter issues)

2.  **Build and Push the Image:**
    Use the provided script to build and push the Docker image to your private Docker Hub repository. By default, the script automatically determines the image tag based on the latest Git tag or short commit hash. You only need to specify a tag manually for specific versioning needs (e.g., overriding the auto-generated tag).
    
    To build and push using the auto-generated tag:
    ```bash
    ./build_and_push.sh
    ```
    To build and push with a specific manual tag:
    ```bash
    ./build_and_push.sh v1.0.0
    ```
    This will build the image `kokogen/remrec:<tag>` and push it to Docker Hub.

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