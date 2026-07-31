# DOH Pest e-Card — API Integration

For DOH CRM frontend (`dohadminpanel`) — **Pest e-Card** button on Agent Booking.

**Base URL:** `https://api.vacationbna.site`  
**Auth:** `Authorization: Bearer <access_token>` (same PestControl99 JWT as DOH Client Data)

---

## 1. Check if already sent

Call when the customer mobile is a valid 10-digit number.

```http
GET /api/e-card/sent-check/?mobile=9372792693
```

**Not sent:**
```json
{ "already_sent": false, "mobile": "9372792693" }
```

**Already sent:**
```json
{
  "already_sent": true,
  "mobile": "9372792693",
  "sent_at": "2026-07-30T10:45:00Z",
  "sent_by": "Rahul Sharma"
}
```

| Result | Button |
|--------|--------|
| `already_sent: false` | Enable |
| `already_sent: true` | Disable + show: `Pest e-Card already sent on {date} by {sent_by}` |

---

## 2. Mark as sent

Call **only after** WhatsApp send succeeds.

```http
POST /api/e-card/mark-sent/
Content-Type: application/json

{
  "mobile": "9372792693",
  "customer_name": "Adnan 1",
  "source": "doh_crm"
}
```

---

## 3. Flow

```text
Enter mobile → GET sent-check
  → already_sent true  → disable button
  → already_sent false → enable button
       → send WhatsApp (WhatsFlow)
       → POST mark-sent
       → disable button
```

Do not call `mark-sent` if WhatsApp send fails.
