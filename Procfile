release: python manage.py collectstatic --noinput
web: gunicorn backend.wsgi:application --bind 0.0.0.0:$PORT --access-logfile - --error-logfile - --timeout 120
