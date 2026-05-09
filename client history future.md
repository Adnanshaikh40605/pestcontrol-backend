# ✅ Customer Global Search Flow for CRM

## 🎯 Goal

Create a:

```text id="0xg5fe"
Global Customer Search System
```

inside CRM.

When staff searches:

* mobile number
* customer name
* booking ID

system should instantly show:

```text id="0dwt3u"
complete customer history
```

like:

* all bookings
* all services
* service calls
* reminders
* feedback
* technician history
* revenue
* AMC history
* cancellations
* upcoming services

This should work like:

```text id="yxy4zi"
Urban Company CRM / Zomato Business CRM
```

---

# 🚨 CURRENT PROBLEM

Now search works only:

```text id="4ly1t2"
inside current tab
```

Example:

* Pending tab search only pending
* Done tab search only done

This is NOT good for CRM operations.

---

# ✅ NEW FLOW REQUIRED

# ADD NEW TOP GLOBAL SEARCH

Place at top navbar/header.

Example:

```text id="xq5n6h"
🔍 Search Customer / Mobile / Booking ID
```

This search should work:

```text id="q7jl6v"
globally across entire CRM
```

---

# ✅ SEARCH SHOULD FIND

# By Mobile Number

Example:

```text id="ocjlwm"
9821234567
```

---

# By Customer Name

Example:

```text id="ly5q0u"
SALMAN
```

---

# By Booking ID

Example:

```text id="9i5t89"
245
```

---

# By Address

Optional future feature.

---

# ✅ WHEN USER SEARCHES

Open:

```text id="5d2l7r"
Customer Detail Drawer / Modal / Page
```

---

# ✅ CUSTOMER DETAIL PAGE FLOW

# CUSTOMER PROFILE SECTION

Show:

| Field              | Value          |
| ------------------ | -------------- |
| Customer Name      | Salman         |
| Mobile             | 9821234567     |
| Alternate Number   | xxx            |
| Address            | Full address   |
| City               | Mumbai         |
| Total Bookings     | 8              |
| First Booking Date | date           |
| Last Service Date  | date           |
| Customer Type      | AMC / One-time |

---

# ✅ COMPLETE BOOKING HISTORY

Table:

| Booking ID | Service | Date | Status | Technician | Amount |
| ---------- | ------- | ---- | ------ | ---------- | ------ |

---

# ✅ SERVICE HISTORY SECTION

Show:

```text id="a8u1z4"
all services customer has taken
```

Example:

* Cockroach
* Bed Bug
* Termite

---

# ✅ UPCOMING SERVICES

Show:

```text id="d90m3t"
future AMC visits
```

---

# ✅ FEEDBACK HISTORY

Show:

| Rating | Remark | Technician | Date |
| ------ | ------ | ---------- | ---- |

---

# ✅ REMINDERS HISTORY

Show:

```text id="3d0cc6"
all reminders created for customer
```

---

# ✅ REVENUE SUMMARY

Show:

| Metric        | Value   |
| ------------- | ------- |
| Total Revenue | ₹25,000 |
| Paid Services | 10      |
| AMC Revenue   | ₹15,000 |

---

# ✅ TECHNICIAN HISTORY

Show:

```text id="3u1l4n"
which technicians visited customer
```

---

# ✅ QUICK ACTION BUTTONS

Buttons:

```text id="bq2bzw"
Create Booking
Create Reminder
Call Customer
WhatsApp Customer
View Feedback
View Invoice
```

---

# ✅ SEARCH EXPERIENCE

# As User Types

Example:

```text id="7t7z4p"
98
982
9821
```

Show live suggestions dropdown.

---

# Example Dropdown

| Result              | Type     |
| ------------------- | -------- |
| Salman - 9821234567 | Customer |
| Booking #245        | Booking  |
| Salman AMC          | Service  |

---

# ✅ BACKEND API FLOW

# Global Search API

```text id="98y0ej"
GET /api/v1/global-search/?q=salman
```

---

# Customer Detail API

```text id="cikjlwm"
GET /api/v1/customer-history/{id}/
```

---

# ✅ DATABASE QUERY FLOW

Search across:

```python id="16jwsv"
customer_name
mobile
booking_id
address
```

using:

```python id="57w1i7"
icontains
```

---

# ✅ IMPORTANT PERFORMANCE OPTIMIZATION

Use:

```python id="7odjlwm"
select_related()
prefetch_related()
```

to avoid slow CRM loading.

---

# ✅ UI/UX RECOMMENDATION

# BEST OPTION

Create:

```text id="zyf3d6"
right-side sliding drawer
```

instead of full page reload.

Like:

* Facebook business CRM
* HubSpot
* Urban Company

Fast and modern.

---

# ✅ ADD CUSTOMER TAGS

Example:

| Tag             | Meaning            |
| --------------- | ------------------ |
| AMC Client      | yearly client      |
| Repeat Customer | multiple bookings  |
| High Revenue    | VIP                |
| Low Rating      | complaint customer |

---

# ✅ FUTURE FEATURES

# WhatsApp Integration

Quick message:

```text id="3t4nhf"
Your next service is tomorrow.
```

---

# Call Logs

Track customer communication.

---

# Payment History

Track total payments.

---

# 🚀 FINAL AI DEV PROMPT

```text id="rzj1rx"
Create Global Customer Search System in CRM.

Current issue:
Search only works inside current booking tab.

Need new global CRM search system.

Requirements:

1. Add dedicated global search bar in top header/navbar.

Placeholder:
"Search Customer / Mobile / Booking ID"

2. Search should work globally across:
- Pending
- On Process
- Done
- Upcoming Services
- Reminders
- Feedbacks

3. Search by:
- customer name
- mobile number
- booking ID
- address

4. When searching:
show live dropdown suggestions.

5. On selecting customer:
open complete customer history page/drawer.

6. Customer history should show:
- customer details
- booking history
- service history
- AMC history
- reminders
- feedback ratings
- technicians history
- revenue summary
- upcoming services

7. Add quick actions:
- create booking
- create reminder
- call
- WhatsApp
- invoice

8. Backend APIs:
- global search API
- customer history API

9. Use optimized Django ORM:
- select_related
- prefetch_related
- annotate

10. UI/UX:
Modern CRM style.
Fast loading.
Responsive.
Professional business dashboard.
Prefer right-side drawer instead of page reload.
```
