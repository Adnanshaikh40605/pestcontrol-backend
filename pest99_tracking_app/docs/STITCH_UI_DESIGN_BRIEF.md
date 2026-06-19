# Pest99 Tracking App — Google Stitch UI Design Brief

**Product:** Pest99 Tracking (Field Staff GPS App)  
**Company:** Pest Control 99 / Multi Pest LLP  
**Platform:** Android mobile app (Flutter implementation later — **this document is design-only**)  
**Design tool:** [Google Stitch](https://stitch.withgoogle.com)  
**Companion app:** Pest 99 Partner App (bookings) — same brand, same login accounts  
**Manager UI:** Pest CRM → Staff Tracking section (web — out of scope for this doc)

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

**Design scope:** Mobile app only (`pest99_tracking_app`).  
**Not in scope:** CRM web pages, Partner booking app, backend admin.

---

## 2. Product summary

Pest99 Tracking is a **field staff GPS attendance & live location app** for pest control technicians and field staff.

| What staff do | What managers see (CRM — reference only) |
|---------------|------------------------------------------|
| Check in at shift start with GPS | Live map of all staff |
| App sends location pings while checked in | Attendance reports |
| Check out at shift end | Route history & distance |
| View own attendance history | Staff directory |

**Privacy rule (must show in UI):** Location is recorded **only while checked in**, not on weekends/off-hours unless actively on duty.

**Login:** Same mobile number + password as Partner app (`/api/staff-tracking/auth/login/`).

---

## 3. User persona

| Field | Value |
|-------|-------|
| Name | Example: Arshad Khan |
| Role | Field technician / pest control operator |
| Age | 22–45 |
| Device | Android (5.5"–6.7"), mid-range |
| Literacy | Comfortable with WhatsApp-style apps |
| Language | English primary; Hindi labels acceptable on key buttons |
| Environment | Bright sunlight, gloves, moving between sites |
| Pain points | Small buttons, unclear GPS status, battery anxiety |

**Design goals:** Large tap targets (min 48dp), high contrast, obvious on/off-duty state, minimal typing.

---

## 4. Feature roadmap (for screen planning)

### Phase 1 — MVP (design & build first)

| # | Feature | Screen(s) |
|---|---------|-----------|
| F1 | Splash & session restore | Splash |
| F2 | Login (mobile + password) | Login |
| F3 | GPS tracking consent (legal) | Consent |
| F4 | Today dashboard (shift status) | Home |
| F5 | Check-in with GPS | Home → Check-in confirm |
| F6 | Check-out with GPS | Home → Check-out confirm |
| F7 | Live tracking indicator (while on duty) | Home banner + status chip |
| F8 | Offline sync status | Home sync chip |
| F9 | My attendance history (30 days) | Attendance History |
| F10 | My route today (map) | My Route |
| F11 | Profile & logout | Profile |
| F12 | Location permission education | Permission primer |
| F13 | Error & session expired | Error states |

### Phase 2 — Operations (design after MVP approved)

| # | Feature | Screen(s) |
|---|---------|-----------|
| F14 | Today's assigned visits (from JobCard) | Visits list |
| F15 | Visit check-in near client (geo verify) | Visit detail |
| F16 | Push notifications (shift reminders) | Notification list |
| F17 | Battery low warning (self) | Home alert banner |

### Phase 3 — HR (future)

| # | Feature | Screen(s) |
|---|---------|-----------|
| F18 | Leave apply / balance | Leave |
| F19 | Expense claim + receipt photo | Expenses |
| F20 | Tasks assigned by manager | Tasks |

**This brief includes full specs for Phase 1 screens + wireframes for Phase 2–3 so Stitch can design a coherent app shell.**

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

Common icons: `location_on`, `my_location`, `login`, `logout`, `schedule`, `history`, `map`, `battery_full`, `cloud_sync`, `cloud_off`, `person`, `shield`, `check_circle`, `warning`, `error`.

### 5.5 Logo

- Use Pest Control 99 logo (green pest shield / brand mark)
- App name on login: **Pest99 Tracking**
- Subtitle: **Field Staff GPS**

---

## 6. Navigation architecture

```
[Splash] → (session?) → [Home] or [Login]
[Login] → [Consent?] → [Home]
[Home] ← bottom nav → [My Route] [Attendance] [Profile]
```

### Bottom navigation (4 tabs — Phase 1)

| Tab | Icon | Label |
|-----|------|-------|
| 1 | `home` | Today |
| 2 | `map` | My Route |
| 3 | `event_note` | Attendance |
| 4 | `person` | Profile |

**Rule:** Check-in / Check-out is a **primary action on Home**, not a separate tab.

---

## 7. Screen specifications (Phase 1)

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

#### Stitch prompt

```
Design a mobile splash screen for "Pest99 Tracking" Android app.
Style: clean Material 3, pest control company branding.
Background #F7FAF8, primary green #1B8E3D.
Center: app logo placeholder (green shield), title "Pest99 Tracking",
subtitle "Field Staff GPS", small circular loading indicator below.
Font: Manrope for titles. Minimal, professional, no photos.
Portrait 390×844.
```

---

### Screen 02 — Login

**Route:** `/login`  
**Feature:** F2 — Authentication

#### Layout

```
┌─────────────────────────┐
│ [Logo]                  │
│ Pest99 Tracking         │
│ Sign in to start shift  │
│                         │
│ ┌─────────────────────┐ │
│ │ 📱 Mobile number    │ │
│ └─────────────────────┘ │
│ ┌─────────────────────┐ │
│ │ 🔒 Password      👁 │ │
│ └─────────────────────┘ │
│                         │
│ [    Sign In (full)   ] │
│                         │
│ Same login as Partner   │
│ app · Contact admin     │
└─────────────────────────┘
```

#### Components

- Logo (small, top-left or centered)
- Mobile `TextField` — numeric keyboard, 10 digits
- Password `TextField` — obscured, visibility toggle
- Primary CTA: **Sign In**
- Footer helper text

#### Copy

| Element | Text |
|---------|------|
| Headline | `Sign in` |
| Subhead | `Use your technician mobile & password` |
| Mobile label | `Mobile number` |
| Mobile hint | `10-digit mobile` |
| Password label | `Password` |
| CTA | `Sign In` |
| Footer | `Same account as Pest 99 Partner app. Need help? Contact admin.` |
| Error (invalid) | `Invalid mobile or password` |
| Error (network) | `No internet. Check connection and try again.` |

#### States

| State | UI |
|-------|-----|
| Default | Empty fields, CTA enabled |
| Loading | CTA shows spinner, fields disabled |
| Error | Red inline banner above CTA |
| Validation | Mobile < 10 digits → `Enter valid 10-digit mobile` |

#### Stitch prompt

```
Design a login screen for field technician GPS tracking app "Pest99 Tracking".
Material 3, white surface card on #F7FAF8 background, primary button #1B8E3D.
Headline "Sign in", subtitle "Use your technician mobile & password".
Two outlined text fields: Mobile number (phone icon), Password (lock icon, show/hide).
Large full-width "Sign In" button. Small gray footer about same Partner app login.
Portrait mobile 390×844. Manrope headings, Inter body. Professional pest control brand.
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

### Screen 04 — Location Permission Primer

**Route:** `/permissions` (before first check-in)  
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
│ [Today][Route][Attend][Profile] │
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
│ Last ping: 2 min ago    │
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
| Bottom nav | 4 tabs |

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
Bottom navigation: Today, My Route, Attendance, Profile (Today active).
Portrait 390×844, Manrope headings.
```

**On duty:**

```
Same app home screen ON DUTY state. Green pulsing dot "ON DUTY · GPS active".
Status card: checked in time, GPS tracking on, battery 78%, Synced checkmark.
Large red outline "Check Out" button.
Stats: 4.2 km distance, 5h 12m time on duty. "Last ping: 2 min ago".
Bottom nav unchanged. Material 3 green pest control theme.
```

---

### Screen 06 — Check-in Confirmation (bottom sheet)

**Route:** Modal on Home  
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

### Screen 07 — Check-out Confirmation (bottom sheet)

**Route:** Modal on Home  
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

### Screen 08 — My Route

**Route:** `/route`  
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

### Screen 09 — Attendance History

**Route:** `/attendance`  
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

### Screen 10 — Profile

**Route:** `/profile`  
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

## 8. Phase 2 screens (wireframe + Stitch prompt)

### Screen 12 — Today's Visits

```
┌─────────────────────────┐
│ Today's Visits     (3)  │
├─────────────────────────┤
│ ┌─────────────────────┐ │
│ │ #725 · AMC Service  │ │
│ │ Mr. Sharma · 10:30  │ │
│ │ Lonavala · 2.3 km   │ │
│ │ [ Navigate ]        │ │
│ └─────────────────────┘ │
└─────────────────────────┘
```

**Stitch prompt:** `Today's Visits list for pest control technician. Job cards with client name, time slot, area, distance away, Navigate button. Material 3 green theme, portrait mobile.`

### Screen 13 — Visit Detail + Geo Check-in

**Stitch prompt:** `Visit detail screen with client address, map, big "Arrive & Check in" button when within 100m geofence. Job #725 AMC Service. Material 3.`

---

## 9. Phase 3 screens (placeholder prompts)

| Screen | Stitch one-liner |
|--------|------------------|
| Leave apply | `Leave request form: date range, reason dropdown, submit. HR app green theme.` |
| Expense claim | `Expense form with amount, category, camera receipt upload, submit.` |
| Tasks | `Kanban-style task list: To Do, In Progress, Done columns, mobile.` |

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
| `BottomNav` | 4 tabs |
| `GpsPulseDot` | Animated on / static off |

---

## 11. Motion & feedback

| Action | Feedback |
|--------|----------|
| Check-in success | Green toast + haptic + status card animate to ON DUTY |
| Check-out success | Neutral toast + card animate to OFF DUTY |
| GPS ping failed | Silent queue; show `Offline` chip only |
| Pull to refresh on Home | Refresh location + sync status |

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
3. **Screen 02 Login**
4. **Screen 03 Consent**
5. **Screen 05 Home** — both OFF DUTY and ON DUTY variants
6. **Screen 06–07** bottom sheets
7. **Screen 08 My Route**
8. **Screen 09 Attendance**
9. **Screen 10 Profile**
10. **Screen 01 Splash** + **Screen 11 Errors**
11. Phase 2 screens when MVP approved

### Export checklist from Stitch

- [ ] PNG/SVG export at **390×844** (base) and **360×800** (small)
- [ ] Design tokens documented (colors, spacing)
- [ ] All CTA labels match copy in Section 7
- [ ] Dark mode: **not required** for v1 (light only)

---

## 14. API data mapping (for designers — labels on screen)

| UI label | API field (`GET /me/`) |
|----------|------------------------|
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

---

## 15. Out of scope (do not design in this app)

- Manager live map (CRM web only)
- Booking accept/start/complete (Partner app)
- Payment collection
- Client CRM data entry
- Blog / marketing website

---

## 16. Quick reference — all Phase 1 screens

| # | Screen | Route | Priority |
|---|--------|-------|----------|
| 01 | Splash | `/splash` | P0 |
| 02 | Login | `/login` | P0 |
| 03 | GPS Consent | `/consent` | P0 |
| 04 | Permission primer | `/permissions` | P0 |
| 05 | Home (Today) | `/home` | P0 |
| 06 | Check-in sheet | modal | P0 |
| 07 | Check-out sheet | modal | P0 |
| 08 | My Route | `/route` | P1 |
| 09 | Attendance | `/attendance` | P1 |
| 10 | Profile | `/profile` | P1 |
| 11 | Error states | global | P1 |

---

**Document version:** 1.0  
**Last updated:** June 2026  
**Owner:** Pest Control 99 — Staff Tracking project  
**Next step:** Open Google Stitch → paste prompts from Section 7 in order → export assets to `pest99_tracking_app/docs/stitch-exports/`
