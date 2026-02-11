# Risk-Hub — Active Issues & Decisions

## Recently Fixed (2026-02-10)

- **Substance detail 404**: Root cause was `org.id` vs `org.tenant_id` mismatch
  in `import_substances` command. Fixed by using `org.tenant_id`.
- **Substance detail 500**: `ExIntegrationService.get_ex_data()` called
  `require_permission()` without user context. Fixed with try/except wrapper.
- **Risk assessment UI unstyled**: Templates were standalone HTML without
  `base.html`. Refactored to extend base with Tailwind styling.

## Known Technical Debt

- `ExIntegrationService.get_ex_data()` should accept an optional substance
  object to avoid redundant DB query + permission check
- Some templates in `explosionsschutz/` and `dashboard/` have inline CSS styles
- No CI/CD pipeline — deployment is manual Docker build + push
- No automated tests for management commands

## Environment Gotchas

- `docker-compose.prod.yml`: Do NOT use `${VAR}` interpolation in the
  `environment:` section — it overrides `.env.prod` values with empty strings.
  Use `env_file: .env.prod` exclusively.
- WSL `docker exec` with multi-line Python: Write script to file, SCP to
  server, `docker cp` into container, then `docker exec python /tmp/script.py`
