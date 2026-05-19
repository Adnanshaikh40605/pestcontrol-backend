# Pest 99 Partner App

Flutter app for field technicians — accepts CRM bookings, starts jobs with selfie, completes with payment.

## Setup

1. Install Flutter SDK 3.11+
2. From this folder:

```bash
flutter pub get
flutter run --dart-define=API_BASE_URL=https://YOUR-BACKEND-URL
```

3. Register a partner account via `/api/partner/register/` or Django admin.
4. In Django admin, link **Partner → CRM Technician** (`core_technician` field).

## CRM flow

1. Staff creates booking → **Pending**
2. CRM → **Send to Partner App** (mobile icon) → technician with partner account
3. App **Bookings** tab → Accept → CRM **On Process**
4. App **Accepted** → Start job (camera selfie) → CRM **Technician Selfies** page
5. App → End service (Cash/Online) → CRM **Done** + payment shown on booking

## API docs

Backend Swagger: `/api/partner/docs/`
