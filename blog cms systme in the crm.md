Create a complete Blog CMS System for Pest Control CRM + Website with proper SEO architecture and scalable backend structure.

Need 3 parts:

1. CRM Admin Blog CMS
2. Backend APIs
3. Public Website Blog System

System must be lightweight, SEO-friendly, crawl-friendly, and production ready.

---

## CORE REQUIREMENT

Need simple but powerful blog CMS.

Admin should be able to:

* Create blog
* Edit blog
* Delete blog
* Draft / Publish
* Upload images
* Manage SEO
* Manage slugs
* Manage categories

No word limit in all fields .

Must support long-form SEO blogs.

---

## BLOG FIELDS

Create these fields:

Basic:

* title
* slug
* content (rich editor)
* featured_image
* excerpt

SEO:

* meta_title
* meta_description
* target_keywords
* canonical_url
* schema_type

Status:

* draft
* published

Additional:

* author
* category
* tags
* reading_time
* publish_date
* created_at
* updated_at
* views_count

---

## IMAGE SYSTEM

Need proper image optimization system.

Requirements:

* max upload size = 10MB
* auto convert image to WEBP
* auto compress image slightly
* keep high quality
* generate responsive sizes

Example:

* thumbnail
* medium
* full

Need:

* lazy loading support
* SEO alt text support
* image title support

Backend should automatically:

* convert jpg/png/jpeg → webp
* compress
* save optimized version

Need fallback error handling.

---

## CONTENT EDITOR

Need modern rich text editor.

Features:

* headings
* bold
* tables
* links
* lists
* image embed
* youtube embed
* code blocks
* FAQ blocks

Need SEO-friendly HTML output.

No inline messy styles.

Clean semantic HTML only.

---

## SEO REQUIREMENTS

Very important.

Need:

* dynamic meta tags
* dynamic canonical URLs
* open graph tags
* twitter meta tags
* schema markup
* sitemap support
* robots.txt support
* clean URLs

Example:
/blog/best-cockroach-control-mumbai

NOT:
?id=22

Need:

* automatic slug generation
* slug uniqueness validation

---

## GOOGLE CRAWL OPTIMIZATION

Need best practices for indexing.

Implement:

* server-side rendering friendly structure
* sitemap.xml auto generation
* blog structured data
* breadcrumb schema
* article schema
* FAQ schema

Need:

* proper heading hierarchy
* H1 only once
* SEO validation support

---

## CRM BLOG CMS PAGES

Need these admin pages:

1. Blog Dashboard

* total blogs
* published
* drafts
* total views

2. Blog List Page

* search
* filter
* pagination
* edit
* delete
* publish toggle

3. Create Blog Page

* full editor
* SEO fields
* image upload
* preview mode

4. Blog Analytics Page

* views
* traffic
* top blogs

---

## PUBLIC WEBSITE BLOG PAGES

Need frontend pages:

1. Blog Listing Page

* latest blogs
* categories
* search
* pagination

2. Blog Detail Page

* SEO optimized
* related blogs
* table of contents
* share buttons

3. Category Page
4. Tag Page
5. Search Page

---

## REQUIRED BACKEND APIs

Need proper REST APIs.

AUTH APIs:

1. POST /api/blogs/create/
2. PUT /api/blogs/{id}/update/
3. DELETE /api/blogs/{id}/delete/
4. GET /api/blogs/
5. GET /api/blogs/{slug}/
6. POST /api/blogs/upload-image/

PUBLIC APIs:
7. GET /api/public/blogs/
8. GET /api/public/blogs/{slug}/
9. GET /api/public/categories/
10. GET /api/public/tags/
11. GET /api/public/related-blogs/

SEO APIs:
12. GET /sitemap.xml
13. GET /robots.txt

Analytics:
14. POST /api/blogs/view/

---

## DATABASE BEST PRACTICES

Need:

* indexed slug
* indexed publish_date
* indexed status
* indexed category

Need optimized queryset usage:

* select_related
* prefetch_related

Need scalable pagination.

---

## SECURITY

Need:

* upload validation
* XSS protection
* HTML sanitization
* secure image upload
* rate limiting

---

## PERFORMANCE

Need:

* caching
* optimized queries
* lazy loading
* compressed responses
* image CDN ready structure

---

## TECH STACK

Backend:

* Django
* DRF
* Pillow for image optimization

Frontend:

* React

Editor:

* CKEditor or TipTap

---

## IMPORTANT

Need production-grade architecture.
Need scalable structure.
Need SEO-first implementation.
Need Google crawl friendly output.
Need mobile-first rendering.

Please create:

* backend flow
* API architecture
* database models
* frontend page flow
* admin CMS flow
* SEO flow
* image optimization flow
* sitemap generation flow

Need complete implementation structure before coding.
