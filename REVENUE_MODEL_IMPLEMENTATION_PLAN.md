# Revenue Model v2 — Implementation Plan (living doc)

Source requirements: `pest control project new model  chenges .md`  
Locked Cursor plan: `revenue_model_integration_b34140f6`  
OpenAPI sketches: `docs/revenue_model_openapi.md`

## Locked decisions (Phase 0)

1. Extend JobCard stack — do not invent parallel Booking/Visit systems.
2. Legacy cutover: existing JobCards → `payout_status=legacy_exempt`. No historical PartnerEarning backfill.
3. Contractual is also 40/60 revenue sharing. Per-visit pool = visit_value × 40%, split equally among **partner** technicians who attended. Salaried techs excluded from divisor. Zero eligible partners → `held`.
4. Keep singular `JobCard.technician` / `JobCard.partner` as lead; crew via `JobCardTechnicianParticipation`.
5. Feature flag: `REVENUE_MODEL_V2` (default `false`).

### Locked constants (`core/revenue_constants.py`)

| Constant | Value |
|----------|-------|
| Technician share | 40% |
| Company share | 60% |
| Settlement cadence default | weekly (monthly supported) |
| Auto-suspend offline days | **3** |

---

## Phase 1 shipped — Schema + payout engine

| Piece | Location |
|-------|----------|
| Constants | `core/revenue_constants.py` |
| Payout engine | `core/payout_engine.py` |
| Technician fields | type, KYC, deposit, presence |
| JobCard revenue fields | package/payment model, shares, visit snapshots, payout_status |
| Crew model | `JobCardTechnicianParticipation` |
| PartnerEarning | earning_type, participation, is_approved, unique (job, partner, type) |
| Hooks | partner `partner_complete_booking` + CRM Done in `JobCardSerializer.update` |
| APIs | participants CRUD; `POST .../payout-recalculate/` |
| Migrations | `core/0094_revenue_model_v2`, `partner/0008_revenue_model_v2_earnings` |
| Tests | `core/tests/test_payout_engine.py` |

### Enable cutover

1. Deploy migrations with flag **off**.
2. Confirm existing bookings show `payout_status=legacy_exempt`.
3. Set `REVENUE_MODEL_V2=true` on Railway.
4. New bookings get `payment_model=revenue_sharing` + `payout_status=not_applicable` on create.
5. On Done/complete → engine writes `PartnerEarning` and sets `pending` / `held`.

---

## Phase 2 shipped — CRM UX + API tests

| Piece | Location |
|-------|----------|
| Feature flags API | `GET /api/v1/feature-flags/` |
| Payout hold/approve | `POST .../payout-hold/`, `.../payout-approve/` |
| Backend API tests | `core/tests/test_revenue_model_api.py` |
| CRM flag hook | `pest crm/src/hooks/useRevenueModelV2.ts` |
| Booking revenue fields | `RevenueModelFields` on Create/Edit JobCard |
| Crew + payout panel | `JobCrewPanel` on Edit JobCard |
| Technicians type/KYC-lite | Type badge + modal fields when flag on |
| Payout preview utils + vitest | `revenuePayoutPreview.ts` + `.test.ts` |

---

## Phase 3 shipped — Settlements + Excel

| Piece | Location |
|-------|----------|
| Models | `TechnicianSettlement`, `SettlementLineItem` (`core/0095`) |
| Builder | `core/settlement_engine.py` |
| Excel | `core/settlement_excel.py` |
| APIs | `/api/v1/settlements/` build/approve/mark-paid/cancel/export/revenue-sharing-report |
| Tests | `core/tests/test_settlements.py` |
| CRM page | `/settlements` (flag-gated sidebar) |
| CRM helpers + vitest | `settlementPeriods.ts` + `.test.ts` |

---

## Phase 4 shipped — Partner app

| Piece | Location |
|-------|----------|
| Presence helpers | `partner/presence.py` |
| Leave model | `PartnerLeaveRequest` (`partner/0009`) |
| Partner APIs | presence, leave-requests, settlements (read-only) |
| Suspended gate | accept/start blocked when `presence_status=suspended` |
| Earnings extras | settlement_status, payout fields, approved_earnings |
| Complete response | `visit_payout_amount`, `payout_status`, `payment_model` |
| Backend tests | `partner/tests/test_revenue_apis.py` |
| Flutter | earnings + settlements, leave, presence toggle, payout on detail |
| Flutter tests | `pest_99_partner_app/test/revenue_model_parsing_test.dart` |

---

## Phase 5 shipped — Customer App (MVP)

| Piece | Location |
|-------|----------|
| Django app | `customer/` — JWT auth, catalog, book, track, pay stub, rate, invoice, AMC schedule |
| Models | `CustomerAccount` ↔ `core.Client`, `CustomerRevokedJti` |
| APIs | `/api/customer/*` |
| JobCard source | `creation_source=customer_app`, `reference=Customer App` |
| Backend tests | `customer/tests/test_customer_apis.py` |
| Flutter app | `pest_99_customer_app/` |
| Flutter tests | `pest_99_customer_app/test/customer_models_test.dart` |

**Deferred:** real payment gateway, push, deep AMC UI.

---

## Phase 6 shipped — Hardening (docs + ops)

| Piece | Location |
|-------|----------|
| OpenAPI sketches | `docs/revenue_model_openapi.md` |
| Revenue ActivityLog helper | `core/revenue_audit.py` (payout calc/hold/approve, settlements, auto-suspend) |
| Auto-suspend command | `python manage.py auto_suspend_inactive_technicians` |
| API docs section | `BACKEND_API_DOCUMENTATION.md` → Revenue Model v2 |

---

## Rollback

1. Feature flag off → CRM hides new fields; calculator no-ops.
2. Deploy previous app builds (additive columns remain harmless).
3. Never delete JobCard revenue columns in emergency — only stop writing.
