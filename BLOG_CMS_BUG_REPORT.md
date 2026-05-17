# Blog CMS — Bug Report (Backend + CRM)

**Project:** Pest Control 99 — Blog CMS  
**Report date:** May 17, 2026  
**Scope:** Django blog API (`blog/`) + Pest CRM (`pest crm/`)  
**Related spec:** `rich text editor in the crm.md`, `blog cms systme in the crm.md`

---

## Executive summary

| Area | Open bugs | Fixed (pending deploy) | Configuration / env |
|------|-----------|-------------------------|---------------------|
| **Backend** | 2 | 3 | 4 items |
| **CRM** | 1 | 4 | 1 item |

Most user-facing issues (broken images, double toolbar, confusing layout) have **code fixes in the repo** but require **deployment** and correct **Railway/Vercel + S3** settings to verify in production.

---

## Backend bugs

### BUG-BE-001 — Uploaded image URL not loadable in browser (Critical)

| Field | Detail |
|-------|--------|
| **Severity** | Critical |
| **Status** | Mitigated in code — verify after deploy |
| **Component** | `blog/views.py` → `ImageUploadView`, `blog/storage.py`, `blog/media_urls.py` |
| **Endpoint** | `POST /api/blogs/upload-image/` |

**Description**  
API returns `201 Created` with a `url` field, but images appear as broken icons in the CRM rich text editor and in saved HTML.

**Root causes (identified)**  
1. Response URL used `localhost` or internal host when CRM runs on Vercel and API on Railway.  
2. S3 objects uploaded with `AWS_DEFAULT_ACL = None` may be **private** (403 on GET).  
3. `USE_AWS=False` on production saves files to ephemeral disk; `/media/` may not persist or match public URL.

**Fix applied**  
- `build_public_media_url()` rewrites localhost URLs using `PUBLIC_API_BASE_URL`.  
- Default `AWS_DEFAULT_ACL=public-read` when S3 is enabled.  
- `.env.example` documents required variables.

**Reproduction**  
1. Log in to CRM on production.  
2. Create blog → Content → insert image via toolbar.  
3. Observe 201 in Network tab; open `response.url` in new tab.  
4. If tab shows 403/404, bug is storage/ACL, not Quill.

**Expected**  
`url` is absolute `https://...` and loads in browser without auth.

**Verification checklist**  
- [ ] Railway: `USE_AWS=True`, AWS credentials, bucket policy allows public read on `blog/*`  
- [ ] Railway: `PUBLIC_API_BASE_URL=https://api.vacationbna.site`  
- [ ] `python manage.py check_s3_storage` succeeds  
- [ ] Paste upload `url` in browser — image displays  

---

### BUG-BE-002 — Media files lost on Railway without S3 (High)

| Field | Detail |
|-------|--------|
| **Severity** | High |
| **Status** | Open (configuration) |
| **Component** | `backend/settings.py`, `backend/urls.py` |

**Description**  
With `USE_AWS=False`, uploads go to `MEDIA_ROOT` on the container. Railway redeploys can wipe files; URLs may 404 after restart.

**Expected**  
Production uses S3 (`USE_AWS=True`) for all blog uploads.

**Recommendation**  
Enable S3 on Railway; do not rely on local `media/` in production.

---

### BUG-BE-003 — `build_absolute_uri` may use wrong host behind proxy (Medium)

| Field | Detail |
|-------|--------|
| **Severity** | Medium |
| **Status** | Mitigated via `build_public_media_url` |
| **Component** | `ImageUploadView`, Django request host |

**Description**  
Without `PUBLIC_API_BASE_URL`, proxy/Railway internal hostnames can appear in media URLs.

**Fix**  
Set `PUBLIC_API_BASE_URL` in production `.env`.

---

### BUG-BE-004 — No dedicated Quill upload path from spec (Low / By design)

| Field | Detail |
|-------|--------|
| **Severity** | Low |
| **Status** | Closed (intentional) |
| **Component** | API routing |

**Description**  
Spec example used `POST /api/upload/quill/`; implementation uses `POST /api/blogs/upload-image/`.

