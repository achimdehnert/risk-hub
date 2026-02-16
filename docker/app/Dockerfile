FROM python:3.12-slim

# OCI Labels (ADR-022)
ARG APP_NAME=risk-hub
LABEL org.opencontainers.image.source="https://github.com/achimdehnert/${APP_NAME}"
LABEL org.opencontainers.image.description="Schutztat - Occupational Safety SaaS"

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# System deps (weasyprint needs pango, gdk-pixbuf, cairo)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b libfribidi0 \
    libgdk-pixbuf-2.0-0 libcairo2 libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy shared packages first
COPY packages/bfagent-core /app/packages/bfagent-core
COPY packages/bfagent-llm /app/packages/bfagent-llm
COPY packages/platform-context /app/packages/platform-context

# Install shared packages
RUN pip install --no-cache-dir -U pip \
    && pip install --no-cache-dir /app/packages/bfagent-core \
    && pip install --no-cache-dir /app/packages/bfagent-llm \
    && pip install --no-cache-dir /app/packages/platform-context

# Install main app dependencies
COPY pyproject.toml /app/pyproject.toml
RUN pip install --no-cache-dir \
    Django dj-database-url "psycopg[binary]" python-dotenv \
    django-htmx django-ninja djangorestframework django-filter \
    pydantic boto3 httpx structlog jinja2 jsonschema tenacity \
    weasyprint python-docx "celery[redis]" \
    gunicorn whitenoise

COPY docker/app/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

COPY src /app/src
WORKDIR /app/src

ENV PYTHONPATH=/app/src

# Collect static files at build time
RUN DJANGO_SECRET_KEY=build-only \
    DJANGO_SETTINGS_MODULE=config.settings \
    DATABASE_URL=sqlite:///dev-null \
    python manage.py collectstatic --noinput 2>/dev/null || true

# Create non-root user (ADR-022)
RUN groupadd --gid 1000 app && \
    useradd --uid 1000 --gid 1000 --create-home app && \
    chown -R app:app /app
USER app

EXPOSE 8000

# Health check (ADR-022: python urllib, no curl)
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/livez/')" || exit 1

ENTRYPOINT ["/entrypoint.sh"]
CMD ["web"]
