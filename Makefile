.PHONY: test lint format-check verify e2e compose-config shell-check release-check

test:
	.venv/bin/python -m pytest -q

lint:
	.venv/bin/ruff check .

format-check:
	.venv/bin/ruff format --check .

verify: test lint format-check

e2e:
	./e2e-local.sh

compose-config:
	docker compose config --quiet

shell-check:
	bash -n deploy-local.sh deploy.sh e2e-local.sh sync-env-from-github.sh

release-check: verify shell-check compose-config e2e
