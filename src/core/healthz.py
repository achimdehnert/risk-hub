"""
Health check endpoints for Risk-Hub (ADR-022).

These endpoints are exempt from authentication and tenant resolution.
They MUST be accessible without a subdomain for Docker healthchecks
and load balancer probes to function correctly.

Registration in config/urls.py:
    from core.healthz import HEALTH_PATHS, liveness, readiness

    urlpatterns = [
        path("livez/", liveness, name="health-liveness"),
        path("healthz/", readiness, name="health-readiness"),
    ]
"""

import time

from django.db import connection
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET

# Paths that must bypass tenant middleware (import in middleware)
HEALTH_PATHS = frozenset({"/livez/", "/healthz/"})


@csrf_exempt
@require_GET
def liveness(request):
    """Liveness probe: process is running. No dependency checks."""
    return JsonResponse({"status": "alive"})


@csrf_exempt
@require_GET
def readiness(request):
    """Readiness probe: all dependencies healthy, ready to serve."""
    checks = {}
    healthy = True

    # Database
    try:
        t0 = time.monotonic()
        with connection.cursor() as cur:
            cur.execute("SELECT 1")
        latency = round((time.monotonic() - t0) * 1000, 1)
        checks["database"] = {"status": "ok", "latency_ms": latency}
    except Exception as exc:
        checks["database"] = {"status": "fail", "error": str(exc)[:200]}
        healthy = False

    # Redis (optional)
    try:
        from django.core.cache import cache

        t0 = time.monotonic()
        cache.set("_healthz", "ok", timeout=5)
        val = cache.get("_healthz")
        latency = round((time.monotonic() - t0) * 1000, 1)
        if val == "ok":
            checks["redis"] = {"status": "ok", "latency_ms": latency}
        else:
            checks["redis"] = {"status": "fail", "error": "read mismatch"}
            healthy = False
    except Exception as exc:
        checks["redis"] = {"status": "fail", "error": str(exc)[:200]}
        healthy = False

    payload = {
        "status": "ok" if healthy else "fail",
        "checks": checks,
    }
    return JsonResponse(payload, status=200 if healthy else 503)
