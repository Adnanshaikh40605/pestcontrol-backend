# Pest Control 99 — Meta WhatsApp API Integration Guide

This document explains how to connect **Pest Control 99** to Meta WhatsApp, fetch template IDs, manage campaigns, and add a **“Send WhatsApp Template”** button so staff can message customers from the CRM.

> **Security:** Permanent Meta access tokens are secrets. Keep this file private. Do **not** push tokens to a public GitHub repo. Rotate the token in Meta if it was ever exposed.

---

## 1. Overview

| Item | Value |
|------|--------|
| CRM frontend | `https://driveronhire.ai/whatsapp-crm` |
| API base (WhatsFlow) | `https://api.driveronhire.ai/api/v1` |
| Embed API base (external sites) | `https://api.driveronhire.ai/api` |
| Meta webhook | `https://api.driveronhire.ai/api/v1/onboarding/webhooks/whatsapp/` |
| Graph API version | `v21.0` |
| Organization name | **Pest Control 99** |
| Organization UUID | `96d71345-5c98-4e9a-8095-0eae9ff855c4` |
| Website / brochure | `https://www.pestcontrol99.com` · e-card `https://www.pestcontrol99.com/e-card/` |
| Business call number (template CTA) | `+918080748282` |

**Two ways to integrate:**

| Use case | API |
|----------|-----|
| Staff inside WhatsFlow CRM (templates, campaigns, test send) | `/api/v1/...` + JWT |
| **pestcontrol99.com** or another external CRM with a Send button | `/api/auth/sso-login/` + `/api/inbox/messages/template/` |

---

## 1.1 Pest Control 99 — Meta credentials (from this project)

These values were already saved in the WhatsFlow project files:

| Source file | What it contains |
|-------------|------------------|
| `backend/.env` | Phone Number ID, WABA ID, permanent access token |
| `whatsapp detials.md` | Phone Number ID + WABA ID (same IDs) |

### Meta WhatsApp Cloud API credentials

| Field | Value | Env var / CRM field |
|-------|--------|---------------------|
| **Phone Number ID** | `1117687894770354` | `WHATSAPP_PHONE_NUMBER_ID` / `whatsapp_phone_number_id` |
| **WhatsApp Business Account ID (WABA)** | `2080017302589668` | `WHATSAPP_BUSINESS_ACCOUNT_ID` / `whatsapp_business_account_id` |
| **Permanent Access Token** | `EAASOAun8ClkBR2IPpgIjxoF9zFqbu3WMMQbDykxKc6sepoLVZBU7oBe9ps6k2nhuLxqnPtaxGcgV0luYBiAVOssqstSAcS62Yz2b7BGohdUwvfCwGcPaK3AY60jA9lOE8SQ9TjGTjGxU6OZALiPMlaQhZCdZCZCX7ja42DRwlYcOWFod9dqZBF7ou334V2LwZDZD` | `WHATSAPP_ACCESS_TOKEN` / `whatsapp_access_token` |

### How credentials are stored

1. **Local backend env** (`backend/.env`) — used by management commands / local Graph API tests.
2. **Per-organization in the database** — paste the same three values in CRM **Developer** so Pest Control 99 can send/sync in production:
   - `whatsapp_phone_number_id` = `1117687894770354`
   - `whatsapp_business_account_id` = `2080017302589668`
   - `whatsapp_access_token` = the `EAAS...` token above

### Related orgs in this CRM

| Organization | UUID |
|--------------|------|
| Pest Control 99 | `96d71345-5c98-4e9a-8095-0eae9ff855c4` |
| DriverOnHire | `36697a5a-0dcd-4418-9c38-278382444c92` |

Use **Pest Control 99** UUID in `X-Organization-ID` and embed `organization_id`.

### Approved templates (synced from Meta)

| Template name | Meta template ID | Category | Language |
|---------------|------------------|----------|----------|
| `pest_business_details` | `1333062758460952` | utility | `en_US` |
| `pestecardaadsd` | `898122920007286` | utility | `en_US` |

When sending, Meta uses **`template_name` + `language`**, not the numeric Meta ID. The numeric ID is for reference / Meta Manager only.

---

## 2. One-time: Connect Meta to Pest Control 99

### 2.1 Credentials (already in this project)

You do **not** need to create new Meta credentials unless the token expired. Use the values in **§1.1**.

If you ever need to regenerate a token:

