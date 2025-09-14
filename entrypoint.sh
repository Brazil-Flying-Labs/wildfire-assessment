#!/bin/bash
python manage.py migrate
python manage.py collectstatic --noinput

# Create Django superuser (one-time, remove after first run)
python manage.py shell -c "from django.contrib.auth.models import User; User.objects.filter(username='admin').exists() or User.objects.create_superuser('admin', 'admin@example.com', 'adminpassword')"

# Start the Gunicorn server
gunicorn api.wsgi:application --bind 0.0.0.0:10000