**Impact**  
None if CRM uses `blogApi.ts` (correct endpoint).

---

### BUG-BE-005 — Image size limit mismatch in docs (Low)

| Field | Detail |
|-------|--------|
| **Severity** | Low |
| **Status** | Open (documentation) |
| **Component** | `blog/utils.py` vs `rich text editor in the crm.md` |

**Description**  
Spec mentions 5 MB; backend and CRM enforce **10 MB** (`MAX_UPLOAD_SIZE_MB`, `MAX_IMAGE_MB`).

**Recommendation**  
Align documentation or add configurable limit.

---

## CRM bugs

### BUG-CRM-001 — Duplicate Quill toolbar (High)

| Field | Detail |
|-------|--------|
| **Severity** | High |
| **Status** | **Fixed** |
| **Component** | `pest crm/src/components/blog/QuillEditor.tsx` |
| **Environment** | Dev (`React.StrictMode` in `main.tsx`) |

**Description**  
Two identical formatting toolbars stacked above the blog body.

**Root cause**  
Quill injects `.ql-toolbar` as a sibling of the editor host. Cleanup only cleared inner HTML of a nested div, leaving the first toolbar. Strict Mode double-mount added a second toolbar.

**Fix**  
Mount Quill on single `rootRef`; `destroyQuillMount()` clears entire container on unmount; init runs once with `[]` deps.

**Verification**  
- [ ] Hard refresh `/blog/create` — exactly **one** toolbar  

---

### BUG-CRM-002 — Images broken in editor after successful upload (Critical)

| Field | Detail |
|-------|--------|
| **Severity** | Critical |
| **Status** | Mitigated in code — depends on BUG-BE-001 |
| **Component** | `QuillEditor.tsx`, `utils/mediaUrl.ts` |

**Description**  
Upload returns 201; editor shows broken image placeholders.

**Root causes**  
1. Invalid/non-public `url` from API (see BUG-BE-001).  
2. Quill `Image.sanitize` stripping or corrupting `src` (patched).  
3. `resolveMediaUrl` not rewriting localhost URLs (patched).

**Fix applied**  
- Custom `Image.sanitize` for `https://` URLs.  
- `insertEditorImage()` fallback sets `src` on DOM if embed fails.  
- `rewriteToApiOrigin()` in `mediaUrl.ts`.

**Verification**  
- [ ] Deploy CRM + backend  
- [ ] Upload image — visible in editor  
- [ ] Save draft — reload edit — images still visible  

---

### BUG-CRM-003 — Blog title/slug in header unclear (Medium)

| Field | Detail |
|-------|--------|
| **Severity** | Medium |
| **Status** | **Fixed** |
| **Component** | `pest crm/src/pages/blog/BlogEditor.tsx` |

**Description**  
Title and slug in top bar used faint placeholder styling; users did not understand where to enter title.

**Fix**  
Title and slug moved to **Content** tab with labels; header shows “Create/Edit Blog Post” only.

---

### BUG-CRM-004 — Settings tab / field placement (Low / UX)

| Field | Detail |
|-------|--------|
| **Severity** | Low |
| **Status** | **Fixed** (by design change) |
| **Component** | `BlogEditor.tsx` |

**Description**  
User requested removal of Settings tab; Excerpt and Status moved to end of SEO tab.

**Verification**  
- [ ] Only **Content** and **SEO** tabs  
- [ ] Excerpt + Status under “Listing & publish” at bottom of SEO  

---

### BUG-CRM-005 — Editor content lost on tab switch / preview (Medium)

| Field | Detail |
|-------|--------|
| **Severity** | Medium |
| **Status** | Open (known limitation) |
| **Component** | `BlogEditor.tsx`, `QuillEditor.tsx` |

**Description**  
Switching to SEO tab or toggling Preview **unmounts** `QuillEditor`. Content remains in `form.content`, but undo/redo history is reset when returning.

**Expected (ideal)**  
Keep editor mounted or preserve history (optional enhancement).

