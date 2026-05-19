"""Generate railway variabe.md for Railway Raw Editor paste. Run locally only."""
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sa = json.loads((BASE / "pest-99-partner-app-firebase-adminsdk-fbsvc-27d3132bb0.json").read_text())
old = json.loads((BASE / "railway variabe.md").read_text(encoding="utf-8").split("```json")[-1].split("```")[0] if "```json" in (BASE / "railway variabe.md").read_text(encoding="utf-8") else (BASE / "railway variabe.md").read_text(encoding="utf-8"))

# If old file is plain json without markdown wrapper
if isinstance(old, str):
    old = json.loads((BASE / "railway variabe.md").read_text(encoding="utf-8"))

vars_map = {
    "DJANGO_SECRET_KEY": old["DJANGO_SECRET_KEY"],
    "DJANGO_DEBUG": "False",
    "DJANGO_ALLOWED_HOSTS": (
        "localhost,127.0.0.1,api.vacationbna.site,.railway.app,.up.railway.app,"
        "pestcontrol-backend-production.up.railway.app"
    ),
    "CSRF_TRUSTED_ORIGINS": (
        "https://api.vacationbna.site,https://*.railway.app,https://*.up.railway.app,"
        "https://pestcontrol-backend-production.up.railway.app,"
        "https://pestcontrol-crm-frontend.vercel.app,https://www.pestcontrol99.com,"
        "https://pestcontrol99.com"
    ),
    "CORS_ALLOWED_ORIGINS": (
        "http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,"
        "https://www.pestcontrol99.com,https://pestcontrol99.com,"
        "https://pestcontrol-crm-frontend.vercel.app,https://pestcontrol-crm.vercel.app"
    ),
    "PUBLIC_API_BASE_URL": "https://api.vacationbna.site",
    "RAILWAY_ENVIRONMENT": "production",
    "DJANGO_LOG_LEVEL": "INFO",
    "DATABASE_URL": old["DATABASE_URL"],
    "DJANGO_SUPERUSER_USERNAME": old["DJANGO_SUPERUSER_USERNAME"],
    "DJANGO_SUPERUSER_EMAIL": old["DJANGO_SUPERUSER_EMAIL"],
    "DJANGO_SUPERUSER_PASSWORD": old["DJANGO_SUPERUSER_PASSWORD"],
    "JWT_ACCESS_TOKEN_LIFETIME_HOURS": "24",
    "JWT_REFRESH_TOKEN_LIFETIME_DAYS": "60",
    "PARTNER_FIREBASE_PROJECT_ID": "pest-99-partner-app",
    "FIREBASE_SERVICE_ACCOUNT_JSON": json.dumps(sa, separators=(",", ":")),
    "TELEGRAM_BOT_TOKEN": old["TELEGRAM_BOT_TOKEN"],
    "TELEGRAM_CHAT_ID": old["TELEGRAM_CHAT_ID"],
    "TELEGRAM_NOTIFICATIONS_ENABLED": "true",
}

header = """# Railway variables (pestcontrol-backend)

Paste **only the JSON block below** into Railway → **pestcontrol-backend** → **Variables** → **Raw Editor** → select all → paste → **Update Variables**.

**Removed (wrong project / unused):** `FIREBASE_PROJECT_ID`, `FIREBASE_PRIVATE_KEY`, `FIREBASE_CLIENT_EMAIL`, `FIREBASE_CLIENT_ID`, `FIREBASE_CLIENT_X509_CERT_URL`, `FCM_SERVER_KEY`, `chat_id`.

**After save:** wait for redeploy (~2 min). Open https://api.vacationbna.site/api/v1/health/ — `partner_fcm.configured` must be `true`.

⚠️ Do not commit this file to GitHub (secrets). Listed in `.gitignore`.

---

```json
"""
footer = "\n```\n"
(BASE / "railway variabe.md").write_text(
    header + json.dumps(vars_map, indent=2) + footer,
    encoding="utf-8",
)
print("OK:", BASE / "railway variabe.md")
