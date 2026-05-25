# Follow-up Reminders — How It Works (Staff Guide)

This document explains how **customer follow-up reminders** work in the Pest Control 99 CRM. It is written for office staff, sales, and managers — no technical background needed.

---

## 1. What is a reminder?

A **reminder** is a note in the system that says:

> “On this **date** (and optionally this **time**), call or follow up with this **customer** about something.”

Examples:

- Customer asked to call back tomorrow about price  
- Website lead said “call me Monday”  
- Need to check if they decided on AMC  

Reminders are linked to a **CRM Inquiry** or **Website Lead**, not to a completed booking by default.

---

## 2. What is **not** a reminder?

| Feature | What it is | Where you see it |
|--------|------------|------------------|
| **Upcoming Renewals** | AMC / society contract due dates (often auto-created for society jobs) | View Bookings → **Upcoming Renewals** tab, or **Renewals** page |
| **Upcoming Services** | Next scheduled service visit for AMC jobs | View Bookings → **Upcoming Services** tab |
| **Complaint calls** | Active complaint bookings | View Bookings → **Complaint Calls** tab |

Do not confuse **Renewals** with **Reminders**. Renewals are for contract/monthly service dates. Reminders are for “call this person back” follow-ups.

---

## 3. Very important: reminders do **not** pop up on your phone

The CRM **does not** send:

- Push notifications to staff phones  
- Automatic WhatsApp or SMS when reminder time arrives  
- Email alerts  

**You must open the CRM** and check the reminder list (see below). The red number on the sidebar is your cue — it is not an alarm on your personal phone.

---

## 4. How to **create** a reminder (main way — recommended)

### From CRM Inquiries or Website Leads

1. Log in to the CRM.  
2. Open **CRM Inquiries** or **Website Leads** (Inquiries).  
3. Find the customer row.  
4. Click the amber **Reminder** button (bell icon).  
5. Fill in the form:  
   - **Reminder date** (required)  
   - **Reminder time** (optional — default is 10:00 AM)  
   - **Short note** (required) — e.g. “Call for quotation”, “Follow up on AMC price”  
6. Click **Save Reminder**.

The system saves a **Reminder** record tied to that inquiry. The same customer can have more than one reminder on **different dates**, but you **cannot** save two **pending** reminders for the **same inquiry on the same date** (the system will show an error).

### From Job Cards → Reminders tab (edit only)

On **View Bookings → Reminders**, you can **edit**, **mark done**, or **delete** reminders. New reminders are normally created from the inquiry pages above.

You can also open the edit popup from the Reminders tab (pencil icon).

---

## 5. Where reminders **show up** (when they “come”)

Reminders do not “arrive” at a exact second like an alarm. They **appear in lists** when their date is relevant and staff open the CRM.

### A. Sidebar badge (red number)

- Next to **View Bookings** (or reminders count in the app), you may see a number.  
- This is the count of all **pending** reminders in the system (not only today).  
- When you mark reminders done, this number goes down.

### B. View Bookings → **Reminders** tab (main daily list)

1. Go to **View Bookings**.  
2. Click the **Reminders** tab (it may show the badge count).  
3. You see a table: date/time, customer name, mobile, source (CRM or Website), note, who created it, status.  

**What you see by default:**

- Only **pending** reminders (completed ones are hidden unless you change filters in the future).  
- Sorted by date and time.  
- **Today’s** reminders are highlighted (red background, “FOLLOW-UP TODAY”).  

**Search:** You can search by name, mobile, or note using the search bar on that page.

### C. Global search

If you search the customer in the top **global search**, matching reminders can appear as type **Reminder**. Clicking opens **View Bookings → Reminders**.

### D. Customer history

When you open a **client’s history**, past and pending reminders for that mobile number can appear in the **Reminders** section (includes reminders from inquiries and some older data stored on bookings).

---

## 6. When should staff **act** on a reminder?

| Situation | What to do |
|-----------|------------|
| Reminder date is **today** | Row is highlighted — call/WhatsApp the customer and complete follow-up. |
| Reminder date is **in the future** | It stays in the list; work on it on that day. |
| Reminder date was **yesterday** and still pending | It still shows in the pending list — treat as overdue and call. |
| After you spoke to the customer | Mark the reminder **done** (see section 7). |

