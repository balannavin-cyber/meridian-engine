-- Rollback for sql/2026-11-03_s104_marketview_ro_role.sql: removes the role, its grants and its policies.
DROP OWNED BY marketview_ro;
DROP ROLE marketview_ro;
