IMPLEMENT AWS S3 STORAGE FOR BLOG CMS + TECHNICIAN SELFIE UPLOAD
(Django Backend + React CRM + Flutter Partner App + Railway)

OBJECTIVE:
Move all image storage to AWS S3.

Store:

1. Blog Featured Images
2. Blog Editor Images (Quill uploads)
3. Technician Start Job Selfies
4. Future quotation images
5. Profile images

NO local media storage.

────────────────────────
PART 1 — BACKEND (DJANGO)
────────────────────────

Install:

pip install django-storages boto3 pillow

settings.py

INSTALLED_APPS += [
"storages"
]

DEFAULT_FILE_STORAGE =
"storages.backends.s3boto3.S3Boto3Storage"

AWS_STORAGE_BUCKET_NAME =
env("S3_BUCKET_NAME")

AWS_ACCESS_KEY_ID =
env("AWS_ACCESS_KEY_ID")

AWS_SECRET_ACCESS_KEY =
env("AWS_SECRET_ACCESS_KEY")

AWS_S3_REGION_NAME =
env("AWS_REGION")

AWS_QUERYSTRING_AUTH=False

AWS_DEFAULT_ACL=None

AWS_S3_FILE_OVERWRITE=False

AWS_S3_SIGNATURE_VERSION="s3v4"

AWS_S3_OBJECT_PARAMETERS={
"CacheControl":"max-age=86400"
}

MEDIA_URL=
f"https://{bucket}.s3.{region}.amazonaws.com/"

────────────────────────
PART 2 — CREATE STORAGE CLASSES
────────────────────────

storage.py

BlogFeaturedStorage
location=
featured_images/

BlogEditorStorage
location=
quill_uploads/

SelfieStorage
location=
technician_selfies/

ProfileStorage
location=
profiles/

QuotationStorage
location=
quotations/

────────────────────────
PART 3 — BLOG IMAGE FLOW
────────────────────────

Featured upload:

Frontend
→ API
→ Convert WEBP
→ Compress
→ Upload S3
→ Save URL

Folder:

featured_images/

Rules:

jpg
jpeg
png
webp

max:
10MB

convert:
webp

quality:
82

max width:
1920

────────────────────────
PART 4 — QUILL EDITOR IMAGE FLOW
────────────────────────

POST

/api/v1/blog/upload/

Response:

{
"url":"https://..."
}

Store:

quill_uploads/

Auto:
WEBP

quality:
80

────────────────────────
PART 5 — TECHNICIAN SELFIE FLOW
────────────────────────

Partner App

Start Job

Take Selfie

POST

/api/v1/partner/jobs/{id}/start/

multipart

Fields:

selfie
lat
lng
device_time

Backend:

Validate:

image exists

size<10mb

Save:

technician_selfies/

DB:

job_start_selfie

job_start_selfie_url

────────────────────────
PART 6 — RAILWAY VARIABLES
────────────────────────

Add Environment Variables:

AWS_ACCESS_KEY_ID

AWS_SECRET_ACCESS_KEY

AWS_REGION

S3_BUCKET_NAME

MEDIA_BACKEND=s3

IMAGE_MAX_MB=10

IMAGE_WEBP_QUALITY=82

IMAGE_MAX_WIDTH=1920

Do NOT hardcode secrets.

────────────────────────
PART 7 — FRONTEND (CRM)
────────────────────────

React Upload

Show:

Uploading...

Progress

Preview

Retry

Success

Save only S3 URL.

────────────────────────
PART 8 — FLUTTER
────────────────────────

Use:

multipart upload

Compress before upload

Show:

Uploading selfie...

Disable button

Prevent double submit

────────────────────────
PART 9 — SECURITY
────────────────────────

Allowed:

image/jpeg
image/png
image/webp

Block:

svg
exe
pdf
zip

Generate random filenames

Example:

blogs/
2026/
05/
uuid.webp

Never expose secret keys.

────────────────────────
PART 10 — TEST
────────────────────────

Test:

Blog upload

Selfie upload

Delete image

Edit image

10MB upload

Slow internet

Parallel uploads

Railway deploy

No broken URLs
