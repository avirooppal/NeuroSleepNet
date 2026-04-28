#!/bin/bash
set -euo pipefail

# Defaults (can be overridden by environment variables passed to docker run)
POSTGRES_USER=${POSTGRES_USER:-nsn}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-nsn}
POSTGRES_DB=${POSTGRES_DB:-neurosleepnet}
DB_DATA_DIR=${DB_DATA_DIR:-/var/lib/postgresql/data}

export DATABASE_URL="postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@localhost:5432/${POSTGRES_DB}"
export REDIS_URL="redis://localhost:6379/0"
export NSN_ENCRYPTION_KEY="${NSN_ENCRYPTION_KEY:-changeme-in-production-32chars!!}"

mkdir -p "$DB_DATA_DIR"
chown -R postgres:postgres "$DB_DATA_DIR" || true

# Initialize Postgres data directory if empty
if [ ! -f "$DB_DATA_DIR/PG_VERSION" ]; then
  echo "Initializing Postgres DB cluster..."
  su postgres -c "initdb -D $DB_DATA_DIR"
fi

# Ensure supervisord log exists
mkdir -p /var/log
touch /var/log/supervisord.log

# Start supervisord in background
echo "Starting supervisord..."
/usr/bin/supervisord -c /app/docker/supervisord.conf &

# Wait for Postgres to be ready
echo "Waiting for Postgres to be ready..."
for i in {1..60}; do
  if su postgres -c "pg_isready -q"; then
    echo "Postgres is ready"
    break
  fi
  sleep 1
done

# Create DB and user if they don't exist
echo "Creating Postgres user and database if missing..."
set +e
su postgres -c "psql -v ON_ERROR_STOP=1 --username=postgres --dbname=postgres -c \"SELECT 1 FROM pg_roles WHERE rolname='$POSTGRES_USER'\"" | grep -q 1
if [ $? -ne 0 ]; then
  su postgres -c "psql --username=postgres --dbname=postgres -c \"CREATE USER $POSTGRES_USER WITH PASSWORD '$POSTGRES_PASSWORD';\""
fi
su postgres -c "psql -v ON_ERROR_STOP=1 --username=postgres --dbname=postgres -c \"SELECT 1 FROM pg_database WHERE datname='$POSTGRES_DB'\"" | grep -q 1
if [ $? -ne 0 ]; then
  su postgres -c "psql --username=postgres --dbname=postgres -c \"CREATE DATABASE $POSTGRES_DB OWNER $POSTGRES_USER;\""
fi
set -e

# Small delay to allow other services to start
sleep 2

# Tail supervisord log to keep container running and show combined logs in terminal
exec tail -F /var/log/supervisord.log
