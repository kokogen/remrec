# Remarkable Recognizer

A containerized Python application that automates the process of converting handwritten notes from a reMarkable tablet into text-based PDFs. The workflow is designed to be robust, autonomous, and easy to deploy.

The application watches a specified Dropbox folder for new PDF exports, processes each one using a Gemini-based AI model for handwriting recognition (OCR), and uploads a searchable, text-based PDF back to a different Dropbox folder.

## Features

- **Automated OCR**: Converts handwritten notes from PDF images into structured text.
- **Dropbox Integration**: Seamlessly uses Dropbox for both input and output of files.
- **AI-Powered**: Leverages large vision models (like Gemini) for high-accuracy handwriting recognition.
- **Containerized**: Packaged with Docker and Docker Compose for easy, one-command deployment.
- **Scheduled & On-Demand**: Runs automatically on a `cron` schedule and supports on-demand single runs for debugging.
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
        - This is a long-lived token that you only need to generate once using the included utility script. See the section below.

    - `OPENAI_API_KEY`:
        - Get this from your AI provider's dashboard (e.g., [OpenAI API Keys](https://platform.openai.com/api-keys)).

    - `OPENAI_BASE_URL`:
        - The base URL for the recognition API. If you are using a proxy, enter it here. For connecting directly to OpenAI, use `https://api.openai.com/v1`.

### How to Get a Dropbox Refresh Token

The `auth.py` script is a one-time utility to get your refresh token.

1.  **Temporarily Edit `auth.py`**: Open `auth.py` and paste your App Key and App Secret into the `client_id` and `client_secret` variables at the bottom of the file.
2.  **Run the Script**: Execute `python auth.py` in your terminal.
3.  **Authorize in Browser**: The script will open a browser window asking you to authorize your Dropbox app. Click "Allow".
4.  **Copy the Token**: After authorization, the script will print the `Refresh Token` to your console. Copy this value and paste it into the `DROPBOX_REFRESH_TOKEN` field in your `.env` file.

## Usage

All commands should be run from the root of the project directory.

### Running in Production (Cron Mode)

This command builds the Docker image (if it doesn't exist) and starts the service in the background. The `cron` job inside the container will then trigger the processing script on its schedule (default: every 5 minutes).

```shell
docker-compose up -d --build
```

### Viewing Logs

To see the live output of the application, including `cron` triggers and file processing logs:

```shell
docker-compose logs -f
```

### Running a One-Time Task (Debug Mode)

To process all files in the source folder immediately, without waiting for `cron`, run the following command. This is useful for debugging or manual runs.

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
- `cronjob`: The cron task definition file.

## Testing

This project uses `pytest` for unit and integration testing. Mocks are heavily used to isolate services and test logic independently of external APIs (Dropbox, OpenAI).

The tests are located in the `tests/` directory.

### Running Tests

To run the complete test suite, execute the following command from the project root:

```bash
.venv/bin/pytest -v
```