# Release Notes

## Full Change Cycle

Use this cycle for code, tests, dependencies, Docker, scripts, configuration, or
mixed changes:

1. Check branch and worktree:
   ```shell
   git status --short --branch
   ```
2. Create a feature branch from `master`.
3. Make scoped changes.
4. Run:
   ```shell
   make release-check
   ```
   This runs unit tests, ruff lint, ruff format check, shell syntax checks,
   Docker Compose config validation, and local E2E.
5. Fix failures and rerun relevant checks.
6. Commit the feature branch.
7. Merge into `master` with a merge commit.
8. Create the next `vX.Y.Z` tag.
9. Push `master` and the tag in the same release step:
   ```shell
   git push origin master vX.Y.Z
   ```

Pushing a version tag triggers GitHub Actions to run CI and build/push the Docker
image.

## Documentation-Only Cycle

Use this only when changes are limited to documentation files (`*.md`), comments,
or agent notes, and do not modify code, tests, dependencies, Docker, scripts, or
configuration.

1. Check branch and worktree.
2. Create a feature branch from `master`.
3. Make the documentation-only change.
4. Skip local test, lint, format, and E2E gates by policy.
5. Commit, merge into `master` with a merge commit, create the next tag, and push
   `master` plus the tag.
6. Report that verification was intentionally skipped because the change was
   documentation-only.

## Local Quirks

- `.dropbox.token` must be a regular file. If it exists as a directory, remove it
  before running `deploy-local.sh`.
- E2E uses live `.env` credentials. An empty source folder is a valid successful
  result.
- A transient Docker BuildKit snapshot/cache export error has been observed once;
  rerunning the same E2E command succeeded.
