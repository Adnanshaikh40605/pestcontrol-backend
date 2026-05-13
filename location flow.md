# Booking Location System Flow

You should create proper master-based location system in CRM.

Flow should work like this:

---

# 1. CREATE MASTER LOCATION SYSTEM

Already you have:

* Country
* State
* City
* Location

Good.

Now connect this with booking form.

---

# 2. BOOKING FORM FLOW

## By Default Auto Select

When Create Booking opens:

```text
Country → India
State → Maharashtra
City → Mumbai
```

already selected automatically.

Staff should not select every time.

---

# 3. LOCATION DROPDOWN FLOW

## Location field

Dropdown should load from API.

Example:

```text
Andheri East
Andheri West
Bandra West
Malad East
Malad West
Jogeshwari
Borivali
Powai
```

These come dynamically from:

```text
Master → Location
```

---

# 4. FRONTEND FLOW

# ON PAGE LOAD

Call API:

```http
GET /api/v1/master/locations/?city=Mumbai
```

Response:

```json
[
  {
    "id": 1,
    "name": "Andheri East"
  },
  {
    "id": 2,
    "name": "Bandra West"
  }
]
```

Then show inside dropdown.

---

# 5. BOOKING FORM STRUCTURE

## Booking Form

Fields:

```text
Country     → India (readonly/default)
State       → Maharashtra (readonly/default)
City        → Mumbai (readonly/default)
Location    → dropdown from API
Address     → manual text
```

---

# 6. IMPORTANT DATABASE FLOW

In booking model add:

```python
country
state
city
location
full_address
```

VERY IMPORTANT:

Do NOT save only address.

Save proper structured location.

---

# 7. OLD BOOKINGS ISSUE

Now your old job cards only have:

```text
full address
```

No location selected.

Need migration/update script.

---

# 8. BEST SOLUTION FOR OLD BOOKINGS

# OPTION 1 → AUTO LOCATION MATCHING SCRIPT (BEST)

Run backend script.

Script checks:

```text
address contains:
- andheri
- bandra
- malad
- jogeshwari
```

Then auto assign location.

---

# 9. EXAMPLE SCRIPT LOGIC

```python
if "andheri" in address.lower():
    location = "Andheri"

elif "bandra" in address.lower():
    location = "Bandra"

elif "malad" in address.lower():
    location = "Malad"
```

Then:

```python
booking.location = matched_location
booking.save()
```

---

# 10. BETTER ADVANCED SYSTEM

Create keyword mapping table.

Example:

| Keyword      | Location     |
| ------------ | ------------ |
| andheri east | Andheri East |
| andheri west | Andheri West |
| malad west   | Malad West   |
| jogeshwari   | Jogeshwari   |

Then script intelligently matches.

VERY GOOD for old data cleanup.

---

# 11. SUPER BEST SOLUTION (RECOMMENDED)

## Create Management Command

Example:

```bash
python manage.py auto_assign_locations
```

Script will:

* scan old bookings
* detect location from address
* auto assign nearest location
* save automatically

---

# 12. SAFE FLOW

Before saving:

Show report:

```text
Total bookings scanned: 1200
Matched successfully: 950
Not matched: 250
```

Then manually fix remaining.

---

# 13. UNMATCHED BOOKINGS FLOW

For unmatched bookings:

Show admin screen:

```text
Address → Select Location
```

Manual correction.

---

# 14. FUTURE BENEFITS

After proper location system:

You can build:

* technician area assignment
* nearest technician
* city analytics
* location revenue
* area-wise reports
* booking heatmaps
* zone management
* smart routing

---

# 15. BEST UI FLOW

## Create Booking

```text
Country   [India]
State     [Maharashtra]
City      [Mumbai]
Location  [Dropdown]
Address   [Textarea]
```

Location dropdown searchable.

Example:

```text
Search location...
```

---

# 16. VERY IMPORTANT

Do NOT allow free-text location typing.

Always use:

* master location dropdown

Otherwise:

* Andheri
* andheri
* Andheri East
* Andheri E

all become duplicate messy data.

---

# 17. API FLOW

## Get Locations

```http
GET /api/v1/locations/
```

---

## Filter by city

```http
GET /api/v1/locations/?city=Mumbai
```

---

# 18. PROPER FLOW FOR AI DEV

```text
Implement Master Location System in CRM.

Requirements:

1. In Create/Edit Booking:
- Country auto selected = India
- State auto selected = Maharashtra
- City auto selected = Mumbai

2. Location field:
- searchable dropdown
- load dynamically from master locations API
- only master locations selectable

3. Database:
Add structured fields:
- country
- state
- city
- location
- full_address

4. Create backend API:
GET /api/v1/locations/?city=Mumbai

5. Create automatic migration script for old bookings:
- scan address text
- detect matching area keywords
- auto assign location
- unmatched records remain manual

6. Create Django management command:
python manage.py auto_assign_locations

7. Prevent duplicate location names.

8. Use optimized indexed queries for future analytics.
```