1. [Meta for Developers](https://developers.facebook.com/) → your app → **WhatsApp** → **API setup**
2. Or Meta Business Settings → **System users** → generate a permanent token with:
   - `whatsapp_business_messaging`
   - `whatsapp_business_management`

Official docs: [WhatsApp Cloud API Get Started](https://developers.facebook.com/docs/whatsapp/cloud-api/get-started)

### 2.2 Connect inside WhatsFlow CRM

1. Open `https://driveronhire.ai/whatsapp-crm`
2. Switch organization to **Pest Control 99** (top-right)
3. Go to **Developer** (`/whatsapp-crm/api-settings`)
4. Paste:

| Field | Paste this |
|-------|------------|
| WhatsApp Business Account ID | `2080017302589668` |
| Phone Number ID | `1117687894770354` |
| Permanent Access Token | `EAASOAun8ClkBR2IPpgIjxoF9zFqbu3WMMQbDykxKc6sepoLVZBU7oBe9ps6k2nhuLxqnPtaxGcgV0luYBiAVOssqstSAcS62Yz2b7BGohdUwvfCwGcPaK3AY60jA9lOE8SQ9TjGTjGxU6OZALiPMlaQhZCdZCZCX7ja42DRwlYcOWFod9dqZBF7ou334V2LwZDZD` |

5. Click **Connect**
6. Confirm dashboard shows WhatsApp status **LIVE**

**API (admin only) — ready-to-use body:**

```http
POST https://api.driveronhire.ai/api/v1/onboarding/whatsapp/connect/
Authorization: Bearer <your_crm_jwt>
X-Organization-ID: 96d71345-5c98-4e9a-8095-0eae9ff855c4
Content-Type: application/json

{
  "waba_id": "2080017302589668",
  "phone_number_id": "1117687894770354",
  "access_token": "EAASOAun8ClkBR2IPpgIjxoF9zFqbu3WMMQbDykxKc6sepoLVZBU7oBe9ps6k2nhuLxqnPtaxGcgV0luYBiAVOssqstSAcS62Yz2b7BGohdUwvfCwGcPaK3AY60jA9lOE8SQ9TjGTjGxU6OZALiPMlaQhZCdZCZCX7ja42DRwlYcOWFod9dqZBF7ou334V2LwZDZD"
}
```

**CLI (local backend, same credentials):**

```bash
cd backend
python manage.py connect_whatsapp "Pest Control 99" \
  --phone-number-id=1117687894770354 \
  --waba-id=2080017302589668 \
  --access-token="EAASOAun8ClkBR2IPpgIjxoF9zFqbu3WMMQbDykxKc6sepoLVZBU7oBe9ps6k2nhuLxqnPtaxGcgV0luYBiAVOssqstSAcS62Yz2b7BGohdUwvfCwGcPaK3AY60jA9lOE8SQ9TjGTjGxU6OZALiPMlaQhZCdZCZCX7ja42DRwlYcOWFod9dqZBF7ou334V2LwZDZD"
```

**Response:**

```json
{
  "success": true,
  "message": "Success",
  "data": {
    "connected": true,
    "waba_id": "2080017302589668",
    "phone_number_id": "1117687894770354",
    "webhook_configured": true
  }
}
```

### 2.3 Webhook (delivery / read / replies)

Meta callback URL:

```text
https://api.driveronhire.ai/api/v1/onboarding/webhooks/whatsapp/
```

Verify token: value of `WHATSAPP_VERIFY_TOKEN` on the server (default `whatsflow_verify`).

Without webhooks, messages can still **send**, but delivered/read status and inbound replies may not update in the CRM.

### 2.4 Direct Meta Graph API smoke test (optional)

Uses the same Phone Number ID + token from `backend/.env`:

```bash
curl -s -X POST "https://graph.facebook.com/v21.0/1117687894770354/messages" \
  -H "Authorization: Bearer EAASOAun8ClkBR2IPpgIjxoF9zFqbu3WMMQbDykxKc6sepoLVZBU7oBe9ps6k2nhuLxqnPtaxGcgV0luYBiAVOssqstSAcS62Yz2b7BGohdUwvfCwGcPaK3AY60jA9lOE8SQ9TjGTjGxU6OZALiPMlaQhZCdZCZCX7ja42DRwlYcOWFod9dqZBF7ou334V2LwZDZD" \
  -H "Content-Type: application/json" \
  -d '{
    "messaging_product": "whatsapp",
    "to": "919372792693",
    "type": "template",
    "template": {
      "name": "pest_business_details",
      "language": { "code": "en_US" }
    }
  }'
```

Replace `to` with your test WhatsApp number (country code, no `+`).

---

## 3. Authentication

### 3.1 WhatsFlow CRM login (staff)

```http
POST https://api.driveronhire.ai/api/v1/auth/login/
Content-Type: application/json

{
  "name": "staff_username",
  "password": "password"
}
```

Use `data.tokens.access` as `Authorization: Bearer ...`.

**Every CRM request must include the org:**

```http
X-Organization-ID: <pest_control_99_org_uuid>
```

Switch org via:

```http
POST https://api.driveronhire.ai/api/v1/organizations/<org_id>/switch/
Authorization: Bearer <access_token>
```

### 3.2 Embed API (pestcontrol99.com external CRM)

For an external site that should **not** store Meta tokens:

1. Create an API key in WhatsFlow: **Settings → API Keys** (scopes: `embed`, `inbox`, `write`)
2. SSO login:

```http
POST https://api.driveronhire.ai/api/auth/sso-login/
Content-Type: application/json

{
  "api_key": "wf_xxxxxxxx",
      "organization_id": "96d71345-5c98-4e9a-8095-0eae9ff855c4",
      "external_user": {
        "id": "staff_42",
        "name": "Adnan",
        "role": "staff"
      }
}
```

**Response:**

```json
{
  "success": true,
  "data": {
    "access_token": "eyJ...",
    "refresh_token": "...",
    "user": { "id": "...", "name": "Adnan", "role": "staff" },
    "organization": { "id": "...", "name": "Pest Control 99" }
  }
}
```

Use `access_token` for all embed calls. Organization is embedded in the JWT — no `X-Organization-ID` header needed.

---

## 4. Templates — list, sync, Meta IDs

### 4.1 Sync from Meta (recommended first)

Pulls all templates from Meta into the CRM and removes ones deleted on Meta.

```http
POST https://api.driveronhire.ai/api/v1/campaigns/templates/sync_meta/
Authorization: Bearer <access_token>
X-Organization-ID: <org_uuid>
```

**Response:**

```json
{
  "success": true,
  "message": "Synced 2 templates from Meta · removed 0 deleted on Meta",
  "data": {
    "synced_count": 2,
    "removed_count": 0
  }
}
```

### 4.2 List all templates (with Meta template IDs)

```http
GET https://api.driveronhire.ai/api/v1/campaigns/templates/?status=approved
Authorization: Bearer <access_token>
X-Organization-ID: <org_uuid>
```

**Query params:**

| Param | Values |
|-------|--------|
| `status` | `approved`, `pending`, `rejected`, `draft` |
| `category` | `utility`, `marketing`, `authentication` |
| `search` | name / body text |

**Example template object:**

```json
{
  "id": "104a68ed-88e1-477e-9bce-2f14b490a4ae",
  "name": "pest_business_details",
  "language": "en_US",
  "category": "utility",
  "status": "approved",
  "whatsapp_template_id": "1333062758460952",
  "meta_status": "APPROVED",
  "quality_rating": "",
  "body": "Dear {{1}}, ...",
  "header": { "type": "HEADER", "format": "TEXT", "text": "Dear, Customer" },
  "footer": "Pest Control 99",
  "buttons": [
    { "type": "PHONE_NUMBER", "text": "Call Now", "phone_number": "+91..." },
    { "type": "URL", "text": "E-Brochure", "url": "https://..." }
  ],
  "variables": [],
  "last_synced_at": "2026-07-22T06:25:00Z"
}
```

| Field | Meaning |
|-------|---------|
| `id` | CRM UUID — use in `/send_test/` and campaigns |
| `whatsapp_template_id` | **Meta template ID** (numeric string from Meta Manager) |
| `name` | Template name Meta uses when sending (e.g. `pest_business_details`) |
| `language` | e.g. `en_US` |

### 4.3 Get one template

```http
GET https://api.driveronhire.ai/api/v1/campaigns/templates/<crm_template_uuid>/
```

### 4.4 Preview

```http
GET https://api.driveronhire.ai/api/v1/campaigns/templates/<crm_template_uuid>/preview/
```

---

## 5. Campaigns — create, details, launch

### 5.1 List campaigns

```http
GET https://api.driveronhire.ai/api/v1/campaigns/?archived=false
Authorization: Bearer <access_token>
X-Organization-ID: <org_uuid>
```

### 5.2 Get campaign details

```http
GET https://api.driveronhire.ai/api/v1/campaigns/<campaign_uuid>/
```

**Example response fields:**

```json
{
  "id": "...",
  "name": "July Pest Offer",
  "status": "completed",
  "campaign_type": "broadcast",
  "template": "<crm_template_uuid>",
  "contact_group": "<group_uuid>",
  "audience_filter": {},
  "total_recipients": 150,
  "sent_count": 148,
  "delivered_count": 140,
  "read_count": 95,
  "failed_count": 2,
  "scheduled_at": null,
  "created_at": "..."
}
```

### 5.3 Campaign analytics

```http
GET https://api.driveronhire.ai/api/v1/campaigns/<campaign_uuid>/analytics/overview/
GET https://api.driveronhire.ai/api/v1/campaigns/<campaign_uuid>/analytics/recipients/?page=1
GET https://api.driveronhire.ai/api/v1/campaigns/<campaign_uuid>/dashboard/
```

### 5.4 Create campaign

```http
POST https://api.driveronhire.ai/api/v1/campaigns/
Authorization: Bearer <access_token>
X-Organization-ID: <org_uuid>
Content-Type: application/json

{
  "name": "Pest Service Reminder",
  "campaign_type": "broadcast",
  "template": "<crm_template_uuid>",
  "contact_group": "<contact_group_uuid>",
  "message_content": "",
  "audience_filter": {},
  "status": "draft"
}
```

**Rules:**

- `template` must be **approved**
- `contact_group` = group created under **Contacts**
- Or use `audience_filter`: `{ "contact_ids": ["uuid1", "uuid2"] }`

### 5.5 Launch campaign (bulk send)

```http
POST https://api.driveronhire.ai/api/v1/campaigns/<campaign_uuid>/launch/
```

This queues Celery to send the template to every contact in the audience.

**Note:** Bulk campaign send uses template **name + language** only. Templates with `{{1}}`, `{{2}}` variables need fixed example values in the template body, or use the **single-send** APIs below for per-contact variables.

---

## 6. Send WhatsApp Template button (staff click)

This is the main flow for: *“Staff opens a customer record → clicks Send Template → message goes on WhatsApp.”*

### Option A — Inside WhatsFlow CRM (already built)

1. **Templates** → open approved template → **Test Send**
2. Or **Campaigns** → create + **Launch** for bulk

API used internally:

```http
POST https://api.driveronhire.ai/api/v1/campaigns/templates/<crm_template_uuid>/send_test/
Authorization: Bearer <access_token>
X-Organization-ID: <org_uuid>
Content-Type: application/json

{
  "phone": "919876543210",
  "body_params": ["Adnan", "BKG1024"]
}
```

| Field | Format |
|-------|--------|
| `phone` | Country code + number, no `+` (e.g. `919876543210`) |
| `body_params` | Values for `{{1}}`, `{{2}}`, … in order |

**Success response:**

```json
{
  "success": true,
  "message": "Test template sent",
  "data": {
    "messaging_product": "whatsapp",
    "contacts": [{ "input": "919876543210", "wa_id": "919876543210" }],
    "messages": [{ "id": "wamid.HBgM..." }]
  }
}
```

### Option B — pestcontrol99.com (Embed API) **recommended for external CRM**

```http
POST https://api.driveronhire.ai/api/inbox/messages/template/
Authorization: Bearer <embed_access_token>
Content-Type: application/json

{
  "phone": "919876543210",
  "template_name": "pest_business_details",
  "language": "en_US",
  "body_params": ["Customer Name"]
}
```

| Field | Required | Notes |
|-------|----------|-------|
| `phone` | Yes* | E.164 without `+` |
| `conversation_id` | Yes* | Alternative to phone if conversation exists |
| `template_name` | Yes | Meta template name, not Meta numeric ID |
| `language` | No | Default `en` — use `en_US` for Pest Control templates |
| `body_params` | No | Array of variable values |

Message is queued, sent via Meta, and appears in **Live Chat** history.

### Option C — Direct Meta Graph API (advanced)

Only if you manage tokens yourself (not recommended when WhatsFlow is connected):

```http
POST https://graph.facebook.com/v21.0/<PHONE_NUMBER_ID>/messages
Authorization: Bearer <PERMANENT_TOKEN>
Content-Type: application/json

{
  "messaging_product": "whatsapp",
  "to": "919876543210",
  "type": "template",
  "template": {
    "name": "pest_business_details",
    "language": { "code": "en_US" },
    "components": [
      {
        "type": "body",
        "parameters": [
          { "type": "text", "text": "Adnan" }
        ]
      }
    ]
  }
}
```

WhatsFlow already wraps this in `WhatsAppService.send_template()`.

---

## 7. Button implementation example (pestcontrol99.com)

### 7.1 Flow

```mermaid
sequenceDiagram
  participant Staff as Staff browser
  participant PC99 as pestcontrol99.com
  participant API as api.driveronhire.ai
  participant Meta as Meta WhatsApp

  Staff->>PC99: Click "Send WhatsApp Template"
  PC99->>API: POST /api/auth/sso-login/ (api_key)
  API-->>PC99: access_token
  PC99->>API: GET /api/v1/campaigns/templates/?status=approved
  API-->>PC99: template list with names + Meta IDs
  Staff->>PC99: Pick template + confirm
  PC99->>API: POST /api/inbox/messages/template/
  API->>Meta: POST /{phone_number_id}/messages
  Meta-->>API: wamid message id
  API-->>PC99: success
  PC99-->>Staff: "Message sent"
```

### 7.2 JavaScript example (Send button)

```javascript
const API_BASE = 'https://api.driveronhire.ai/api'
const API_V1 = 'https://api.driveronhire.ai/api/v1'
const ORG_ID = '96d71345-5c98-4e9a-8095-0eae9ff855c4' // Pest Control 99
const API_KEY = 'wf_your_key_from_whatsflow_settings'

async function getEmbedToken() {
  const res = await fetch(`${API_BASE}/auth/sso-login/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      api_key: API_KEY,
      organization_id: ORG_ID,
      external_user: { id: '1', name: 'Staff', role: 'staff' },
    }),
  })
  const json = await res.json()
  if (!json.success) throw new Error(json.message)
  return json.data.access_token
}

