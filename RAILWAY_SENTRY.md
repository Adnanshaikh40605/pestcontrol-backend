# Sentry setup (pest99 organization)

Dashboard: https://pest99.sentry.io

Projects created via Cursor Sentry MCP:

| App | Sentry project | Platform |
|-----|----------------|----------|
| Django API | `pestcontrol-backend` | python-django |
| Partner Flutter app | `pest99-partner-app` | flutter |

## Railway (backend)

Add to **pestcontrol-backend** variables:

```env
SENTRY_DSN=https://2a26f12f95bd752fc669c65b13b10ed6@o4511440839245824.ingest.us.sentry.io/4511440868605952
SENTRY_ENVIRONMENT=production
SENTRY_TRACES_SAMPLE_RATE=0.1
```

Redeploy, then verify:

- `GET https://api.vacationbna.site/api/v1/health/` → `"sentry": {"configured": true, ...}`
- (debug only) `GET /sentry-debug/` with `DJANGO_DEBUG=True` sends a test error

## Flutter partner APK

Build with DSN (see `pest_99_partner_app/build_release_apk.bat`):

```bash
flutter build apk --release \
  --dart-define=API_BASE_URL=https://api.vacationbna.site \
  --dart-define=SENTRY_DSN=https://3dff814000a4c0b792316d578253d2d9@o4511440839245824.ingest.us.sentry.io/4511440868671488 \
  --dart-define=SENTRY_ENVIRONMENT=production
```

Test from app: trigger an error or use Sentry → test in dashboard.

## CRM frontend (optional)

CRM repo is separate. Create a **React** project in Sentry and add `@sentry/react` with `VITE_SENTRY_DSN` if you use Vite.

## Notes

- DSNs are safe in client apps but treat backend DSN as a secret in Railway only.
- Health check URLs are filtered and not sent to Sentry.
- `send_default_pii` is **false** (no automatic email/phone in events).
