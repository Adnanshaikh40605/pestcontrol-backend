# Railway Deployment Checklist

## Environment Variables to Set in Railway

### Required Variables:
- `DJANGO_SECRET_KEY` - Your Django secret key
- `DJANGO_DEBUG` - Set to `False` for production
- `DJANGO_ALLOWED_HOSTS` - Set to `.railway.app,.up.railway.app,your-custom-domain.com`
- `CSRF_TRUSTED_ORIGINS` - Set to `https://*.railway.app,https://*.up.railway.app,https://your-custom-domain.com`
- `DATABASE_URL` - Railway will provide this automatically
- `RAILWAY_ENVIRONMENT` - Set to `production`
- `DJANGO_LOG_LEVEL` - Set to `INFO`

### Optional Variables:
- `DJANGO_SETTINGS_MODULE` - Should be `backend.settings` (default)
- `PORT` - Railway sets this automatically

## Railway Settings

### Healthcheck:
- **Path**: `/health/`
- **Timeout**: 30 seconds (default)

### Start Command:
```
gunicorn backend.wsgi:application --bind 0.0.0.0:$PORT --access-logfile - --error-logfile - --timeout 120
```

### Post-Deploy Command (optional):
```
python manage.py migrate --noinput
```

## What We Fixed

1. **Logging Crash**: Replaced file-based logging with console-only logging in containers
2. **Health Endpoint**: Added `/health/` endpoint that always returns 200
3. **Gunicorn Configuration**: Added proper logging and timeout settings
4. **Environment Variables**: Added CSRF and security settings for production
5. **Container Detection**: Automatically detects Railway environment and adjusts logging

## Testing Locally

Before deploying, test these commands locally:

```bash
# Test Django settings
export DJANGO_SETTINGS_MODULE=backend.settings
python manage.py check

# Test Django startup
python -c "import django,os; os.environ.setdefault('DJANGO_SETTINGS_MODULE','backend.settings'); django.setup(); print('django ok')"

# Test Gunicorn
gunicorn backend.wsgi:application --bind 127.0.0.1:8000 --timeout 120
```

## Expected Behavior

After deployment:
1. Django should start without crashing
2. Healthcheck at `/health/` should return 200
3. All logs should appear in Railway's log viewer (stdout/stderr)
4. No file system access attempts for logging
