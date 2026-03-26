#!/bin/sh
set -e

# ADR-137: Dual DATABASE_URL support for RLS
# DATABASE_URL         = app-user (RLS enforced) — used by gunicorn/worker
# DATABASE_URL_MIGRATE = table-owner (RLS-exempt) — used for migrate/seed
MIGRATE_URL="${DATABASE_URL_MIGRATE:-$DATABASE_URL}"

echo "Waiting for database..."
until python -c "import psycopg; psycopg.connect('$DATABASE_URL')" 2>/dev/null; do
    echo "  DB not ready, waiting..."
    sleep 2
done
echo "Database ready!"

echo "Collecting static files..."
python manage.py collectstatic --noinput

if [ "$1" = "web" ]; then
    echo "Running migrations (owner role)..."
    DATABASE_URL="$MIGRATE_URL" python manage.py migrate --noinput --fake-initial

    echo "Seeding GBU reference data..."
    DATABASE_URL="$MIGRATE_URL" python manage.py seed_all_gbu || echo "WARNING: GBU seed failed (non-fatal)"

    echo "Seeding aifw action types (ADR-147)..."
    DATABASE_URL="$MIGRATE_URL" python manage.py seed_action_types || echo "WARNING: aifw seed failed (non-fatal)"

    echo "Starting web server (gunicorn, app-user with RLS)..."
    exec gunicorn config.wsgi:application \
        --bind 0.0.0.0:8000 \
        --workers "${GUNICORN_WORKERS:-2}" \
        --timeout 120 \
        --max-requests 500 \
        --max-requests-jitter 50 \
        --access-logfile -
fi

if [ "$1" = "worker" ]; then
    echo "Starting worker..."
    exec python -m outbox.publisher
fi

echo "Usage: /entrypoint.sh [web|worker]"
exit 1
