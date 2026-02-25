#!/bin/sh
set -e

echo "Waiting for database..."
until python -c "import psycopg; psycopg.connect('$DATABASE_URL')" 2>/dev/null; do
    echo "  DB not ready, waiting..."
    sleep 2
done
echo "Database ready!"

echo "Running migrations..."
python manage.py migrate --noinput --skip-checks

echo "Collecting static files..."
python manage.py collectstatic --noinput

if [ "$1" = "web" ]; then
    echo "Starting web server (gunicorn)..."
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
