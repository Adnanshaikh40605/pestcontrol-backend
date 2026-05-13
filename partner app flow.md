# Partner App Backend + API Architecture Flow

```text
PROJECT GOAL:
Create complete Partner App backend system inside Django CRM project.

App Name:
partner

Purpose:
Technicians use mobile app to:
- login
- accept booking
- reject booking
- view details
- call customer
- open maps
- start service
- end service
- view completed jobs
- view profile
- view ratings
- view earnings
```

---

# 1. DJANGO APP STRUCTURE

```bash
partner/
│
├── models.py
├── apis.py
├── serializers.py
├── urls.py
├── permissions.py
├── services.py
├── utils.py
├── admin.py
├── apps.py
```

---

# 2. PARTNER USER FLOW

## Registration

Technician creates account using:

* Full Name
* Mobile Number
* Password
* User Type

Dropdown:

* technician
* technician_admin

---

## Login

Login with:

* mobile number
* password

Backend returns:

* JWT Access Token
* Refresh Token

---

# 3. DATABASE FLOW

## Partner Model

```python
class Partner(models.Model):
    ROLE_CHOICES = (
        ('technician', 'Technician'),
        ('technician_admin', 'Technician Admin'),
    )

    full_name
    mobile
    password
    role
    profile_image
    is_active
    created_at
```

---

# 4. BOOKING FLOW

## CRM Admin Side

When booking assigned:

```python
booking.partner = technician
booking.partner_status = "pending"
```

Then automatically visible in:

APP → Available Bookings Tab

---

# 5. APP TAB FLOW

# TAB 1 → BOOKINGS

Shows:
Pending assigned bookings.

Data:

* booking id
* pest type
* location
* schedule date
* time
* service type
* priority

Buttons:

* Accept Booking
* Reject Booking

---

# TAB 2 → ACCEPTED

After technician accepts:

```python
partner_status = "accepted"
```

Show:

* accepted bookings only

Buttons:

* View Details
* Maps
* Call
* Start Service
* End Service

---

# TAB 3 → COMPLETED

After technician clicks:

```python
End Service
```

Show popup:

Payment Mode:

* Cash
* Online

Then:

```python
booking.status = "done"
payment_mode = selected_value
completed_by = technician
completed_at = now()
```

Move booking to:
Completed Tab

---

# TAB 4 → PROFILE

Show:

* profile image
* name
* mobile
* total jobs
* completed jobs
* ratings
* service calls
* earnings

Options:

* Edit profile
* Bank details
* Earnings history
* Logout

---

# 6. BOOKING DETAIL SCREEN FLOW

## Show Full Details

Customer:

* name
* number
* address

Property:

* bhk
* property type

Service:

* pest type
* treatment type
* amc/service call/complaint

Payment:

* amount
* payment mode

Buttons:

* Call
* Open Maps
* End Service

---

# 7. IMPORTANT BUSINESS LOGIC

## AMC FLOW

AMC Follow-up visits:

* must NOT duplicate revenue

Main booking:
₹3000

Follow-up:
Included in AMC

---

# 8. API STRUCTURE

# AUTH APIs

## Register

```http
POST /api/partner/register/
```

Body:

```json
{
  "full_name": "Arshad",
  "mobile": "9876543210",
  "password": "123456",
  "role": "technician"
}
```

---

## Login

```http
POST /api/partner/login/
```

Response:

```json
{
  "access": "token",
  "refresh": "token",
  "partner": {}
}
```

---

# PROFILE APIs

## My Profile

```http
GET /api/partner/profile/
```

---

## Update Profile

```http
PUT /api/partner/profile/update/
```

---

# BOOKING APIs

## Available Bookings

```http
GET /api/partner/bookings/available/
```

Shows:

* assigned
* not accepted yet

---

## Accept Booking

```http
POST /api/partner/bookings/{id}/accept/
```

---

## Reject Booking

```http
POST /api/partner/bookings/{id}/reject/
```

---

## Accepted Bookings

```http
GET /api/partner/bookings/accepted/
```

---

## Completed Bookings

```http
GET /api/partner/bookings/completed/
```

---

## Booking Detail

```http
GET /api/partner/bookings/{id}/
```

---

## End Service

```http
POST /api/partner/bookings/{id}/complete/
```

Body:

```json
{
  "payment_mode": "cash"
}
```

OR

```json
{
  "payment_mode": "online"
}
```

---

# 9. FLUTTER CONNECTION FLOW

# LOGIN SCREEN

Connect:

```http
POST /api/partner/login/
```

Save:

* access token

---

# BOOKINGS SCREEN

Connect:

```http
GET /api/partner/bookings/available/
```

---

# ACCEPT BUTTON

Connect:

```http
POST /api/partner/bookings/{id}/accept/
```

---

# COMPLETED BUTTON

Connect:

```http
POST /api/partner/bookings/{id}/complete/
```

---

# PROFILE SCREEN

Connect:

```http
GET /api/partner/profile/
```

---

# 10. SWAGGER FLOW

IMPORTANT:
Need separate Swagger only for Partner APIs.

URL:

```bash
/api/partner/docs/
```

Only show:

* partner APIs
* mobile app APIs

Do NOT show:

* admin APIs
* CRM APIs

---

# 11. SWAGGER ORGANIZATION

Group APIs properly:

## Authentication

* Register
* Login

## Bookings

* Available
* Accept
* Reject
* Detail
* Complete

## Profile

* My profile
* Update profile

---

# 12. SECURITY FLOW

Use:

* JWT Authentication

Partner can ONLY access:

* own bookings
* own profile

NOT other technician data.

---

# 13. DJANGO URL FLOW

## partner/urls.py

```python
urlpatterns = [
    path('register/', RegisterAPIView.as_view()),
    path('login/', LoginAPIView.as_view()),
    path('profile/', ProfileAPIView.as_view()),

    path('bookings/available/', AvailableBookingsAPIView.as_view()),
    path('bookings/accepted/', AcceptedBookingsAPIView.as_view()),
    path('bookings/completed/', CompletedBookingsAPIView.as_view()),

    path('bookings/<int:id>/', BookingDetailAPIView.as_view()),

    path('bookings/<int:id>/accept/', AcceptBookingAPIView.as_view()),
    path('bookings/<int:id>/reject/', RejectBookingAPIView.as_view()),
    path('bookings/<int:id>/complete/', CompleteBookingAPIView.as_view()),
]
```

---

# 14. IMPORTANT STATUS FLOW

```text
ADMIN ASSIGNS BOOKING
        ↓
AVAILABLE TAB
        ↓
TECHNICIAN ACCEPTS
        ↓
ACCEPTED TAB
        ↓
START SERVICE
        ↓
END SERVICE
        ↓
PAYMENT MODE POPUP
        ↓
DONE STATUS
        ↓
COMPLETED TAB
```

---

# 15. EXTRA IMPORTANT FEATURES

## Add realtime counters

Show:

* Available jobs count
* Accepted jobs count
* Completed jobs count

---

## Push Notifications

When new booking assigned:

Send notification:

```text
New booking assigned
```

---

# 16. RECOMMENDED TECH STACK

Backend:

* Django
* Django REST Framework
* SimpleJWT
* drf-spectacular

Frontend:

* Flutter

Maps:

* Google Maps

Notifications:

* Firebase FCM

---

# 17. IMPORTANT UI RULE

App must be:

* lightweight
* fast
* large buttons
* technician friendly
* simple navigation
* mobile first

Technicians should operate with:

* one hand
* low internet
* fast actions

```
```
