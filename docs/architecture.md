# Architecture Notes

`remrec` is a Python 3.11 Dockerized OCR workflow for reMarkable PDF exports.
It polls a Dropbox or Google Drive source folder, recognizes handwritten pages
through an OpenAI-compatible vision API, writes a text PDF, uploads it to a
destination folder, and either deletes or quarantines the original.

## Workflow

1. `src.main` loads typed settings and initializes the configured storage client.
2. The workflow verifies source, destination, and failed folders.
3. Files are listed from the source folder. Listing failures are mapped to
   workflow statuses instead of escaping raw.
4. Each PDF is processed by `src.processing` under a per-file lock.
5. Processing downloads the PDF, reads its page count, converts and recognizes
   pages one at a time, creates the output PDF, uploads it, then deletes the
   original only after a result exists.
6. Permanent file failures are moved to the failed folder. Transient failures are
   left in place for retry.

## Module Boundaries

- `src/main.py`: orchestration, workflow status, loop and `--run-once`.
- `src/processing.py`: one-file processing and local temporary files.
- `src/storage/base.py`, `src/storage/dto.py`: provider-neutral storage boundary.
- `src/dbox.py`, `src/gdrive.py`: provider adapters and provider-specific path,
  ID, chunking, and query details.
- `src/recognition.py`: OpenAI-compatible vision API adapter.
- `src/pdf_utils.py`: output PDF generation. OCR text must be escaped before
  ReportLab paragraph markup.
- `src/config.py`: typed environment settings and provider folder normalization.
- `src/exceptions.py`: domain exception taxonomy used for workflow decisions.

## Invariants

- Provider SDK exceptions should be translated into domain exceptions at adapter
  boundaries.
- Workflow decisions should depend on `PermanentError`, `TransientError`, and
  storage/recognition subclasses.
- Source files should be deleted only after the recognized output is known to
  exist or after duplicate output is detected.
- OCR output text is untrusted input and must be escaped before PDF markup.
- Runtime Docker images should contain only runtime code/assets, not local
  secrets, tests, caches, credentials, logs, or coverage output.
