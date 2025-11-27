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

## Configuration for Local Use

To run this application on your own machine, you'll need to provide your credentials and settings via an environment file.

1.  **Create an `.env` file**:
    Copy the provided example file to a new file named `.env`. This file is ignored by Git and will contain your secrets.
    ```shell
    cp .env.example .env
    ```

2.  **Fill in your `.env` file**:
    Open the newly created `.env` file and provide your credentials for the following variables:
    *   `DROPBOX_APP_KEY`
    *   `DROPBOX_APP_SECRET`
    *   `OPENAI_API_KEY`
    You can also customize other non-secret settings in this file if needed.

3.  **Generate a Dropbox Refresh Token**:
    Run the interactive `auth.py` script to generate your Dropbox refresh token.
    ```shell
    docker-compose run --rm app python auth.py
    ```
    Follow the on-screen prompts. This will create a `.dropbox.token` file in your project root, which is automatically used by the application.

## Running the Service Locally

The easiest way to run the service on your local machine is with the `deploy-local.sh` script.

1.  **Find an Image Tag:** Find the latest version tag to use from the project's Docker Hub or Git repository.
2.  **Run the Script:** Execute the script with the desired tag.
    ```shell
    ./deploy-local.sh v1.2.4
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
    docker-compose run --rm app python main.py --run-once
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