async function listApprovedTemplates(token) {
  const res = await fetch(`${API_V1}/campaigns/templates/?status=approved`, {
    headers: {
      Authorization: `Bearer ${token}`,
      'X-Organization-ID': ORG_ID,
    },
  })
  const json = await res.json()
  return json.data?.results ?? json.data ?? []
}

async function sendTemplateToCustomer(token, phone, templateName, bodyParams = []) {
  const res = await fetch(`${API_BASE}/inbox/messages/template/`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      phone: phone.replace(/\D/g, ''), // digits only, with country code
      template_name: templateName,
      language: 'en_US',
      body_params: bodyParams,
    }),
  })
  const json = await res.json()
  if (!json.success) throw new Error(json.message || 'Send failed')
  return json.data
}

// Button handler
document.getElementById('send-whatsapp-btn').addEventListener('click', async () => {
  const phone = document.getElementById('customer-phone').value
  const templateName = 'pest_business_details' // or from dropdown
  const customerName = document.getElementById('customer-name').value

  try {
    const token = await getEmbedToken()
    await sendTemplateToCustomer(token, phone, templateName, [customerName])
    alert('WhatsApp template sent!')
  } catch (e) {
    alert('Failed: ' + e.message)
  }
})
```

### 7.3 React / WhatsFlow CRM button (same org)

If the button lives inside WhatsFlow frontend, use existing client:

```typescript
import { campaignApi } from '../lib/api'

