-- PostgreSQL read-only user template
--
-- Replace the placeholders in this file before running:
--   - REPLACE_ME_PASSWORD
--   - your_db
--   - public (schema)
--
-- Run as a DB admin and/or the schema owner (default privileges are per role).

-- 1) Create a login role
CREATE ROLE readonly
  LOGIN
  PASSWORD 'REPLACE_ME_PASSWORD'
  NOSUPERUSER
  NOCREATEDB
  NOCREATEROLE
  NOINHERIT;

-- 2) Allow connect + schema usage
GRANT CONNECT ON DATABASE your_db TO readonly;
GRANT USAGE ON SCHEMA public TO readonly;

-- Safety: try to prevent object creation in the schema.
-- Note: if your schema grants CREATE to PUBLIC (Postgres defaults), revoking it from `readonly`
-- is not sufficient; consider revoking CREATE from PUBLIC (careful: affects other users).
REVOKE CREATE ON SCHEMA public FROM readonly;
-- Optional (stronger, may be disruptive):
-- REVOKE CREATE ON SCHEMA public FROM PUBLIC;

-- 3) Allow SELECT on existing tables
GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly;

-- 4) Ensure future tables are also readable (applies to objects created by *this* role)
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO readonly;

-- Optional: if you use sequences explicitly (not required for plain SELECTs on tables)
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO readonly;
-- ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO readonly;

-- Optional safety limits (pick values that fit your workload)
ALTER ROLE readonly SET statement_timeout = '5s';
ALTER ROLE readonly SET idle_in_transaction_session_timeout = '10s';
ALTER ROLE readonly SET default_transaction_read_only = on;
