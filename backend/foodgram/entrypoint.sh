#!/bin/sh
while ! nc -z db 5432; do
sleep 0.1
done
python /app/manage.py migrate
exec "$@"