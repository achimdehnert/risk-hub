# ── Stage 1: Builder (has build-essential+git, removed from final) ──────
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Build deps + runtime libs needed for compilation
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential git libffi-dev \
    libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b libfribidi0 \
    libgdk-pixbuf-2.0-0 libcairo2 \
    && rm -rf /var/lib/apt/lists/*

# Build-time secret for private GitHub packages — injected via BuildKit --secret, never stored in layers
# Usage: docker build --secret id=PROJECT_PAT,env=PROJECT_PAT ...

# Install public packages first (always succeeds)
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -U pip setuptools wheel \
    && grep -v 'git+https://' /app/requirements.txt | grep -v '^#' | grep -v '^$' > /tmp/requirements-public.txt \
    && pip install --no-cache-dir -r /tmp/requirements-public.txt

# Install private packages via direct git clone + pip install (avoids pip resolvelib bug)
RUN --mount=type=secret,id=PROJECT_PAT \
    pip install --no-cache-dir hatchling hatch-vcs flit_core \
    && PROJECT_PAT=$(cat /run/secrets/PROJECT_PAT 2>/dev/null || echo "") \
    && if [ -n "${PROJECT_PAT}" ]; then git config --global url."https://x-access-token:${PROJECT_PAT}@github.com/".insteadOf "https://github.com/"; fi \
    && git clone --depth=1 https://github.com/achimdehnert/platform.git /tmp/platform 2>/dev/null || true \
    && echo "SKIP: platform django-tenancy (risk-hub uses its own)" \
    && (pip install --no-cache-dir /tmp/platform/packages/platform-context 2>&1 && echo "OK: platform-context") || echo "SKIP: platform-context" \
    && (pip install --no-cache-dir /tmp/platform/packages/django-module-shop 2>&1 && echo "OK: django-module-shop") || echo "SKIP: django-module-shop" \
    && (pip install --no-cache-dir "/tmp/platform/packages/concept-templates[llm,pdf]" 2>&1 && echo "OK: concept-templates") || echo "SKIP: concept-templates" \
    && (grep 'git+https://github.com/achimdehnert/nl2cad' /app/requirements.txt > /tmp/nl2cad-pkgs.txt || true) \
    && git clone --depth=1 https://github.com/achimdehnert/nl2cad.git /tmp/nl2cad 2>/dev/null || true \
    && (pip install --no-cache-dir /tmp/nl2cad/packages/nl2cad-core 2>&1 && echo "OK: nl2cad-core") || echo "SKIP: nl2cad-core" \
    && (pip install --no-cache-dir /tmp/nl2cad/packages/nl2cad-areas 2>&1 && echo "OK: nl2cad-areas") || echo "SKIP: nl2cad-areas" \
    && (pip install --no-cache-dir /tmp/nl2cad/packages/nl2cad-brandschutz 2>&1 && echo "OK: nl2cad-brandschutz") || echo "SKIP: nl2cad-brandschutz" \
    && (pip install --no-cache-dir /tmp/nl2cad/packages/nl2cad-gaeb 2>&1 && echo "OK: nl2cad-gaeb") || echo "SKIP: nl2cad-gaeb" \
    && git clone --depth=1 https://github.com/achimdehnert/iil-fieldprefill.git /tmp/iil-fieldprefill 2>/dev/null || true \
    && (pip install --no-cache-dir /tmp/iil-fieldprefill 2>&1 && echo "OK: iil-fieldprefill") || echo "SKIP: iil-fieldprefill" \
    && git clone --depth=1 https://github.com/achimdehnert/iil-enrichment.git /tmp/iil-enrichment 2>/dev/null || true \
    && (pip install --no-cache-dir "/tmp/iil-enrichment[gestis,pubchem]" 2>&1 && echo "OK: iil-enrichment") || echo "SKIP: iil-enrichment" \
    && rm -rf /tmp/platform /tmp/nl2cad /tmp/iil-fieldprefill /tmp/iil-enrichment \
    && git config --global --remove-section url."https://x-access-token:${PROJECT_PAT}@github.com/" 2>/dev/null || true

# Install risk-hub's own django-tenancy in builder
COPY packages /app/packages
RUN pip install --no-cache-dir /app/packages/django-tenancy 2>&1 \
    && echo "OK: risk-hub django-tenancy" || echo "SKIP: risk-hub django-tenancy"

# ── Stage 2: Runtime (slim, no build tools) ─────────────────────────────
FROM python:3.12-slim

# OCI Labels (ADR-022)
ARG APP_NAME=risk-hub
LABEL org.opencontainers.image.source="https://github.com/achimdehnert/${APP_NAME}"
LABEL org.opencontainers.image.description="Schutztat - Occupational Safety SaaS"

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Runtime-only system deps (weasyprint needs pango/gdk-pixbuf/cairo at runtime)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b libfribidi0 \
    libgdk-pixbuf-2.0-0 libcairo2 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY docker/app/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

COPY packages /app/packages
COPY src /app/src
WORKDIR /app/src

ENV PYTHONPATH=/app/src

# ADR-083: Collect static files with build-safe settings (no dummy env vars, no || true)
RUN DJANGO_SETTINGS_MODULE=config.settings_build \
    python manage.py collectstatic --noinput
RUN chown -R 1000:1000 /app/src/staticfiles

# Create non-root user (ADR-022)
RUN groupadd --gid 1000 app && \
    useradd --uid 1000 --gid 1000 --create-home app && \
    chown -R app:app /app
USER app

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/livez/')" || exit 1

CMD ["web"]
