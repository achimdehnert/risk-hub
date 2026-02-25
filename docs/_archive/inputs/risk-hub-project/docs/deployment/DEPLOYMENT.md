# risk-hub Deployment Guide

## 📋 Voraussetzungen

### Lokale Tools

```bash
# Terraform (>= 1.5)
brew install terraform  # macOS
# oder: https://www.terraform.io/downloads

# Ansible (>= 2.15)
brew install ansible  # macOS
pip install ansible   # oder via pip

# Hetzner CLI (optional)
brew install hcloud
```

### Accounts & API Keys

1. **Hetzner Cloud Account**: https://console.hetzner.cloud/
2. **Hetzner API Token**: Cloud Console → Security → API Tokens → Generate
3. **SSH Key**: In Hetzner Console hochladen

---

## 🚀 Initial Deployment

### 1. Repository klonen

```bash
git clone https://github.com/bfagent/risk-hub.git
cd risk-hub
```

### 2. Terraform konfigurieren

```bash
cd infra/terraform

# Variables erstellen
cp environments/prod/prod.tfvars.example environments/prod/prod.tfvars

# prod.tfvars editieren:
# - hcloud_token = "dein-api-token"
# - ssh_keys = ["dein-ssh-key-name"]
# - domain = "deine-domain.de"
```

### 3. Infrastruktur provisionieren

```bash
# Terraform initialisieren
terraform init

# Plan prüfen
terraform plan -var-file="environments/prod/prod.tfvars"

# Infrastruktur erstellen
terraform apply -var-file="environments/prod/prod.tfvars"

# Outputs speichern
terraform output -json > ../../outputs.json
terraform output ansible_inventory > ../ansible/inventory/prod
```

### 4. DNS konfigurieren

Nach dem Terraform Apply erhältst du die Load Balancer IP.
Konfiguriere bei deinem DNS Provider:

```
A     @     → <load_balancer_ip>
A     *     → <load_balancer_ip>
AAAA  @     → <load_balancer_ipv6>
AAAA  *     → <load_balancer_ipv6>
```

### 5. Secrets vorbereiten

```bash
cd ../ansible

# Ansible Vault für Secrets
ansible-vault create group_vars/all/secrets.yml

# Inhalt:
# django_secret_key: "$(python -c 'import secrets; print(secrets.token_urlsafe(50))')"
# db_password: "sicheres-passwort"
# s3_access_key: "dein-s3-key"
# s3_secret_key: "dein-s3-secret"
```

### 6. Server konfigurieren

```bash
# Alle Server konfigurieren
ansible-playbook -i inventory/prod playbooks/site.yml --ask-vault-pass

# Oder schrittweise:
ansible-playbook -i inventory/prod playbooks/site.yml --tags common
ansible-playbook -i inventory/prod playbooks/site.yml --tags docker
ansible-playbook -i inventory/prod playbooks/site.yml --tags postgres
ansible-playbook -i inventory/prod playbooks/site.yml --tags app
```

### 7. App deployen

```bash
# Zurück ins Projekt-Root
cd ../..

# Docker Image bauen und pushen
./scripts/deploy.sh prod latest
```

### 8. Initialisierung

```bash
# Auf einem App Server:
ssh root@<app-server-ip>

# Migrationen
docker exec risk-hub-app python manage.py migrate

# Superuser erstellen
docker exec -it risk-hub-app python manage.py createsuperuser

# Demo Tenant (optional)
docker exec risk-hub-app python manage.py seed_demo
```

---

## 🔄 Updates deployen

### Application Update

```bash
# Neues Image bauen und deployen
./scripts/deploy.sh prod v1.2.3

# Oder manuell:
docker build -t ghcr.io/bfagent/risk-hub-app:v1.2.3 .
docker push ghcr.io/bfagent/risk-hub-app:v1.2.3

ansible-playbook -i inventory/prod playbooks/site.yml \
  --tags deploy \
  -e "app_version=v1.2.3"
```

### Infrastructure Update

```bash
cd infra/terraform
terraform plan -var-file="environments/prod/prod.tfvars"
terraform apply -var-file="environments/prod/prod.tfvars"
```

---

## 🔒 SSL Zertifikate

### Option A: Hetzner Load Balancer (empfohlen)

1. Zertifikat in Hetzner Console hochladen
2. Load Balancer Service konfigurieren

```hcl
# In main.tf hinzufügen:
resource "hcloud_uploaded_certificate" "main" {
  name        = "risk-hub-cert"
  private_key = file("certs/privkey.pem")
  certificate = file("certs/fullchain.pem")
}
```

### Option B: Let's Encrypt via Certbot

```bash
# Auf App Server
apt install certbot
certbot certonly --standalone -d risk-hub.de -d *.risk-hub.de
```

---

## 📊 Monitoring Setup (Optional)

### Prometheus + Grafana

```bash
# Monitoring aktivieren
cd infra/terraform
terraform apply -var-file="environments/prod/prod.tfvars" -var="enable_monitoring=true"

# Monitoring konfigurieren
cd ../ansible
ansible-playbook -i inventory/prod playbooks/monitoring.yml
```

### Alerts konfigurieren

```yaml
# In ansible/roles/monitoring/files/alerts.yml
groups:
  - name: risk-hub
    rules:
      - alert: HighErrorRate
        expr: rate(django_http_responses_total{status=~"5.."}[5m]) > 0.1
        for: 5m
        labels:
          severity: critical
```

---

## 🔙 Backup & Restore

### Automatische Backups

Backups werden täglich um 3:00 erstellt:
- PostgreSQL: `/opt/postgres/backups/`
- Retention: 14 Tage lokal

### Manuelles Backup

```bash
ssh root@<db-server-ip>
/opt/postgres/backup.sh
```

### Restore

```bash
# Stop App
docker stop risk-hub-app

# Restore Backup
gunzip -c /opt/postgres/backups/risk_hub_20260128.sql.gz | \
  docker exec -i postgres psql -U app risk_hub

# Start App
docker start risk-hub-app
```

---

## 🔧 Troubleshooting

### Logs prüfen

```bash
# App Logs
ssh root@<app-server-ip>
docker logs -f risk-hub-app

# Worker Logs
ssh root@<worker-server-ip>
docker logs -f risk-hub-worker

# Postgres Logs
ssh root@<db-server-ip>
docker logs -f postgres
```

### Health Check

```bash
# API Health
curl https://api.risk-hub.de/health/

# Load Balancer Status
hcloud load-balancer describe risk-hub-lb-prod
```

### Häufige Probleme

| Problem | Lösung |
|---------|--------|
| 502 Bad Gateway | App Container neu starten: `docker restart risk-hub-app` |
| DB Connection Error | PgBouncer prüfen: `docker logs pgbouncer` |
| SSL Fehler | Zertifikat-Datum prüfen, ggf. erneuern |
| Tenant nicht gefunden | DNS Propagation abwarten, Cache leeren |

---

## 📞 Support

Bei Problemen:
1. Logs prüfen (siehe oben)
2. GitHub Issues erstellen
3. Dokumentation konsultieren
