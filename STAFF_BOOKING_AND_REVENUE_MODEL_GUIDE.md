# PestControl99 — How the New Model Works

**For staff, supervisors, and management**  
Simple guide to the full project flow: bookings, technicians, money split, and who does what.

---

## 1. In one minute

| Topic | Rule |
|--------|------|
| Money split | **Technician 40%** · **Company 60%** |
| Who earns the 40% | **Partner** technicians only (not salaried staff) |
| Old bookings | Stay on the old system (no 40/60 change) |
| New system switch | Turned on with a company setting (`REVENUE_MODEL_V2`) |
| Settlement | Weekly (default) or monthly — after payout is **approved** |
| Offline rule | Partner offline **3 days** without approved leave → auto-**suspended** |

We did **not** build a second booking system. Everything still runs on the same **Job Card / Booking**.

---

## 2. Who is who

| Role | What they use | Main job |
|------|----------------|----------|
| **Customer** | Website / Customer app / Phone | Enquiry → book → pay → get service → rate |
| **CRM Staff** | PestControl CRM | Convert leads, create bookings, assign / send to app, approve payouts, settlements |
| **Partner Technician** | Partner mobile app | Go online, accept jobs, selfie start, complete, see earnings & leave |
| **Salaried Technician** | CRM / field work | Does jobs on salary — **not** paid from the 40% pool |
| **Admin / Management** | CRM + reports | Approves settlements, KYC/deposit, suspensions, overall revenue |

**Important:**  
CRM **Technician** record = company roster.  
Partner **App login** = mobile account.  
They must be **linked** for a partner to accept jobs and earn.

---

## 3. How money works (40 / 60)

### Simple formula

```
Job / visit value  →  40% technician pool  →  60% company
```

### Three booking types

| Type | How payout is calculated |
|------|---------------------------|
| **One-time** | 40% of the booking amount → goes to the partner who completed it |
| **AMC** | Full AMC package ÷ number of visits → each completed visit pays **40% of that visit value** |
| **Contractual** (society / hotel / office / commercial) | Same 40% of **that visit’s value**, then split **equally** among partner technicians who **attended** that visit |

### Extra rules staff must remember

1. **Salaried** technicians never take a share of the 40% pool.
2. If a contractual visit has **no eligible partner** attendees → payout is **Held** until crew/attendance is fixed.
3. Payout is created when the job is marked **Done / Completed** (partner app or CRM).
4. Partner does **not** get bank credit until CRM **approves** the payout and runs **Settlement → Paid**.
5. **Legacy** (old) bookings are marked **Legacy exempt** — no new 40/60 math on them.

### Tiny examples

**One-time ₹2,500**  
→ Technician pool ₹1,000 · Company ₹1,500  

**AMC ₹12,000 / 3 visits**  
→ Visit value ₹4,000 · Per visit tech pool ₹1,600  

**Society visit ₹10,000, 2 partner techs attended**  
→ Pool ₹4,000 · Each partner ₹2,000  

---

## 4. Full project flow (big picture)

```text
Customer enquiry (Website / CRM / Phone / Partner referral)
        ↓
Staff converts or creates Booking (Job Card)
        ↓
        ├─ Desk assign (CRM only)     → technician works offline/desk path
        └─ Send to Partner App        → open lineup for approved partners
                ↓
        Partner accepts (first one wins)
                ↓
        Start job (selfie) → Complete (Cash / Online)
                ↓
        Payment recorded + 40/60 payout created (Pending / Held)
                ↓
        CRM: Hold / Recalculate / Approve
                ↓
        Weekly/Monthly Settlement → Mark Paid → Excel if needed
```

---

## 5. Booking flow — step by step

### A) From website enquiry

1. Customer fills website form → appears in CRM as **Website Inquiry**.
2. Staff contacts customer, confirms price/date/address.
3. Staff clicks **Convert** → system creates a **Booking**.
4. Inquiry status becomes **Converted** (cannot convert twice).

### B) From CRM enquiry

