---
description: Test-Infrastruktur (ADR-058)
---

# Testing Setup

```
# requirements-dev.txt
pytest>=8.0
pytest-django>=4.8
pytest-mock>=3.12
factory-boy>=3.3
platform-context[testing]>=0.3.0
```

```python
# src/conftest.py
from platform_context.testing.fixtures import admin_client, admin_user, auth_client, htmx_client  # noqa
```
