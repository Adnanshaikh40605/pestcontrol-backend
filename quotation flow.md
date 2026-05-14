Based on your quotation samples, invoices, AMC services, residential + commercial formats, and the rat guard invoice format you shared  

You should build a complete **Quotation Management System** inside your CRM.

Your current quotations are:

* Residential
* Commercial
* One-time
* AMC
* Rat Guard
* Mosquito
* Rodent
* Society quotations
* Clinic quotations
* Multi-service quotations

Now create one centralized quotation system for all.

---

# COMPLETE QUOTATION SYSTEM FLOW

## 1. Add New Sidebar

```text
Quotation Management
```

Inside:

* Create Quotation
* All Quotations
* Pending Quotations
* Approved Quotations
* Converted Quotations
* Invoice Generator

---

# 2. CREATE QUOTATION FLOW

When staff clicks:

```text
+ Create Quotation
```

Open quotation form.

---

# 3. QUOTATION TYPES

Dropdown:

```text
- Residential
- Commercial
- Society
- Office
- Restaurant
- Clinic/Hospital
- AMC Package
- One Time Service
```

---

# 4. CUSTOMER DETAILS SECTION

Fields:

```text
Customer Name
Mobile Number
Email
Address
City
State
Pincode
Contact Person
Company/Society Name
```

---

# 5. AUTO GENERATED DETAILS

System automatically creates:

```text
Quotation No
Invoice No
Reference No
Created Date
Expiry Date
Created By Staff Name
```

Example:

```text
QT-2026-00125
INV-2026-00125
```

---

# 6. SERVICE SECTION

Staff can add multiple services dynamically.

Example:

| Service           | Frequency  | Qty | Rate | Total |
| ----------------- | ---------- | --- | ---- | ----- |
| Cockroach Control | 12 Service | 12  | 2500 | 30000 |
| Rodent Control    | 6 Service  | 6   | 1000 | 6000  |

Add button:

```text
+ Add Service
```

---

# 7. SERVICE MASTER SYSTEM

Create service master table.

Services:

```text
- Cockroach
- Bed Bug
- Rodent
- Termite
- Mosquito
- Rat Guard
- Ants
- Lizard
- General Pest Control
```

When selected:
auto fill:

```text
default frequency
default description
default scope
```

---

# 8. AMC FLOW (VERY IMPORTANT)

Fix your current revenue issue.

CURRENT WRONG:
3000 + 3000 + 3000

CORRECT FLOW:

AMC has:

* Contract Amount
* Service Visits

Example:

```text
AMC Total Contract = ₹3000
Visits = 3
```

System should show:

| Visit   | Revenue  |
| ------- | -------- |
| Visit 1 | Included |
| Visit 2 | Included |
| Visit 3 | Included |

NOT:

```text
₹3000 x 3
```

VERY IMPORTANT:

Store:

```text
contract_amount
visit_count
per_visit_charge
is_amc
```

Revenue rule:

```text
Only first/main invoice counts revenue.
Follow-up visits = Included in AMC.
```

---

# 9. SCOPE OF WORK SECTION

Large text editor.

Templates auto load based on service type.

Example from your quotation 

Like:

* Termite treatment scope
* Rodent monitoring
* Mosquito fogging
* General pest control

---

# 10. PAYMENT TERMS SECTION

Dropdown templates:

```text
- 50% Advance
- Full Advance
- After Completion
- Monthly Billing
- Per Service Billing
```

---

# 11. QUOTATION STATUS FLOW

Statuses:

```text
Draft
Sent
Approved
Rejected
Converted to Booking
Expired
```

---

# 12. PDF GENERATOR

Generate professional PDF automatically.

PDF should include:

* Logo
* Quotation No
* Date
* Customer details
* Service table
* Grand total
* Scope of work
* Terms
* Signature
* Stamp
* Bank details

Like your existing quotations.

---

# 13. WHATSAPP SHARE FLOW

Buttons:

```text
- Download PDF
- Share WhatsApp
- Send Email
```

WhatsApp message:

```text
Hello Sir/Madam,

Please find attached quotation from PestControl99.

Quotation No: QT-2026-00125

Thank you.
```

---

# 14. CONVERT TO BOOKING FLOW

Button:

```text
Convert to Booking
```

When clicked:

Automatically create booking with:

* customer details
* service details
* amount
* AMC details
* schedule

---

# 15. QUOTATION HISTORY

Customer profile should show:

```text
Previous Quotations
Invoices
Bookings
AMC History
```

---

# 16. BACKEND DATABASE FLOW

Create tables:

```text
Quotation
QuotationItem
QuotationScope
QuotationPaymentTerm
QuotationHistory
```

---

# 17. IMPORTANT BACKEND FIELDS

Quotation Model:

```text
quotation_no
invoice_no
customer_name
mobile
address
quotation_type
total_amount
grand_total
status
created_by
created_at
expiry_date
is_amc
visit_count
contract_amount
```

---

# 18. RESIDENTIAL FLOW

Simple one-page quotation.

Example:

* Cockroach
* Bed Bug
* Rodent

Like your clinic quotation 

---

# 19. COMMERCIAL FLOW

Advanced multi-service quotation.

Like:

* Society
* Office
* Building
* Hotel

Like your society quotation 

---

# 20. INVOICE FLOW

After payment:
generate invoice automatically.

Invoice includes:

```text
Bill No
Payment Mode
Paid Amount
Balance
GST
```

Like your invoice sample 

---

# 21. DASHBOARD COUNTS

Show:

```text
Total Quotations
Pending Quotations
Approved Quotations
Converted Quotations
Revenue from Quotations
```

---

# 22. STAFF LOGS

Track:

```text
who created quotation
who edited
who converted
who sent PDF
```

---

# 23. FUTURE AI FEATURE (OPTIONAL)

Later you can add:

```text
AI auto quotation generator
```

Example:
staff enters:

```text
2 BHK cockroach + rodent
```

AI creates full quotation automatically.

---

# MOST IMPORTANT FIX FOR YOUR CURRENT SYSTEM

DO THIS:

## AMC BOOKINGS SHOULD HAVE:

```text
Main Contract Booking
```

AND

```text
Follow-up Visits
```

Follow-up visits should NOT create new revenue.

Only:

* track service completion
* technician visit
* next service date

Revenue only from:

* original AMC contract

This is the correct business logic.
