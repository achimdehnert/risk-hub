# ADR-004: API-Versionierung & Contracts

| Metadaten | |
| --------- | --- |
| **Status** | ✅ APPROVED |
| **Version** | 1.0 |
| **Datum** | 2026-02-01 |
| **Autor** | Achim Dehnert (AI-unterstützt) |
| **Depends On** | ADR-003 (Tenant/RBAC) |

---

## 📋 Executive Summary

Dieses ADR definiert die **API-Versionierungs-Strategie** für Risk-Hub. Ziel ist eine stabile, dokumentierte API für externe Integrationen (CAT-Tools, ERP-Systeme, Mobile Apps) bei gleichzeitiger Weiterentwicklungsfähigkeit.

### Kernentscheidungen

| # | Entscheidung | Begründung |
| --- | ------------ | ---------- |
| 1 | URL-basierte Versionierung | Explizit, Cache-freundlich, Proxy-kompatibel |
| 2 | OpenAPI 3.0 als Contract | Industrie-Standard, Code-Generierung |
| 3 | 12-Monate Deprecation Policy | Balance zwischen Stabilität und Evolution |
| 4 | Semantic Versioning für Breaking Changes | Klare Kommunikation |

---

## 1. Kontext

Risk-Hub entwickelt sich zu einer Plattform mit externen Integrationen:

- **Interne Clients**: HTMX-Frontend, Mobile App (geplant)
- **Externe Clients**: ERP-Systeme, CAT-Tools, Behörden-Schnittstellen
- **Partner-Integrationen**: SDS-Datenbanken, Ex-Schutz-Software

### 1.1 Anforderungen

- **Stabilität**: Externe Clients dürfen nicht bei Updates brechen
- **Evolution**: Neue Features ohne Breaking Changes
- **Dokumentation**: Self-Service für Integratoren
- **Testbarkeit**: Contract Testing, Mock-Server

---

## 2. Architektur-Entscheidungen

### 2.1 Versionierungs-Schema

**URL-basierte Versionierung (gewählt):**

```
/api/v1/substances/
/api/v2/substances/
```

**Alternativen (abgelehnt):**

| Methode | Beispiel | Ablehnung |
| ------- | -------- | --------- |
| Header-basiert | `Accept: application/vnd.riskhub.v1+json` | Debugging schwierig |
| Query-Parameter | `/api/substances?version=1` | Cache-Probleme |
| Content-Type | `application/vnd.riskhub+json;version=1` | Komplexität |

### 2.2 URL-Struktur

```
/api/v{major}/
├── auth/                    # Authentifizierung
│   ├── token/               # POST: JWT Token
│   └── refresh/             # POST: Token Refresh
│
├── tenants/                 # Tenant-Management
│   ├── {tenant_id}/
│   │   ├── sites/
│   │   └── users/
│
├── substances/              # Gefahrstoffe
│   ├── {id}/
│   │   ├── sds/             # Sicherheitsdatenblätter
│   │   └── inventories/     # Standort-Inventare
│
├── ex/                      # Explosionsschutz
│   ├── areas/
│   ├── equipment/
│   ├── concepts/
│   └── assessments/
│
├── documents/               # Dokumente
│   ├── {id}/
│   │   └── download/
│
└── reports/                 # Berichte
    ├── ex-concept/
    └── substance-inventory/
```

### 2.3 Versioning-Regeln

| Version Change | Wann | Beispiel |
| -------------- | ---- | -------- |
| **Patch** (v1.0.1) | Bug Fixes, keine API-Änderung | Security Fix |
| **Minor** (v1.1.0) | Neue Endpoints, optionale Felder | Neues Filter-Feld |
| **Major** (v2.0.0) | Breaking Changes | Feld-Entfernung, Umbenennung |

### 2.4 Breaking Change Definition

**Breaking Changes (erfordern Major-Version):**

- ❌ Entfernen eines Endpoints
- ❌ Entfernen eines Response-Feldes
- ❌ Umbenennen eines Feldes
- ❌ Ändern eines Feld-Typs
- ❌ Ändern von HTTP-Methoden
- ❌ Ändern von Status-Codes
- ❌ Entfernen von Enum-Werten

**Non-Breaking Changes (Minor/Patch):**

- ✅ Hinzufügen neuer Endpoints
- ✅ Hinzufügen optionaler Request-Felder
- ✅ Hinzufügen von Response-Feldern
- ✅ Hinzufügen von Enum-Werten
- ✅ Lockern von Validierungen

