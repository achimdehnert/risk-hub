-- =============================================================================
-- risk-hub PostgreSQL Initialization
-- =============================================================================
-- This script runs on first database creation
-- =============================================================================

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- Für Fuzzy Search

-- App Schema (für RLS Session Variable)
CREATE SCHEMA IF NOT EXISTS app;

-- =============================================================================
-- RLS Setup (aktivieren mit enable_rls.sql)
-- =============================================================================
-- Die RLS Policies werden separat angewendet nach Migrationen
-- Siehe: scripts/enable_rls.sql

-- =============================================================================
-- Performance Indexes (zusätzlich zu Django Migrations)
-- =============================================================================
-- Diese werden nach den Django Migrations angelegt

-- Beispiel für später:
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_risk_assessment_tenant_status 
--     ON risk_assessment (tenant_id, status);