**Workaround**  
Content is not lost; only undo stack resets.

---

### BUG-CRM-006 — No table support in rich text editor (Low)

| Field | Detail |
|-------|--------|
| **Severity** | Low |
| **Status** | Open (feature gap) |
| **Component** | `QuillEditor.tsx` |

**Description**  
Previous TipTap setup had table insert; current Quill toolbar has no table module.

**Impact**  
Users cannot insert tables via toolbar unless HTML pasted manually.

---

### BUG-CRM-007 — Production bundle size warning (Low)

| Field | Detail |
|-------|--------|
| **Severity** | Low |
| **Status** | Open |
| **Component** | Vite build |

**Description**  
`npm run build` warns main chunk > 500 kB (Quill + app code).

**Recommendation**  
Code-split blog routes/editor (future optimization).

---

### BUG-CRM-008 — TipTap packages removed (Info)

| Field | Detail |
|-------|--------|
| **Severity** | Info |
| **Status** | **Fixed** |
| **Component** | `package.json` |

**Description**  
All `@tiptap/*` dependencies removed; editor is Quill-only. No remaining imports in `src/`.

---

## Cross-system integration issues

| ID | Issue | Backend | CRM | Status |
|----|-------|---------|-----|--------|
| INT-001 | Auth token key | JWT `access_token` | `localStorage.access_token` | OK |
| INT-002 | Upload field name | expects `image` | sends `image` in FormData | OK |
| INT-003 | CORS / cookies | API on separate domain | Axios + Bearer | OK if CORS configured |
| INT-004 | Featured image URL | `AbsoluteImageField` | `resolveMediaUrl()` | OK |
| INT-005 | Content HTML storage | `Blog.content` TextField | Quill HTML string | OK |

---

## Test matrix (QA)

| # | Test case | Backend | CRM | Pass? |
|---|-----------|---------|-----|-------|
| 1 | Create blog with title, slug, body | | | |
| 2 | Auto slug from title (new post) | | | |
| 3 | Upload inline image in body | | | |
| 4 | YouTube embed in body | | | |
| 5 | Save draft + reload edit | | | |
| 6 | Publish + toggle status in SEO tab | | | |
| 7 | Featured image upload | | | |
| 8 | Category + tags | | | |
| 9 | SEO meta + Google preview uses `form.slug` | | | |
| 10 | Single Quill toolbar (dev Strict Mode) | | | |
| 11 | Preview mode renders HTML | | | |
| 12 | Public blog API returns content with images | | | |

---

## Deployment requirements (not code bugs)

These are **required** for production image and media behavior:

```env
# Railway (backend)
USE_AWS=True
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_STORAGE_BUCKET_NAME=vacation-blog-user
AWS_S3_REGION_NAME=ap-south-1
AWS_DEFAULT_ACL=public-read
PUBLIC_API_BASE_URL=https://api.vacationbna.site
```

```env
# Vercel (CRM) — optional override
VITE_API_BASE_URL=https://api.vacationbna.site/api
```

**S3 bucket:** Public read policy for `blog/*` (or equivalent) if ACLs are disabled at bucket level.

---

## Files changed (reference)

### Backend
- `blog/views.py` — `ImageUploadView`, public URL helper  
- `blog/media_urls.py` — `build_public_media_url`  
- `backend/settings.py` — `PUBLIC_API_BASE_URL`, `AWS_DEFAULT_ACL`  
- `.env.example`  

### CRM
- `pest crm/src/components/blog/QuillEditor.tsx`  
- `pest crm/src/components/blog/QuillEditor.css`  
- `pest crm/src/pages/blog/BlogEditor.tsx`  
- `pest crm/src/utils/mediaUrl.ts`  
- `pest crm/src/services/blogApi.ts`  
- `pest crm/package.json` (Quill in; TipTap out)  

---

## Sign-off

| Role | Action |
|------|--------|
| Developer | Deploy backend + CRM; set Railway env vars |
| QA | Run test matrix on staging/production |
| DevOps | Confirm S3 bucket policy + `check_s3_storage` |

---

*End of report*
