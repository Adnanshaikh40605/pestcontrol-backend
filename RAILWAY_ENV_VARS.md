# Railway Environment Variables - Complete Setup

## 🚀 **Required Environment Variables for Railway**

Copy and paste these **exactly** into Railway → Variables:

```json
{
  "DJANGO_SECRET_KEY": "q!w4g6*z3=1^a_2$k&@7s8z%u$1%m7-c7+o7j4-rzgf6=^1k^j",
  "DJANGO_DEBUG": "False",
  "DJANGO_ALLOWED_HOSTS": "localhost,127.0.0.1,.railway.app,.up.railway.app,pestcontrol-backend-production.up.railway.app",
  "CSRF_TRUSTED_ORIGINS": "https://*.railway.app,https://*.up.railway.app,https://pestcontrol-backend-production.up.railway.app",
  "RAILWAY_ENVIRONMENT": "production",
  "DJANGO_LOG_LEVEL": "INFO",
  "DATABASE_URL": "postgresql://postgres:iUEBAUYrSdJUAgtYrHxRyApYqYTlDPPa@centerbeam.proxy.rlwy.net:31166/railway?sslmode=require"
}
```

## 🔧 **Railway Service Configuration**

### 1. **Start Command** (already in Procfile):
```
gunicorn backend.wsgi:application --bind 0.0.0.0:$PORT --access-logfile - --error-logfile - --timeout 120
```

### 2. **Healthcheck Settings**:
- **Path**: `/health/`
- **Timeout**: 30 seconds (default)

### 3. **Post-Deploy Command** (optional but recommended):
```
python manage.py migrate --noinput
```

## 📊 **Database Connection Details**

- **Host**: `centerbeam.proxy.rlwy.net:31166` (external access)
- **Internal Host**: `postgres.railway.internal:5432` (same project)
- **Database**: `railway`
- **Username**: `postgres`
- **Password**: `iUEBAUYrSdJUAgtYrHxRyApYqYTlDPPa`
- **Port**: `5432`

## 🔒 **Security Notes**

- ✅ **SSL Required**: Using `?sslmode=require` for secure connections
- ✅ **Debug Disabled**: Production-safe configuration
- ✅ **Secret Key**: Production-ready secret key
- ✅ **CSRF Protection**: All Railway domains trusted

## 🧪 **Testing the Connection**

After deployment, test your database connection:

1. **Check Health Endpoint**: `/health/` should return "ok"
2. **Check Admin**: `/admin/` should load (if you have superuser)
3. **Check API**: Your API endpoints should work

## 🚨 **Troubleshooting**

### If Database Connection Fails:
1. **Check DATABASE_URL** is set correctly in Railway
2. **Verify SSL**: Try `?sslmode=disable` if SSL issues
3. **Check Network**: Ensure Railway services are in same project

### If App Still Crashes:
1. **Check Logs**: Railway → your service → Logs
2. **Verify Environment**: All variables are set
3. **Check Start Command**: Matches Procfile exactly

## 📝 **Local Development**

For local development, your `.env` file will use:
- SQLite database (when `DEBUG=True` and no `DATABASE_URL`)
- Local PostgreSQL (when `DATABASE_URL` is set)

## 🎯 **Expected Result**

After setting these variables:
1. ✅ Django starts without crashing
2. ✅ Connects to Railway PostgreSQL
3. ✅ Health endpoint responds
4. ✅ All logs appear in Railway console
5. ✅ No file system access attempts
