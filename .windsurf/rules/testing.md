---
trigger: glob
globs:
  - "**/tests/**"
  - "**/test_*.py"
  - "**/conftest.py"
  - "pytest.ini"
---

# Testing Conventions (risk-hub)

## Framework

- pytest with pytest-django
- `DJANGO_SETTINGS_MODULE = config.settings.test`
- Run all: `cd src && pytest`
- Run app: `cd src && pytest <app>/`

## Test Structure

- App tests: `<app>/tests/test_<module>.py`
- Integration: `tests/test_<feature>.py`
- Fixtures: `tests/conftest.py` (fixture_tenant, fixture_user, fixture_assignment)

## Test Patterns

- Use `@pytest.mark.django_db` for DB access
- Functions: `test_should_<expected_behavior>`
- Max 5 assertions per test, max 30 lines per function
- Mock external services (API calls, HTTP)
- Management commands: test via Docker exec on server
