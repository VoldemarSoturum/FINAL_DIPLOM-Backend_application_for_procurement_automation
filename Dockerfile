FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# -----------------------------------------------------------------------------
# System deps
# -----------------------------------------------------------------------------
# Нужно для:
# - curl (healthcheck / отладка)
# - make (твои make targets)
# - libmagic (python-magic -> django-versatileimagefield)
#
# Важно: ставим в одном RUN, чтобы слои не дублировали apt-get update.
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    make \
    libmagic1 \
    libmagic-mgc \
    && rm -rf /var/lib/apt/lists/*

# -----------------------------------------------------------------------------
# Python deps (слои кешируются лучше, чем если копировать весь проект до pip install)
# -----------------------------------------------------------------------------
COPY requirements.txt /app/requirements.txt
COPY requirements-dev.txt /app/requirements-dev.txt

RUN pip install --upgrade pip \
 && pip install -r /app/requirements.txt \
 && if [ -f /app/requirements-dev.txt ]; then pip install -r /app/requirements-dev.txt; fi

# -----------------------------------------------------------------------------
# App code
# -----------------------------------------------------------------------------
COPY . /app

# По умолчанию ничего не запускаем — команды задаёт docker-compose