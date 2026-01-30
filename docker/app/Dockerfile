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

# Install shared packages
RUN pip install --no-cache-dir -U pip \
    && pip install --no-cache-dir /app/packages/bfagent-core \
    && pip install --no-cache-dir /app/packages/bfagent-llm

# Install main app dependencies
COPY pyproject.toml /app/pyproject.toml
RUN pip install --no-cache-dir Django dj-database-url "psycopg[binary]" python-dotenv django-htmx django-ninja pydantic boto3 httpx structlog jinja2 jsonschema tenacity gunicorn

COPY docker/app/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

COPY src /app/src
WORKDIR /app/src

ENV PYTHONPATH=/app/src
