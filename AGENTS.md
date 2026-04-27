# Codex Working Notes

## Full Development Cycle

Current agreed process for implementation requests that should be completed end to end:

1. Check the current branch and worktree state with `git status --short --branch`.
2. Create a feature branch from `master`; do not implement directly on `master`.
3. Make the requested code, test, documentation, and configuration changes.
4. Keep the change scoped to the accepted recommendation; avoid unrelated refactors.
5. Run local verification:
   - `pytest -q`
   - `ruff check .`
   - `ruff format --check .`
6. Run one local E2E pass as the final local test gate:
   - `./e2e-local.sh`
   - Use the default build behavior so the Docker image is rebuilt from the current working tree.
   - A successful empty-source run is valid if the configured storage provider has no files to process.
7. If any verification step fails, stop the release sequence, fix the problem, and rerun the relevant checks.
8. Commit the feature branch with a concise descriptive message.
9. Merge the feature branch into `master` with a merge commit.
10. Assign the next version tag after the latest `vX.Y.Z` tag.
11. Push `master` and the new tag to GitHub in the same release step.
12. Report the commit, merge commit, tag, push result, and completed checks.

GitHub Actions are triggered by pushing a version tag. After push, the remote workflow is expected to run the CI test job and Docker build/push job.
