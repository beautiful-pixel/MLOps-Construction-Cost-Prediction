#!/bin/bash
# Create additional databases on first startup.
# This script is executed by the postgres entrypoint (docker-entrypoint-initdb.d).

set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE DATABASE mlflow;
    CREATE USER mlflow WITH PASSWORD 'mlflow';
    GRANT ALL PRIVILEGES ON DATABASE mlflow TO mlflow;

    -- Grant schema permissions (required for PostgreSQL 15+)
    \c mlflow
    GRANT ALL ON SCHEMA public TO mlflow;
EOSQL
