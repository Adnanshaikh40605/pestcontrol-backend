# Partner Refer Client — Flow & API

## Overview

Technicians submit referrals from the **Partner App**. Each submission creates a **CRM inquiry** plus a **PartnerReferral** record. Status is owned by the CRM inquiry; the app shows simplified labels.

## Status mapping

| CRM (`CRMInquiry.status`) | Partner app label |
|---------------------------|-------------------|
| New                       | Pending           |
| Contacted                 | In Progress       |
| Converted                 | Successful        |
| Closed                    | Closed            |

## APIs

### Partner app (Bearer partner JWT)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/partner/refer-client/` | Submit referral |
| GET | `/api/partner/referrals/` | List own referrals |
| GET | `/api/partner/referrals/<id>/` | Single referral |

### CRM (Bearer staff JWT)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/partner-referrals/` | List all partner referrals |
| PATCH | `/api/v1/partner-referrals/<id>/` | Body: `{ "status": "New" \| "Contacted" \| "Converted" \| "Closed" }` |

## UX flow

1. **Partner app** → Refer Client form → submit → **Referral Progress** (new item highlighted).
2. **CRM** → **Partner Referrals** sidebar → table with date/time, partner, client, status dropdown.
3. Staff changes status → partner app list reflects on refresh.

## Deploy

1. Run migration: `partner.0007_partner_referral`
2. Deploy backend to Railway
3. Deploy CRM frontend (Vercel) with new `/partner-referrals` page
4. Rebuild partner APK
