# Google Play Console — Pest Control 99 Customer App

## Package name (application ID)

`com.pestcontrol99.pest_99_customer_app`

Set the **same** package in Play Console when creating the app.

## Target API (mandatory from 31 Aug 2026)

- `compileSdk = 36`
- `targetSdk = 36` (Android 16)

Pinned in `android/app/build.gradle.kts`.

## Required URLs (pestcontrol99.com)

| Purpose | URL |
|---------|-----|
| Privacy policy | https://www.pestcontrol99.com/privacy-policy/ |
| Account deletion | https://www.pestcontrol99.com/delete-account/ |
| Data deletion | https://www.pestcontrol99.com/data-deletion/ |
| Terms | https://www.pestcontrol99.com/terms-and-conditions/ |
| Contact | https://www.pestcontrol99.com/contact/ |

In-app: Account → Privacy / Terms / Help, plus login footer. Delete account is available in Account.

## Demo credentials for Play reviewers (production)

Paste into Play Console → **App content** → **App access**:

```
Login required: Yes
How to access: Open app → Login
Mobile number: 9999900999
OTP: 2468
Steps: Enter mobile → tap Send OTP → enter 2468 → Continue
Notes: Fixed reviewer OTP on production API (api.vacationbna.site). No WhatsApp needed for this number.
```

Backend env (Railway):

- `CUSTOMER_OTP_REVIEWER_MOBILES=9999900999`
- `CUSTOMER_OTP_REVIEWER_CODE=2468`

Seed account: `python manage.py seed_play_reviewer --mobile 9999900999`

## Data safety (honest answers)

| Data | Collected |
|------|-----------|
| Name | Yes |
| Phone number | Yes |
| Email | No (not collected in app UI) |
| Photos | No |
| Precise location | **No** |
| Financial info | No (pay after service; no card vaulting) |
| Device IDs | No FCM yet |

## Permissions justification

- **Internet / Network state**: HTTPS API for auth, catalog, bookings, invoices, complaints.
- No camera, location, notifications, or storage permissions are declared.

## Release signing

1. Create upload keystore:
   `keytool -genkey -v -keystore upload-keystore.jks -keyalg RSA -keysize 2048 -validity 10000 -alias upload`
2. Copy `android/key.properties.example` → `android/key.properties` and fill paths.
3. Build AAB: `flutter build appbundle --release --dart-define=API_BASE_URL=https://api.vacationbna.site`

## Closed testing (personal developer accounts)

If the Play developer account is a **personal** account created after 13 Nov 2023:

1. Upload AAB to a **Closed testing** track.
2. Recruit **≥ 12 testers** who opt in via the Play opt-in link.
3. Keep them opted in for **14 continuous days**.
4. Apply for **production access** from the Play Console dashboard and answer the testing questionnaire.

Organization accounts (D-U-N-S) are generally exempt from this gate — confirm in your Console.

## Production backend checklist

Before production traffic:

- [ ] `DEBUG=False`
- [ ] `CUSTOMER_OTP_FIXED=` (empty)
- [ ] `CUSTOMER_OTP_WHATSAPP_TEMPLATE=` set to approved Meta/WhatsFlow OTP template
- [ ] `WHATSFLOW_API_KEY=` configured
- [ ] `CUSTOMER_ONLINE_PAYMENT_ENABLED=False` until Razorpay (or similar) is live
- [ ] HTTPS API (`api.vacationbna.site` or production domain) reachable from devices
- [ ] Privacy / delete-account pages live on pestcontrol99.com

## Known deferred (not Play blockers if disclosed)

- Online payment gateway (pay after service messaging is intentional)
- Push notifications / FCM
- PDF invoice download (JSON invoice fields shown in booking detail)
- Coupons / documents modules (removed from menus until APIs exist)
