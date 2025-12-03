# Gemini Context File

This file provides a comprehensive overview of the **Remarkable Recognizer** project for the Gemini AI agent. It covers the project's purpose, architecture, key files, and development conventions.

---

## Global Instructions: Git Workflow

**Before making any changes to the codebase, strictly follow these steps:**

1.  **Create a Feature Branch:** Do not work on the `master` branch directly.
2.  **Ask for Branch Name:** Explicitly ask the user for the name of the new feature branch.
3.  **Implement Changes:** Perform all code modifications within this new branch.
4.  **Await Approval:** After the changes are complete and verified, wait for explicit user approval to commit them (e.g., "Зафиксируй текущее состояние" or "Commit the current state").
5.  **Commit, Merge, and Push:** Once approval is given:
    *   Commit the changes with a descriptive message.
    *   Merge the feature branch back into the `master` branch.
    *   Push the `master` branch to the remote repository.
6.  **Tagging:** If the user explicitly provides a tag, apply it during the commit or push process.
---

## Project Overview

This is a containerized Python application designed to automate the OCR (Optical Character Recognition) process for handwritten notes from a reMarkable tablet.

The application runs as a service that:
1.  Watches a specified source folder in a Dropbox account.
2.  When a new PDF file appears, it downloads the file.
3.  Converts each page of the PDF into an image.
4.  Sends the images to an AI vision model (like Gemini) via an OpenAI-compatible API to perform handwriting recognition.
5.  Assembles the recognized text into a new, text-searchable PDF.
6.  Uploads the new PDF to a specified destination folder in Dropbox.
7.  Moves the original file to a "failed" folder if processing fails, distinguishing between transient (e.g., network error) and permanent (e.g., corrupted file) errors.

The architecture is modular, with clear separation of concerns, and it relies on environment variables for configuration, loaded via `pydantic`.

### Core Technologies
- **Language:** Python 3.11
- **Containerization:** Docker, Docker Compose
- **Key Libraries:**
    - `dropbox`: For all Dropbox API interactions.
    - `openai`: To communicate with the AI model.
    - `pydantic-settings`: For robust configuration management.
    - `pdf2image`: To convert PDF pages to images for processing.
    - `reportlab`: To create the final text-searchable PDF.
    - `pytest`: For unit and integration testing.
- **System Dependencies:** `poppler-utils` (for `pdf2image`).

---

## Building and Running

### Configuration
The application is configured using environment variables. Secret variables are managed via GitHub Secrets in the CI/CD pipeline and should *not* be in your local `.env` file.

1.  **`.env` file**: The `.env` file is now part of version control and contains non-secret application settings. Ensure your local `.env` is up-to-date with the latest version from the repository.

2.  **GitHub Secrets**: The following secret variables must be configured in your GitHub repository's `Settings > Secrets and variables > Actions`:
    *   `DROPBOX_APP_KEY`
    *   `DROPBOX_APP_SECRET`
    *   `OPENAI_API_KEY`
    *   `DOCKER_USERNAME` (Your Docker Hub username)
    *   `DOCKER_HUB_ACCESS_TOKEN` (A Personal Access Token for Docker Hub with push/pull access)

3.  **Generate a Dropbox Refresh Token**: You can generate your refresh token by running the application with a special command. This interactive process will guide you through authenticating with Dropbox in your browser and will then automatically save the refresh token to `.dropbox.token` on your local machine. This `.dropbox.token` file is automatically mounted into the container.
    ```bash
    docker-compose run --rm app python auth.py
    ```
    Follow the prompts:
    *   The script will print a URL. Copy and paste it into your browser.
    *   Authorize in Browser: Click "Allow".
    *   Copy the FULL URL from your browser's address bar.
    *   Paste the full redirect URL back into your terminal.
    
    The token will be saved to `./.dropbox.token`.

### Automated CI/CD: Build and Push Docker Image (GitHub Actions)

The Docker image is now automatically built and pushed to Docker Hub by a GitHub Actions workflow.

-   **Trigger:** The workflow runs automatically only when a new version tag (e.g., `v1.2.3`) is pushed to any branch.
-   **Workflow File:** `.github/workflows/build-and-push.yml`
-   **Image Naming:** The image is tagged intelligently based on the Git tag.
-   **Secrets:** Docker Hub credentials and API keys are securely managed via GitHub Secrets.
-   **Manual Build/Push:** The `build_and_push.sh` script has been removed. Local builds/pushes are not the primary workflow; use GitHub Actions. To trigger a build, create and push a new Git tag (e.g., `git tag v1.0.0 && git push origin v1.0.0`).

### Running the Service
To run the application in its standard, continuous-loop mode:
```bash
# Pull the latest image defined by REMREC_IMAGE_TAG in .env
docker-compose pull

# Start the service in the background
docker-compose up -d
```

### Viewing Logs
To see the application's output, including file processing status:
```bash
docker-compose logs -f
```
Logs are also written to `app.log`, which is mounted to the host machine via the `docker-compose.yml` file.

### Running a One-Time Task
For debugging or to process all files in the source folder immediately, use the `--run-once` flag:
```bash
docker-compose run --rm app python main.py --run-once
```

### Stopping the Application
```bash
docker-compose down
```

### Running Tests
The project uses `pytest`. To run the full test suite:
```bash
.venv/bin/pytest -v
```

---

## Development Conventions

### Code Style
- The code is modular, with responsibilities separated into different files (`dbox.py`, `recognition.py`, `processing.py`, etc.).
- Configuration is centralized in `config.py` using `pydantic-settings` and is strictly typed.
- Custom exceptions (`PermanentError`, `TransientError`) are defined in `exceptions.py` and used throughout the application to control the workflow based on error types.

### Error Handling
- The application distinguishes between two main types of errors:
    - **`TransientError`**: Represents temporary issues (e.g., network timeouts, API rate limits). When this error occurs, the file is left in the source folder to be retried on the next run.
    - **`PermanentError`**: Represents issues that will not be resolved by retrying (e.g., a corrupted PDF, an invalid API key). When this error occurs, the problematic file is moved to a `/failed_files` directory to prevent repeated processing attempts.

### Testing
- Unit and integration tests are located in the `tests/` directory.
- `pytest` is the test runner.
- The testing strategy relies heavily on mocking external services and dependencies using `unittest.mock` (`@patch`, `MagicMock`). This allows the application's internal logic to be tested in isolation.
- Fixtures (`@pytest.fixture`) are used to create reusable mock objects for tests.
