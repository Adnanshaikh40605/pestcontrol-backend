# Pest Control 99 — Customer App

Flutter customer app for booking pest control services against the Django `/api/customer/` backend.

## Production API base

Default: `https://api.vacationbna.site`  
Override locally:

```bash
flutter run --dart-define=API_BASE_URL=http://127.0.0.1:8000
```

## Core flows (live)

- Guest home browsing; login required for account features / confirm booking
- OTP login & register
- CRM catalog prices → book with address / city / area
- Bookings, AMC schedule, payments & invoices list, booking detail + rate
- Complaint / re-service → creates CRM complaint JobCard
- Profile display, logout, **delete account** (Play requirement)
- Legal links (Privacy / Terms / Contact)

## Intentionally deferred

- Online payment gateway (`CUSTOMER_ONLINE_PAYMENT_ENABLED` is off — pay after service)
- FCM push notifications
- PDF invoice download

## Play Store

See `docs/PLAY_CONSOLE_SETUP.md` and `docs/PLAY_STORE_LISTING.md`.

- applicationId: `com.pestcontrol99.pest_99_customer_app`
- targetSdk / compileSdk: **36**
- Release signing via `android/key.properties` (see example file)

```bash
flutter build appbundle --release --dart-define=API_BASE_URL=https://api.vacationbna.site
```
