# Pest99 Tracking App

Field staff GPS tracking mobile app for Pest Control 99.

## Setup

```bash
cd pest99_tracking_app
flutter pub get
```

If Android/iOS folders are missing, generate platform projects:

```bash
flutter create . --org com.multipestcare --project-name pest99_tracking_app
```

## Run on device

```bash
flutter run --dart-define=API_BASE_URL=https://api.vacationbna.site
```

## Build release APK (install on Android phone)

**Mac:**
```bash
./build_release_apk.sh
```

**Windows:**
```bat
build_release_apk.bat
```

**Output APK:**
- `build/app/outputs/flutter-apk/app-release.apk`
- Copy: `Pest99-Tracking-v1.0.0.apk` (project root after build)

### Install on your phone

1. Copy `Pest99-Tracking-v1.0.0.apk` to your Android phone (USB, AirDrop, Google Drive, WhatsApp).
2. Open the file on the phone → **Install** (allow “Install unknown apps” if asked).
3. Login with **technician mobile + password** (same as Partner app).
4. Allow **location** permissions when prompted.
5. Accept GPS consent → **Check In** to start tracking.

**Backend required:** Deploy `staff_tracking` migration on Railway before login works:
`python manage.py migrate staff_tracking && python manage.py backfill_tracking_profiles`

## Features (Phase 1)

- Login with technician mobile + password (same accounts as Partner app)
- GPS consent + check-in / check-out
- Background location pings while checked in
- Offline ping queue with batch sync
- Today status dashboard

## API

All endpoints: `/api/staff-tracking/*`

Auth: `POST /api/staff-tracking/auth/login/`

## Android permissions

Location (foreground + background) required for tracking during active shift.