**Time field:** If a time was set (e.g. 3:00 PM), use it as a guide for when to call. The system will **not** ring or notify you at that time automatically.

---

## 7. How to **finish** a reminder

On **View Bookings → Reminders**:

1. Find the row.  
2. Click the green **tick** button (**Mark Reminder Done**).  
3. Status becomes **completed** and it leaves the default pending list.  
4. The sidebar badge count updates.

You can also **delete** a reminder (trash icon) if it was created by mistake.

To go back to the original inquiry, use the blue **arrow** button (opens CRM Inquiries or Website Leads).

---

## 8. Other places reminder **fields** exist (optional / secondary)

These are **extra** fields on the record itself. They are **not** the same as the main **Reminders** tab list unless staff also used the **Reminder** button.

| Place | Fields | Purpose |
|-------|--------|---------|
| **Create CRM Inquiry** | Optional “Follow-up Reminder” date, time, note | Saved on the inquiry record when creating a lead |
| **Create / Edit Booking** | “Set Follow-up Reminder” date, time, note | Saved on the job card for booking-level follow-up |

**For daily team work, use the amber Reminder button** so everything appears in **View Bookings → Reminders** and in the sidebar count.

---

## 9. Simple daily routine for staff

```
Morning:
  1. Open CRM
  2. Check sidebar number for pending reminders
  3. Go to View Bookings → Reminders tab
  4. Work on rows marked "FOLLOW-UP TODAY" first
  5. Call/WhatsApp customer (use WhatsApp link on the row if needed)
  6. Mark reminder done when finished

During the day:
  - When a customer says "call me later", click Reminder on their inquiry
  - Set the date they asked for and a clear note

End of day:
  - Skim pending reminders — anything overdue still pending?
```

---

## 10. Flow diagram (simple)

```
Customer inquiry (CRM or Website)
        │
        ▼
Staff clicks "Reminder" → enters date, time, note → Save
        │
        ▼
Reminder stored as PENDING
        │
        ├── Shows in View Bookings → Reminders tab
        ├── Increases sidebar badge count
        └── Visible in global search / customer history
        │
        ▼
On reminder date: staff opens CRM, calls customer
        │
        ▼
Staff clicks "Mark Done" → status COMPLETED
        │
        └── Badge count decreases; row leaves pending list
```

---

## 11. Quick reference — staff vs system

| Question | Answer |
|----------|--------|
| Who creates reminders? | Staff, using the Reminder button on inquiries |
| When does it appear? | Immediately in the Reminders list (as pending) |
| When do we call? | On or after the **reminder date** (use time as a guide) |
| Do we get a phone alert? | **No** — open CRM and check the tab |
| Where is the main list? | **View Bookings → Reminders** |
| How do we close it? | Green tick → Mark done |
| Same customer, two dates? | Allowed (two separate reminders) |
| Same inquiry, same date twice? | **Not allowed** while both are pending |
| Renewals vs reminders? | Renewals = AMC/contract dates; Reminders = call-back follow-ups |

---

## 12. For managers / admins (technical summary)

| Item | Detail |
|------|--------|
| Main data | `Reminder` table — status `pending` or `completed` |
| API | `GET/POST /api/v1/reminders/`, `POST .../mark_complete/` |
| Badge | `GET /api/v1/dashboard/counts/` → `reminders` = count of pending reminders |
| CRM URL | Production CRM on Vercel; API `https://api.vacationbna.site` |
| Timezone | Dates/times in CRM UI use **India (Asia/Kolkata)** for “today” highlighting |

---

## 13. Common mistakes to avoid

1. **Only filling reminder fields on Create Booking** and expecting them on the Reminders tab — use the **Reminder** button on the inquiry instead.  
2. **Waiting for a phone notification** — there isn’t one; check the CRM daily.  
3. **Confusing Renewals tab with Reminders tab** — different purpose.  
4. **Forgetting to mark done** — pending count stays high and the same customer keeps appearing.  

---

*Last updated for Pest Control 99 CRM — staff training document.*
