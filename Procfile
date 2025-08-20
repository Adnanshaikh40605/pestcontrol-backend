release: python manage.py collectstatic --noinput && python manage.py migrate --noinput
web: gunicorn backend.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 120 --access-logfile - --error-logfile -
