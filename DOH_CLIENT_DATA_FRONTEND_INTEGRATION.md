# DOH Client Data — Frontend Integration Guide

Share this with the **DOH CRM frontend developer** (`https://dohadminpanel.vercel.app`).

This document describes how to implement the **DOH Client Data** page using the PestControl99 backend APIs.

---

## 1. Overview

| Item | Value |
|------|--------|
| **Page name** | `DOH Client Data` |
| **Suggested route** | `/doh-client-data` |
| **Purpose** | Show last ~6 months booking clients (name + mobile), with search filters, pagination, and per-row remarks |
| **API base URL** | `https://api.vacationbna.site` |
| **Auth** | JWT Bearer token (same CRM login token) |
| **CORS** | Allowed for `https://dohadminpanel.vercel.app` |

Total records currently in production: **~33,182**

---

## 2. Authentication

All endpoints require a logged-in CRM user JWT.

```http
Authorization: Bearer <access_token>
Content-Type: application/json
```

Get token the same way your DOH CRM already logs into PestControl99 API:

```http
POST https://api.vacationbna.site/api/token/
Content-Type: application/json

{
  "username": "<crm_username_or_mobile>",
  "password": "<password>"
}
```

Use `access` from the response in the `Authorization` header.

---

## 3. APIs

### 3.1 List clients (main table)

```http
GET https://api.vacationbna.site/api/booking-report-clients/
```

#### Query params

| Param | Required | Default | Description |
|-------|----------|---------|-------------|
| `page` | No | `1` | Page number |
| `page_size` | No | `10` | Rows per page (max `100`) |
| `city` | No | — | **`Mumbai`** or **`Pune`** (case-insensitive). Mumbai filter never returns Pune rows and vice versa |
| `name` | No | — | Filter by client name (partial, case-insensitive) |
| `number` | No | — | Filter by mobile (partial digits). Alias: `mobile` |
| `search` / `q` | No | — | Search name **or** mobile |
| `ordering` | No | `city,name` | e.g. `name`, `-name`, `city`, `mobile`, `-updated_at` |

#### Example requests

```http
GET /api/booking-report-clients/?page=1&page_size=10
GET /api/booking-report-clients/?city=Mumbai&page=1&page_size=10
GET /api/booking-report-clients/?city=Pune&page=1&page_size=10
GET /api/booking-report-clients/?city=Mumbai&name=Mahesh&page=1&page_size=10
GET /api/booking-report-clients/?number=9167909431&page_size=10
GET /api/booking-report-clients/?search=abhi&page=1&page_size=10
```

#### Example response

```json
{
  "count": 11400,
  "next": "https://api.vacationbna.site/api/booking-report-clients/?city=Mumbai&page=2&page_size=10",
  "previous": null,
  "results": [
    {
      "id": 1,
      "name": "Mahesh",
      "mobile": "9167909431",
      "city": "Mumbai",
      "remarks_count": 1,
      "latest_remark": {
        "id": 1,
        "remark": "Called customer, interested in AMC",
        "remark_type": "NOTE",
        "created_by_name": "admin",
        "created_at": "2026-07-22T21:41:45.678835+05:30"
      },
      "created_at": "2026-07-22T21:35:13.595024+05:30",
      "updated_at": "2026-07-22T21:35:13.595038+05:30"
    }
  ]
}
```

#### Field meaning

| Field | Type | UI use |
|-------|------|--------|
| `id` | number | Row id — use for Remark button APIs |
| `name` | string | Client name column |
| `mobile` | string | Mobile / number column |
| `city` | string | `Mumbai` or `Pune` — use for city tabs / dropdown filter |
| `remarks_count` | number | Badge / history count |
| `latest_remark` | object \| null | Show latest remark preview in row |
| `latest_remark.remark` | string | Latest remark text |
| `latest_remark.created_by_name` | string | Who added it |
| `latest_remark.created_at` | string | When added |
| `created_at` / `updated_at` | ISO datetime | Optional meta columns |

---

### 3.2 Get one client (optional)

```http
GET https://api.vacationbna.site/api/booking-report-clients/{id}/
```

Same object shape as one item in `results`.

---

### 3.3 List remarks for one client

```http
GET https://api.vacationbna.site/api/booking-report-clients/{id}/remarks/
```

#### Query params

| Param | Default | Description |
|-------|---------|-------------|
| `page` | `1` | Page |
| `page_size` | `20` | Max `20` |

#### Example response

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "client": 1,
      "remark": "Called customer, interested in AMC",
      "remark_type": "NOTE",
      "created_by": 1,
      "created_by_name": "admin",
      "created_at": "2026-07-22T21:41:45.678835+05:30",
      "updated_at": "2026-07-22T21:41:45.678850+05:30"
    }
  ]
}
```

---

### 3.4 Add remark (text only)

```http
POST https://api.vacationbna.site/api/booking-report-clients/{id}/remarks/
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "remark": "Called customer, interested in AMC"
}
```

**Important for UI:**

- Only send **`remark`** (text field).
- Do **not** ask the user for `remark_type` or other extra fields.
- Backend defaults type internally if needed.

#### Success response (`201`)

```json
{
  "id": 1,
  "client": 1,
  "remark": "Called customer, interested in AMC",
  "remark_type": "NOTE",
  "created_by": 1,
  "created_by_name": "admin",
  "created_at": "2026-07-22T21:41:45.678835+05:30",
  "updated_at": "2026-07-22T21:41:45.678850+05:30"
}
```

#### Error (`400`)

```json
{
  "error": "Remark text is required"
}
```

---

### 3.5 Update / delete remark (admin only — optional)

```http
PATCH https://api.vacationbna.site/api/booking-report-clients/remarks/{remark_id}/
Content-Type: application/json

