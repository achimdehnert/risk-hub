#!/bin/bash
# setup-server.sh — Initial server setup for risk-hub production + staging
# Run once on 88.198.191.108 as root/sudo
# Usage: bash setup-server.sh [prod|staging|all]
set -euo pipefail

DEPLOY_PATH="/opt/risk-hub"
NGINX_CONF_DIR="/etc/nginx/sites-available"
TARGET="${1:-all}"

echo "=== risk-hub Server Setup (target: $TARGET) ==="

# ── 1. Create directories ─────────────────────────────────────────────────────
echo "[1/5] Creating deploy directories..."
mkdir -p "${DEPLOY_PATH}"
mkdir -p /opt/backups/risk-hub
chmod 750 "${DEPLOY_PATH}"

# ── 2. Create .env files (placeholders — filled by CI secrets injection) ──────
echo "[2/5] Creating .env placeholder files..."

if [[ "$TARGET" == "prod" || "$TARGET" == "all" ]]; then
    if [[ ! -f "${DEPLOY_PATH}/.env.prod" ]]; then
        cat > "${DEPLOY_PATH}/.env.prod" << 'EOF'
# Production — filled by CI/CD
DJANGO_SETTINGS_MODULE=config.settings
DJANGO_DEBUG=0
DJANGO_ALLOWED_HOSTS=schutztat.de,www.schutztat.de,.schutztat.de
DJANGO_SECRET_KEY=REPLACE_IN_CI
DATABASE_URL=postgresql://risk_hub:REPLACE_IN_CI@risk-hub-db:5432/risk_hub
REDIS_URL=redis://risk-hub-redis:6379/0
POSTGRES_USER=risk_hub
POSTGRES_PASSWORD=REPLACE_IN_CI
POSTGRES_DB=risk_hub
CSRF_TRUSTED_ORIGINS=https://schutztat.de,https://www.schutztat.de,https://*.schutztat.de
TENANT_BASE_DOMAIN=schutztat.de
TENANT_ALLOW_LOCALHOST=0
TENANT_RESERVED_SUBDOMAINS=www,staging
S3_ENDPOINT=http://risk-hub-minio:9000
S3_BUCKET=documents
S3_ACCESS_KEY=REPLACE_IN_CI
S3_SECRET_KEY=REPLACE_IN_CI
MINIO_ROOT_USER=REPLACE_IN_CI
MINIO_ROOT_PASSWORD=REPLACE_IN_CI
GHCR_OWNER=achimdehnert
GHCR_REPO=risk-hub
EOF
        echo "  Created ${DEPLOY_PATH}/.env.prod (placeholder)"
    else
        echo "  ${DEPLOY_PATH}/.env.prod already exists — skipping"
    fi
fi

if [[ "$TARGET" == "staging" || "$TARGET" == "all" ]]; then
    if [[ ! -f "${DEPLOY_PATH}/.env.staging" ]]; then
        cat > "${DEPLOY_PATH}/.env.staging" << 'EOF'
# Staging — filled by CI/CD
DJANGO_SETTINGS_MODULE=config.settings
DJANGO_DEBUG=0
DJANGO_ALLOWED_HOSTS=staging.schutztat.de,.staging.schutztat.de
DJANGO_SECRET_KEY=REPLACE_IN_CI
DATABASE_URL=postgresql://risk_hub:REPLACE_IN_CI@risk-hub-staging-db:5432/risk_hub_staging
REDIS_URL=redis://risk-hub-staging-redis:6379/0
POSTGRES_USER=risk_hub
POSTGRES_PASSWORD=REPLACE_IN_CI
POSTGRES_DB=risk_hub_staging
CSRF_TRUSTED_ORIGINS=https://staging.schutztat.de,https://*.staging.schutztat.de
TENANT_BASE_DOMAIN=staging.schutztat.de
TENANT_ALLOW_LOCALHOST=0
TENANT_RESERVED_SUBDOMAINS=www
S3_ENDPOINT=http://risk-hub-staging-minio:9000
S3_BUCKET=documents-staging
S3_ACCESS_KEY=REPLACE_IN_CI
S3_SECRET_KEY=REPLACE_IN_CI
MINIO_ROOT_USER=REPLACE_IN_CI
MINIO_ROOT_PASSWORD=REPLACE_IN_CI
GHCR_OWNER=achimdehnert
GHCR_REPO=risk-hub
STRIPE_SECRET_KEY=sk_test_dummy
STRIPE_PUBLISHABLE_KEY=pk_test_dummy
STRIPE_WEBHOOK_SECRET=whsec_dummy
EOF
        echo "  Created ${DEPLOY_PATH}/.env.staging (placeholder)"
    else
        echo "  ${DEPLOY_PATH}/.env.staging already exists — skipping"
    fi
fi

# ── 3. Copy compose files ─────────────────────────────────────────────────────
echo "[3/5] Note: compose files are deployed by CI/CD via git checkout."
echo "  Manual: scp docker-compose.prod.yml docker-compose.staging.yml user@server:/opt/risk-hub/"

# ── 4. Install nginx configs ──────────────────────────────────────────────────
echo "[4/5] Installing nginx configuration..."

if [[ ! -d "$NGINX_CONF_DIR" ]]; then
    echo "  WARN: nginx not installed — run: apt-get install -y nginx"
else
    for CONF in nginx-prod nginx-staging; do
        SRC="${DEPLOY_PATH}/docker/nginx/${CONF}.conf"
        DEST="${NGINX_CONF_DIR}/risk-hub-${CONF#nginx-}.conf"
        if [[ -f "$SRC" ]]; then
            cp "$SRC" "$DEST"
            ln -sf "$DEST" "/etc/nginx/sites-enabled/risk-hub-${CONF#nginx-}.conf"
            echo "  Installed $DEST"
        fi
    done
    nginx -t && systemctl reload nginx && echo "  nginx reloaded OK"
fi

# ── 5. Done ───────────────────────────────────────────────────────────────────
echo "[5/5] Setup complete."
echo ""
echo "Next steps:"
echo "  1. Push to main → CI builds image + deploys prod + staging"
echo "  2. DNS: schutztat.de + staging.schutztat.de → 88.198.191.108"
echo "  3. Cloudflare: proxy ON for both domains"
