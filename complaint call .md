# ✅ Complaint Call Management Flow — Complete CRM System

## 🎯 Goal

When customer calls and says:

```text id="0x8w3v"
service not good
problem still there
technician issue
need revisit
```

staff should quickly:

1. Search customer globally
2. Create complaint call
3. Complaint booking auto-create
4. Show inside dedicated:

```text id="j8znv0"
Complaint Calls Tab
```

This should work like:

* Urban Company Support CRM
* Zomato Complaint Ticket
* Service Center CRM

---

# ✅ COMPLETE FLOW

# STEP 1 — CUSTOMER CALLS

Customer says:

```text id="z0kq2o"
Cockroach still coming
service not effective
need revisit
```

---

# STEP 2 — STAFF GLOBAL SEARCH

Staff searches:

```text id="k4n1vt"
mobile number
customer name
booking ID
```

inside:

```text id="y90i7f"
Global CRM Search
```

---

# STEP 3 — CUSTOMER HISTORY OPENS

Customer drawer/page opens.

Now show new button:

```text id="lx4jlt"
🚨 Create Complaint Call
```

---

# STEP 4 — COMPLAINT POPUP/MODAL

Open modal.

Fields:

| Field                     | Type            |
| ------------------------- | --------------- |
| Complaint Type            | dropdown        |
| Complaint Note            | textarea        |
| Priority                  | low/medium/high |
| Revisit Date              | date            |
| Assign Technician         | optional        |
| Complaint Against Booking | auto selected   |

---

# ✅ COMPLAINT TYPES

Dropdown:

```text id="crjv4m"
Service Not Effective
Cockroach Still Coming
Bed Bugs Still Active
Need Revisit
Technician Behavior
Chemical Smell Issue
Incomplete Service
Warranty Claim
AMC Complaint
Other
```

---

# STEP 5 — CREATE COMPLAINT BOOKING

After submit:

System should:

## Create:

```text id="xizjlwm"
Complaint Service Booking
```

NOT normal booking.

---

# ✅ IMPORTANT DATABASE FLOW

# Add Fields in JobCard

```python id="k18djj"
is_complaint_call = models.BooleanField(default=False)

complaint_parent_booking = models.ForeignKey(
    'self',
    null=True,
    blank=True,
    on_delete=models.SET_NULL
)

complaint_status = models.CharField(
    max_length=50,
    default='open'
)

complaint_note = models.TextField(blank=True)
```

---

# ✅ FLOW RELATION

Example:

## Original Booking

```text id="qnyhj9"
Booking ID: 245
Cockroach AMC
DONE
```

---

## Complaint Call

```text id="u0ts1f"
Booking ID: 301
Complaint Against: 245
Type: Complaint Call
Status: Pending
```

---

# 🚨 IMPORTANT

Complaint booking should NEVER duplicate customer manually.

System auto-copy:

* customer name
* mobile
* address
* service type

from original booking.

---

# ✅ NEW CRM TAB

Add new tab:

```text id="y3t2fk"
Complaint Calls
```

inside:

```text id="v9htf3"
View Bookings
```

---

# ✅ COMPLAINT TAB SHOULD SHOW

| Column            | Value                     |
| ----------------- | ------------------------- |
| Complaint ID      | booking ID                |
| Parent Booking ID | original booking          |
| Customer          | name                      |
| Service           | service type              |
| Complaint Type    | issue                     |
| Complaint Date    | created                   |
| Technician        | assigned                  |
| Priority          | High/Medium               |
| Status            | Open/In Progress/Resolved |
| Revisit Date      | scheduled                 |

---

# ✅ COMPLAINT STATUS FLOW

| Status      | Meaning             |
| ----------- | ------------------- |
| Open        | complaint created   |
| Assigned    | technician assigned |
| In Progress | technician working  |
| Resolved    | issue solved        |
| Closed      | customer confirmed  |

---

# ✅ TECHNICIAN FLOW

