# Revenue Model v2 — OpenAPI sketches (Phase 0)

Locked constants (`core/revenue_constants.py`):

| Constant | Value |
|----------|-------|
| Technician share | **40%** |
| Company share | **60%** |
| Default settlement cadence | **weekly** (monthly supported) |
| Auto-suspend offline days | **3** (no approved leave) |

Feature flag: `REVENUE_MODEL_V2` (env / settings, default `false`).

---

## CRM (`/api/v1/`) — auth: CRM JWT

### Feature flags
- `GET /api/v1/feature-flags/` → `{ "REVENUE_MODEL_V2": true|false }`

### JobCard participants (crew)
- `GET /api/v1/jobcards/{id}/participants/`
- `POST /api/v1/jobcards/{id}/participants/` body: `{ "technician_id", "role": "lead|crew" }`
- `PATCH /api/v1/jobcards/{id}/participants/{pid}/`
- `DELETE /api/v1/jobcards/{id}/participants/{pid}/`

### Payout actions
- `POST /api/v1/jobcards/{id}/payout-recalculate/`
- `POST /api/v1/jobcards/{id}/payout-hold/`
- `POST /api/v1/jobcards/{id}/payout-approve/`

### Settlements
- `GET /api/v1/settlements/?period_start=&period_end=&status=`
- `POST /api/v1/settlements/` build batch `{ period_start, period_end, cadence }`
- `POST /api/v1/settlements/{id}/approve/`
- `POST /api/v1/settlements/{id}/mark-paid/`
- `POST /api/v1/settlements/{id}/cancel/`
- `GET /api/v1/settlements/export/` → Excel
- `GET /api/v1/settlements/revenue-sharing-report/` → Excel

Additive JobCard fields (response): `package_tier`, `payment_model`, `technician_share_percent`, `company_share_percent`, `visit_*_amount`, `payout_status`.

---

## Partner (`/api/partner/`) — auth: Partner JWT

- `GET|POST /api/partner/presence/` body: `{ "presence_status": "online"|"offline" }`
- `GET|POST /api/partner/leave-requests/`
- `POST /api/partner/leave-requests/{id}/cancel/`
- `GET /api/partner/earnings/` → totals + settlement fields
- `GET /api/partner/settlements/` → approved/paid only
- Complete booking response adds: `visit_payout_amount`, `payout_status`, `payment_model`

Suspended technicians: accept/start return `400` `{ "code": "suspended" }`.

---

## Customer (`/api/customer/`) — auth: Customer JWT

- `POST /api/customer/register/` / `login/` / `token/refresh/`
- `GET /api/customer/catalog/` (public)
- `GET|POST /api/customer/bookings/`
- `GET /api/customer/bookings/{id}/`
- `POST /api/customer/bookings/{id}/pay/` (MVP stub)
- `POST /api/customer/bookings/{id}/rate/`
- `GET /api/customer/bookings/{id}/invoice/`
- `GET /api/customer/history/`
- `GET /api/customer/amc-schedule/`

Bookings created with `creation_source=customer_app`, `reference=Customer App`.
