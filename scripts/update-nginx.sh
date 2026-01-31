#!/bin/bash
cd /opt/risk-hub
IP=$(docker inspect risk_hub_web --format '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}')
echo "Container IP: $IP"
sed -i "s|proxy_pass http://[0-9.]*:8000|proxy_pass http://$IP:8000|" /etc/nginx/sites-available/risk-hub.schutztat.de.conf
nginx -t && systemctl reload nginx
echo "Testing HTTPS..."
curl -sI https://risk-hub.schutztat.de | head -10
