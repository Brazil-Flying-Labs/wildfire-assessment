#!/bin/bash
python manage.py migrate
python manage.py collectstatic --noinput

# Start the Gunicorn server with increased timeout and multiple workers
# Multiple workers ensure health checks are served while long requests are processed
opentelemetry-instrument gunicorn api.wsgi:application --bind 0.0.0.0:10000 --timeout 600 --workers 3