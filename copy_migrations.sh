#!/bin/bash
set -e
CID=$(docker create risk-hub-temp:nomig)
for app in actions approvals audit documents explosionsschutz identity notifications outbox permissions reporting risk substances tenancy; do
  docker cp "$CID:/app/src/$app/migrations/." "/home/dehnert/github/risk-hub/src/$app/migrations/" 2>/dev/null && echo "Copied: $app"
done
docker rm "$CID" > /dev/null
echo "Done copying migrations"