---

## 3. OpenAPI Specification

### 3.1 Spec-Struktur

```yaml
# openapi/v1/openapi.yaml
openapi: 3.0.3
info:
  title: Risk-Hub API
  version: 1.0.0
  description: API für Risikomanagement und Compliance
  contact:
    email: api@risk-hub.de
  license:
    name: Proprietary

servers:
  - url: https://api.risk-hub.de/api/v1
    description: Production
  - url: https://staging.risk-hub.de/api/v1
    description: Staging

security:
  - bearerAuth: []
  - apiKeyAuth: []

tags:
  - name: substances
    description: Gefahrstoff-Management
  - name: ex
    description: Explosionsschutz
  - name: documents
    description: Dokumenten-Management

paths:
  /substances/:
    $ref: './paths/substances.yaml'
  /ex/areas/:
    $ref: './paths/ex-areas.yaml'

components:
  securitySchemes:
    bearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT
    apiKeyAuth:
      type: apiKey
      in: header
      name: X-API-Key
  schemas:
    $ref: './schemas/_index.yaml'
  responses:
    $ref: './responses/_index.yaml'
```

### 3.2 Schema-Beispiel

```yaml
# openapi/v1/schemas/substance.yaml
Substance:
  type: object
  required:
    - id
    - name
    - cas_number
  properties:
    id:
      type: string
      format: uuid
      readOnly: true
      description: Eindeutige Substanz-ID
    name:
      type: string
      maxLength: 500
      description: Substanzname
    cas_number:
      type: string
      pattern: '^\d{1,7}-\d{2}-\d$'
      description: CAS-Nummer
    h_statements:
      type: array
      items:
        $ref: '#/components/schemas/HStatement'
      description: H-Sätze (Gefahrenhinweise)
    created_at:
      type: string
      format: date-time
      readOnly: true
    updated_at:
      type: string
      format: date-time
      readOnly: true

SubstanceList:
  type: object
  properties:
    count:
      type: integer
    next:
      type: string
      format: uri
      nullable: true
    previous:
      type: string
      format: uri
      nullable: true
    results:
      type: array
      items:
        $ref: '#/components/schemas/Substance'
```

### 3.3 Error-Response-Format

```yaml
# Einheitliches Error-Format
Error:
  type: object
  required:
    - code
    - message
  properties:
    code:
      type: string
      enum:
        - validation_error
        - not_found
        - permission_denied
        - rate_limit_exceeded
        - internal_error
    message:
      type: string
    details:
      type: array
      items:
        type: object
        properties:
          field:
            type: string
          message:
            type: string
          code:
            type: string
    request_id:
      type: string
      format: uuid
```

---

## 4. Deprecation Policy

### 4.1 Zeitplan

```
┌────────────────────────────────────────────────────────────────┐
│                    DEPRECATION TIMELINE                         │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Announce    ──────────────────────────────────────► Sunset     │
│     │                                                    │      │
│     │◄───────────── 12 Monate ─────────────────────────►│      │
│     │                                                    │      │
│  ┌──┴──┐     ┌─────────┐     ┌─────────┐     ┌────────┴─┐     │
│  │ v1  │────►│ v1 dep. │────►│ v1 warn │────►│ v1 EOL  │     │
│  │ GA  │     │ notice  │     │ headers │     │ removed │     │
│  └─────┘     └─────────┘     └─────────┘     └──────────┘     │
│     │                                                           │
│     └──► v2 GA (parallel)                                       │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

### 4.2 Deprecation-Headers

```http
HTTP/1.1 200 OK
Deprecation: Sun, 01 Feb 2027 00:00:00 GMT
Sunset: Sun, 01 Aug 2027 00:00:00 GMT
Link: </api/v2/substances/>; rel="successor-version"
X-API-Warn: "This endpoint is deprecated. Please migrate to v2."
```

### 4.3 Kommunikation

| Phase | Aktion |
| ----- | ------ |
| **Ankündigung** | Changelog, E-Mail an API-Key-Inhaber |
| **6 Monate vor EOL** | Warning-Header, Dashboard-Banner |
| **1 Monat vor EOL** | Direkte E-Mail, Rate-Limiting auf alte Version |
| **EOL** | 410 Gone Response |

---

## 5. Authentifizierung

### 5.1 Methoden

| Methode | Use Case | TTL |
| ------- | -------- | --- |
| **JWT Bearer** | Web-Clients, SPA | 15min Access, 7d Refresh |
| **API Key** | Server-to-Server | Unbegrenzt (rotierbar) |
| **OAuth 2.0** | Third-Party Apps | Client Credentials |

### 5.2 API Key Format

```
rh_live_xxxxxxxxxxxxxxxxxxxxxxxxxxxx
rh_test_xxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

