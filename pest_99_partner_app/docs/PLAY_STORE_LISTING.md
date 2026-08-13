# Google Play Store Listing — Pest 99 Partner App

Use this guide for **Grow users → Store presence → Main store listing** (Default – English).

---

## Copy-paste text

### App name (max 30 characters) — **Required**

```
Pest 99 Partner
```

*(19 characters. Do not use long names like “Pestcontrol99 Partner” unless you prefer.)*

---

### Short description (max 80 characters) — **Required**

```
Official Pest Control 99 app for technicians. Jobs, alerts & earnings.
```

*(72 characters)*

**Alternative (shorter):**

```
Pest Control 99 technician app — accept jobs, track work & get alerts.
```

*(68 characters)*

---

### Full description (max 4000 characters) — **Required**

```
Pest 99 Partner is the official mobile app for field technicians of Pest Control 99, operated by Multi Pest Care LLP.

Use this app only if you are an approved Pest Control 99 technician. New users can register in the app; admin approval is required before you can accept jobs.

WHAT YOU CAN DO
• View new service bookings near you
• Accept or manage assigned jobs
• See accepted and completed work history
• Start service with quick verification steps
• Update your profile and optional bank details
• Get instant push notifications for new bookings
• Contact support and read privacy & account policies in the app

WHO THIS APP IS FOR
• Licensed / approved pest control technicians
• Partner staff working under Pest Control 99

NOT FOR CUSTOMERS
This is not a customer booking app. Customers should visit www.pestcontrol99.com or call +91 80807 48282.

SUPPORT
Email: accounts@pestcontrol99.com
Website: https://www.pestcontrol99.com

Privacy Policy: https://www.pestcontrol99.com/privacy-policy/
Delete Account: https://www.pestcontrol99.com/delete-account/
```

---

## Graphics — what is required vs optional

| Asset | Required? | Size | Format | Notes |
|-------|-----------|------|--------|--------|
| **App name** | Yes | max 30 chars | text | See above |
| **Short description** | Yes | max 80 chars | text | See above |
| **Full description** | Yes | max 4000 chars | text | See above |
| **App icon** | Yes | **512 × 512 px** | PNG or JPEG, ≤ 1 MB | Use file in `docs/play-store-assets/` |
| **Feature graphic** | Yes | **1024 × 500 px** | PNG or JPEG, ≤ 1 MB | Banner on store page — create in Canva |
| **Phone screenshots** | Yes | **min 2**, max 8 | PNG/JPEG, ≤ 8 MB each | 16:9 or 9:16; sides 320–3840 px |
| **Video** | No | YouTube URL | optional | Skip for now |
| **7" tablet screenshots** | No | same rules | optional | Skip unless you test on tablet |
| **10" tablet screenshots** | No | same rules | optional | Skip |
| **Chromebook screenshots** | No | optional | Skip |
| **Android XR** | No | optional | Skip |

**Rule:** You cannot publish to Production until **all required** items above are filled.

---

## App icon file (ready in project)

Upload this file in Play Console → **App icon**:

| File | Path |
|------|------|
| **512×512 (use this)** | `pest_99_partner_app/docs/play-store-assets/play-store-icon-512x512.png` |
| **1024 source (if Play asks for higher quality)** | `pest_99_partner_app/docs/play-store-assets/app-icon-source-1024.png` |
| **Backup logo** | `pest_99_partner_app/assets/logo/app_icon.png` |
| **Root logo** | `Pest Control 99 logo.png` (project root — resize to 512×512 if needed) |

---

## How to create assets you don’t have

### 1. Feature graphic (1024 × 500) — **Required**

**Easiest: Canva (free)**

1. Go to [canva.com](https://www.canva.com) → Create design → Custom size **1024 × 500 px**
2. Background: green gradient (brand color `#00C950`)
3. Add logo from `Pest Control 99 logo.png` or `assets/logo/app_icon.png`
4. Text: **Pest 99 Partner** + subtitle **For Pest Control 99 Technicians**
5. Download as **PNG**
6. Upload to Play Console → Feature graphic

### 2. Phone screenshots (min 2) — **Required**

**Option A — Real phone (best)**

1. Install app (internal test link or APK)
2. Open screens: **Login**, **Bookings list**, **Profile**
3. Press **Power + Volume Down** to screenshot
4. Upload PNGs to Play Console → Phone screenshots

**Option B — Android emulator**

1. Android Studio → Device Manager → run Pixel phone
2. Install APK → screenshot each screen
3. Size is usually fine automatically (1080×2400 etc.)

**Option C — Mockup frame (looks professional)**

1. Canva → “App Store Screenshot” or “Phone mockup” template
2. Size: **1080 × 1920 px** (9:16) per image
3. Place your raw screenshot inside phone frame
4. Export PNG → upload

**Suggested 4 screenshots (order):**

1. Login / Welcome  
2. Available bookings  
3. Booking detail  
4. Profile + legal links  

### 3. Resize icon to exactly 512×512 (if needed)

- [iloveimg.com/resize-image](https://www.iloveimg.com/resize-image) → 512 × 512 px  
- Or Paint / Photos app on Windows → Resize → 512 × 512  

---

## Play Console checklist (same page)

1. Paste **App name**, **Short**, **Full** description  
2. Upload **App icon** (`play-store-icon-512x512.png`)  
3. Upload **Feature graphic** (1024×500 — you create)  
4. Upload **2+ phone screenshots**  
5. Click **Save**  
6. **Publishing overview** → Send for review (when rest of dashboard is done)  

---

## Category (separate page)

**Grow users → Store settings** or **Dashboard → Select app category**

- **Category:** Business or Productivity  
- **Contact email:** accounts@pestcontrol99.com  
- **Website:** https://www.pestcontrol99.com  

---

## Data safety reminder

Your app **does collect** data (name, phone, photos, device ID).  
Store preview must **not** say “No data collection”.  
If it does, edit **App content → Data safety** → answer **Yes** and select data types (see `PLAY_CONSOLE_SETUP.md`).
