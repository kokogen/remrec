# Codex Working Notes

## Project Snapshot

`remrec` is a Python 3.11 Dockerized service that watches a Dropbox or Google Drive
source folder for exported reMarkable PDFs, converts each page to an image, sends
the image to an OpenAI-compatible vision model for OCR, writes a text PDF, uploads
it to the destination folder, and deletes or quarantines the original depending on
the outcome.

## Structure And Architecture

- `src/main.py` is the orchestration layer: storage initialization, folder
  validation, workflow status mapping, continuous loop, and `--run-once`.
- `src/processing.py` owns one-file processing. It downloads the PDF, reads page
  count, converts and recognizes pages one at a time, creates the output PDF, and
  deletes the source only after a result exists.
- `src/storage/base.py` and `src/storage/dto.py` define the storage boundary.
  Provider clients must translate SDK failures into `src/exceptions.py` domain
  exceptions instead of leaking raw SDK exceptions.
- `src/dbox.py` and `src/gdrive.py` are provider adapters. Keep provider-specific
  path/ID/query handling inside these modules.
- `src/recognition.py` is the OpenAI-compatible API adapter and classifies
  provider errors as transient, permanent, or auth failures.
- `src/pdf_utils.py` builds the result PDF. OCR text must be escaped before it is
  passed to ReportLab paragraph markup.
- `src/config.py` is the typed environment configuration. `STORAGE_PROVIDER` is
  limited to `dropbox` or `gdrive`; provider folders are centralized as
  `SRC_FOLDER`, `DST_FOLDER`, and `FAILED_FOLDER`.

## Development Approach

- Preserve the storage abstraction and domain exception model. Workflow decisions
  should depend on `PermanentError`, `TransientError`, and provider-specific
  subclasses, not raw SDK exceptions.
- Keep changes narrow. Avoid unrelated refactors, dependency churn, or deployment
  changes unless they are part of the requested scope.
- For auth bootstrap, `src.auth` must require only `DROPBOX_APP_KEY`; it must not
  require an existing Dropbox refresh token.
- For Docker images, keep runtime contents explicit. The current `Dockerfile`
  copies only `src/` and `DejaVuSans.ttf` after installing runtime requirements.
- Local secrets and generated files belong outside Git and Docker build context:
  `.env`, `.dropbox.token`, `credentials.json`, `gdrive_token.json`, logs, caches,
  and coverage artifacts.

## Testing Notes

- Unit tests mock external services. Do not make tests depend on live Dropbox,
  Google Drive, or recognition APIs.
- When changing workflow status behavior, add focused tests in `tests/test_main.py`.
- When changing storage provider query/path behavior, add provider tests in
  `tests/test_dbox.py` or `tests/test_gdrive.py`.
- When changing PDF processing or output formatting, add tests in
  `tests/test_processing.py` or `tests/test_pdf_utils.py`.
- Local E2E is live and uses `.env`. An empty source folder is a valid successful
  E2E result.

## Deployment Notes

- `docker-compose.yml` is used for local development and E2E, and builds from the
  current working tree by default.
- `deploy-local.sh` is for running a published Docker Hub image tag locally. It
  uses Docker Compose v2, validates `.dropbox.token` as a regular file, updates
  `REMREC_IMAGE_TAG`, pulls the image, and starts without rebuilding.
- `deploy.sh` targets the configured Synology host and copies `.env` plus
  `docker-compose.yml` before pulling and restarting remotely.
- Pushing a `vX.Y.Z` tag triggers GitHub Actions to run CI and build/push the
  Docker image.

## Common Commands

- `make test`: run `pytest -q`.
- `make lint`: run `ruff check .`.
- `make format-check`: run `ruff format --check .`.
- `make verify`: run unit tests, lint, and format check.
- `make shell-check`: validate shell script syntax.
- `make compose-config`: validate Docker Compose config.
- `make e2e`: run local live E2E with a Docker rebuild.
- `make release-check`: run the full local release gate.

## Quick References

- Detailed architecture: `docs/architecture.md`.
- Release and doc-only cycles: `docs/release.md`.
- Local quirks: `.dropbox.token` must be a file, E2E may pass with an empty
  source folder, and rare transient Docker BuildKit cache errors can be retried.

## Full Development Cycle

- For code, tests, dependencies, Docker, scripts, configuration, or mixed changes:
  create a feature branch from `master`, make scoped changes, run
  `make release-check`, commit, merge to `master` with a merge commit, tag the
  next `vX.Y.Z`, and push `master` plus the tag.
- For documentation-only changes, use the short cycle in `docs/release.md`:
  branch, edit, skip local verification by policy, commit, merge, tag, push, and
  report that checks were intentionally skipped.
- GitHub Actions are triggered by pushing a version tag.

## Documentation-Only Cycle

See `docs/release.md`; do not duplicate the detailed checklist here.
