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

# Copy local packages before pip install
COPY packages/ /app/packages/

# Install all dependencies from requirements.txt (single source of truth)
COPY requirements.txt /app/requirements.txt
RUN git config --global url."https://x-access-token:${PROJECT_PAT}@github.com/".insteadOf "https://github.com/" \
    && pip install --no-cache-dir -U pip \
    && pip install --no-cache-dir -r /app/requirements.txt \
    && pip install --no-cache-dir -e /app/packages/django-module-shop/ \
    && git config --global --unset url."https://x-access-token:${PROJECT_PAT}@github.com/".insteadOf || true

COPY docker/app/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

COPY src /app/src
WORKDIR /app/src

ENV PYTHONPATH=/app/src

# Collect static files at build time
RUN DJANGO_SETTINGS_MODULE=config.settings_build \
    python manage.py collectstatic --noinput
RUN chown -R app:app /app/src/staticfiles 2>/dev/null || true

# Create non-root user (ADR-022)
RUN groupadd --gid 1000 app && \
    useradd --uid 1000 --gid 1000 --create-home app && \
    chown -R app:app /app
USER app

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
CMD ["web"]
