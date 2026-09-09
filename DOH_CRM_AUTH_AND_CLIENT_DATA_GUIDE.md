# CRM WhatsApp / WhatsFlow — Vercel Environment Variables

Project: `pestcontrol-crm-frontend`  
Environments: **Production** and **Preview**

The CRM reads **`VITE_WHATSAPP_API_KEY`** (also accepts `VITE_WHATSFLOW_API_KEY`).

---

## 1. API URL

| Field | Value |
|-------|--------|
| **Key** | `VITE_WHATSAPP_API_URL` |
| **Value** | `https://api.driveronhire.ai` |

---

## 2. API Key (permanent — Active key from WhatsFlow)

| Field | Value |
|-------|--------|
| **Key** | `VITE_WHATSAPP_API_KEY` |
| **Value** | `wf_f019ka3yk6xsWrFktc-qDCEmBGOICbYn2hM-Tu1B7E0` |

Optional alias (same value):

| Field | Value |
|-------|--------|
| **Key** | `VITE_WHATSFLOW_API_KEY` |
| **Value** | `wf_f019ka3yk6xsWrFktc-qDCEmBGOICbYn2hM-Tu1B7E0` |

> Do **not** use `wf_MI8s99OGlpLwjczoAVbM518n-hDWSZnNcbIER93Q-F4` — that key is revoked/invalid.
> WhatsFlow returns the misleading message `api_key or embed_token is required` for that dead key.

---

## After saving on Vercel

1. Save for **Production** (and Preview)
2. **Deployments → Redeploy** (required — Vite bakes env at build time)
3. Hard refresh CRM
4. Clear site Local Storage if SSO still fails:
   - `whatsflow_access_token`
   - `whatsflow_refresh_token`

### Why you see `api_key or embed_token is required`

1. Request body has no `api_key` (empty env / forgot redeploy), **or**
2. The `wf_…` key is revoked/invalid (WhatsFlow returns the same message)

### Permanent vs temporary

| Token | Permanent? | Notes |
|-------|------------|--------|
| `wf_…` API key (Settings → API Keys) | **Yes** until you revoke/delete it | Put this in Vercel |
| JWT from `/api/auth/sso-login/` | **No** (~30 min) | CRM stores in localStorage and re-SSO with the permanent `wf_` key |
