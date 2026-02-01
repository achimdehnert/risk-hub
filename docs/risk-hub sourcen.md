#!/usr/bin/env bash
# generate.sh — creates the full repo skeleton (Docker + Django + HTMX + Postgres RLS + Subdomain tenancy + Documents(S3))
set -euo pipefail

ROOT="risk-saas"
PYTHON_VERSION="3.12"

mkdir -p "$ROOT"/{docker/app,docker/nginx,scripts,src/{config,common,tenancy,identity,audit,outbox,risk/{templates/risk/partials},documents/{templates/documents/partials},actions}}

write() {
  local path="$1"
  shift
  mkdir -p "$(dirname "$ROOT/$path")"
  cat > "$ROOT/$path" <<'EOF'
'"$@"'
EOF
}

# -------------------------
# Top-level files
# -------------------------
write "README.md" '
# risk-saas (Hetzner start, Docker, Django + HTMX, Postgres RLS, Subdomain Tenancy, Documents S3)

## Prereqs
- Docker + Docker Compose
- (Optional) `psql` locally for DB inspection

## Quick start
```bash
cp .env.example .env
docker compose up --build -d
docker compose exec app python manage.py migrate
docker compose exec app python manage.py createsuperuser
docker compose exec app python manage.py seed_demo
Then add to your hosts file:

127.0.0.1 demo.localhost

Open:

http://demo.localhost:8080/risk/assessments/

Tenant resolution: via subdomain demo → tenant slug demo.

Enable RLS (recommended for prod)
For local dev, RLS is not enforced by default (to reduce friction).
For prod/staging, execute:

docker compose exec db psql -U app -d app -f /app/scripts/enable_rls.sql
Documents (S3 / MinIO)
MinIO runs in compose:

S3 endpoint: http://minio:9000

Console: http://localhost:9001 (minio/minio123)
Bucket is auto-created by seed command.

Upload docs:

http://demo.localhost:8080/documents/

Architecture rules (enforced by convention)
No business logic in views/templates/JS — call service layer only.

All writes go through */services.py (application layer).

DB-driven: constraints + (prod) RLS + migrations.

Audit event for every risk-relevant write.

Outbox pattern for async integration/events.

Notes for Hetzner
Start with Docker on VMs + LB.

Path to Kubernetes: k3s on Hetzner (same container images, same env).

'

write ".env.example" '
DJANGO_DEBUG=1
DJANGO_SECRET_KEY=change-me
DJANGO_ALLOWED_HOSTS=.localhost,localhost,127.0.0.1

DB
DATABASE_URL=postgres://app:app@db:5432/app

Redis (optional for future async; outbox worker uses DB polling in this MVP)
REDIS_URL=redis://redis:6379/0

Tenant resolution via subdomain
TENANT_BASE_DOMAIN=localhost
TENANT_ALLOW_LOCALHOST=1

S3 / MinIO (documents)
S3_ENDPOINT=http://minio:9000
S3_REGION=us-east-1
S3_ACCESS_KEY=minio
S3_SECRET_KEY=minio123
S3_BUCKET=documents
S3_USE_SSL=0
S3_PUBLIC_BASE_URL=http://localhost:9000/documents

Security
CSRF_TRUSTED_ORIGINS=http://*.localhost:8080,http://localhost:8080
'

write "Makefile" '
.PHONY: up down logs migrate seed rls shell

up:
docker compose up --build -d

down:
docker compose down -v

logs:
docker compose logs -f --tail=200

migrate:
docker compose exec app python manage.py migrate

seed:
docker compose exec app python manage.py seed_demo

rls:
docker compose exec db psql -U app -d app -f /app/scripts/enable_rls.sql

shell:
docker compose exec app python manage.py shell
'

write "pyproject.toml" "
[project]
name = "risk-saas"
version = "0.1.0"
requires-python = ">=${PYTHON_VERSION}"
dependencies = [
"Django>=5.0,<6.0",
"dj-database-url>=2.2",
"psycopg[binary]>=3.2",
"python-dotenv>=1.0",
"django-htmx>=1.17",
"pydantic>=2.7",
"boto3>=1.34",
]

[tool.ruff]
line-length = 100
"

write "docker-compose.yml" '
services:
db:
image: postgres:16
environment:
POSTGRES_DB: app
POSTGRES_USER: app
POSTGRES_PASSWORD: app
ports:
- "5432:5432"
volumes:
- pgdata:/var/lib/postgresql/data
- ./scripts/init_db.sql:/docker-entrypoint-initdb.d/00-init.sql
healthcheck:
test: ["CMD-SHELL", "pg_isready -U app -d app"]
interval: 5s
timeout: 3s
retries: 30

redis:
image: redis:7
ports:
- "6379:6379"

app:
build:
context: .
dockerfile: docker/app/Dockerfile
env_file: .env.example
depends_on:
db:
condition: service_healthy
minio:
condition: service_started
volumes:
- ./src:/app/src
- ./scripts:/app/scripts
ports:
- "8000:8000"
command: ["/entrypoint.sh", "web"]

worker:
build:
context: .
dockerfile: docker/app/Dockerfile
env_file: .env.example
depends_on:
db:
condition: service_healthy
volumes:
- ./src:/app/src
command: ["/entrypoint.sh", "worker"]

nginx:
image: nginx:1.27
depends_on:
- app
ports:
- "8080:80"
volumes:
- ./docker/nginx/nginx.conf:/etc/nginx/nginx.conf:ro

minio:
image: minio/minio:RELEASE.2024-10-13T13-34-11Z
command: server /data --console-address ":9001"
environment:
MINIO_ROOT_USER: minio
MINIO_ROOT_PASSWORD: minio123
ports:
- "9000:9000"
- "9001:9001"
volumes:
- miniodata:/data

volumes:
pgdata:
miniodata:
'

write "docker/app/Dockerfile" '
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends
build-essential curl
&& rm -rf /var/lib/apt/lists/*

COPY pyproject.toml /app/pyproject.toml

RUN pip install --no-cache-dir -U pip
&& pip install --no-cache-dir "uv>=0.4"
&& uv pip install --system -r <(python -c "import tomllib; d=tomllib.load(open('pyproject.toml','rb')); print('\n'.join(d['project']['dependencies']))")

COPY docker/app/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

COPY src /app/src
WORKDIR /app/src
'

write "docker/app/entrypoint.sh" '
#!/bin/sh
set -e

python manage.py migrate --noinput

if [ "$1" = "web" ]; then
exec python manage.py runserver 0.0.0.0:8000
fi

if [ "$1" = "worker" ]; then
exec python -m outbox.publisher
fi

echo "Usage: /entrypoint.sh [web|worker]"
exit 1
'

write "docker/nginx/nginx.conf" '
events {}

http {
upstream django_upstream { server app:8000; }

server {
listen 80;

# allow subdomains like demo.localhost
server_name ~^(?<sub>.+)\.localhost$ localhost;

location / {
  proxy_pass http://django_upstream;
  proxy_set_header Host $host;
  proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
  proxy_set_header X-Forwarded-Proto $scheme;
}
}
}
'

-------------------------
Scripts (DB init + RLS)
-------------------------
write "scripts/init_db.sql" '
CREATE SCHEMA IF NOT EXISTS app;
-- used by RLS:
-- current_setting('app.current_tenant', true)
'

write "scripts/enable_rls.sql" '
-- Enable RLS for tenant-scoped tables (run after migrations)
-- IMPORTANT: For local dev, you may skip this. For prod/staging, enable it.

ALTER TABLE tenancy_organization ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenancy_site ENABLE ROW LEVEL SECURITY;

ALTER TABLE risk_assessment ENABLE ROW LEVEL SECURITY;
ALTER TABLE actions_action_item ENABLE ROW LEVEL SECURITY;

ALTER TABLE documents_document ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents_document_version ENABLE ROW LEVEL SECURITY;

ALTER TABLE audit_audit_event ENABLE ROW LEVEL SECURITY;
ALTER TABLE outbox_outbox_message ENABLE ROW LEVEL SECURITY;

-- policies
CREATE POLICY tenant_isolation_org ON tenancy_organization
USING (tenant_id = current_setting('app.current_tenant')::uuid);

CREATE POLICY tenant_isolation_site ON tenancy_site
USING (tenant_id = current_setting('app.current_tenant')::uuid);

CREATE POLICY tenant_isolation_assessment ON risk_assessment
USING (tenant_id = current_setting('app.current_tenant')::uuid);

CREATE POLICY tenant_isolation_action ON actions_action_item
USING (tenant_id = current_setting('app.current_tenant')::uuid);

CREATE POLICY tenant_isolation_doc ON documents_document
USING (tenant_id = current_setting('app.current_tenant')::uuid);

CREATE POLICY tenant_isolation_doc_ver ON documents_document_version
USING (tenant_id = current_setting('app.current_tenant')::uuid);

CREATE POLICY tenant_isolation_audit ON audit_audit_event
USING (tenant_id = current_setting('app.current_tenant')::uuid);

CREATE POLICY tenant_isolation_outbox ON outbox_outbox_message
USING (tenant_id = current_setting('app.current_tenant')::uuid);
'

-------------------------
Django project
-------------------------
write "src/manage.py" '
#!/usr/bin/env python
import os
import sys

def main():
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
from django.core.management import execute_from_command_line
execute_from_command_line(sys.argv)

if name == "main":
main()
'

write "src/config/init.py" ''

write "src/config/settings.py" '
from pathlib import Path
import os
import dj_database_url

BASE_DIR = Path(file).resolve().parent.parent

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-only")
DEBUG = os.getenv("DJANGO_DEBUG", "0") == "1"
ALLOWED_HOSTS = os.getenv("DJANGO_ALLOWED_HOSTS", ".localhost,localhost,127.0.0.1").split(",")

INSTALLED_APPS = [
"django.contrib.admin",
"django.contrib.auth",
"django.contrib.contenttypes",
"django.contrib.sessions",
"django.contrib.messages",
"django.contrib.staticfiles",
"django_htmx",

"common",
"tenancy",
"identity",
"audit",
"outbox",
"risk",
"actions",
"documents",
]

MIDDLEWARE = [
"django.middleware.security.SecurityMiddleware",
"django.contrib.sessions.middleware.SessionMiddleware",
"django.middleware.common.CommonMiddleware",
"django_htmx.middleware.HtmxMiddleware",
"django.middleware.csrf.CsrfViewMiddleware",
"django.contrib.auth.middleware.AuthenticationMiddleware",

# context + tenancy
"common.middleware.RequestContextMiddleware",
"common.middleware.SubdomainTenantMiddleware",

"django.contrib.messages.middleware.MessageMiddleware",
"django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
{
"BACKEND": "django.template.backends.django.DjangoTemplates",
"DIRS": [BASE_DIR / "templates"],
"APP_DIRS": True,
"OPTIONS": {"context_processors": [
"django.template.context_processors.request",
"django.contrib.auth.context_processors.auth",
"django.contrib.messages.context_processors.messages",
"common.context_processors.tenant_context",
]},
}
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
"default": dj_database_url.config(default=os.getenv("DATABASE_URL"))
}

AUTH_USER_MODEL = "identity.User"

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

Tenancy
TENANT_BASE_DOMAIN = os.getenv("TENANT_BASE_DOMAIN", "localhost")
TENANT_ALLOW_LOCALHOST = os.getenv("TENANT_ALLOW_LOCALHOST", "1") == "1"

CSRF
CSRF_TRUSTED_ORIGINS = [o for o in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",") if o]

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

Documents / S3
S3_ENDPOINT = os.getenv("S3_ENDPOINT", "")
S3_REGION = os.getenv("S3_REGION", "us-east-1")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY", "")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY", "")
S3_BUCKET = os.getenv("S3_BUCKET", "documents")
S3_USE_SSL = os.getenv("S3_USE_SSL", "0") == "1"
S3_PUBLIC_BASE_URL = os.getenv("S3_PUBLIC_BASE_URL", "")

'

write "src/config/urls.py" '
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
path("admin/", admin.site.urls),
path("risk/", include("risk.urls")),
path("documents/", include("documents.urls")),
]
'

write "src/config/asgi.py" '
import os
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
application = get_asgi_application()
'

write "src/config/wsgi.py" '
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
application = get_wsgi_application()
'

-------------------------
common
-------------------------
write "src/common/init.py" ''

write "src/common/request_context.py" '
import contextvars
from dataclasses import dataclass
from uuid import UUID

_request_id = contextvars.ContextVar("request_id", default=None)
_current_tenant_id = contextvars.ContextVar("tenant_id", default=None)
_current_tenant_slug = contextvars.ContextVar("tenant_slug", default=None)
_current_user_id = contextvars.ContextVar("user_id", default=None)

@dataclass(frozen=True)
class RequestContext:
request_id: str | None
tenant_id: UUID | None
tenant_slug: str | None
user_id: UUID | None

def set_request_id(v: str | None) -> None:
_request_id.set(v)

def set_tenant(tenant_id: UUID | None, tenant_slug: str | None) -> None:
_current_tenant_id.set(tenant_id)
_current_tenant_slug.set(tenant_slug)

def set_user_id(v) -> None:
_current_user_id.set(v)

def get_context() -> RequestContext:
return RequestContext(
request_id=_request_id.get(),
tenant_id=_current_tenant_id.get(),
tenant_slug=_current_tenant_slug.get(),
user_id=_current_user_id.get(),
)
'

write "src/common/db.py" '
from django.db import connection
from uuid import UUID

def set_db_tenant(tenant_id: UUID | None) -> None:
"""
Set Postgres session var used by RLS policies.
Safe default: empty => no tenant access (once RLS enabled).
"""
value = "" if tenant_id is None else str(tenant_id)
with connection.cursor() as cur:
cur.execute("SELECT set_config('app.current_tenant', %s, true)", [value])
'

write "src/common/middleware.py" '
import uuid
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings
from django.http import HttpResponseForbidden
from tenancy.models import Organization
from common.request_context import set_request_id, set_tenant, set_user_id
from common.db import set_db_tenant

def _parse_subdomain(host: str) -> str | None:
# host may contain port
host = host.split(":")[0].lower()
base = settings.TENANT_BASE_DOMAIN.lower()

# allow demo.localhost, or demo.deine-domain.tld (base domain configured)
if host == base:
    return None

if host.endswith("." + base):
    return host[: -(len(base) + 1)]  # strip ".base"
return None
class RequestContextMiddleware(MiddlewareMixin):
def process_request(self, request):
rid = request.headers.get("X-Request-Id") or str(uuid.uuid4())
set_request_id(rid)
set_user_id(request.user.id if getattr(request, "user", None) and request.user.is_authenticated else None)

class SubdomainTenantMiddleware(MiddlewareMixin):
"""
Tenant resolution:
- tenant slug from subdomain (demo.localhost -> demo)
- looks up Organization.slug
- sets RequestContext + Postgres session var for RLS
"""
def process_request(self, request):
sub = _parse_subdomain(request.get_host())
if not sub:
# allow admin without tenant in local dev
if settings.TENANT_ALLOW_LOCALHOST and request.path.startswith("/admin/"):
set_tenant(None, None)
set_db_tenant(None)
return None
return HttpResponseForbidden("Missing tenant subdomain")

    org = Organization.objects.filter(slug=sub).first()
    if not org:
        return HttpResponseForbidden("Unknown tenant")

    set_tenant(org.tenant_id, org.slug)
    set_db_tenant(org.tenant_id)
    request.tenant = org
    return None
'

write "src/common/context_processors.py" '
from common.request_context import get_context

def tenant_context(request):
ctx = get_context()
return {"tenant_slug": ctx.tenant_slug, "tenant_id": ctx.tenant_id}
'

write "src/common/s3.py" '
import boto3
from django.conf import settings

def s3_client():
return boto3.client(
"s3",
endpoint_url=settings.S3_ENDPOINT or None,
aws_access_key_id=settings.S3_ACCESS_KEY or None,
aws_secret_access_key=settings.S3_SECRET_KEY or None,
region_name=settings.S3_REGION or None,
use_ssl=settings.S3_USE_SSL,
)
'

-------------------------
tenancy
-------------------------
write "src/tenancy/init.py" ''

write "src/tenancy/apps.py" '
from django.apps import AppConfig

class TenancyConfig(AppConfig):
default_auto_field = "django.db.models.BigAutoField"
name = "tenancy"
'

write "src/tenancy/models.py" '
from django.db import models
import uuid

class Organization(models.Model):
id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
tenant_id = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)
slug = models.SlugField(max_length=63, unique=True) # subdomain key, e.g. "demo"
name = models.CharField(max_length=200)
created_at = models.DateTimeField(auto_now_add=True)

class Meta:
    db_table = "tenancy_organization"
class Site(models.Model):
id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
tenant_id = models.UUIDField()
organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
name = models.CharField(max_length=200)

class Meta:
    db_table = "tenancy_site"
    constraints = [
        models.UniqueConstraint(fields=["tenant_id", "name"], name="uq_site_name_per_tenant"),
    ]
'

write "src/tenancy/admin.py" '
from django.contrib import admin
from tenancy.models import Organization, Site

@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
list_display = ("name", "slug", "tenant_id", "created_at")
search_fields = ("name", "slug", "tenant_id")

@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
list_display = ("name", "tenant_id", "organization_id")
'

-------------------------
identity
-------------------------
write "src/identity/init.py" ''

write "src/identity/apps.py" '
from django.apps import AppConfig

class IdentityConfig(AppConfig):
default_auto_field = "django.db.models.BigAutoField"
name = "identity"
'

write "src/identity/models.py" '
from django.contrib.auth.models import AbstractUser
from django.db import models
import uuid

class User(AbstractUser):
id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
tenant_id = models.UUIDField(null=True, blank=True)

class Meta:
    db_table = "identity_user"
'

write "src/identity/admin.py" '
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from identity.models import User

@admin.register(User)
class UserAdmin(DjangoUserAdmin):
model = User
list_display = ("username", "email", "tenant_id", "is_staff", "is_active")
'

-------------------------
audit
-------------------------
write "src/audit/init.py" ''

write "src/audit/apps.py" '
from django.apps import AppConfig

class AuditConfig(AppConfig):
default_auto_field = "django.db.models.BigAutoField"
name = "audit"
'

write "src/audit/models.py" '
from django.db import models
import uuid

class AuditEvent(models.Model):
id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
tenant_id = models.UUIDField()
actor_user_id = models.UUIDField(null=True, blank=True)

category = models.CharField(max_length=80)        # e.g. "risk.assessment"
action = models.CharField(max_length=80)          # e.g. "created", "approved"
entity_type = models.CharField(max_length=120)    # e.g. "risk.Assessment"
entity_id = models.UUIDField()

payload = models.JSONField(default=dict)
request_id = models.CharField(max_length=64, null=True, blank=True)
created_at = models.DateTimeField(auto_now_add=True)

class Meta:
    db_table = "audit_audit_event"
    indexes = [
        models.Index(fields=["tenant_id", "created_at"]),
        models.Index(fields=["entity_type", "entity_id"]),
    ]
'

write "src/audit/services.py" '
from audit.models import AuditEvent
from common.request_context import get_context

def emit_audit_event(
*,
tenant_id,
category: str,
action: str,
entity_type: str,
entity_id,
payload: dict,
) -> None:
ctx = get_context()
AuditEvent.objects.create(
tenant_id=tenant_id,
actor_user_id=ctx.user_id,
category=category,
action=action,
entity_type=entity_type,
entity_id=entity_id,
payload=payload,
request_id=ctx.request_id,
)
'

write "src/audit/admin.py" '
from django.contrib import admin
from audit.models import AuditEvent

@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
list_display = ("created_at", "tenant_id", "category", "action", "entity_type", "entity_id")
list_filter = ("category", "action")
search_fields = ("entity_type", "entity_id", "tenant_id")
'

-------------------------
outbox
-------------------------
write "src/outbox/init.py" ''

write "src/outbox/apps.py" '
from django.apps import AppConfig

class OutboxConfig(AppConfig):
default_auto_field = "django.db.models.BigAutoField"
name = "outbox"
'

write "src/outbox/models.py" '
from django.db import models
import uuid

class OutboxMessage(models.Model):
id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
tenant_id = models.UUIDField()
topic = models.CharField(max_length=120) # e.g. "risk.assessment.created"
payload = models.JSONField()
published_at = models.DateTimeField(null=True, blank=True)
created_at = models.DateTimeField(auto_now_add=True)

class Meta:
    db_table = "outbox_outbox_message"
    indexes = [
        models.Index(fields=["tenant_id", "published_at", "created_at"]),
    ]
'

write "src/outbox/publisher.py" '
import os
import time
from django import setup
from django.db import transaction
from django.utils import timezone
from outbox.models import OutboxMessage

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
setup()

POLL_SECONDS = 2

def publish(msg: OutboxMessage) -> None:
# MVP: print. Replace with webhook/Kafka/Rabbit later.
print(f"[OUTBOX] topic={msg.topic} tenant={msg.tenant_id} payload={msg.payload}")

def run_forever():
while True:
with transaction.atomic():
qs = (
OutboxMessage.objects
.select_for_update(skip_locked=True)
.filter(published_at__isnull=True)
.order_by("created_at")[:50]
)
msgs = list(qs)
for m in msgs:
publish(m)
m.published_at = timezone.now()
m.save(update_fields=["published_at"])
time.sleep(POLL_SECONDS)

if name == "main":
run_forever()
'

write "src/outbox/admin.py" '
from django.contrib import admin
from outbox.models import OutboxMessage

@admin.register(OutboxMessage)
class OutboxMessageAdmin(admin.ModelAdmin):
list_display = ("created_at", "tenant_id", "topic", "published_at")
list_filter = ("topic",)
'

-------------------------
risk + HTMX
-------------------------
write "src/risk/init.py" ''

write "src/risk/apps.py" '
from django.apps import AppConfig

class RiskConfig(AppConfig):
default_auto_field = "django.db.models.BigAutoField"
name = "risk"
'

write "src/risk/models.py" '
from django.db import models
import uuid

class Assessment(models.Model):
STATUS_CHOICES = [
("draft", "Draft"),
("approved", "Approved"),
("archived", "Archived"),
]

id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
tenant_id = models.UUIDField()
title = models.CharField(max_length=240)
status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
created_at = models.DateTimeField(auto_now_add=True)

class Meta:
    db_table = "risk_assessment"
    constraints = [
        models.CheckConstraint(
            check=models.Q(status__in=["draft", "approved", "archived"]),
            name="ck_assessment_status_valid",
        ),
        models.UniqueConstraint(fields=["tenant_id", "title"], name="uq_assessment_title_per_tenant"),
    ]
'

write "src/risk/services.py" '
from dataclasses import dataclass
from django.db import transaction
from common.request_context import get_context
from audit.services import emit_audit_event
from outbox.models import OutboxMessage
from risk.models import Assessment

@dataclass(frozen=True)
class CreateAssessmentCmd:
title: str

@transaction.atomic
def create_assessment(cmd: CreateAssessmentCmd) -> Assessment:
ctx = get_context()
if ctx.tenant_id is None:
raise ValueError("tenant required")

a = Assessment.objects.create(
    tenant_id=ctx.tenant_id,
    title=cmd.title.strip(),
    status="draft",
)

emit_audit_event(
    tenant_id=ctx.tenant_id,
    category="risk.assessment",
    action="created",
    entity_type="risk.Assessment",
    entity_id=a.id,
    payload={"title": a.title, "status": a.status},
)

OutboxMessage.objects.create(
    tenant_id=ctx.tenant_id,
    topic="risk.assessment.created",
    payload={"assessment_id": str(a.id), "title": a.title},
)
return a
@transaction.atomic
def approve_assessment(assessment_id) -> Assessment:
ctx = get_context()
if ctx.tenant_id is None:
raise ValueError("tenant required")

a = Assessment.objects.get(id=assessment_id)
if a.status != "draft":
    raise ValueError("Only draft can be approved")

a.status = "approved"
a.save(update_fields=["status"])

emit_audit_event(
    tenant_id=a.tenant_id,
    category="risk.assessment",
    action="approved",
    entity_type="risk.Assessment",
    entity_id=a.id,
    payload={"status": a.status},
)

OutboxMessage.objects.create(
    tenant_id=a.tenant_id,
    topic="risk.assessment.approved",
    payload={"assessment_id": str(a.id)},
)
return a
'

write "src/risk/views.py" '
from django.shortcuts import render, redirect
from django.http import HttpResponseBadRequest
from risk.models import Assessment
from risk.services import create_assessment, CreateAssessmentCmd, approve_assessment

def assessment_list(request):
if request.method == "POST":
title = request.POST.get("title", "").strip()
if not title:
return HttpResponseBadRequest("title required")
create_assessment(CreateAssessmentCmd(title=title))
return redirect("risk:assessment_list")

assessments = Assessment.objects.order_by("-created_at")[:100]
return render(request, "risk/assessment_list.html", {"assessments": assessments})
def assessment_approve(request, assessment_id):
if request.method != "POST":
return HttpResponseBadRequest("POST required")
approve_assessment(assessment_id)
return redirect("risk:assessment_list")
'

write "src/risk/urls.py" '
from django.urls import path
from . import views

app_name = "risk"

urlpatterns = [
path("assessments/", views.assessment_list, name="assessment_list"),
path("assessments/uuid:assessment_id/approve/", views.assessment_approve, name="assessment_approve"),
]
'

write "src/risk/templates/risk/assessment_list.html" '

<!doctype html> <html> <head> <meta charset="utf-8"/> <title>Assessments</title> <script src="https://unpkg.com/htmx.org@2.0.4"></script> </head> <body> <div style="display:flex; gap:12px; align-items:center;"> <h1 style="margin:0;">Risk Assessments</h1> <div style="opacity:.7;">Tenant: {{ tenant_slug }}</div> <div><a href="/documents/">Documents</a></div> </div>
<form method="post" style="margin-top:12px;">
  {% csrf_token %}
  <input name="title" placeholder="New assessment title" />
  <button type="submit">Create</button>
</form>

{% include "risk/partials/assessment_table.html" %}
</body> </html> '
write "src/risk/templates/risk/partials/assessment_table.html" '

<table border="1" cellpadding="6" style="margin-top:12px;"> <tr> <th>Title</th><th>Status</th><th>Created</th><th>Actions</th> </tr> {% for a in assessments %} <tr> <td>{{ a.title }}</td> <td>{{ a.status }}</td> <td>{{ a.created_at }}</td> <td> {% if a.status == "draft" %} <form method="post" action="{% url "risk:assessment_approve" a.id %}"> {% csrf_token %} <button type="submit">Approve</button> </form> {% endif %} </td> </tr> {% endfor %} </table> '
-------------------------
actions (minimal placeholder)
-------------------------
write "src/actions/init.py" ''

write "src/actions/apps.py" '
from django.apps import AppConfig

class ActionsConfig(AppConfig):
default_auto_field = "django.db.models.BigAutoField"
name = "actions"
'

write "src/actions/models.py" '
from django.db import models
import uuid

class ActionItem(models.Model):
id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
tenant_id = models.UUIDField()
title = models.CharField(max_length=240)
due_date = models.DateField(null=True, blank=True)
status = models.CharField(max_length=24, default="open")

class Meta:
    db_table = "actions_action_item"
    constraints = [
        models.UniqueConstraint(fields=["tenant_id", "title"], name="uq_action_title_per_tenant"),
    ]
'

-------------------------
documents module (S3 / MinIO)
-------------------------
write "src/documents/init.py" ''

write "src/documents/apps.py" '
from django.apps import AppConfig

class DocumentsConfig(AppConfig):
default_auto_field = "django.db.models.BigAutoField"
name = "documents"
'

write "src/documents/models.py" '
from django.db import models
import uuid

class Document(models.Model):
id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
tenant_id = models.UUIDField()
title = models.CharField(max_length=240)
category = models.CharField(max_length=120, default="general") # e.g. brandschutz, explosionsschutz, arbeitschutz
created_at = models.DateTimeField(auto_now_add=True)

class Meta:
    db_table = "documents_document"
    constraints = [
        models.UniqueConstraint(fields=["tenant_id", "title"], name="uq_doc_title_per_tenant"),
    ]
class DocumentVersion(models.Model):
id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
tenant_id = models.UUIDField()
document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="versions")
version = models.IntegerField()
filename = models.CharField(max_length=255)
content_type = models.CharField(max_length=120)
size_bytes = models.BigIntegerField()
sha256 = models.CharField(max_length=64)

s3_key = models.CharField(max_length=512)
uploaded_at = models.DateTimeField(auto_now_add=True)

class Meta:
    db_table = "documents_document_version"
    constraints = [
        models.UniqueConstraint(fields=["document", "version"], name="uq_doc_version"),
    ]
'

write "src/documents/services.py" '
import hashlib
from dataclasses import dataclass
from django.db import transaction
from django.core.files.uploadedfile import UploadedFile
from common.request_context import get_context
from common.s3 import s3_client
from django.conf import settings
from audit.services import emit_audit_event
from outbox.models import OutboxMessage
from documents.models import Document, DocumentVersion

@dataclass(frozen=True)
class CreateDocumentCmd:
title: str
category: str

@dataclass(frozen=True)
class UploadDocumentVersionCmd:
document_id: str
file: UploadedFile

def _ensure_bucket():
c = s3_client()
try:
c.head_bucket(Bucket=settings.S3_BUCKET)
except Exception:
c.create_bucket(Bucket=settings.S3_BUCKET)

@transaction.atomic
def create_document(cmd: CreateDocumentCmd) -> Document:
ctx = get_context()
if ctx.tenant_id is None:
raise ValueError("tenant required")
doc = Document.objects.create(
tenant_id=ctx.tenant_id,
title=cmd.title.strip(),
category=cmd.category.strip() or "general",
)
emit_audit_event(
tenant_id=ctx.tenant_id,
category="documents.document",
action="created",
entity_type="documents.Document",
entity_id=doc.id,
payload={"title": doc.title, "category": doc.category},
)
OutboxMessage.objects.create(
tenant_id=ctx.tenant_id,
topic="documents.document.created",
payload={"document_id": str(doc.id)},
)
return doc

@transaction.atomic
def upload_new_version(cmd: UploadDocumentVersionCmd) -> DocumentVersion:
ctx = get_context()
if ctx.tenant_id is None:
raise ValueError("tenant required")

_ensure_bucket()
doc = Document.objects.get(id=cmd.document_id)

latest = DocumentVersion.objects.filter(document=doc).order_by("-version").first()
next_ver = 1 if not latest else latest.version + 1

# hash
h = hashlib.sha256()
for chunk in cmd.file.chunks():
    h.update(chunk)
sha = h.hexdigest()

key = f\"{ctx.tenant_slug}/{doc.id}/v{next_ver}/{cmd.file.name}\"

# upload (stream again: easiest MVP is read full; in prod use multipart streaming)
cmd.file.seek(0)
c = s3_client()
c.upload_fileobj(
    cmd.file,
    settings.S3_BUCKET,
    key,
    ExtraArgs={\"ContentType\": cmd.file.content_type or \"application/octet-stream\"},
)

ver = DocumentVersion.objects.create(
    tenant_id=ctx.tenant_id,
    document=doc,
    version=next_ver,
    filename=cmd.file.name,
    content_type=cmd.file.content_type or \"application/octet-stream\",
    size_bytes=cmd.file.size,
    sha256=sha,
    s3_key=key,
)

emit_audit_event(
    tenant_id=ctx.tenant_id,
    category=\"documents.document\",
    action=\"version_uploaded\",
    entity_type=\"documents.DocumentVersion\",
    entity_id=ver.id,
    payload={\"document_id\": str(doc.id), \"version\": next_ver, \"filename\": ver.filename, \"sha256\": sha},
)

OutboxMessage.objects.create(
    tenant_id=ctx.tenant_id,
    topic=\"documents.document.version_uploaded\",
    payload={\"document_id\": str(doc.id), \"version\": next_ver, \"sha256\": sha},
)
return ver
def public_url(s3_key: str) -> str:
# for MinIO dev; in prod use CloudFront/CDN or signed URLs if private
base = settings.S3_PUBLIC_BASE_URL.rstrip("/")
if not base:
return ""
return f"{base}/{s3_key}"
'

write "src/documents/views.py" '
from django.shortcuts import render, redirect
from django.http import HttpResponseBadRequest
from documents.models import Document
from documents.services import create_document, CreateDocumentCmd, upload_new_version, UploadDocumentVersionCmd, public_url

def document_list(request):
if request.method == "POST":
title = request.POST.get("title", "").strip()
category = request.POST.get("category", "general").strip()
if not title:
return HttpResponseBadRequest("title required")
create_document(CreateDocumentCmd(title=title, category=category))
return redirect("documents:document_list")

docs = Document.objects.order_by("-created_at")[:100]
return render(request, "documents/document_list.html", {"docs": docs})
def upload_version(request, document_id):
if request.method != "POST":
return HttpResponseBadRequest("POST required")
f = request.FILES.get("file")
if not f:
return HttpResponseBadRequest("file required")
upload_new_version(UploadDocumentVersionCmd(document_id=str(document_id), file=f))
return redirect("documents:document_detail", document_id=document_id)

def document_detail(request, document_id):
doc = Document.objects.get(id=document_id)
versions = list(doc.versions.order_by("-version")[:20])
version_rows = []
for v in versions:
version_rows.append({
"version": v.version,
"filename": v.filename,
"content_type": v.content_type,
"size_bytes": v.size_bytes,
"sha256": v.sha256,
"url": public_url(v.s3_key),
})
return render(request, "documents/document_detail.html", {"doc": doc, "versions": version_rows})
'

write "src/documents/urls.py" '
from django.urls import path
from . import views

app_name = "documents"

urlpatterns = [
path("", views.document_list, name="document_list"),
path("uuid:document_id/", views.document_detail, name="document_detail"),
path("uuid:document_id/upload/", views.upload_version, name="upload_version"),
]
'

write "src/documents/templates/documents/document_list.html" '

<!doctype html> <html> <head> <meta charset="utf-8"/> <title>Documents</title> <script src="https://unpkg.com/htmx.org@2.0.4"></script> </head> <body> <div style="display:flex; gap:12px; align-items:center;"> <h1 style="margin:0;">Documents</h1> <div style="opacity:.7;">Tenant: {{ tenant_slug }}</div> <div><a href="/risk/assessments/">Assessments</a></div> </div>
<form method="post" style="margin-top:12px;">
  {% csrf_token %}
  <input name="title" placeholder="Document title" />
  <select name="category">
    <option value="general">general</option>
    <option value="brandschutz">brandschutz</option>
    <option value="explosionsschutz">explosionsschutz</option>
    <option value="arbeitsschutz">arbeitsschutz</option>
  </select>
  <button type="submit">Create</button>
</form>

<table border="1" cellpadding="6" style="margin-top:12px;">
  <tr><th>Title</th><th>Category</th><th>Created</th><th>Open</th></tr>
  {% for d in docs %}
    <tr>
      <td>{{ d.title }}</td>
      <td>{{ d.category }}</td>
      <td>{{ d.created_at }}</td>
      <td><a href="/documents/{{ d.id }}/">Open</a></td>
    </tr>
  {% endfor %}
</table>
</body> </html> '
write "src/documents/templates/documents/document_detail.html" '

<!doctype html> <html> <head> <meta charset="utf-8"/> <title>{{ doc.title }}</title> </head> <body> <div style="display:flex; gap:12px; align-items:center;"> <h1 style="margin:0;">{{ doc.title }}</h1> <div style="opacity:.7;">Category: {{ doc.category }}</div> <div><a href="/documents/">Back</a></div> </div>
<h3>Upload new version</h3>
<form method="post" action="/documents/{{ doc.id }}/upload/" enctype="multipart/form-data">
  {% csrf_token %}
  <input type="file" name="file" required />
  <button type="submit">Upload</button>
</form>

<h3>Versions</h3>
<table border="1" cellpadding="6">
  <tr><th>Version</th><th>Filename</th><th>Type</th><th>Size</th><th>SHA</th><th>Link</th></tr>
  {% for v in versions %}
    <tr>
      <td>v{{ v.version }}</td>
      <td>{{ v.filename }}</td>
      <td>{{ v.content_type }}</td>
      <td>{{ v.size_bytes }}</td>
      <td style="font-family:monospace;">{{ v.sha256 }}</td>
      <td>
        {% if v.url %}
          <a href="{{ v.url }}">Download</a>
        {% else %}
          (no public url)
        {% endif %}
      </td>
    </tr>
  {% endfor %}
</table>
</body> </html> '
-------------------------
Management commands (seed)
-------------------------
mkdir -p "$ROOT/src/tenancy/management/commands" "$ROOT/src/documents/management/commands"

write "src/tenancy/management/init.py" ''
write "src/tenancy/management/commands/init.py" ''

write "src/tenancy/management/commands/seed_demo.py" '
from django.core.management.base import BaseCommand
from tenancy.models import Organization
from documents.services import _ensure_bucket # dev-only convenience

class Command(BaseCommand):
help = "Create demo tenant: demo.localhost"

def handle(self, *args, **kwargs):
    org, created = Organization.objects.get_or_create(
        slug="demo",
        defaults={"name": "Demo Org"},
    )
    _ensure_bucket()
    self.stdout.write(self.style.SUCCESS(f"Tenant ready: slug={org.slug} tenant_id={org.tenant_id} created={created}"))
'

also provide a project-level alias command
mkdir -p "$ROOT/src/config/management/commands"
write "src/config/management/init.py" ''
write "src/config/management/commands/init.py" ''
write "src/config/management/commands/seed_demo.py" '
from tenancy.management.commands.seed_demo import Command as TenancySeedCommand

class Command(TenancySeedCommand):
pass
'

-------------------------
Done
-------------------------
echo "✅ Repo generated at: $ROOT"
echo
echo "Next:"
echo " cd $ROOT"
echo " cp .env.example .env"
echo " docker compose up --build -d"
echo " docker compose exec app python manage.py seed_demo"
echo " Add: 127.0.0.1 demo.localhost (to /etc/hosts)"
echo " Open: http://demo.localhost:8080/risk/assessments/"


---

