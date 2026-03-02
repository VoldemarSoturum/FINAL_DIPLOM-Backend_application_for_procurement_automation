FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# system deps for psycopg2-binary обычно не нужны, но pg_isready/ssl и т.п. полезны
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Сначала зависимости — для кеширования слоёв
COPY requirements.txt /app/requirements.txt
COPY requirements-dev.txt /app/requirements-dev.txt

RUN pip install --upgrade pip \
 && pip install -r /app/requirements.txt \
 && if [ -f /app/requirements-dev.txt ]; then pip install -r /app/requirements-dev.txt; fi

# Потом код
COPY . /app

# По умолчанию ничего не запускаем — команды задаёт docker-compose