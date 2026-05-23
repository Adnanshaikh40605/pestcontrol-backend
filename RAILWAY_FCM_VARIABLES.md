# Railway — Partner app FCM (Firebase)

Project: **pest-99-partner-app**  
Android package: **com.example.pest_99_partner_app**

## Variables to add on `pestcontrol-backend`

| Variable | Value |
|----------|--------|
| `PARTNER_FIREBASE_PROJECT_ID` | `pest-99-partner-app` |
| `FIREBASE_SERVICE_ACCOUNT_JSON` | Full contents of your `pest-99-partner-app-firebase-adminsdk-*.json` file as **one line** |

### How to set `FIREBASE_SERVICE_ACCOUNT_JSON`

1. Open the downloaded service account JSON in a text editor.
2. Copy the entire file.
3. In Railway → Variables → Raw Editor, add:
   ```json
   "FIREBASE_SERVICE_ACCOUNT_JSON": "{paste entire JSON here — must be valid JSON string}"
   ```
4. Or use Railway’s **single variable** UI and paste the minified JSON (one line).

**Do not** commit this JSON to GitHub (it is in `.gitignore`).

### Local development (optional)

In your local `.env` (not committed):

```env
PARTNER_FIREBASE_PROJECT_ID=pest-99-partner-app
GOOGLE_APPLICATION_CREDENTIALS=pest-99-partner-app-firebase-adminsdk-fbsvc-4f0bd12f14.json
```

Place the JSON file in the project root (already gitignored).

## After deploy

1. Run migration: `python manage.py migrate partner`
2. Health check: `GET https://api.vacationbna.site/api/v1/health/`  
   → `partner_fcm.configured` should be `true`
3. Install rebuilt partner APK on a real Android phone
4. Log in → allow notifications → `GET /api/partner/push-health/` (with partner JWT) should show `device_tokens_count: 1`
5. CRM → Send to Partner App → phone receives **New Booking Available**

## Partner must be approved

Push only goes to partners with **`is_app_approved=True`** in Django admin / CRM Technicians.
