#!/bin/sh
set -e

python manage.py migrate --noinput

if [ "$1" = "web" ]; then
    exec python manage.py runserver 0.0.0.0:8000
fi

if [ "$1" = "worker" ]; then
    exec python -m outbox.publisher
fi

echo "Usage: /entrypoint.sh [web|worker]"
exit 1
