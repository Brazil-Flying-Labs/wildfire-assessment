#!/bin/bash
python manage.py migrate
python manage.py collectstatic --noinput
# Start the Gunicorn server
gunicorn api.wsgi:application --bind 0.0.0.0:10000