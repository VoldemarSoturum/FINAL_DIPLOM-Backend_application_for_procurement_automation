.PHONY: test test-fast test-docker test-cov

test:
	pytest

test-fast:
	pytest -m "not slow and not integration"

test-cov:
	pytest --cov-report=term-missing --cov-report=html

test-docker:
	POSTGRES_HOST=db POSTGRES_PORT=5432 DJANGO_SETTINGS_MODULE=config.settings_test_pg pytest -q