await campaignApi.sendTestTemplate(templateId, {
  phone: '919876543210',
  body_params: ['Adnan'],
})
```

`templateId` = CRM UUID from `GET /campaigns/templates/`, not Meta numeric ID.

---

## 8. Contacts (required before campaigns)

```http
GET  https://api.driveronhire.ai/api/v1/crm/contacts/
POST https://api.driveronhire.ai/api/v1/crm/contacts/
GET  https://api.driveronhire.ai/api/v1/crm/groups/
POST https://api.driveronhire.ai/api/v1/crm/groups/
```

Phone format: include country code. Indian mobiles are normalized to `91XXXXXXXXXX`.

---

## 9. Error handling

| Error | Cause | Fix |
|-------|-------|-----|
| `WhatsApp Business Account is not connected` | Org missing Meta credentials | Developer → Connect |
| `Template must be approved` | Template pending/rejected | Wait for Meta or fix template |
| `Approved template not found` | Wrong `template_name` or `language` | Sync templates; use exact name |
| `Phone number is required` | Missing `phone` | Pass E.164 digits |
| `relation "whatsapptemplate" does not exist` | Wrong DB table in custom scripts | Use WhatsFlow API, not raw SQL |
| Meta `#131026` / template mismatch | Variables don't match body | Pass correct `body_params` count/order |

