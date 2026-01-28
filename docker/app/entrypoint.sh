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

if [ "$1" = "web" ]; then
    echo "Starting web server..."
    exec python manage.py runserver 0.0.0.0:8000
fi

if [ "$1" = "worker" ]; then
    echo "Starting worker..."
    exec python -m outbox.publisher
fi

echo "Usage: /entrypoint.sh [web|worker]"
exit 1
