---
description: Deploy risk-hub to production server (88.198.191.108)
---

# Deploy Risk-Hub

## Prerequisites

- All changes committed and pushed to `main`
- Docker logged in to GHCR (`docker login ghcr.io`)

## Steps

1. Verify git status is clean

// turbo
2. Run tests locally: `cd src && pytest`

3. Build Docker image:
```bash
cd /home/dehnert/github/risk-hub
docker build -f docker/app/Dockerfile -t ghcr.io/achimdehnert/risk-hub/risk-hub-web:latest .
```

4. Push image to GHCR:
```bash
docker push ghcr.io/achimdehnert/risk-hub/risk-hub-web:latest
```

5. Pull new image on server:
```bash
ssh root@88.198.191.108 'cd /opt/risk-hub && docker compose -f docker-compose.prod.yml pull risk-hub-web'
```

6. Restart containers with force-recreate:
```bash
ssh root@88.198.191.108 'cd /opt/risk-hub && docker compose -f docker-compose.prod.yml up -d --force-recreate risk-hub-web risk-hub-worker'
```

7. Wait 5 seconds for gunicorn to boot, then verify health:
```bash
ssh root@88.198.191.108 'sleep 5 && curl -s -o /dev/null -w "%{http_code}" -H "Host: demo.schutztat.de" http://127.0.0.1:8090/'
```
Expected: `200`

8. Check container logs for errors:
```bash
ssh root@88.198.191.108 'docker logs risk_hub_web --tail 10 2>&1'
```
