# Booking Module Enhancement PRD

## Dynamic Service Configuration, AMC Scheduling & Upcoming Service Automation

## Objective

Enhance the **Create Booking** module to support dynamic service configuration, AMC scheduling, automatic visit generation, property-specific fields, and seamless integration with the existing CRM without breaking any current functionality.

---

# Scope

This enhancement applies only to the Booking module and its integration with:

* Create Booking
* View Bookings
* Upcoming Services
* Technician Assignment
* Notifications
* CRM Dashboard

The implementation must remain fully backward compatible.

---

# 1. Property Type

Add a new required field before the Service Selection section.

## Property Types

* Society
* Hotel
* Office
* Bungalow
* Villa
* School
* Warehouse
* Factory
* Shop
* Restaurant


---

# 2. Service Configuration

After selecting services, each selected service should create its own configuration card.

Example

Bed Bugs

* Service Type
* Area
* AMC Package (if applicable)
* Auto Generated Schedule
* Next Scheduled Visit

Cockroach

* Service Type
* Area
* AMC Package
* Auto Generated Schedule
* Next Scheduled Visit

Mosquito

* Service Type
* Area
* AMC Package
* Auto Generated Schedule
* Next Scheduled Visit

Each service should work independently.

---

# 3. Service Type

Each service must first ask:

* One Time Service
* AMC Service

If **One Time Service** is selected:

* No AMC package should be displayed.
* Only one visit is created.

If **AMC Service** is selected:

Display the available AMC packages for that service.

---

# 4. AMC Packages

## General Pest Control

Available Packages

* 3 Services
* 4 Services
* 6 Services

Schedule Rules

| Package    | Interval       |
| ---------- | -------------- |
| 3 Services | Every 4 Months |
| 4 Services | Every 3 Months |
| 6 Services | Every 2 Months |

Automatically generate all future service visits.

---

## Rodent Control

Available Packages

* 3 Services
* 4 Services
* 6 Services
* 12 Services

| Package     | Interval       |
| ----------- | -------------- |
| 3 Services  | Every 4 Months |
| 4 Services  | Every 3 Months |
| 6 Services  | Every 2 Months |
| 12 Services | Every Month    |

Automatically generate all future visits.

---

## Mosquito Control

Available Packages

* 3 Services
* 4 Services
* 6 Services
* 12 Services

| Package     | Interval       |
| ----------- | -------------- |
| 3 Services  | Every 4 Months |
| 4 Services  | Every 3 Months |
| 6 Services  | Every 2 Months |
| 12 Services | Every Month    |

Automatically generate all future visits.

---

## Cockroach / Ants

Support

* One Time Service
* AMC Service

AMC Packages

* 3 Services
* 4 Services
* 6 Services
* 12 Services

Use the same scheduling logic as General Pest Control.

---

## Bed Bugs

Support

* One Time Service

Keep backend flexible for future AMC support.

---

# 5. Termite Treatment

Termite must NOT behave like a normal AMC.

User selects

One Time Treatment

Immediately after booking creation, the system should automatically create:

* Treatment Visit
* Check-up 1 (After 6 Months)
* Check-up 2 (After 12 Months)
* Check-up 3 (After 18 Months)
* Check-up 4 (After 24 Months)

Total Records

* 1 Treatment
* 4 Check-up Visits

Total = 5 Visit Records

No manual scheduling is required.

---

# 6. Auto Visit Generation

When a booking is saved:

The backend should automatically generate all scheduled visits based on:

* Booking Date
* Selected Service
* Selected Package

All visits should be stored in the database immediately.

No cron jobs are required.

---

# 7. Next Scheduled Visit (NEW)

Every service configuration card must display the **Next Scheduled Visit** after the schedule is generated.

Example

Bed Bugs

* Service Type: AMC
* Package: 4 Services
* Area: 2 BHK

Next Scheduled Visit

10 October 2026

Cockroach

Next Scheduled Visit

10 October 2026

Rodent

Next Scheduled Visit

10 September 2026

Mosquito

Next Scheduled Visit

10 August 2026

Termite

Next Scheduled Visit

15 January 2027

This should update automatically after every completed visit.

---

# 8. Upcoming Services Module

All automatically generated visits must appear inside:

View Bookings

↓

Upcoming Services

without any manual intervention.

---

# 9. Visit Type Badge

Every upcoming visit should have a badge.

Examples

General Pest Control

AMC VISIT

Rodent

RODENT AMC

Mosquito

MOSQUITO AMC

Cockroach

COCKROACH AMC

Termite

TERMITE CHECK-UP

This helps technicians quickly identify the visit type.

---

# 10. Upcoming Services Table

Add the following columns where applicable:

* Booking ID
* Customer
* Service Name
* Visit Number
* Total Visits
* Visit Type
* Scheduled Date
* Next Scheduled Date
* Technician
* Status

Example

Booking #1025

Service

Rodent

Visit

2 of 6

Visit Type

RODENT AMC

Scheduled Date

15 September 2026

Next Scheduled Date

15 November 2026

Status

Upcoming

---

# 11. View Booking Screen

Inside each booking, display the complete service timeline.

Example

General Pest Control

Visit 1

Completed

15 July 2026

Visit 2

Upcoming

15 September 2026

Visit 3

Upcoming

15 November 2026

Visit 4

Upcoming

15 January 2027

Next Scheduled Visit

15 September 2026

---

# 12. Completion Logic

When a technician marks a visit as completed:

* Mark current visit as Completed.
* Automatically update the Next Scheduled Visit.
* Display the next pending visit date.
* Do not create duplicate visits.
* Do not modify completed records.

---

# 13. Database Structure

Each generated visit should contain:

* Booking ID
* Parent Booking
* Customer
* Service Name
* Service Type
* Visit Number
* Total Visits
* Visit Type
* Scheduled Date
* Next Scheduled Date
* Status
* Technician
* Completed Date
* Completion Notes
* Auto Generated (Yes/No)

---

# 14. Status

Support the following statuses:

* Upcoming
* Assigned
* In Progress
* Completed
* Missed
* Cancelled
* Rescheduled

---

# 15. Business Rules

## One Time Service

Generate only one visit.

---

## AMC Service

Generate all future visits immediately after booking creation.

---

## Termite Treatment

Generate:

* Treatment Visit
* Check-up 1
* Check-up 2
* Check-up 3
* Check-up 4

Automatically schedule them at 6-month intervals over 2 years.

---

## Rescheduling

Rescheduling one visit must only affect that specific visit.

Completed visits should never be modified.

---

# 16. Technical Requirements

The implementation must not break any existing functionality.

Existing modules that must continue to work:

* Create Booking
* Edit Booking
* View Booking
* Pending
* In Process
* Done
* Upcoming Services
* Technician Assignment
* CRM Dashboard
* Quotations
* Invoices
* Reports
* Notifications
* SMS
* WhatsApp
* Existing APIs

The scheduling engine should be modular and configuration-driven, allowing future support for new frequencies (weekly, fortnightly, quarterly, yearly, etc.) without changing core business logic.
