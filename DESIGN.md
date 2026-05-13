# Pest 99 Partner App — DESIGN.md

## Product Overview

Pest 99 Partner App is a modern technician management mobile application for pest control field staff.

The app is designed for:
- Technicians
- Technician Admins

Purpose:
- Accept assigned bookings
- Manage service visits
- Navigate to client location
- Complete services
- Track performance
- Handle service calls and complaint calls

Design style should feel like:
- Urban Company Partner
- Porter Partner
- Zomato Delivery Partner
- Clean enterprise service app

---

# Design Principles

- Mobile-first
- Fast and clean UI
- Minimal clutter
- Large tap targets
- Easy for field technicians
- One-hand usability
- Lightweight interface
- High readability outdoors

---

# Design Language

## Theme

Modern business service application.

### Mood
- Professional
- Trustworthy
- Clean
- Fast
- Operational

---

# Color System

## Primary Green
`#1B8E3D`

## Light Green
`#E8F5EC`

## Background
`#F7FAF8`

## Surface
`#FFFFFF`

## Border
`#E4E7EC`

## Text Primary
`#111827`

## Text Secondary
`#6B7280`

## Success
`#16A34A`

## Warning
`#F59E0B`

## Danger
`#EF4444`

## Blue
`#2563EB`

---

# Typography

## Font Family
- Manrope
- Inter

## Font Weights
- 400
- 500
- 600
- 700
- 800

## Style
- Modern
- High readability
- Slightly bold titles

---

# Spacing System

## Base Radius
16px

## Button Radius
14px

## Card Padding
16px

## Screen Padding
20px

## Section Gap
20px

---

# Shadows

Very soft shadows only.

No heavy neumorphism.

Cards should feel lightweight.

---

# Icons

Use:
- Material Symbols Rounded
OR
- Cupertino icons

Icon style:
- Rounded
- Minimal
- Modern

---

# App Structure

## Main Navigation

Bottom Navigation Tabs:

1. Bookings
2. Accepted
3. Completed
4. Profile

---

# Screen Designs

---

# 1. Splash Screen

## Layout
Centered logo.

Green full background.

### Components
- Pest 99 shield logo
- App name
- Loading indicator

### Feel
Premium startup screen.

---

# 2. Login Screen

## Layout
Centered vertical form.

### Components
- Welcome text
- Phone number field
- Password field
- Login button
- Register text button

### Design
- White card
- Rounded fields
- Large CTA button

---

# 3. Register Screen

## Fields
- Full Name
- Mobile Number
- Password
- User Type Dropdown

Dropdown:
- Technician
- Technician Admin

### CTA
Create Account

---

# 4. Home / Bookings Screen

## Header
- Technician profile image
- Name
- Notification icon

## Tabs
Top segmented tabs:
- Bookings
- Accepted

## Booking Cards

### Card Layout
- Booking ID badge
- Pest Type
- Booking Type Tag
- Area
- Date
- Time

### Actions
- Reject button
- Accept button

### Important
Customer number hidden before accept.

---

# Booking Type Tags

## Booking
Green

## Service Call
Purple

## Complaint Call
Red

## Follow-up
Blue

## AMC Visit
Orange

---

# 5. Accepted Screen

## Card Includes
- Customer Name
- Address
- Phone
- Date & Time
- Pest Type

## Actions
- Call
- Maps
- View Details
- End Service

---

# 6. Booking Detail Screen

## Sections

### Customer Information
- Name
- Mobile
- Address

### Property Information
- Property Type
- BHK
- Notes

### Service Information
- Pest Type
- Treatment Type
- Booking Type

### Schedule
- Date
- Time

### Pricing
- Service Amount

---

# Sticky Bottom CTA

Large green button:
"End Service"

---

# 7. End Service Modal

## Modal Style
Rounded bottom sheet.

### Fields
Payment Mode Dropdown:
- Cash
- Online

### Actions
- Confirm
- Cancel

---

# 8. Completed Screen

## Completed Card
- Booking ID
- Customer Name
- Pest Type
- Payment Mode
- Completed Date

---

# 9. Profile Screen

## Top Section
- Large profile image
- Name
- Mobile
- User Role

## Stats Cards
- Total Jobs
- Completed
- Ratings
- Service Calls

## Actions
- Edit Profile
- Logout

---

# 10. Notifications Screen

## Notification Types
- New Booking
- Complaint Call
- Reminder
- Service Call

---

# Empty States

Need dedicated empty screens.

Examples:
- No bookings assigned
- No completed jobs
- No internet

Use:
- Soft illustration
- Minimal messaging

---

# Loading States

Use:
- Skeleton cards
- Shimmer loading
- Smooth transitions

---

# Animations

## Required
- Smooth tab switching
- Button press feedback
- Bottom sheet animation
- Card fade-in

Duration:
200–300ms only.

---

# Buttons

## Primary Button
Green filled.

## Secondary
Outlined.

## Danger
Red outline.

Large touch area.

---

# Card Style

- Rounded 18px
- White background
- Thin border
- Minimal shadow

---

# Input Fields

Rounded input fields.

Soft borders.

Large touch targets.

---

# Responsive Behavior

Design for:
- Android
- iPhone
- Small devices

Must work perfectly on:
360px width screens.

---

# UX Priorities

## Most Important
- Fast booking handling
- Easy acceptance flow
- Quick calling
- Quick maps access
- Fast completion

Technicians should operate app within seconds.

---

# App Personality

The app should feel:
- Operational
- Reliable
- Fast
- Premium
- Enterprise-grade

NOT:
- childish
- over-animated
- cluttered

---

# Final Goal

The final design should look production-ready and investor-ready.

High-end field service management mobile app.