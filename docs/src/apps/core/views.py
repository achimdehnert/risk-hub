"""
Core Views
==========

Shared views für alle Apps.
"""

from django.http import JsonResponse
from django.db import connection


def health_check(request):
    """
    Health Check Endpoint für Load Balancer.
    
    Prüft:
    - Django läuft
    - Datenbankverbindung
    """
    status = {
        "status": "ok",
        "database": "ok",
    }
    
    # Database Check
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except Exception as e:
        status["database"] = "error"
        status["status"] = "degraded"
        status["database_error"] = str(e)
    
    http_status = 200 if status["status"] == "ok" else 503
    return JsonResponse(status, status=http_status)
