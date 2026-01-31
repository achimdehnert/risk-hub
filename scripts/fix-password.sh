#!/bin/bash
cd /opt/risk-hub
NEW_PASS=$(openssl rand -hex 24)
sed -i "s|POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=${NEW_PASS}|" .env.prod

# Recreate containers with new password
docker compose --env-file .env.prod -f docker-compose.prod.yml down
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d

echo "Containers restarted with new password"
docker ps | grep risk
