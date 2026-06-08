-- One-shot Postgres init for Boussole dev.
-- The PgVectorStore.ensure_schema() also creates these idempotently; this
-- file just guarantees the extension is available the moment the container
-- comes up so the schema migration on first connect does not race.

CREATE EXTENSION IF NOT EXISTS vector;