Complaint booking should also appear in:

```text id="ft8v0u"
Technician Partner App
```

with special badge:

```text id="o4ww9x"
🚨 Complaint Call
```

---

# ✅ PRIORITY COLORS

| Priority | Color  |
| -------- | ------ |
| High     | Red    |
| Medium   | Orange |
| Low      | Yellow |

---

# ✅ AUTOMATIC RULES

# If rating <= 2 stars

System can auto-suggest:

```text id="d7hkwq"
Create Complaint Call
```

---

# If AMC Client

Complaint call should NOT affect AMC cycle.

---

# ✅ IMPORTANT BUSINESS RULE

Complaint calls should be counted separately from:

```text id="mz6jlwm"
normal bookings
service calls
renewals
```

---

# ✅ REPORTING

Add complaint analytics:

| Metric                    | Description          |
| ------------------------- | -------------------- |
| Total Complaints          | total                |
| Resolved Complaints       | fixed                |
| Pending Complaints        | active               |
| Technician Complaint Rate | technician quality   |
| Repeat Complaints         | same customer issues |

---

# ✅ TECHNICIAN PERFORMANCE CONNECTION

If technician gets too many complaints:

show alert in:

```text id="9t9w6k"
Technician Reports
```

---

# ✅ CUSTOMER HISTORY FLOW

Inside customer profile show:

```text id="juxjlwm"
Complaint History
```

Example:

| Date   | Complaint       | Status   |
| ------ | --------------- | -------- |
| 10 May | Cockroach issue | Resolved |

---

# ✅ BACKEND APIs

# Create Complaint

```text id="j9xqj6"
POST /api/v1/complaints/create/
```

---

# Complaint List

```text id="lh2f1t"
GET /api/v1/complaints/
```

---

# Customer Complaints

```text id="yz97s0"
GET /api/v1/customers/{id}/complaints/
```

---

# Complaint Analytics

```text id="vjlwm7"
GET /api/v1/complaints/stats/
```

---

# ✅ UI/UX DESIGN

Complaint rows should look different.

Example:

* red badge
* warning icon
* complaint tag

---

# ✅ SMART AUTOMATION IDEAS

# Auto WhatsApp

After complaint created:

```text id="t2u4k5"
Your complaint has been registered.
Our team will contact you shortly.
```

---

# Auto Escalation

If complaint not resolved in:

```text id="76iv6m"
48 hours
```

mark:

```text id="zjlwm0"
High Priority
```

---

# 🚀 FINAL AI DEV PROMPT

```text id="djlwm5"
Create complete Complaint Call Management System in CRM.

Goal:
When customer calls and complains about service quality, staff should quickly create complaint call booking from global search.

Requirements:

1. Add new tab:
"Complaint Calls"

inside View Bookings section.

2. In Global Customer Search:
Add button:
"Create Complaint Call"

3. On click:
Open complaint modal with:
- complaint type
- complaint note
- priority
- revisit date
- technician assignment

4. After submit:
Automatically create complaint booking.

5. Complaint booking must:
- auto-copy customer details
- auto-copy service details
- link original booking
- create unique complaint booking ID

6. Add database fields:
- is_complaint_call
- complaint_parent_booking
- complaint_status
- complaint_note

7. Complaint bookings should appear:
- Complaint Calls tab
- Technician app
- Customer history

8. Add complaint statuses:
- Open
- Assigned
- In Progress
- Resolved
- Closed

9. Add complaint analytics:
- total complaints
- resolved complaints
- technician complaint rate
- repeat complaints

10. UI/UX:
Professional CRM complaint system.
Complaint rows should have:
- warning badge
- red highlight
- priority color

11. Add APIs:
- create complaint
- complaint list
- customer complaint history
- complaint analytics

12. Important:
Complaint calls must NOT duplicate incorrectly.
Must link with original booking properly.

13. Add technician integration:
Complaint call should show in partner app with:
"🚨 Complaint Call" badge.
```
z