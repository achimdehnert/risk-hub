#!/usr/bin/env python
"""Test substances views."""
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
os.environ["DJANGO_DEBUG"] = "1"

import django
django.setup()

from django.test import Client, override_settings

with override_settings(ALLOWED_HOSTS=["*"]):
    c = Client()
    response = c.get("/substances/")
    print(f"Status: {response.status_code}")
    if response.status_code >= 400:
        print(f"Content: {response.content.decode()[:5000]}")
    else:
        print("OK")
