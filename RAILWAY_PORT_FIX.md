# 🚨 Railway Port Configuration Fix

## ⚠️ **IDENTIFIED ISSUE: Port Configuration Conflict**

The healthcheck is failing because Railway's **Target Port** setting is conflicting with the `$PORT` environment variable.

## 🔧 **IMMEDIATE FIXES NEEDED:**

### **1. Fix Railway Port Settings**

Go to **Railway Dashboard → Your Service → Settings → Networking**:

- **Target Port**: Change from `8000` to **`$PORT`** (or leave empty)
- **Public Port**: Should be auto-assigned by Railway
- **Internal Port**: Should match what your app binds to (`$PORT`)

### **2. Verify Start Command** ✅

Your Procfile is already correct:
```bash
web: gunicorn backend.wsgi:application --bind 0.0.0.0:$PORT --access-logfile - --error-logfile - --timeout 120
```

This binds to whatever port Railway assigns via `$PORT` environment variable.

## 🎯 **Complete Railway Configuration:**

### **Environment Variables** (already correct):
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

### **Service Settings:**
- **Build Command**: (leave empty, uses Procfile)
- **Start Command**: (leave empty, uses Procfile)
- **Healthcheck Path**: `/` (your root endpoint)
- **Target Port**: `$PORT` (or leave empty)

### **Post-Deploy Command** (optional):
```bash
python manage.py migrate --noinput
```

## 🧪 **Alternative: Dedicated Health Endpoint**

For even more reliable healthchecks, you can:

1. **Set Railway Healthcheck Path** to `/health/`
2. **Your app already has this endpoint** returning JSON:
   ```python
   def health(request):
       return JsonResponse({"status": "ok", "service": "pestcontrol-backend"})
   ```

## 🚀 **Deployment Steps:**

### **Step 1: Fix Railway Port Settings**
- Go to Railway Dashboard
- Navigate to your service → Settings → Networking  
- Change Target Port to `$PORT` or leave empty

### **Step 2: Redeploy**
- Click "Deploy" in Railway dashboard
- OR push any small change to trigger auto-deploy

### **Step 3: Monitor Logs**
Watch for:
```
[INFO] Starting gunicorn 21.2.0
[INFO] Listening at: http://0.0.0.0:XXXX  # Should show Railway's assigned port
[INFO] Booting worker with pid: X
```

## 🎯 **Expected Success Indicators:**

After fixing the port:
1. ✅ **Gunicorn starts** and shows correct port
2. ✅ **Healthcheck succeeds** (Railway gets 200 OK)
3. ✅ **No more "Service Unavailable"** errors
4. ✅ **Deployment marked as successful**
5. ✅ **App accessible** at your Railway URL

## 🔍 **If Still Fails:**

1. **Check Railway Logs** for new error messages
2. **Try changing healthcheck** to `/health/` instead of `/`
3. **Verify all environment variables** are set correctly
4. **Check for any Django errors** in the logs

## 🎉 **Your Configuration is 99% Perfect!**

The only issue is the port configuration conflict. Once fixed, your Django PestControl backend should deploy successfully! 🚀

**Fix the Target Port setting and redeploy - this should resolve the healthcheck issue!**