1. Staff creates / receives CRM inquiry.
2. Staff converts → Booking with reference **CRM Inquiry**.
3. Same booking lifecycle as above.

### C) Direct booking (no enquiry)

1. Staff creates Job Card in CRM (or customer books in Customer App).
2. Booking starts as **Pending**.

### D) Getting a technician on the job

Staff has **two clean paths** (do not mix carelessly):

| Path | When to use | What happens |
|------|-------------|--------------|
| **Send to App** | Want partners to pick from phone | Booking enters **open lineup**. Any approved online partner can accept. First accept wins. |
| **Assign in CRM** | Desk / salaried / controlled assign | Status → **On Process**. Job is **removed** from app queue if it was sitting there. |

If a partner already **accepted / started** the job, CRM cannot desk-assign over them until that partner workflow is cleared.

### E) Partner job lifecycle

| Step | Partner app | CRM status |
|------|-------------|------------|
| Available | Shows in New Bookings | Pending + sent to app |
| Accept | Claimed by that tech | On Process |
| Start | Selfie required | In service |
| Complete | Cash / Online | Done + paid (if full collection) |

After complete, presence returns toward **Online** (ready for next job).

---

## 6. Contractual / society / commercial (crew lineup)

These jobs often need **more than one technician**.

### How lineup works

1. Lead technician = main assigned person (`technician` / partner who accepted).
2. Extra crew = added in CRM on the booking (**Crew & Payout** panel).
3. Mark who **checked in / completed / absent**.
4. On complete: **40% pool ÷ eligible partner attendees** (equal split).
5. Salaried crew can help on site but **do not** get a share from this pool.

### Staff checklist for contractual visits

- [ ] Correct job type / society / commercial category  
- [ ] Price / visit amount correct  
- [ ] Crew list complete before approve  
- [ ] Attendance marked for who actually worked  
- [ ] Recalculate payout if crew changed after complete  
- [ ] Approve only when amounts look right  

If crew is wrong → payout may be **Held** or unfair — fix attendance, then recalculate.

---

## 7. Technician perspective (Partner App)

### Daily work

1. Turn **Online** when available.  
2. See new bookings → **Accept** or leave for others.  
3. Reach site → **Start** with selfie.  
4. Finish → **Complete** and choose payment mode.  
5. Check **Earnings** (pending / approved / settled).  
6. Apply **Leave** when needed.

### Presence statuses (simple meaning)

| Status | Meaning |
|--------|---------|
| Online | Can take jobs |
| Offline | Not taking jobs |
| Busy | Accepted a job, not started |
| On Service | Job started |
| On Leave | Approved leave |
| Suspended | Blocked — cannot accept / change presence |

**Locked mid-job:** while Busy / On Service / On Leave, technician cannot casually flip Online/Offline themselves.

**Auto-suspend:** offline for **3 days** without approved leave → suspended. CRM must reactivate.

### What partners see vs don’t see

- They see their share and settlement status.  
- They do **not** approve their own payout.  
- Suspended accounts see a clear message and **empty** new-booking list.

---

## 8. Staff (CRM) perspective

### Daily ops

1. Clear website + CRM enquiries.  
2. Convert to booking with correct price, date, address, package (Standard / Premium when used).  
3. Either **Send to App** or **Assign**.  
4. Track On Process → Done.  
5. After complete: open booking → **Crew & Payout**.  
6. Hold if dispute · Recalculate if crew/price fixed · **Approve** when correct.  
7. On Settlements page: Build period → Approve → Mark Paid → Export Excel.

### Packages

- **Standard** — normal rate.  
- **Premium** — higher rate (customer app uses a markup when Premium is chosen).

### Payment models on a booking

| Model | Meaning |
|-------|---------|
| Revenue sharing | 40/60 applies (default for new model bookings) |
| Salaried | Field salary only — no partner pool for this booking |

### Payout statuses (what you’ll see)

| Status | Meaning |
|--------|---------|
| Legacy exempt | Old booking — ignore new payout UI |
| Not applicable | New booking, not completed yet / or salaried path |
| Pending | Calculated — waiting for CRM approve |
| Held | Needs attention (often no eligible partners) |
| Approved | Ready for settlement batch |
| Paid | Included in a paid settlement |
| Cancelled | Payout cancelled |

