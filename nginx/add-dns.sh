#!/bin/bash
set -e

# Get token from hetzner.ini
TOKEN=$(grep token /etc/letsencrypt/hetzner.ini | cut -d= -f2 | tr -d ' ')

# Install jq if needed
apt install -y jq >/dev/null 2>&1 || true

# Get zone ID for schutztat.de
ZONE_ID=$(curl -s -H "Auth-API-Token: $TOKEN" https://dns.hetzner.com/api/v1/zones | jq -r '.zones[] | select(.name=="schutztat.de") | .id')

echo "Zone ID for schutztat.de: $ZONE_ID"

if [ -z "$ZONE_ID" ]; then
    echo "ERROR: Could not find zone ID for schutztat.de"
    exit 1
fi

# Server IP
SERVER_IP="88.198.191.108"

# Add A record for bfagent.schutztat.de
echo "Adding A record for bfagent.schutztat.de..."
curl -s -X POST "https://dns.hetzner.com/api/v1/records" \
    -H "Auth-API-Token: $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"zone_id\":\"$ZONE_ID\",\"type\":\"A\",\"name\":\"bfagent\",\"value\":\"$SERVER_IP\",\"ttl\":300}"

echo ""

# Add A record for travel.schutztat.de
echo "Adding A record for travel.schutztat.de..."
curl -s -X POST "https://dns.hetzner.com/api/v1/records" \
    -H "Auth-API-Token: $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"zone_id\":\"$ZONE_ID\",\"type\":\"A\",\"name\":\"travel\",\"value\":\"$SERVER_IP\",\"ttl\":300}"

echo ""
echo "Done! DNS records added."
