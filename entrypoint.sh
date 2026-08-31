#!/bin/bash
python manage.py migrate
python manage.py collectstatic --noinput

# Start Gunicorn with multiple workers so health checks are served while
# long requests are processed. Worker recycling (max-requests) acts as a
# safety net against memory leaks; graceful-timeout matches the request
# timeout so long streams are not cut mid-flight during a recycle.
gunicorn api.wsgi:application \
    --bind 0.0.0.0:8000 \
    --timeout 600 \
    --workers 7 \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    --graceful-timeout 600