---

## 10. Pest Control 99 quick reference

### Meta credentials (from `backend/.env` + `whatsapp detials.md`)

| Field | Value |
|-------|--------|
| Phone Number ID | `1117687894770354` |
| WABA ID | `2080017302589668` |
| Access Token | see **§1.1** (starts with `EAASOAun8Clk...`) |
| Org UUID | `96d71345-5c98-4e9a-8095-0eae9ff855c4` |

### Current approved templates

| CRM name | Meta ID | Category |
|----------|---------|----------|
| `pest_business_details` | `1333062758460952` | utility |
| `pestecardaadsd` | `898122920007286` | utility |

Run **Sync from Meta** after any change in Meta Manager.

### Implementation checklist

- [ ] Connect WABA + Phone Number ID + Token in **Developer** (values in §1.1)
- [ ] Webhook URL configured in Meta app
- [ ] **Sync from Meta** on Templates page
- [ ] Contacts imported with valid phones
- [ ] Contact groups created for campaigns
- [ ] API key created for pestcontrol99.com (if external)
- [ ] Send button wired to `POST /api/inbox/messages/template/` or `send_test`
- [ ] Test with your own phone before bulk campaign

### Related docs

- [WHATSAPP_API_CONNECTION_GUIDE.md](./WHATSAPP_API_CONNECTION_GUIDE.md) — full Meta setup
- [backend/apps/embed_api/README.md](../backend/apps/embed_api/README.md) — embed SSO
- Project notes: `whatsapp detials.md` (Phone + WABA IDs)
- Local env: `backend/.env` (`WHATSAPP_*` vars)
- Meta Cloud API: https://developers.facebook.com/docs/whatsapp/cloud-api
- Meta message templates: https://developers.facebook.com/docs/whatsapp/message-templates

