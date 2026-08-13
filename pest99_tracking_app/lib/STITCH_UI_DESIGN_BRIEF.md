# Pest99 Tracking App — Google Stitch UI Design Brief

**Product:** Pest99 Tracking (Field Staff GPS App)  
**Company:** Pest Control 99 / Multi Pest LLP  
**Platform:** Android mobile app (**Flutter — `pest99_tracking_app`**)  
**Design tool:** [Google Stitch](https://stitch.withgoogle.com)  
**Companion app:** Pest 99 Partner App (bookings) — same brand, same login accounts  
**Manager UI:** Pest CRM → Staff Tracking section (web — separate from mobile admin view)

**Document status:** v2.0 — reflects **implemented** Technician + Technician Admin flows (June 2026).

---

## 1. Purpose of this document

Use this file to generate **all mobile app screens** in Google Stitch before Flutter development.

Each screen section includes:

- Feature context
- Layout wireframe (ASCII)
- UI components list
- Copy (exact text)
- States (loading, empty, error, success)
- **Ready-to-paste Stitch prompt** at the end of each screen

**Design scope:** Mobile app only (`pest99_tracking_app`) — **two login modes:**

| Mode | User | Mobile screens |
|------|------|----------------|
| **Technician** | Field staff | Today, Visits, Tasks, More (Attendance, Leave, Expenses, Profile) |
| **Technician Admin** | Supervisor / `technician_admin` Partner role | **Live Tracking only** (map + staff list) — no check-in, visits, tasks, etc. |

**Not in scope for this doc:** CRM web pages (full manager dashboard), Partner booking app, backend admin Django.

---

## 2. Product summary

Pest99 Tracking is a **field staff GPS attendance & live location app** for pest control technicians and field supervisors.

| What **Technician** does | What **Technician Admin** does (mobile) | What **CRM managers** see (web) |
|--------------------------|----------------------------------------|-----------------------------------|
| Check in at shift start with GPS | Monitor **all technicians live** on map | Live map, visits, tasks, leave, expenses |
| App sends location pings while checked in | Refresh staff list + last ping times | Attendance reports, route history |
| Check out at shift end | View on-duty / idle / off-duty status | Staff directory, approvals |
| Today's visits, tasks, leave, expenses | **No** check-in, visits, or HR features | Full FieldPulse-style dashboard |

**Privacy rule (must show in UI):** Location is recorded **only while checked in**, not on weekends/off-hours unless actively on duty.

**Login:** Same mobile number + password as Partner app (`POST /api/staff-tracking/auth/login/`).  
**Login role dropdown:** `Technician` (default) | `Technician Admin` — sent as `app_mode` in API body.

**Technician Admin eligibility:** Partner account with role `technician_admin`, or CRM Admin / Super Admin.

---

## 3. User personas

### 3.1 Technician (field staff)

| Field | Value |
|-------|-------|
| Name | Example: Arshad Khan |
| Role | Field technician / pest control operator |
| Login mode | **Technician** (default) |
| Age | 22–45 |
| Device | Android (5.5"–6.7"), mid-range |
| Literacy | Comfortable with WhatsApp-style apps |
| Language | English primary; Hindi labels acceptable on key buttons |
| Environment | Bright sunlight, gloves, moving between sites |
| Pain points | Small buttons, unclear GPS status, battery anxiety |

**Design goals:** Large tap targets (min 48dp), high contrast, obvious on/off-duty state, minimal typing.

### 3.2 Technician Admin (supervisor — mobile only)

| Field | Value |
|-------|-------|
| Name | Example: Imran Shaikh |
| Role | Team lead / `technician_admin` in Partner app |
| Login mode | **Technician Admin** |
| Age | 28–50 |
| Device | Android phone or tablet |
| Primary job | Monitor where field team is **right now** |
| Pain points | No visibility until CRM web; needs quick map on phone |

**Design goals for admin:** Map-first layout, scannable staff list, clear status colors, fast refresh, **no clutter** — admin app v1 is **live tracking only**.

**Admin scope (v1 — do not design in admin flow):** Visits board, task assignment, leave approval, expense approval, check-in, consent, profile editing — those stay in **CRM web** or **Technician** mode.

---

## 4. Feature roadmap & implementation status

### Phase 1 — Core (Technician) ✅ Built

| # | Feature | Screen(s) | Route |
|---|---------|-----------|-------|
| F1 | Splash & session restore | Splash | `/splash` |
| F2 | Login + **role dropdown** | Login | `/login` |
| F3 | GPS tracking consent | Home (inline card) | `/home` |
| F4 | Today dashboard (shift status) | Home | `/home` |
| F5 | Check-in with GPS | Home | `/home` |
| F6 | Check-out with GPS | Home | `/home` |
| F7 | Live tracking indicator | Home banner | `/home` |
| F8 | Offline sync (batch pings) | Background | — |
| F9 | Attendance history | Attendance | More → Attendance |
| F10 | Profile & logout | Profile | More → Profile |
| F11 | Break start / end | Home (on duty) | `/home` |

### Phase 2 — Operations (Technician) ✅ Built

| # | Feature | Screen(s) | Route |
|---|---------|-----------|-------|
| F14 | Today's visits (JobCard sync) | Visits | `/home` tab Visits |
| F15 | Visit check-in / check-out (geo) | Visits list | Visits tab |
| F20 | Tasks assigned by manager | Tasks | `/home` tab Tasks |

### Phase 3 — HR (Technician) ✅ Built

| # | Feature | Screen(s) | Route |
|---|---------|-----------|-------|
| F18 | Leave apply / balance | Leave | More → Leave |
| F19 | Expense claim + receipt photo | Expenses | More → Expenses |

### Admin mode — Technician Admin ✅ Built (v1 scope)

| # | Feature | Screen(s) | Route |
|---|---------|-----------|-------|
| A1 | Login as Technician Admin | Login (dropdown) | `/login` |
| A2 | Live map — all staff markers | Admin Live Tracking | `/admin/live` |
| A3 | Live staff list + status | Admin Live Tracking | `/admin/live` |
| A4 | Auto-refresh (30s) + manual refresh | Admin Live Tracking | `/admin/live` |
| A5 | Logout | Admin app bar | `/admin/live` |

### Future (not built — design placeholders only)

| # | Feature | Notes |
|---|---------|-------|
| F10 | My Route map (technician self) | Planned; admin has team map first |
| F12 | Dedicated permission primer screen | OS dialog + optional full screen |
| F16 | Push notifications | Not in v1 |
| F17 | Battery low warning banner | Not in v1 |
| A6+ | Admin visits/tasks/leave in app | Out of scope v1 — use CRM |

---

## 5. Design system (match Partner app / Stitch tokens)

Reuse the **same design language** as Pest 99 Partner App (`pest_99_partner_app/lib/core/theme/`).

### 5.1 Colors

| Token | Hex | Usage |
|-------|-----|-------|
| Primary | `#1B8E3D` | Buttons, active states, brand |
| Primary Dark | `#006B28` | Pressed primary, headers |
| Primary Container | `#0C8737` | Filled chips on duty |
| Background | `#F7FAF8` | Screen background |
| Surface | `#FFFFFF` | Cards, sheets |
| Border | `#E4E7EC` | Input borders, dividers |
| Text Primary | `#111827` | Headings, body |
| Text Secondary | `#6B7280` | Captions, hints |
| Success | `#16A34A` | Checked in, GPS active |
| Success BG | `#E8F5EC` | Success banners |
| Warning | `#F59E0B` | Idle, weak GPS, battery low |
| Danger | `#EF4444` | Errors, check-out CTA variant |
| Info Blue | `#2563EB` | Links, map accents |

### 5.2 Typography

| Style | Font | Weight | Size |
|-------|------|--------|------|
| Display / Hero | Manrope | 800 | 32–40sp |
| Headline | Manrope | 700–800 | 24sp |
| Title | Manrope | 600–700 | 18–20sp |
| Body | Inter | 400–500 | 14–16sp |
| Label / Chip | Inter | 600 | 12sp |
| Button | Manrope | 700 | 16sp |

### 5.3 Spacing & shape

- Screen horizontal padding: **20dp**
- Card corner radius: **16dp**
- Button corner radius: **12dp**
- Primary button height: **52dp**
- Icon size (toolbar): **24dp**
- Status chip height: **28dp**

### 5.4 Iconography

Use **Material Symbols Rounded** (filled for active, outlined for inactive).

Common icons: `location_on`, `my_location`, `login`, `logout`, `schedule`, `history`, `map`, `battery_full`, `cloud_sync`, `cloud_off`, `person`, `shield`, `check_circle`, `warning`, `error`, `groups`, `refresh`, `admin_panel_settings`.

### 5.6 Admin status colors (Technician Admin live map)

| Status | API value | Marker / avatar color | Label |
|--------|-----------|----------------------|-------|
| On duty (GPS active) | `on_duty` | Green `#16A34A` | `On duty` |
| Checked in, idle | `checked_in_idle` | Amber `#F59E0B` | `Checked in (idle)` |
| Off duty | `off_duty` | Gray `#9CA3AF` | `Off duty` |

### 5.5 Logo

- Use Pest Control 99 logo (green pest shield / brand mark)
- App name on login: **Pest99 Tracking**
- Subtitle: **Field Staff GPS**

---

## 6. Navigation architecture

### 6.1 App entry (both roles)

```
[Splash] → read session + app_mode
    ├─ Technician      → [MainShell /home]  (bottom nav)
    └─ Technician Admin → [Admin Live /admin/live]  (single screen, no bottom nav)

[Login] → role dropdown → Technician | Technician Admin (default: Technician)
    ├─ Technician      → [MainShell /home]
    └─ Technician Admin → [Admin Live /admin/live]
```

### 6.2 Technician — bottom navigation (4 tabs) ✅ Implemented

| Tab | Icon | Label | Screen |
|-----|------|-------|--------|
| 1 | `home` | Today | Check-in/out, consent, breaks |
| 2 | `place` | Visits | Today's visits + geo check-in/out |
| 3 | `task_alt` | Tasks | Assigned tasks + mark done |
| 4 | `more_horiz` | More | Attendance, Leave, Expenses, Profile |

**More menu (push screens, not tabs):**

| Item | Icon | Route |
|------|------|-------|
| Attendance History | `event_note` | Attendance |
| Leave | `beach_access` | Leave |
| Expenses | `receipt_long` | Expenses |
| Profile | `person` | Profile |

**Rule:** Check-in / Check-out is a **primary action on Today**, not a separate tab.

### 6.3 Technician Admin — no bottom nav ✅ Implemented

Single-screen app after login:

| Element | Action |
|---------|--------|
| App bar title | `Live Tracking` |
| Refresh icon | Manual reload `GET /live/` |
| Logout icon | Clear session → Login |
| Map (top ~260dp) | Staff markers |
| Summary bar | `{n} on duty • {total} total` + last updated time |
| Scrollable list | All staff cards below map |

**Rule:** Admin must **never** see Technician bottom nav or check-in UI. Router blocks `/home` when `app_mode = technician_admin`.

---

## 7. Screen specifications (Technician — Phase 1 core) ✅ Built

> Screens 06–07 (check-in/out bottom sheets) are **optional Stitch variants** — current Flutter build uses **inline hero buttons** on Home (Screen 05) without a modal sheet.

---

### Screen 01 — Splash

**Route:** `/splash`  
**Feature:** F1 — Session restore

#### Layout

```
┌─────────────────────────┐
│                         │
│      [Logo 96×96]         │
│   Pest99 Tracking       │
│   Field Staff GPS       │
│                         │
│      ◠ loading          │
│                         │
└─────────────────────────┘
```

#### Components

- Centered logo
- App title + subtitle
- Circular progress indicator (primary green)

#### Copy

- Title: `Pest99 Tracking`
- Subtitle: `Field Staff GPS`

#### States

| State | UI |
|-------|-----|
| Loading | Spinner visible |
| No animation clutter | No tagline carousel |

#### Post-login routing

| Session `app_mode` | Splash navigates to |
|--------------------|---------------------|
| `technician` | `/home` |
| `technician_admin` | `/admin/live` |
| Not logged in | `/login` |

#### Stitch prompt

```
Minimal splash screen Pest99 Tracking, logo, subtitle Field Staff GPS, green spinner.
No bottom nav. Portrait 390×844. After load routes by role (design note only).
```

---

### Screen 02 — Login (Technician + Technician Admin)

**Route:** `/login`  
**Feature:** F2 / A1 — Authentication with role selection  
**API:** `POST /api/staff-tracking/auth/login/` body: `{ mobile, password, app_mode: "technician" | "technician_admin" }`

#### Layout

```
┌─────────────────────────┐
│ Pest99 Tracking         │  ← Title (bold)
│ Field staff GPS         │  ← Subtitle
│ attendance & live       │
│ tracking                │
│                         │
│ ┌─────────────────────┐ │
│ │ Login as        ▼   │ │  ← Dropdown (default: Technician)
│ │  • Technician       │ │
│ │  • Technician Admin │ │
│ └─────────────────────┘ │
│ ┌─────────────────────┐ │
│ │ Mobile number       │ │
│ └─────────────────────┘ │
│ ┌─────────────────────┐ │
│ │ Password            │ │
│ └─────────────────────┘ │
│                         │
│ (Admin hint text if     │  ← Only when Technician Admin selected
│  Technician Admin)    │
│                         │
│ [ Login ] or            │
│ [ Login as Admin ]      │  ← CTA label changes by role
└─────────────────────────┘
```

#### Components

- App title + subtitle (no logo required in v1 Flutter build)
- **`DropdownButtonFormField`** — label `Login as`
- Mobile `TextField` — phone keyboard
- Password `TextField` — obscured
- Admin helper text (conditional)
- Primary CTA — full width, 52dp height, `#1B8E3D`
- Inline error text (red)

#### Copy

| Element | Technician mode | Technician Admin mode |
|---------|-----------------|----------------------|
| Dropdown label | `Login as` | `Login as` |
| Option 1 | `Technician` (**default**) | `Technician` |
| Option 2 | `Technician Admin` | `Technician Admin` |
| Mobile label | `Mobile number` | `Mobile number` |
| Password label | `Password` | `Password` |
| Helper | — | `Technician Admin can monitor live GPS locations of all field staff.` |
| CTA | `Login` | `Login as Admin` |
| Error (invalid) | `Invalid mobile or password.` | Same |
| Error (not authorized admin) | — | `This account is not authorized for Technician Admin access.` |
| Error (no profile as tech) | `No field profile linked…` | — |

#### States

| State | UI |
|-------|-----|
| Default | Technician selected, empty fields |
| Admin selected | Show helper text + `Login as Admin` CTA |
| Loading | CTA spinner, fields disabled |
| Error | Red text below password |

#### Post-login routing

| Role selected | Navigate to |
|---------------|-------------|
| Technician | `/home` (MainShell) |
| Technician Admin | `/admin/live` (Live Tracking only) |

#### Stitch prompt — Technician mode

```
Design login screen for "Pest99 Tracking" Android app, Technician mode.
Material 3, #F7FAF8 background. Title "Pest99 Tracking", subtitle "Field staff GPS attendance & live tracking".
Outlined dropdown "Login as" with "Technician" selected. Two text fields: Mobile number, Password.
Green #1B8E3D full-width button "Login" 52dp height. Portrait 390×844, Manrope title.
```

#### Stitch prompt — Technician Admin mode

```
Same login screen with dropdown set to "Technician Admin".
Small gray helper: "Technician Admin can monitor live GPS locations of all field staff."
Primary button text "Login as Admin" green #1B8E3D.
Supervisor/manager tone, still same brand. Portrait mobile 390×844.
```

---

### Screen 03 — GPS Consent

**Route:** `/consent` (first login only)  
**Feature:** F3 — Legal consent (India employee monitoring)

#### Layout

```
┌─────────────────────────┐
│ 🛡 Location Permission  │
│                         │
│ ┌─────────────────────┐ │
│ │ Why we need GPS   │ │
│ │ • Only while      │ │
│ │   checked in      │ │
│ │ • For attendance  │ │
│ │ • Not on off days │ │
│ └─────────────────────┘ │
│                         │
│ ☐ I agree to GPS       │
│   tracking during my   │
│   working hours        │
│                         │
│ [ I Agree & Continue ] │
│                         │
│ Privacy Policy link    │
└─────────────────────────┘
```

#### Copy

| Element | Text |
|---------|------|
| Title | `Location tracking consent` |
| Body | `Pest Control 99 uses GPS to verify field attendance and route during your shift. Location is collected only while you are checked in.` |
| Bullet 1 | `Tracking starts at check-in and stops at check-out` |
| Bullet 2 | `Data is used for attendance and safety, not shared for ads` |
| Bullet 3 | `You can request your data from admin` |
| Checkbox | `I agree to GPS tracking during working hours` |
| CTA | `I Agree & Continue` |
| Link | `Privacy Policy` |

#### States

| State | UI |
|-------|-----|
| CTA disabled | Checkbox unchecked |
| CTA enabled | Checkbox checked |

#### Stitch prompt

```
Design a GPS consent screen for employee tracking app. Material 3, green theme #1B8E3D.
Shield icon header "Location tracking consent". White info card with 3 bullet points
about tracking only during check-in. Checkbox "I agree to GPS tracking during working hours".
Primary button "I Agree & Continue" disabled until checked. Link "Privacy Policy" at bottom.
Trustworthy, legal, clean. Portrait 390×844.
```

---

### Screen 04 — Location Permission Primer ⏳ Future

**Route:** `/permissions` *(OS dialog used in current build; dedicated screen not built)*  
**Feature:** F12 — OS permission education

#### Layout

```
┌─────────────────────────┐
│      [Map pin illus.]   │
│ Enable location         │
│                         │
│ We need location access │
│ to record check-in and  │
│ your route while on duty│
│                         │
│ ✓ Allow "While using"   │
│ ✓ Allow "All the time"  │
│   during shift (Android)│
│                         │
│ [ Open Settings ]       │
│ [ Continue ]            │
└─────────────────────────┘
```

#### Copy

| Element | Text |
|---------|------|
| Title | `Enable location` |
| Body | `To track your route while on duty, allow location access. Tracking only runs between check-in and check-out.` |
| Step 1 | `Tap Allow while using the app` |
| Step 2 | `Then allow background location for shift tracking` |
| Primary CTA | `Continue` |
| Secondary | `Open Settings` |

#### Stitch prompt

```
Design Android location permission education screen for field staff app.
Illustration: map pin on soft green circle #E8F5EC.
Title "Enable location", explanatory text, numbered steps list.
Two buttons: primary "Continue" green #1B8E3D, secondary outlined "Open Settings".
Friendly, not scary. Portrait 390×844 Material 3.
```

---

### Screen 05 — Home (Today Dashboard) ★ Primary screen

**Route:** `/home`  
**Features:** F4, F5, F6, F7, F8

#### Layout — OFF DUTY

```
┌─────────────────────────┐
│ Good morning, Arshad 👋 │  ← AppBar
│ Tue, 16 Jun · Lonavala  │
├─────────────────────────┤
│ ┌─────────────────────┐ │
│ │ ○ OFF DUTY          │ │  ← Status card
│ │ Shift: 9:00–18:00   │ │
│ │ Not checked in      │ │
│ └─────────────────────┘ │
│                         │
│ ┌─────────────────────┐ │
│ │                     │ │
│ │   [  CHECK IN  ]    │ │  ← Hero CTA
│ │   Start GPS tracking│ │
│ │                     │ │
│ └─────────────────────┘ │
│                         │
│ Today summary           │
│ ┌──────┐ ┌──────┐      │
│ │ 0 km │ │ --   │      │
│ │Dist. │ │Hours │      │
│ └──────┘ └──────┘      │
│                         │
│ [Today][Visits][Tasks][More] │
└─────────────────────────┘
```

#### Layout — ON DUTY (checked in)

```
┌─────────────────────────┐
│ Good afternoon, Arshad    │
│ ● ON DUTY · GPS active    │  ← green pulsing dot
├─────────────────────────┤
│ ┌─────────────────────┐ │
│ │ ✓ Checked in 9:02 AM│ │
│ │ 📍 GPS tracking on  │ │
│ │ 🔋 78% · Synced ✓   │ │
│ └─────────────────────┘ │
│                         │
│ ┌─────────────────────┐ │
│ │   [ CHECK OUT ]     │ │  ← red/outline CTA
│ │   End shift & stop  │ │
│ └─────────────────────┘ │
│                         │
│ Live stats              │
│ ┌──────┐ ┌──────┐      │
│ │ 4.2km│ │5h 12m│      │
│ │Dist. │ │Time  │      │
│ └──────┘ └──────┘      │
│                         │
│ [Start break][End break]│  ← Outlined row (on duty only)
│ Last ping: 2 min ago    │
│ [Today][Visits][Tasks][More] │
└─────────────────────────┘
```

#### Components

| Component | Description |
|-----------|-------------|
| Greeting header | Name + date + city from profile |
| Status card | Large chip: OFF DUTY / ON DUTY / IDLE |
| Hero CTA | Check In (green filled) or Check Out (red outline) |
| Stats row | Distance today, time on duty |
| Sync chip | `Synced` / `Syncing…` / `Offline — queued` |
| GPS pulse | Animated green dot when tracking |
| Break buttons | `Start break` / `End break` (on duty) |
| Bottom nav | Today · Visits · Tasks · More |

#### Copy

| State | CTA | Subtext |
|-------|-----|---------|
| Off duty | `Check In` | `Start GPS tracking for your shift` |
| On duty | `Check Out` | `End shift and stop location tracking` |
| Success check-in | Toast | `Checked in at 9:02 AM` |
| Success check-out | Toast | `Checked out. GPS tracking stopped.` |

#### Status chip colors

| Status | Color | Label |
|--------|-------|-------|
| `off_duty` | Gray `#9CA3AF` | `OFF DUTY` |
| `on_duty` | Green `#16A34A` | `ON DUTY` |
| `checked_in_idle` | Amber `#F59E0B` | `IDLE` |

#### States

| State | UI |
|-------|-----|
| Loading | Skeleton on status card |
| Checking in | Full-screen semi-modal spinner `Getting GPS fix…` |
| GPS weak | Banner: `Weak GPS signal. Move outdoors.` |
| Offline | Amber banner: `Offline — locations will sync when back online` |
| Error | Red snackbar |

#### Stitch prompts

**Off duty:**

```
Design home dashboard for field technician tracking app "Pest99 Tracking", OFF DUTY state.
Material 3, background #F7FAF8. Top greeting "Good morning, Arshad", date and city.
Gray status card "OFF DUTY", shift hours 9:00-18:00.
Large green #1B8E3D "Check In" button card in center.
Two stat tiles below: Distance 0 km, Hours --.
Bottom navigation: Today, Visits, Tasks, More (Today active).
Portrait 390×844, Manrope headings.
```

**On duty:**

```
Same app home screen ON DUTY state. Green pulsing dot "ON DUTY · GPS active".
Status card: checked in time, GPS tracking on, battery 78%, Synced checkmark.
Large red outline "Check Out" button.
Stats: 4.2 km distance, 5h 12m time on duty. Row: "Start break" | "End break" outlined buttons.
"Last ping: 2 min ago". Bottom nav: Today, Visits, Tasks, More (Today active). Material 3 green theme.
```

---

## 7B. Technician Admin screens (v1 — live tracking only)

> **Scope check:** Admin mode has **one screen** after login. Do **not** add bottom nav, check-in, visits, tasks, leave, or expenses to admin designs in v1.

---

### Screen A1 — Admin Live Tracking ★ Primary admin screen

**Route:** `/admin/live`  
**Features:** A2, A3, A4, A5  
**API:** `GET /api/staff-tracking/live/` — polls every **30 seconds** + manual refresh  
**Auth:** Partner `technician_admin` JWT or CRM Admin JWT

#### Layout

```
┌─────────────────────────┐
│ Live Tracking    🔄  ⎋ │  ← AppBar: refresh + logout
├─────────────────────────┤
│ 3 on duty · 12 total     │  ← Summary bar (#1B8E3D 10% tint)
│ Updated 10:45 AM         │
├─────────────────────────┤
│ ┌─────────────────────┐ │
│ │                     │ │
│ │   [ MAP 260dp ]     │ │  ← OpenStreetMap / map tiles
│ │   🟢🟡 pins = staff │ │
│ │                     │ │
│ └─────────────────────┘ │
├─────────────────────────┤
│ ┌─────────────────────┐ │
│ │ 👤 Arshad Khan      │ │
│ │ On duty · Lonavala  │ │
│ │ 4.2 km      2m ago  │ │
│ └─────────────────────┘ │
│ ┌─────────────────────┐ │
│ │ 👤 Ravi Patil       │ │
│ │ Off duty · Pune     │ │
│ │ —           —       │ │
│ └─────────────────────┘ │
│ ... scrollable list ... │
└─────────────────────────┘
```

#### Map markers

| Staff status | Pin color | Icon |
|--------------|-----------|------|
| `on_duty` | Green `#16A34A` | `person_pin_circle` |
| `checked_in_idle` | Amber `#F59E0B` | `person_pin_circle` |
| `off_duty` / no GPS | Gray — **no pin** if lat/lng null | — |

Default map center when no pins: **Lonavala** `18.752, 73.405`

#### Staff list card

| Row | Source field |
|-----|--------------|
| Title | `name` |
| Subtitle line | `{status label} · {city} · {distance_today_km} km` |
| Trailing | Relative `last_ping_at` — `Just now`, `5m ago`, `2h ago` |
| Leading avatar | Circle with status color + person icon |

#### Copy

| Element | Text |
|---------|------|
| App bar title | `Live Tracking` |
| Summary | `{on_duty_count} on duty · {total} total` |
| Updated | `Updated {time}` |
| Status: on duty | `On duty` |
| Status: idle | `Checked in (idle)` |
| Status: off | `Off duty` |
| Empty list | `No tracking profiles yet. Run backfill on backend.` |
| Error | API error message (red, 12sp below map) |

#### States

| State | UI |
|-------|-----|
| Loading (first load) | Spinner in refresh icon OR center list |
| Loaded | Map + list populated |
| No GPS for staff | Staff in list but no map pin |
| Empty team | Map default center + empty list message |
| Error | Red error text, list may be empty |
| Refreshing | Refresh icon shows small spinner |

#### Interactions

| Action | Behavior |
|--------|----------|
| Tap refresh | Immediate `GET /live/` |
| Auto poll | Every 30s while screen mounted |
| Tap logout | Stop poll → clear session → `/login` |
| Tap staff card | **v1:** no navigation (future: staff detail / history) |

#### Stitch prompt — Admin Live Tracking (default)

```
Design "Live Tracking" supervisor screen for pest control field staff monitoring app.
Material 3, green brand #1B8E3D. App bar "Live Tracking" with refresh and logout icons.
Summary strip: "3 on duty · 12 total" and "Updated 10:45 AM" on light green background.
Large map area (~260dp height) with colored person pins (green on duty, amber idle).
Below: scrollable white cards for each technician — name bold, subtitle status city distance,
trailing "2m ago". No bottom navigation. Portrait 390×844. Professional supervisor dashboard.
```

#### Stitch prompt — Admin Live Tracking (empty)

```
Same Live Tracking admin screen but empty state: map centered on Lonavala India,
center message "No staff with active GPS yet" in list area. Summary "0 on duty · 0 total".
Calm empty state, not alarming. Material 3 green theme.
```

---

### Screen A2 — Admin session / auth errors

**Route:** Redirect to `/login` or inline on Live screen  
**Reuse:** Screen 11 variants + admin-specific copy

| Variant | Title | Body | CTA |
|---------|-------|------|-----|
| Not authorized | `Access denied` | `This account is not authorized for Technician Admin access.` | `Back to login` |
| Session expired | `Session expired` | `Please sign in again.` | `Sign in` |
| Network error on live | (inline red) | API error string | Tap refresh |

#### Stitch prompt

```
Mobile error state for supervisor app: shield lock icon, title "Access denied",
subtitle about Technician Admin authorization only. Green "Back to login" button.
Material 3, minimal illustration, #F7FAF8 background.
```

---

### Admin design checklist ✅

Before marking admin designs complete in Stitch, verify:

- [ ] Login dropdown defaults to **Technician**
- [ ] **Technician Admin** login shows helper text + `Login as Admin` CTA
- [ ] Admin flow has **no bottom navigation bar**
- [ ] Admin flow has **no** Check In / Check Out buttons
- [ ] Live map shows green / amber / gray status legend (in design notes)
- [ ] Staff list shows name, status, city, km, last ping
- [ ] App bar has refresh + logout only (no settings, no profile)
- [ ] Matches API fields from `GET /live/` (Section 14B)

---

### Screen 06 — Check-in Confirmation (bottom sheet) ⏳ Design optional

**Route:** Modal on Home *(not implemented — inline Check In on Screen 05)*  
**Feature:** F5

#### Layout

```
┌─────────────────────────┐
│        ─── handle       │
│ Confirm check-in        │
│                         │
│  📍 Current location    │
│  Lat 18.7521, Lon 73.40 │
│  Accuracy: ±12 m        │
│                         │
│  [ mini map preview ]   │
│                         │
│ [ Cancel ] [ Check In ] │
└─────────────────────────┘
```

#### Copy

- Title: `Confirm check-in`
- Location label: `Your current location`
- Accuracy: `Accuracy: ±{n} m`
- Cancel / Confirm buttons

#### Stitch prompt

```
Material 3 bottom sheet modal for GPS check-in confirmation.
Title "Confirm check-in", map preview thumbnail, coordinates text, accuracy ±12m.
Two buttons: text "Cancel", primary green "Check In".
White sheet, rounded top corners 24dp. Portrait mobile.
```

---

### Screen 07 — Check-out Confirmation (bottom sheet) ⏳ Design optional

**Route:** Modal on Home *(not implemented — inline Check Out on Screen 05)*  
**Feature:** F6

#### Copy

- Title: `End your shift?`
- Body: `GPS tracking will stop. Make sure you have completed today's visits.`
- Stats preview: `Distance today: 4.2 km` · `Time: 5h 12m`
- CTA: `Check Out` (red)
- Cancel: `Continue shift`

#### Stitch prompt

```
Bottom sheet "End your shift?" for tracking app. Warning tone but calm.
Show distance 4.2 km and time 5h 12m. Red primary "Check Out", gray "Continue shift".
Material 3, portrait mobile.
```

---

### Screen 08 — My Route ⏳ Future

**Route:** `/route` *(not built — admin live map shipped first)*  
**Feature:** F10

#### Layout

```
┌─────────────────────────┐
│ ← My Route        Today ▼│
├─────────────────────────┤
│ ┌─────────────────────┐ │
│ │                     │ │
│ │    [ Google Map ]   │ │
│ │    route polyline   │ │
│ │    start/end pins   │ │
│ │                     │ │
│ └─────────────────────┘ │
│                         │
│ 4.2 km · 48 pings       │
│ Started 9:02 AM         │
└─────────────────────────┘
```

#### States

| State | UI |
|-------|-----|
| Not checked in today | Empty: `Check in to see your route` |
| No pings yet | Map centered on check-in point |
| Active route | Blue polyline, green start dot, red current position |

#### Stitch prompt

```
"My Route" screen for GPS tracking app. Full-width map card with blue route line,
green start marker, red current position dot. Header "My Route" with date dropdown "Today".
Below map: "4.2 km · 48 pings · Started 9:02 AM".
Material 3, #F7FAF8 background, portrait 390×844.
```

---

### Screen 09 — Attendance History ✅ Built

**Route:** More → Attendance  
**Feature:** F9

#### Layout

```
┌─────────────────────────┐
│ Attendance              │
├─────────────────────────┤
│ ┌─────────────────────┐ │
│ │ 16 Jun · Present    │ │
│ │ In 9:02 · Out 6:15  │ │
│ │ 4.2 km · On time    │ │
│ └─────────────────────┘ │
│ ┌─────────────────────┐ │
│ │ 15 Jun · Present    │ │
│ │ In 9:18 · Out 6:02  │ │
│ │ 3.8 km · Late       │ │  ← amber "Late" badge
│ └─────────────────────┘ │
│ ┌─────────────────────┐ │
│ │ 14 Jun · No record  │ │
│ └─────────────────────┘ │
└─────────────────────────┘
```

#### Copy

| Badge | Color |
|-------|-------|
| `On time` | Green |
| `Late` | Amber |
| `No record` | Gray |

#### Stitch prompt

```
Attendance history list screen. Cards per day: date, Present/No record badge,
check-in/out times, distance km, On time or Late pill badge.
Material 3 list on #F7FAF8, green #1B8E3D accents. Last 30 days scrollable list.
Portrait mobile.
```

---

### Screen 10 — Profile ✅ Built

**Route:** More → Profile  
**Feature:** F11

#### Layout

```
┌─────────────────────────┐
│ Profile                 │
├─────────────────────────┤
│   [Avatar]              │
│   Arshad Khan           │
│   9876543210            │
│   Lonavala · Technician │
│                         │
│ ── Account ──           │
│ Attendance history   >  │
│ Privacy & consent    >  │
│ ── Support ──           │
│ Contact admin        >  │
│ App version 1.0.0       │
│                         │
│ [ Log out ]             │
└─────────────────────────┘
```

#### Stitch prompt

```
Profile screen for technician app. Avatar circle, name, mobile, city and role.
Grouped list: Attendance history, Privacy & consent, Contact admin.
Red text button "Log out" at bottom. App version small gray text.
Material 3, clean white cards, portrait 390×844.
```

---

### Screen 11 — Session Expired / Error

**Route:** Global  
**Feature:** F13

#### Variants

| Variant | Title | CTA |
|---------|-------|-----|
| Session expired | `Session expired` | `Sign in again` |
| No internet | `You're offline` | `Retry` |
| Server error | `Something went wrong` | `Try again` |
| No technician link | `Account not set up` | `Contact admin` |

#### Stitch prompt

```
Full-screen error state illustration, friendly pest control app style.
Icon cloud off, title "You're offline", subtitle "Locations will sync when connected."
Primary green "Retry" button. Minimal illustration, #F7FAF8 background.
```

---

## 8. Phase 2 screens — Visits & Tasks ✅ Built

### Screen 12 — Today's Visits

**Route:** Visits tab (`/home` → tab 2)  
**API:** `GET /api/staff-tracking/visits/mine/`

```
┌─────────────────────────┐
│ Today's Visits          │
├─────────────────────────┤
│ ┌─────────────────────┐ │
│ │ AMC Service — #725  │ │
│ │ [scheduled] chip    │ │
│ │ Mr. Sharma          │ │
│ │ Lonavala address…   │ │
│ │ [ Check in ]        │ │
│ └─────────────────────┘ │
│ ┌─────────────────────┐ │
│ │ … in_progress …     │ │
│ │ [ Check out ]       │ │
│ └─────────────────────┘ │
└─────────────────────────┘
```

**Status chips:** `scheduled` (amber), `in_progress` (blue), `completed` (green), `missed` (red)

**Stitch prompt:** `Today's Visits list for pest control technician app. Cards with job title, status chip, client, address, Check in/out button. Pull to refresh. Material 3 green #1B8E3D, bottom nav Visits tab active.`

### Screen 13 — Tasks

**Route:** Tasks tab (`/home` → tab 3)  
**API:** `GET /api/staff-tracking/tasks/mine/`

```
┌─────────────────────────┐
│ My Tasks                │
├─────────────────────────┤
│ ┌─────────────────────┐ │
│ │ Follow up client X    │ │
│ │ pending · description│ │
│ │              [ Done ] │ │
│ └─────────────────────┘ │
└─────────────────────────┘
```

**Stitch prompt:** `Task list for field technician. Title, status, Done button. Empty: "No tasks assigned". Material 3 green theme, Tasks tab active.`

---

## 9. Phase 3 screens — Leave & Expenses ✅ Built

### Screen 14 — More hub

**Route:** More tab (`/home` → tab 4)

```
┌─────────────────────────┐
│ More                    │
├─────────────────────────┤
│ ┌ Attendance History  > │
│ ┌ Leave               > │
│ ┌ Expenses            > │
│ ┌ Profile             > │
└─────────────────────────┘
```

### Screen 15 — Leave

**Route:** More → Leave  
**API:** balance, apply, applications

**Stitch prompt:** `Leave screen: balance list at top, apply form (type dropdown, dates, reason, Submit), my applications list below. Material 3 HR style, green accents.`

### Screen 16 — Expenses

**Route:** More → Expenses  
**API:** categories, submit, receipt camera upload

**Stitch prompt:** `Expense claim form: category dropdown, amount, description, toggle "Auto-calculate travel from GPS distance", Submit. List of my claims with camera icon for receipt upload on pending items.`

---

## 9B. Phase 2 screens (legacy wireframe — Visit detail)

### Screen 13B — Visit Detail + Geo Check-in (future enhancement)

**Stitch prompt:** `Visit detail screen with client address, map, big "Arrive & Check in" button when within 100m geofence. Job #725 AMC Service. Material 3.`

---

## 10. Component library (build in Stitch as variants)

Create these as **reusable components** in Stitch before screens:

| Component | Variants |
|-----------|----------|
| `PrimaryButton` | Default, Loading, Disabled |
| `SecondaryButton` | Outlined |
| `DangerButton` | Check-out |
| `StatusChip` | Off duty, On duty, Idle, Late |
| `SyncChip` | Synced, Syncing, Offline |
| `StatTile` | Distance, Hours, Battery |
| `AttendanceCard` | Present, Late, Absent |
| `TextField` | Default, Error, Focused |
| `InfoBanner` | Success, Warning, Error |
| `BottomNav` | 4 tabs (Technician only) |
| `GpsPulseDot` | Animated on / static off |
| `StaffLiveCard` | Admin list row with status avatar |
| `AdminSummaryBar` | On duty count + last updated |
| `LiveMapPanel` | Map + colored staff pins |
| `RoleDropdown` | Technician / Technician Admin |
| `VisitStatusChip` | scheduled / in_progress / completed / missed |

---

## 11. Motion & feedback

| Action | Feedback |
|--------|----------|
| Check-in success | Green toast + haptic + status card animate to ON DUTY |
| Check-out success | Neutral toast + card animate to OFF DUTY |
| GPS ping failed | Silent queue; show `Offline` chip only |
| Pull to refresh on Home | Refresh location + sync status |
| Admin manual refresh | Reload all staff on map + list |
| Admin auto poll (30s) | Silent refresh; update summary timestamp |

---

## 12. Accessibility

- Minimum touch target: **48×48dp**
- Color contrast: WCAG AA for text on backgrounds
- Don't rely on color alone — use icons + text for status
- Support system font scaling up to 1.3×

---

## 13. Stitch workflow (recommended order)

1. **Design system frame** — colors, type, buttons, chips (Section 5)
2. **Component library** (Section 10)
3. **Screen 02 Login** — **both Technician and Technician Admin variants**
4. **Screen A1 Admin Live Tracking** — map + list + empty state
5. **Screen 03 Consent** (inline on Home in current build)
6. **Screen 05 Home** — OFF DUTY and ON DUTY + break buttons
7. **Screen 12 Visits**, **Screen 13 Tasks**, **Screen 14–16 More/Leave/Expenses**
8. **Screen 09 Attendance**, **Screen 10 Profile**
9. **Screen 01 Splash** + **Screen 11 / A2 Errors**
10. Optional: Screen 08 My Route (not built yet)

### Export checklist from Stitch

- [ ] PNG/SVG export at **390×844** (base) and **360×800** (small)
- [ ] Design tokens documented (colors, spacing)
- [ ] All CTA labels match copy in Section 7
- [ ] Dark mode: **not required** for v1 (light only)

---

## 14. API data mapping (for designers — labels on screen)

### 14A. Technician — `GET /me/`

| UI label | API field |
|----------|-----------|
| Name | `profile.name` |
| Mobile | `profile.mobile` |
| City | `profile.city` |
| Checked in? | `is_checked_in` |
| Check-in time | `active_session.check_in_at` |
| Shift start | `settings.shift_start_time` |
| Shift end | `settings.shift_end_time` |
| Ping interval | `settings.ping_interval_moving_seconds` |
| Has consent | `has_consent` |
| Last location | `last_ping.latitude/longitude` |

### 14B. Technician Admin — `GET /live/`

| UI label | API field |
|----------|-----------|
| Staff name | `name` |
| Status | `status` → `on_duty` / `checked_in_idle` / `off_duty` |
| Map pin lat/lng | `latitude`, `longitude` (null = no pin) |
| City | `city` |
| Distance today | `distance_today_km` |
| Last ping time | `last_ping_at` |
| On duty count | Count where `status == on_duty` |
| Total staff | Array length |
| Battery (future) | `battery_percent` |

### 14C. Login — `POST /auth/login/`

| UI | Request field |
|----|---------------|
| Role dropdown | `app_mode`: `technician` (default) or `technician_admin` |
| Response routing | `app_mode` in response → persist → splash routes admin to `/admin/live` |

---

## 15. Out of scope (do not design in this app)

**Technician Admin v1 — do NOT design:**
- Admin check-in / check-out
- Admin visits, tasks, leave, expense management screens
- Admin bottom navigation
- Admin profile / settings (logout in app bar only)

**Entire app — do NOT design:**
- Full CRM manager dashboard (web only)
- Booking accept/start/complete (Partner app)
- Payment collection
- Client CRM data entry
- Blog / marketing website

**Note:** Technician Admin **does** get mobile live map; CRM web still has the **full** Staff Tracking section (visits, tasks, leave, expenses, history).

---

## 16. Quick reference — all screens

### Technician flow

| # | Screen | Route | Status |
|---|--------|-------|--------|
| 01 | Splash | `/splash` | ✅ Built |
| 02 | Login (role dropdown) | `/login` | ✅ Built |
| 03 | GPS Consent | inline on `/home` | ✅ Built |
| 05 | Home (Today) | `/home` tab 1 | ✅ Built |
| 08 | My Route | — | ⏳ Future |
| 09 | Attendance | More → Attendance | ✅ Built |
| 10 | Profile | More → Profile | ✅ Built |
| 11 | Error states | global | ✅ Built |
| 12 | Visits | `/home` tab 2 | ✅ Built |
| 13 | Tasks | `/home` tab 3 | ✅ Built |
| 14 | More hub | `/home` tab 4 | ✅ Built |
| 15 | Leave | More → Leave | ✅ Built |
| 16 | Expenses | More → Expenses | ✅ Built |

### Technician Admin flow

| # | Screen | Route | Status |
|---|--------|-------|--------|
| A1 | Login (Admin mode) | `/login` dropdown | ✅ Built |
| A2 | **Live Tracking** | `/admin/live` | ✅ Built |
| A3 | Admin auth errors | → `/login` | ✅ Built |

---

**Document version:** 2.0  
**Last updated:** June 2026  
**Owner:** Pest Control 99 — Staff Tracking project  
**Next step:** Open Google Stitch → design **Screen 02 (both roles)** + **Screen A1 Admin Live Tracking** first → export to `pest99_tracking_app/docs/stitch-exports/`
