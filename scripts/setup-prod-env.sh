#!/bin/bash
set -e
cd /opt/risk-hub

# Generate secrets
SECRET_KEY=$(openssl rand -base64 50 | tr -d '\n')
PG_PASS=$(openssl rand -base64 24 | tr -d '\n')

# Create .env.prod
cat > .env.prod << EOF
# Risk-Hub Production Environment
GHCR_OWNER=achimdehnert
GHCR_REPO=risk-hub
IMAGE_TAG=latest

# Database
POSTGRES_DB=risk_hub
POSTGRES_USER=risk_hub
POSTGRES_PASSWORD=${PG_PASS}

# Django
SECRET_KEY=${SECRET_KEY}
ALLOWED_HOSTS=risk-hub.schutztat.de,schutztat.de,localhost

# Debug
DEBUG=false
EOF

echo "Created .env.prod with generated secrets"
cat .env.prod | grep -E "(POSTGRES_DB|ALLOWED)"
