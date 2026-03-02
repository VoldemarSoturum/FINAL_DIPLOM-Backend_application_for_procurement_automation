.PHONY: test test-fast test-cov test-docker test-docker-host

test:
	pytest

test-fast:
	pytest -m "not slow and not integration"

test-cov:
	pytest --cov-report=term-missing --cov-report=html

# ЭТО цель для запуска ВНУТРИ контейнера web (docker compose run/exec web ...)
# Т.е. здесь НЕТ docker compose, только pytest + env под compose-сеть.
test-docker:
	DJANGO_SETTINGS_MODULE=config.settings_test_pg \
	POSTGRES_HOST=db \
	POSTGRES_PORT=5432 \
	CELERY_BROKER_URL=redis://redis:6379/0 \
	CELERY_RESULT_BACKEND=redis://redis:6379/1 \
	pytest -q

# ЭТО цель-обёртка для запуска С ХОСТА (одной командой)
test-docker-host:
	docker compose run --rm \
		-e DJANGO_SETTINGS_MODULE=config.settings_test_pg \
		-e POSTGRES_HOST=db \
		-e POSTGRES_PORT=5432 \
		-e CELERY_BROKER_URL=redis://redis:6379/0 \
		-e CELERY_RESULT_BACKEND=redis://redis:6379/1 \
		web pytest -q