# Remarkable Recognizer

A containerized Python application that automates the process of converting handwritten notes from a reMarkable tablet into text-based PDFs. The workflow is designed to be robust, autonomous, and easy to deploy.

The application watches a specified Dropbox or Google Drive folder for new PDF exports, processes each one using a Gemini-based AI model for handwriting recognition (OCR), and uploads a searchable, text-based PDF back to a different folder in the chosen cloud storage.

## Features

- **Automated OCR**: Converts handwritten notes from PDF images into structured text.
- **Dropbox & Google Drive Integration**: Seamlessly uses either Dropbox or Google Drive for both input and output of files.
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

## Configuration for Local Use

To run this application on your own machine, you'll need to provide your credentials and settings via an environment file.

1.  **Create an `.env` file**:
    Copy the provided example file to a new file named `.env`. This file is ignored by Git and will contain your secrets.
    ```shell
    cp .env.example .env
    ```

2.  **Fill in your `.env` file**:
    Open the newly created `.env` file and provide your credentials for the following variables. At a minimum, you must set the secret keys and the source/destination directories/folder IDs.

    **General Settings:**
    *   `STORAGE_PROVIDER`: Set to either `"dropbox"` or `"gdrive"` to choose your cloud storage.
    *   `OPENAI_API_KEY`: Your API key for the recognition service.
    *   `OPENAI_BASE_URL`: The base URL for the API (defaults to a private host).
    *   `RECOGNITION_MODEL`: The specific AI model to use for recognition.

    **For Dropbox:**
    *   `DROPBOX_APP_KEY`: Your key from the Dropbox App Console.
    *   `DROPBOX_APP_SECRET`: Your secret from the Dropbox App Console.
    *   `DROPBOX_SOURCE_DIR`: The folder in your Dropbox to watch for new files (e.g., `/Apps/remarkable`). An empty string (`""`) can be used to specify the root folder.
    *   `DROPBOX_DEST_DIR`: The folder where recognized PDFs will be uploaded.
    *   `DROPBOX_FAILED_DIR`: The folder for files that failed processing.

    **For Google Drive:**
    *   `GDRIVE_CREDENTIALS_JSON`: The content of your `credentials.json` file as a single-line JSON string.
    *   `GDRIVE_TOKEN_JSON`: The content of your `gdrive_token.json` file as a single-line JSON string. (Generated via `gdrive_auth.py`)
    *   `GDRIVE_SOURCE_FOLDER_ID`: The ID of the Google Drive folder to watch for new files.
    *   `GDRIVE_DEST_FOLDER_ID`: The ID of the Google Drive folder where recognized PDFs will be uploaded.
    *   `GDRIVE_FAILED_FOLDER_ID`: The ID of the Google Drive folder for files that failed processing.

    You can also customize other non-secret settings in this file if needed.

3.  **Generate Dropbox Refresh Token (if using Dropbox)**:
    Run the interactive `auth.py` script to generate your Dropbox refresh token.
    ```shell
    docker-compose run --rm app python -m src.auth
    ```
    Follow the on-screen prompts. This will create a `.dropbox.token` file in your project root, which is automatically used by the application.

4.  **Generate Google Drive Token (if using Google Drive)**:
    You need to obtain a `credentials.json` file from the Google Cloud Console for a desktop application. Then, run the interactive `gdrive_auth.py` script.
    ```bash
    docker-compose run --rm app python -m src.gdrive_auth
    ```
    Follow the prompts to provide the path to your `credentials.json` file. This will generate a `gdrive_token.json` file in your project root. You will then need to copy the content of this `gdrive_token.json` and `credentials.json` into your `.env` file under `GDRIVE_TOKEN_JSON` and `GDRIVE_CREDENTIALS_JSON` respectively. Ensure they are single-line JSON strings.

## Running the Service Locally

The easiest way to run the service on your local machine is with the `deploy-local.sh` script.

1.  **Build the Docker Image:**
    The `docker-compose.yml` is configured to build the image from the local `Dockerfile`.
    ```shell
    docker-compose build
    ```
2.  **Find an Image Tag:** Find the latest version tag to use from the project's Docker Hub or Git repository.
3.  **Run the Script:** Execute the script with the desired tag.
    ```shell
    ./deploy-local.sh <your_image_tag>
    ```
This script will automatically:
- Check for the required `.env` file.
- Update the image tag in your `.env` file.
- Pull the specified Docker image from Docker Hub.
- Start the service in the background using `docker-compose up -d`.

### Other Useful Commands

-   **Viewing Logs:**
    ```shell
    docker-compose logs -f
    ```
-   **Running a One-Time Task (Debug Mode):**
    ```shell
    docker-compose run --rm app python -m src.main --run-once
    ```
-   **Stopping the Application:**
    ```shell
    docker-compose down
    ```

---

## Developer & CI/CD Information

### Automated CI/CD (GitHub Actions)

The Docker image is automatically built and pushed to Docker Hub by a GitHub Actions workflow.

-   **Trigger:** The workflow runs automatically only when a new version tag (e.g., `v1.2.3`) is pushed to the repository.
-   **Workflow File:** `.github/workflows/build-and-push.yml`

### Remote Deployment (Synology)
The `deploy.sh` script is designed for deploying the application to a remote server, such as a Synology NAS. It requires manual configuration of SSH details within the script.

### Code Quality
This project uses `ruff` for linting and code formatting. You can run the following commands to check and format the code:
```bash
# Check for linting errors
ruff check .

# Automatically fix linting errors
ruff check . --fix

# Check formatting
ruff format --check .

# Apply formatting
ruff format .
```

## Project Structure

- `main.py`: The main orchestrator that schedules and triggers the workflow.
- `processing.py`: Contains the core logic for processing a single file.
- `dbox.py`: A client class for interacting with the Dropbox API.
- `gdrive.py`: A client class for interacting with the Google Drive API.
- `recognition.py`: Handles the API call to the AI model for OCR.
- `pdf_utils.py`: Utility for creating text-based PDFs.
- `config.py`: Loads and provides all configuration from the environment.
- `exceptions.py`: Defines custom exceptions for error handling.
- `auth.py`: A utility script to generate a Dropbox refresh token.
- `gdrive_auth.py`: A utility script to generate a Google Drive token.
- `requirements.txt`: A list of all Python dependencies for the project.
- `.env.example`: An example file for environment variable configuration.
- `Dockerfile`: Defines the application's container image.
- `docker-compose.yml`: Defines how to run the application service.
- `deploy-local.sh`: A helper script for easy local deployment.
- `deploy.sh`: A helper script for deploying to a remote server.


## Testing

This project uses `pytest` for unit and integration testing. Mocks are heavily used to isolate services and test logic independently of external APIs (Dropbox, OpenAI).

The tests are located in the `tests/` directory.

### Running Tests

To run the complete test suite, execute the following command from the project root:

```bash
docker-compose run --rm app /opt/venv/bin/pytest -v
```