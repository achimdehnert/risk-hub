FROM python:3.12-slim

# OCI Labels (ADR-022)
ARG APP_NAME=risk-hub
LABEL org.opencontainers.image.source="https://github.com/achimdehnert/${APP_NAME}"
LABEL org.opencontainers.image.description="Schutztat - Occupational Safety SaaS"

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# System deps (weasyprint needs pango/gdk-pixbuf/cairo; git for git+https requirements)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential git \
    libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b libfribidi0 \
    libgdk-pixbuf-2.0-0 libcairo2 libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Build-time secret for private GitHub packages (platform-context, django-tenancy)
ARG PROJECT_PAT

# Install public packages first (always succeeds)
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -U pip setuptools wheel \
    && grep -v 'git+https://' /app/requirements.txt | grep -v '^#' | grep -v '^$' > /tmp/requirements-public.txt \
    && pip install --no-cache-dir -r /tmp/requirements-public.txt

# Install private packages (requires PROJECT_PAT, non-fatal if fails)
RUN git config --global url."https://x-access-token:${PROJECT_PAT}@github.com/".insteadOf "https://github.com/" \
    && grep 'git+https://' /app/requirements.txt > /tmp/requirements-private.txt \
    && pip install --no-cache-dir -r /tmp/requirements-private.txt || echo "Private packages install failed (non-fatal)" \
    && (git config --global --unset url."https://x-access-token:${PROJECT_PAT}@github.com/".insteadOf 2>/dev/null || true)

COPY docker/app/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

COPY src /app/src
WORKDIR /app/src

ENV PYTHONPATH=/app/src

# Collect static files at build time (non-fatal if private packages missing)
RUN DJANGO_SETTINGS_MODULE=config.settings_build \
    SECRET_KEY=build-only-not-used-in-prod \
    python manage.py collectstatic --noinput 2>&1 || echo "collectstatic skipped"
RUN chown -R app:app /app/src/staticfiles 2>/dev/null || true

# Create non-root user (ADR-022)
RUN groupadd --gid 1000 app && \
    useradd --uid 1000 --gid 1000 --create-home app && \
    chown -R app:app /app
USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/livez/')" || exit 1

ENTRYPOINT ["/entrypoint.sh"]
CMD ["web"]
