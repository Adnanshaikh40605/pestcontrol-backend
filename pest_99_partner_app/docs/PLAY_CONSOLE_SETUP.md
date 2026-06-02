# Google Play Console — Pest 99 Partner App

## Package name (application ID)

`com.multipestcare.partner`

Set the **same** package in Play Console when creating the app.

### Firebase (done via FlutterFire)

Android app registered in project **pest-99-partner-app**:

- Package: `com.multipestcare.partner`
- App ID: `1:1081130965061:android:94a59a605aa2bfa28cab2c`

Config files: `lib/firebase_options.dart`, `android/app/google-services.json`.

To re-run later (from `pest_99_partner_app`):

```powershell
$env:Path += ";$env:APPDATA\npm;$env:LOCALAPPDATA\Pub\Cache\bin"
flutterfire configure --project=pest-99-partner-app --platforms=android --android-package-name=com.multipestcare.partner -y --overwrite-firebase-options
```

## Required URLs (pestcontrol99.com)

| Purpose | URL |
|---------|-----|
| Privacy policy | https://www.pestcontrol99.com/privacy-policy/ |
| Account deletion | https://www.pestcontrol99.com/delete-account/ |
| Data deletion | https://www.pestcontrol99.com/data-deletion/ |
| Terms | https://www.pestcontrol99.com/terms-and-conditions/ |
| Contact | https://www.pestcontrol99.com/contact/ |

## Demo credentials for reviewers

Create in Django admin → Partners:

- Mobile: (10 digits, e.g. `image.png`)
- Password: (strong test password)
- **is_app_approved**: checked
- **is_active**: checked

Enter the same mobile + password in Play Console → **App access** → login credentials.

Login uses **mobile + password** (not OTP).

## Data safety (honest answers)

| Data | Collected |
|------|-----------|
| Name | Yes |
| Phone number | Yes |
| Email | Optional / referrals only |
| Photos | Yes (profile + job selfie) |
| Device or other IDs | Yes (FCM token) |
| Precise location | **No** |
| Financial info | Optional (bank details in profile) |

## Permissions justification

- **Camera**: Capture profile photo and service-start selfie verification.
- **Notifications**: Booking alerts and service updates.
- **Internet**: API communication (HTTPS only).

## Release signing

1. Create upload keystore:
   `keytool -genkey -v -keystore upload-keystore.jks -keyalg RSA -keysize 2048 -validity 10000 -alias upload`
2. Copy `android/key.properties.example` → `android/key.properties` and fill paths.
3. Build: `flutter build appbundle --release`

## Partner app version (CRM admin)

Django admin → **Partner App Version**:

- `force_update`: off for review unless testing
- `minimum_supported_version`: `2.0.4` or lower
- `latest_version`: `2.0.4`
