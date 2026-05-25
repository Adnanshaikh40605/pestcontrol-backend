# Partner App — Force Update (APK)

## APIs

| Endpoint | Auth | Purpose |
|----------|------|---------|
| `GET /api/app/version/` | None | Partner app launch check |
| `GET/PATCH /api/v1/partner-app-version/` | Super admin | CRM settings |

`GET /api/app/version/` (no login required)

```json
{
  "latest_version": "2.0.0",
  "minimum_supported_version": "2.0.0",
  "force_update": true,
  "update_title": "New Update Available",
  "update_message": "A new version of the Partner App is available..."
}
```

## CRM (Super Admin)

1. Log in to CRM as **super admin**.
2. Sidebar → **Partner App Version** (`/partner-app-version`).
3. Edit versions, toggle **Enable force update**, save.

Or use Django Admin below.

## Django Admin

1. Open **https://api.vacationbna.site/admin/** (or your backend URL).
2. Go to **Partner App Version** (single row).
3. Set:
   - **Latest version** — newest APK you share (e.g. `2.0.0`)
   - **Minimum supported version** — oldest version still allowed (e.g. `2.0.0`)
   - **Force update** — enable to block older APKs
   - **Update title / message** — text on the block screen
4. Save.

**Rule:** When **Force update** is ON and the app version is **below** **Minimum supported version**, the partner app shows a full-screen block and closes on OK. No download link is shown in the app.

## Release workflow

1. Bump `version:` in `pest_99_partner_app/pubspec.yaml` (e.g. `2.0.0+2`).
2. Build APK and share via WhatsApp/CRM (manual).
3. In Django Admin, set `latest_version` and `minimum_supported_version` to match.
4. Turn **Force update** ON when you want to block old APKs.
5. Run migration on Railway: `python manage.py migrate core 0076`

## Migration

```bash
python manage.py migrate core 0076_partnerappversionconfig
```

Default seed: `force_update=false`, `minimum_supported_version=0.1.0` (existing installs keep working until you enable force update).
