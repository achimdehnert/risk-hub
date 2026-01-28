"""
risk-hub Django Configuration Package
======================================
"""

# Celery App laden für Django
from config.celery import app as celery_app

__all__ = ("celery_app",)