{
  "remark": "Updated note text"
}
```

```http
DELETE https://api.vacationbna.site/api/booking-report-clients/remarks/{remark_id}/
```

For v1, **Add + History** is enough. Edit/delete can be skipped unless admin tools are required.

---

## 4. Page UI requirements

### Page title
**DOH Client Data**

### Suggested menu label
**DOH Client Data**

### Suggested route
`/doh-client-data`

### Table columns

| Column | Source |
|--------|--------|
| # | `(page - 1) * page_size + index + 1` |
| Name | `name` |
| Mobile | `mobile` |
| Remark | `latest_remark.remark` + **Add** / **History** buttons |
| Updated | `updated_at` (optional) |

### Filters (above table)

1. **Name** input → query param `name`
2. **Number / Mobile** input → query param `number`

Debounce ~300–400ms before calling API.

### Pagination

- Default **10 rows per page**
- Use `count`, `next`, `previous`, `page`, `page_size`
- Show total count (from `count`)

### Remark UX (per row)

1. Show latest remark text preview (`latest_remark.remark`) or “No remarks yet”
2. **Add** button → modal/popup with **only one text field** + Save/Cancel
3. On Save → `POST /api/booking-report-clients/{id}/remarks/` with `{ "remark": "..." }`
4. **History** button → `GET /api/booking-report-clients/{id}/remarks/`
5. After add success, update row:
   - `remarks_count += 1`
   - `latest_remark` = newly created remark

---

## 5. Frontend TypeScript types (copy-paste)

```ts
export interface LatestRemarkSummary {
  id: number | null;
  remark: string;
  remark_type?: string;
  created_by_name?: string;
  created_at?: string | null;
}

export interface BookingReportClient {
  id: number;
  name: string;
  mobile: string;
  remarks_count: number;
  latest_remark?: LatestRemarkSummary | null;
  created_at: string;
  updated_at: string;
}

export interface BookingReportRemark {
  id: number;
  client: number;
  remark: string;
  remark_type?: string;
  created_by?: number | null;
  created_by_name: string;
  created_at: string;
  updated_at: string;
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}
```

---

## 6. Example fetch helpers

```ts
const API_BASE = 'https://api.vacationbna.site/api';

async function getDohClients(params: {
  page?: number;
  page_size?: number;
  name?: string;
  number?: string;
}, token: string) {
  const qs = new URLSearchParams();
  qs.set('page', String(params.page ?? 1));
  qs.set('page_size', String(params.page_size ?? 10));
  if (params.name) qs.set('name', params.name);
  if (params.number) qs.set('number', params.number);

  const res = await fetch(`${API_BASE}/booking-report-clients/?${qs}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

async function getRemarks(clientId: number, token: string) {
  const res = await fetch(
    `${API_BASE}/booking-report-clients/${clientId}/remarks/?page=1&page_size=20`,
    { headers: { Authorization: `Bearer ${token}` } },
  );
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

async function addRemark(clientId: number, remark: string, token: string) {
  const res = await fetch(
    `${API_BASE}/booking-report-clients/${clientId}/remarks/`,
    {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ remark }), // text only
    },
  );
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
```

---

## 7. CORS / production notes

- Origin already allowed: `https://dohadminpanel.vercel.app`
- API host: `https://api.vacationbna.site`
- Do **not** call from `www` frontend domain; use API domain above
- Always send `Authorization: Bearer ...`
- Without token you will get `401/403`

---

## 8. Implementation checklist for DOH frontend

- [ ] Create page **DOH Client Data** (`/doh-client-data`)
- [ ] Add menu item **DOH Client Data**
- [ ] Call list API with `page=1&page_size=10`
- [ ] Add **Name** + **Number** filters
- [ ] Show table: Name, Mobile, Remark, Updated
- [ ] Remark **Add** modal = text field only
- [ ] Remark **History** modal from remarks list API
- [ ] Pagination with total `count`
- [ ] Handle loading / empty / error states
- [ ] Use existing CRM JWT auth header

---

## 9. Quick reference

```text
List:    GET  /api/booking-report-clients/?page=1&page_size=10
City:    GET  /api/booking-report-clients/?city=Mumbai
City:    GET  /api/booking-report-clients/?city=Pune
Filter:  GET  /api/booking-report-clients/?name=Mahesh
Filter:  GET  /api/booking-report-clients/?number=9167909431
History: GET  /api/booking-report-clients/{id}/remarks/
Add:     POST /api/booking-report-clients/{id}/remarks/
         Body: { "remark": "your text here" }
```

**Base URL:** `https://api.vacationbna.site`

If anything fails (CORS / 401 / empty list), share the Network request URL + response status with backend.
