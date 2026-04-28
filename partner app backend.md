Good move 👍 — you’re basically building a **Technician Partner App + API layer** on top of your CRM.
Don’t create a separate project. Do it inside the same Django backend (clean + scalable).

I’ll give you a **clear architecture + exact plan** so you don’t mess this up.

---

# 🧠 BIG PICTURE

You will have:

### 1. CRM (already done)

* Staff creates bookings

### 2. Partner App (NEW – Flutter)

* Technicians login
* See assigned bookings
* Accept → Start → Complete

### 3. Backend (Django – same project)

* New app: `partner`
* APIs for mobile app

---

# ✅ STEP 1: CREATE NEW DJANGO APP

Inside your project:

```bash
python manage.py startapp partner
```

Add to settings:

```python
INSTALLED_APPS = [
    ...
    "partner",
]
```

---

# ✅ STEP 2: TECHNICIAN AUTH SYSTEM

## Extend Technician Model (or create if not exists)

```python
# partner/models.py

class Technician(models.Model):
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15, unique=True)
    password = models.CharField(max_length=255)

    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name
```

👉 Use **JWT Auth** (important for app)

Install:

```bash
pip install djangorestframework-simplejwt
```

---

# ✅ STEP 3: LINK JOBCARD WITH TECHNICIAN

In your existing JobCard model:

```python
technician = models.ForeignKey(
    "partner.Technician",
    null=True,
    blank=True,
    on_delete=models.SET_NULL
)

is_accepted = models.BooleanField(default=False)
accepted_at = models.DateTimeField(null=True, blank=True)
started_at = models.DateTimeField(null=True, blank=True)
completed_at = models.DateTimeField(null=True, blank=True)
```

---

# ✅ STEP 4: API STRUCTURE (VERY IMPORTANT)

Create file:

```bash
partner/apis.py
```

---

## 1. 🔐 LOGIN API

```python
@api_view(['POST'])
def login(request):
    phone = request.data.get("phone")
    password = request.data.get("password")

    tech = Technician.objects.filter(phone=phone).first()

    if not tech:
        return Response({"error": "Invalid"}, status=400)

    # (use hashed password in real)
    if tech.password != password:
        return Response({"error": "Wrong password"}, status=400)

    token = generate_jwt_token(tech)

    return Response({
        "token": token,
        "technician": {
            "id": tech.id,
            "name": tech.name,
            "phone": tech.phone
        }
    })
```

---

## 2. 📦 BOOKINGS LIST (NOT ACCEPTED)

```python
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def available_bookings(request):
    tech = request.user

    jobs = JobCard.objects.filter(
        technician=tech,
        is_accepted=False,
        status="pending"
    )

    return Response([...])
```

👉 Show only:

* Service name
* Area
* Location
* Date

❌ Hide:

* Full address
* Mobile number

---

## 3. ✅ ACCEPT BOOKING

```python
@api_view(['POST'])
def accept_booking(request, pk):
    job = JobCard.objects.get(id=pk)

    job.is_accepted = True
    job.accepted_at = timezone.now()
    job.status = "on_process"
    job.save()

    return Response({"message": "Accepted"})
```

---

## 4. 📍 ACCEPTED BOOKINGS

```python
@api_view(['GET'])
def accepted_bookings(request):
    tech = request.user

    jobs = JobCard.objects.filter(
        technician=tech,
        is_accepted=True,
        status="on_process"
    )

    return Response([...])
```

👉 Show FULL DATA:

* Address
* Mobile number
* Client name

---

## 5. ✅ COMPLETE SERVICE

```python
@api_view(['POST'])
def complete_booking(request, pk):
    job = JobCard.objects.get(id=pk)

    job.status = "done"
    job.completed_at = timezone.now()
    job.save()

    return Response({"message": "Completed"})
```

---

# ✅ STEP 5: URL CONFIG

```python
# partner/urls.py

urlpatterns = [
    path("login/", login),
    path("bookings/", available_bookings),
    path("accepted/", accepted_bookings),
    path("accept/<int:pk>/", accept_booking),
    path("complete/<int:pk>/", complete_booking),
]
```

---

# ✅ STEP 6: CRM SIDE CHANGE (IMPORTANT)

When technician accepts:

👉 Your CRM `/jobcards` should show:

* Technician name ✅
* Status → `On Process` ✅
* Tag → “Accepted” (optional)

---

# 📱 STEP 7: FLUTTER APP STRUCTURE

## Tabs:

### 1. BOOKINGS

* List of assigned jobs
* Limited info
* Button → **Accept**

---

### 2. ACCEPTED

* Full details
* Button → **End Service**

---

## Flow:

### Booking Page

→ Click Accept
→ Move to Accepted tab

---

### Accepted Page

→ Click End Service
→ Move to Done
→ Sync CRM

---

# 🎨 UI IDEA (KEEP SIMPLE + FAST)

## Booking Card

* Service: Cockroach
* Area: Jogeshwari
* Date: 27 Apr
* Button: ACCEPT

---

## Accepted Card

* Full address
* Call button 📞
* Map button 📍
* Button: END SERVICE

---

# 🔥 IMPORTANT LOGIC

| Action       | Result                              |
| ------------ | ----------------------------------- |
| Accept       | status → on_process                 |
| Complete     | status → done                       |
| CRM sync     | auto                                |
| Next service | auto trigger (your previous system) |

---

# ⚠️ DO NOT DO THIS

❌ Separate backend project
❌ Duplicate models
❌ Manual sync

---

# 🚀 FINAL RESULT

You will have:

✅ CRM (Admin + Staff)
✅ Partner App (Technicians)
✅ Real-time workflow
✅ Clean scalable system

---

If you want next step, I can give:

* Flutter UI code (ready screens)
* JWT setup properly
* API response format clean
* Push notification system (VERY useful)

Just tell 👍