---

## 9. Customer perspective

1. Enquiry on website **or** book in Customer App.  
2. Choose service / package / preferred date.  
3. Pay (app payment is currently a controlled stub until full gateway).  
4. Track booking status.  
5. After Done → rate the service.  
6. AMC customers can see AMC schedule / follow-up visits in history.

Customers do **not** see technician earnings or settlement screens.

---

## 10. Admin / management view

### What this project achieved

- One booking system (Job Card) for website, CRM, partner app, customer app.  
- Clear **40/60** partner economics.  
- Crew-based fair split for contractual sites.  
- App workflow: accept → selfie → complete.  
- Settlements with Excel for accounts.  
- Presence + leave + auto-suspend for discipline.  
- Old jobs protected (no sudden back-billing).

### Controls you care about

1. Feature flag on only after training + migrations.  
2. Approve payouts before money goes out.  
3. Settlement cadence weekly/monthly.  
4. Suspend / reactivate technicians.  
5. KYC / deposit fields on technician profiles.  
6. Reports: revenue sharing, settlements, technician activity.

### What “smooth” looks like

- Lead → booking in minutes.  
- No double bookings from double Convert.  
- App queue and desk assign don’t fight each other.  
- First partner accept locks the job.  
- Complete creates the right earning once.  
- Approve → settle → pay without disputes.

---

## 11. Do’s and Don’ts for staff

### Do

- Confirm price before Convert / Send to App.  
- Use **Send to App** for partner lineup; use **Assign** for desk control.  
- Mark contractual attendance honestly.  
- Approve payouts only after checking pool and crew.  
- Reactivate suspended techs only after issue is resolved.

### Don’t

- Convert the same enquiry twice (system blocks it).  
- Desk-assign over a job already accepted in the app.  
- Expect salaried techs to appear in the 40% split.  
- Change share % after approve without knowing it is locked.  
- Promise partners payment before settlement is **Paid**.

---

## 12. Quick FAQ

**Q: Does every completed job pay 40%?**  
A: Only when the new model is ON, the booking is not legacy, and payment model is revenue sharing. Salaried bookings do not.

**Q: Two partners tap Accept — who gets it?**  
A: The first successful accept. The other sees “already accepted”.

**Q: Customer paid in app, technician also collects?**  
A: System avoids double full payment posting. Staff should still check payment status on the booking.

**Q: AMC follow-up visits — pay again?**  
A: Visit-level 40% of visit value applies on completed visits under the new model; package total is spread across planned visits.

**Q: Where do I pay technicians?**  
A: CRM → Settlements → build period → approve → mark paid (export Excel for accounts).

---

## 13. Simple status map

| Stage | Customer | Staff CRM | Partner App |
|-------|----------|-----------|-------------|
| Enquiry | Submitted | New / Contacted | — |
| Converted | Waiting schedule | Booking Pending | — |
| Sent to app | Waiting tech | In app queue | New booking |
| Accepted | Tech assigned | On Process | Accepted |
| Started | In progress | In service | On service + selfie |
| Completed | Done / rate | Done + payout pending | Completed + earning |
| Settled | — | Settlement paid | Shows settled |

---

## 14. Bottom line for the team

1. **Same booking** for everyone — website, CRM, apps.  
2. **Partners earn 40%**, company keeps **60%**.  
3. **Contractual** = same 40%, shared equally by partners who attended.  
4. **Staff control** convert, assign/send, approve, settle.  
5. **Technicians** work through the app with clear status and earnings.  
6. **Old jobs** stay untouched.  
7. Run the new model only when the company flag is ON and the team is trained.

If something looks wrong on a live booking: check **price → crew/attendance → payout status → settlement** in that order before changing anything else.

---

*Document for internal training. Matches the locked Revenue Model v2 rules (40/60, 3-day auto-suspend, weekly/monthly settlements, Job Card–based flow).*
