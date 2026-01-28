FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl \
    && rm -rf /var/lib/apt/lists/*

# Copy shared packages first
COPY packages/bfagent-core /app/packages/bfagent-core
COPY packages/bfagent-llm /app/packages/bfagent-llm

COPY pyproject.toml /app/pyproject.toml

RUN pip install --no-cache-dir -U pip \
    && pip install --no-cache-dir -e /app/packages/bfagent-core \
    && pip install --no-cache-dir -e /app/packages/bfagent-llm \
    && pip install --no-cache-dir -e .

COPY docker/app/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

COPY src /app/src
WORKDIR /app/src
