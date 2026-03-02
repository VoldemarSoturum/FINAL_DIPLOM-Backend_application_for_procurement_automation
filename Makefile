.PHONY: test test-fast test-cov test-docker test-docker-host

test:
	pytest

test-fast:
	pytest -m "not slow and not integration"

test-cov:
	pytest --cov-report=term-missing --cov-report=html

# ------------------------------------------------------------
# test-docker: запуск ВНУТРИ контейнера (web / tests)
# ВАЖНО:
# - здесь НЕТ docker compose
# - просто выставляем env под compose-сеть и запускаем pytest
# Пример:
#   docker compose exec web make test-docker
# ------------------------------------------------------------
test-docker:
	DJANGO_SETTINGS_MODULE=config.settings_test_pg \
	POSTGRES_HOST=db \
	POSTGRES_PORT=5432 \
	CELERY_BROKER_URL=redis://redis:6379/0 \
	CELERY_RESULT_BACKEND=redis://redis:6379/1 \
	pytest -q

# ------------------------------------------------------------
# test-docker-host: запуск С ХОСТА одной командой
# Запускает pytest внутри контейнера web (compose-сеть видит db/redis по именам)
# Пример:
#   make test-docker-host
# ------------------------------------------------------------
test-docker-host:
	docker compose run --rm \
		-e DJANGO_SETTINGS_MODULE=config.settings_test_pg \
		-e POSTGRES_HOST=db \
		-e POSTGRES_PORT=5432 \
		-e CELERY_BROKER_URL=redis://redis:6379/0 \
		-e CELERY_RESULT_BACKEND=redis://redis:6379/1 \
		web pytest -q