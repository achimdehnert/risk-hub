-- Initialize database for Risk-Hub
CREATE SCHEMA IF NOT EXISTS app;

-- Session variable for RLS (used by middleware)
-- current_setting('app.current_tenant', true)