---

## 11. cURL cheat sheet

```bash
# Login
curl -s -X POST https://api.driveronhire.ai/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"name":"USERNAME","password":"PASSWORD"}'

export TOKEN="<crm_jwt_access_token>"
export ORG="96d71345-5c98-4e9a-8095-0eae9ff855c4"

# Sync templates
curl -s -X POST https://api.driveronhire.ai/api/v1/campaigns/templates/sync_meta/ \
  -H "Authorization: Bearer $TOKEN" -H "X-Organization-ID: $ORG"

# List approved templates (with Meta IDs)
curl -s "https://api.driveronhire.ai/api/v1/campaigns/templates/?status=approved" \
  -H "Authorization: Bearer $TOKEN" -H "X-Organization-ID: $ORG"

# Send pest_business_details to one customer (use CRM template UUID from list)
curl -s -X POST "https://api.driveronhire.ai/api/v1/campaigns/templates/<TEMPLATE_UUID>/send_test/" \
  -H "Authorization: Bearer $TOKEN" -H "X-Organization-ID: $ORG" \
  -H "Content-Type: application/json" \
  -d '{"phone":"919372792693","body_params":[]}'

# Embed: send by template name (after SSO login)
curl -s -X POST "https://api.driveronhire.ai/api/inbox/messages/template/" \
  -H "Authorization: Bearer <embed_access_token>" \
  -H "Content-Type: application/json" \
  -d '{"phone":"919372792693","template_name":"pest_business_details","language":"en_US","body_params":[]}'

# Create + launch campaign
curl -s -X POST https://api.driveronhire.ai/api/v1/campaigns/ \
  -H "Authorization: Bearer $TOKEN" -H "X-Organization-ID: $ORG" \
  -H "Content-Type: application/json" \
  -d '{"name":"Test Blast","template":"<TEMPLATE_UUID>","contact_group":"<GROUP_UUID>","campaign_type":"broadcast","status":"draft"}'

curl -s -X POST "https://api.driveronhire.ai/api/v1/campaigns/<CAMPAIGN_UUID>/launch/" \
  -H "Authorization: Bearer $TOKEN" -H "X-Organization-ID: $ORG"
```

---

*Last updated: July 2026 — Pest Control 99 / WhatsFlow CRM*
*Credentials sourced from `backend/.env` and `whatsapp detials.md`*
