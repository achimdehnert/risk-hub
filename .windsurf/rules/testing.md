---
trigger: glob
globs:
  - "**/tests/**"
  - "**/test_*.py"
  - "**/conftest.py"
  - "pytest.ini"
  - "pyproject.toml"
---

# Testing Conventions (risk-hub)

## Framework
- pytest with pytest-django
- `DJANGO_SETTINGS_MODULE = config.settings`
- Run all: `cd src && python -m pytest`
- Run app: `cd src && python -m pytest <app>/`

## Test Structure
- App tests: `src/<app>/tests/test_<module>.py`
- Integration: `src/tests/test_<feature>.py`

## Test Patterns
- Use `@pytest.mark.django_db` for DB access
- Functions: `test_should_<expected_behavior>`
- Max 5 assertions per test, max 30 lines per function
- Mock external services (LLM, HTTP)
- CRITICAL: All test data must include `tenant_id`
