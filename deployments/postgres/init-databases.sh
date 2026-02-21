#!/bin/bash
# Create additional databases on first startup.
# This script is executed by the postgres entrypoint (docker-entrypoint-initdb.d).

set -e

GATEWAY_DB_NAME="${GATEWAY_DB_NAME:-gateway_api}"
GATEWAY_DB_USER="${GATEWAY_DB_USER:-gateway}"
GATEWAY_DB_PASSWORD="${GATEWAY_DB_PASSWORD:-gateway}"

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE DATABASE mlflow;
    CREATE USER mlflow WITH PASSWORD 'mlflow';
    GRANT ALL PRIVILEGES ON DATABASE mlflow TO mlflow;

    -- Grant schema permissions (required for PostgreSQL 15+)
    \c mlflow
    GRANT ALL ON SCHEMA public TO mlflow;

    -- Gateway API database/user
    \c $POSTGRES_DB
    CREATE DATABASE $GATEWAY_DB_NAME;
    CREATE USER $GATEWAY_DB_USER WITH PASSWORD '$GATEWAY_DB_PASSWORD';
    GRANT ALL PRIVILEGES ON DATABASE $GATEWAY_DB_NAME TO $GATEWAY_DB_USER;

    \c $GATEWAY_DB_NAME
    GRANT ALL ON SCHEMA public TO $GATEWAY_DB_USER;
EOSQL
