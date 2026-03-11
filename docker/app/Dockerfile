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

# Install private packages via direct git clone + pip install (avoids pip resolvelib bug)
RUN pip install --no-cache-dir hatchling hatch-vcs flit_core \
    && git config --global url."https://x-access-token:${PROJECT_PAT}@github.com/".insteadOf "https://github.com/" \
    && git clone --depth=1 --filter=blob:none https://github.com/achimdehnert/platform.git /tmp/platform 2>/dev/null || true \
    && (pip install --no-cache-dir /tmp/platform/packages/django-tenancy 2>&1 && echo "OK: django-tenancy") || echo "SKIP: django-tenancy" \
    && (pip install --no-cache-dir /tmp/platform/packages/platform-context 2>&1 && echo "OK: platform-context") || echo "SKIP: platform-context" \
    && (pip install --no-cache-dir /tmp/platform/packages/django-module-shop 2>&1 && echo "OK: django-module-shop") || echo "SKIP: django-module-shop" \
    && grep 'git+https://github.com/achimdehnert/nl2cad' /app/requirements.txt > /tmp/nl2cad-pkgs.txt \
    && git clone --depth=1 --filter=blob:none https://github.com/achimdehnert/nl2cad.git /tmp/nl2cad 2>/dev/null || true \
    && (pip install --no-cache-dir /tmp/nl2cad/packages/nl2cad-core 2>&1 && echo "OK: nl2cad-core") || echo "SKIP: nl2cad-core" \
    && (pip install --no-cache-dir /tmp/nl2cad/packages/nl2cad-areas 2>&1 && echo "OK: nl2cad-areas") || echo "SKIP: nl2cad-areas" \
    && (pip install --no-cache-dir /tmp/nl2cad/packages/nl2cad-brandschutz 2>&1 && echo "OK: nl2cad-brandschutz") || echo "SKIP: nl2cad-brandschutz" \
    && (pip install --no-cache-dir /tmp/nl2cad/packages/nl2cad-gaeb 2>&1 && echo "OK: nl2cad-gaeb") || echo "SKIP: nl2cad-gaeb" \
    && rm -rf /tmp/platform /tmp/nl2cad \
    && (git config --global --unset url."https://x-access-token:${PROJECT_PAT}@github.com/".insteadOf 2>/dev/null || true)

COPY docker/app/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

COPY src /app/src
COPY packages /app/packages
WORKDIR /app/src

ENV PYTHONPATH=/app/src

# Override platform's django-tenancy with risk-hub's own version (UUID PK, tenancy_organization table)
RUN pip install --no-cache-dir /app/packages/django-tenancy 2>&1 && echo "OK: risk-hub django-tenancy" || echo "SKIP: risk-hub django-tenancy"

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