Prefix `rh_live_` für Production, `rh_test_` für Sandbox.

### 5.3 Rate Limiting

```yaml
# Rate Limits pro Plan
rate_limits:
  free:
    requests_per_minute: 60
    requests_per_day: 1000
  professional:
    requests_per_minute: 300
    requests_per_day: 50000
  enterprise:
    requests_per_minute: 1000
    requests_per_day: unlimited
```

**Response Headers:**

```http
X-RateLimit-Limit: 300
X-RateLimit-Remaining: 299
X-RateLimit-Reset: 1706788800
```

---

## 6. Implementierung (Django)

### 6.1 URL-Konfiguration

```python
# config/urls.py
from django.urls import path, include

urlpatterns = [
    path("api/v1/", include("api.v1.urls", namespace="api-v1")),
    path("api/v2/", include("api.v2.urls", namespace="api-v2")),
]
```

### 6.2 DRF-Konfiguration

```python
# config/settings.py
REST_FRAMEWORK = {
    "DEFAULT_VERSIONING_CLASS": "rest_framework.versioning.URLPathVersioning",
    "DEFAULT_VERSION": "v1",
    "ALLOWED_VERSIONS": ["v1", "v2"],
    "VERSION_PARAM": "version",
    
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "api.authentication.APIKeyAuthentication",
    ],
    
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.UserRateThrottle",
        "rest_framework.throttling.AnonRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "user": "300/minute",
        "anon": "60/minute",
    },
    
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "api.exceptions.custom_exception_handler",
}
```

### 6.3 Versionierte ViewSets

```python
# api/v1/views/substances.py
class SubstanceViewSet(TenantScopedViewSet):
    """Substance API v1."""
    
    queryset = Substance.objects.all()
    serializer_class = SubstanceSerializerV1
    permission_classes = [IsAuthenticated, HasPermission("substance.view")]
    
    @extend_schema(
        summary="List substances",
        responses={200: SubstanceListSerializer},
    )
    def list(self, request):
        ...


# api/v2/views/substances.py
class SubstanceViewSet(TenantScopedViewSet):
    """Substance API v2 - mit erweitertem Schema."""
    
    queryset = Substance.objects.all()
    serializer_class = SubstanceSerializerV2  # Neues Schema
    
    # Neue Features in v2
    filterset_class = SubstanceFilterV2
    search_fields = ["name", "cas_number", "synonyms"]
```

---

## 7. Testing

### 7.1 Contract Testing

```python
# tests/api/test_contracts.py
import schemathesis

schema = schemathesis.from_path("openapi/v1/openapi.yaml")

@schema.parametrize()
def test_api_contract(case):
    """Test that API matches OpenAPI spec."""
    response = case.call_and_validate()
    assert response.status_code < 500
```

### 7.2 Backwards Compatibility

```python
# tests/api/test_backwards_compat.py
class TestV1BackwardsCompatibility:
    """Ensure v1 responses remain stable."""
    
    def test_substance_response_has_required_fields(self, api_client):
        response = api_client.get("/api/v1/substances/")
        
        # Diese Felder MÜSSEN existieren
        for item in response.json()["results"]:
            assert "id" in item
            assert "name" in item
            assert "cas_number" in item
```

---

## 8. Konsequenzen

### Positiv

- ✅ Klare Versioning-Strategie für externe Partner
- ✅ Self-Service Dokumentation via OpenAPI
- ✅ Contract Testing verhindert Breaking Changes
- ✅ Parallele Versionen ermöglichen sanfte Migration

### Negativ

- ❌ Mehraufwand für Dual-Maintenance (v1 + v2)
- ❌ OpenAPI-Spec muss synchron gehalten werden
- ❌ Komplexere Routing-Konfiguration

---

## 9. Referenzen

- [OpenAPI Specification 3.0](https://spec.openapis.org/oas/v3.0.3)
- [REST API Versioning](https://www.baeldung.com/rest-versioning)
- [Stripe API Versioning](https://stripe.com/blog/api-versioning)
- [GitHub API Deprecation](https://developer.github.com/changes/)

---

**Erstellt:** 2026-02-01  
**Version:** 1.0
