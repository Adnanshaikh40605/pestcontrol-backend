# PestControl99.com — Blog Website Implementation Guide

**Website Domain:** `https://www.pestcontrol99.com`  
**Backend API:** `https://api.vacationbna.site`  
**Tech Stack:** Next.js (recommended for SSR/SEO) or React + SSR framework  
**Purpose:** Public-facing customer website with full SEO-optimized blog system

---

## BACKEND CROSS-CHECK RESULT

### ✅ Verified Working

| Component | Status | Notes |
|---|---|---|
| Blog models (Category, Tag, Blog) | ✅ Pass | All fields indexed, migrations clean |
| Serializers | ✅ Pass | Source conflicts fixed, validation passes |
| Admin APIs (JWT auth) | ✅ Pass | All CRUD, toggle-publish, upload-image |
| Public APIs (no auth, cached) | ✅ Pass | List, detail, categories, tags, related |
| Image optimization (WebP variants) | ✅ Pass | Signal-based, detects new uploads |
| View tracking | ✅ Pass | Rate-limited, IP-deduplicated |
| sitemap.xml | ✅ Pass | Dynamic, cached 1h, includes blogs + categories |
| robots.txt | ✅ Pass | Correct Disallow rules + Sitemap reference |
| Django system check | ✅ 0 issues | |

### Fixed Issues (Cross-check)
- Serializer `source` conflicts removed — `category_detail` and `tags_detail` now use `SerializerMethodField`
- Explicit `create()` / `update()` added to `BlogAdminSerializer` for M2M tag handling
- `pre_save` signal added to detect new image uploads on existing blogs (prevents skipping re-processing)
- Cleaned unused imports from `views.py` (`BytesIO`, `ValidationError`, `method_decorator`, `cache_page`, `IsBlogAdmin`, `CategoryLiteSerializer`, `TagLiteSerializer`, `BlogDashboardSerializer`)
- `F("views_count")` import moved to module level

---

## WEBSITE PAGES — FULL IMPLEMENTATION PLAN

### Page 1: Blog Listing Page
**URL:** `https://www.pestcontrol99.com/blog/`

#### What it does
- Shows all published blogs, latest first
- Filter by category, filter by tag
- Search blogs
- Paginated (10 per page)

#### API Used
```
GET https://api.vacationbna.site/api/public/blogs/
```

**Query Parameters:**
| Param | Type | Example | Purpose |
|---|---|---|---|
| `page` | integer | `?page=2` | Pagination |
| `page_size` | integer | `?page_size=10` | Results per page (max 50) |
| `category` | slug | `?category=cockroach-control` | Filter by category |
| `tag` | slug | `?tag=mumbai` | Filter by tag |
| `q` | string | `?q=pest+control` | Search |

**Response Shape:**
```json
{
  "count": 48,
  "total_pages": 5,
  "current_page": 1,
  "next": "https://api.vacationbna.site/api/public/blogs/?page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "title": "Best Cockroach Control Methods in Mumbai",
      "slug": "best-cockroach-control-methods-mumbai",
      "excerpt": "Short description here...",
      "featured_image": "https://api.vacationbna.site/media/blog/images/2026/5/abc123_full.webp",
      "image_thumbnail": "https://api.vacationbna.site/media/blog/images/2026/5/abc123_thumb.webp",
      "featured_image_alt": "Cockroach control Mumbai",
      "meta_title": "Best Cockroach Control Mumbai | PestControl99",
      "meta_description": "Expert cockroach control services...",
      "publish_date": "2026-05-14T10:00:00+05:30",
      "reading_time": 5,
      "views_count": 1240,
      "author_name": "Adnan Khan",
      "category": { "id": 1, "name": "Cockroach Control", "slug": "cockroach-control" },
      "tags": [
        { "id": 3, "name": "Mumbai", "slug": "mumbai" }
      ]
    }
  ]
}
```

#### SEO Implementation
```html
<!-- In <head> -->
<title>Pest Control Blog | Tips, Guides & Expert Advice | PestControl99</title>
<meta name="description" content="Read expert pest control blogs, tips, and guides for Mumbai & India. Cockroach, termite, rodent, mosquito control advice." />
<meta name="robots" content="index, follow" />
<link rel="canonical" href="https://www.pestcontrol99.com/blog/" />

<!-- Open Graph -->
<meta property="og:title" content="Pest Control Blog | PestControl99" />
<meta property="og:description" content="Expert pest control guides for homes and businesses." />
<meta property="og:type" content="website" />
<meta property="og:url" content="https://www.pestcontrol99.com/blog/" />
<meta property="og:image" content="https://www.pestcontrol99.com/og-blog.jpg" />

<!-- Twitter Card -->
<meta name="twitter:card" content="summary_large_image" />
<meta name="twitter:title" content="Pest Control Blog | PestControl99" />
<meta name="twitter:description" content="Expert pest control tips and guides." />
```

#### Structured Data (JSON-LD)
```json
{
  "@context": "https://schema.org",
  "@type": "Blog",
  "name": "PestControl99 Blog",
  "url": "https://www.pestcontrol99.com/blog/",
  "description": "Expert pest control tips, guides, and advice.",
  "publisher": {
    "@type": "Organization",
    "name": "PestControl99",
    "url": "https://www.pestcontrol99.com",
    "logo": {
      "@type": "ImageObject",
      "url": "https://www.pestcontrol99.com/logo.png"
    }
  }
}
```

#### Breadcrumb Structured Data
```json
{
  "@context": "https://schema.org",
  "@type": "BreadcrumbList",
  "itemListElement": [
    { "@type": "ListItem", "position": 1, "name": "Home", "item": "https://www.pestcontrol99.com/" },
    { "@type": "ListItem", "position": 2, "name": "Blog", "item": "https://www.pestcontrol99.com/blog/" }
  ]
}
```

---

### Page 2: Blog Detail Page
**URL:** `https://www.pestcontrol99.com/blog/{slug}/`  
**Example:** `https://www.pestcontrol99.com/blog/best-cockroach-control-methods-mumbai/`

#### What it does
- Displays full blog content (sanitized HTML from rich editor)
- Shows featured image (responsive: thumbnail → medium → full)
- Table of contents (auto-generated from H2/H3 headings in content)
- Author, publish date, reading time, category, tags
- Related blogs section
- Social share buttons
- Auto-increments view count on page load

#### APIs Used

**1. Fetch blog detail:**
```
GET https://api.vacationbna.site/api/public/blogs/{slug}/
```

**Response Shape:**
```json
{
  "id": 1,
  "title": "Best Cockroach Control Methods in Mumbai",
  "slug": "best-cockroach-control-methods-mumbai",
  "content": "<h2 id='introduction'>Introduction</h2><p>Cockroaches are...</p>",
  "excerpt": "Comprehensive guide to cockroach control...",
  "featured_image": "https://api.vacationbna.site/media/blog/images/2026/5/abc_full.webp",
  "featured_image_alt": "Cockroach control expert spraying in Mumbai kitchen",
  "featured_image_title": "Professional cockroach treatment",
  "image_thumbnail": "https://api.vacationbna.site/media/blog/images/2026/5/abc_thumb.webp",
  "image_medium": "https://api.vacationbna.site/media/blog/images/2026/5/abc_medium.webp",
  "meta_title": "Best Cockroach Control Mumbai 2026 | PestControl99",
  "meta_description": "Expert methods to eliminate cockroaches. Professional pest control services in Mumbai.",
  "target_keywords": "cockroach control mumbai, pest control mumbai, cockroach treatment",
  "keywords_list": ["cockroach control mumbai", "pest control mumbai", "cockroach treatment"],
  "canonical_url": "",
  "schema_type": "Article",
  "og_title": "Best Cockroach Control Mumbai | PestControl99",
  "og_description": "Expert methods to eliminate cockroaches permanently.",
  "status": "published",
  "publish_date": "2026-05-14T10:00:00+05:30",
  "author_name": "Adnan Khan",
  "category": { "id": 1, "name": "Cockroach Control", "slug": "cockroach-control" },
  "tags": [
    { "id": 3, "name": "Mumbai", "slug": "mumbai" },
    { "id": 7, "name": "Cockroach", "slug": "cockroach" }
  ],
  "reading_time": 7,
  "views_count": 1245,
  "created_at": "2026-05-01T09:00:00+05:30",
  "updated_at": "2026-05-14T10:00:00+05:30"
}
```

**2. Fetch related blogs:**
```
GET https://api.vacationbna.site/api/public/related-blogs/?slug={slug}&limit=4
```

**3. Track view (call on page mount, once per session):**
```
POST https://api.vacationbna.site/api/blogs/view/
Content-Type: application/json

{ "slug": "best-cockroach-control-methods-mumbai" }
```

#### SEO Implementation
```html
<!-- Dynamic from API response -->
<title>{blog.meta_title || blog.title + " | PestControl99"}</title>
<meta name="description" content="{blog.meta_description || blog.excerpt}" />
<meta name="keywords" content="{blog.target_keywords}" />
<meta name="robots" content="index, follow" />
<link rel="canonical" href="{blog.canonical_url || 'https://www.pestcontrol99.com/blog/' + blog.slug + '/'}" />

<!-- Open Graph -->
<meta property="og:title" content="{blog.og_title || blog.meta_title}" />
<meta property="og:description" content="{blog.og_description || blog.meta_description}" />
<meta property="og:type" content="article" />
<meta property="og:url" content="https://www.pestcontrol99.com/blog/{blog.slug}/" />
<meta property="og:image" content="{blog.featured_image}" />
<meta property="og:image:alt" content="{blog.featured_image_alt}" />
<meta property="article:published_time" content="{blog.publish_date}" />
<meta property="article:modified_time" content="{blog.updated_at}" />
<meta property="article:author" content="{blog.author_name}" />
<meta property="article:section" content="{blog.category.name}" />
{blog.tags.map(tag => `<meta property="article:tag" content="${tag.name}" />`)}

<!-- Twitter Card -->
<meta name="twitter:card" content="summary_large_image" />
<meta name="twitter:title" content="{blog.og_title}" />
<meta name="twitter:description" content="{blog.og_description}" />
<meta name="twitter:image" content="{blog.featured_image}" />
```

#### Structured Data — Article Schema
```json
{
  "@context": "https://schema.org",
  "@type": "{blog.schema_type}",
  "headline": "{blog.title}",
  "description": "{blog.meta_description}",
  "image": {
    "@type": "ImageObject",
    "url": "{blog.featured_image}",
    "description": "{blog.featured_image_alt}"
  },
  "author": {
    "@type": "Person",
    "name": "{blog.author_name}"
  },
  "publisher": {
    "@type": "Organization",
    "name": "PestControl99",
    "logo": {
      "@type": "ImageObject",
      "url": "https://www.pestcontrol99.com/logo.png"
    }
  },
  "datePublished": "{blog.publish_date}",
  "dateModified": "{blog.updated_at}",
  "mainEntityOfPage": {
    "@type": "WebPage",
    "@id": "https://www.pestcontrol99.com/blog/{blog.slug}/"
  },
  "keywords": "{blog.target_keywords}",
  "articleSection": "{blog.category.name}",
  "wordCount": 1400
}
```

#### Breadcrumb Structured Data
```json
{
  "@context": "https://schema.org",
  "@type": "BreadcrumbList",
  "itemListElement": [
    { "@type": "ListItem", "position": 1, "name": "Home", "item": "https://www.pestcontrol99.com/" },
    { "@type": "ListItem", "position": 2, "name": "Blog", "item": "https://www.pestcontrol99.com/blog/" },
    { "@type": "ListItem", "position": 3, "name": "{blog.category.name}", "item": "https://www.pestcontrol99.com/blog/category/{blog.category.slug}/" },
    { "@type": "ListItem", "position": 4, "name": "{blog.title}", "item": "https://www.pestcontrol99.com/blog/{blog.slug}/" }
  ]
}
```

#### Featured Image — Responsive Implementation
```html
<!-- Use srcset for responsive WebP images -->
<picture>
  <source
    type="image/webp"
    srcset="
      {blog.image_thumbnail} 400w,
      {blog.image_medium}    800w,
      {blog.featured_image}  1600w
    "
    sizes="(max-width: 480px) 400px, (max-width: 900px) 800px, 1600px"
  />
  <img
    src="{blog.image_medium}"
    alt="{blog.featured_image_alt}"
    title="{blog.featured_image_title}"
    width="800"
    height="500"
    loading="lazy"
    decoding="async"
  />
</picture>
```

---

### Page 3: Category Page
**URL:** `https://www.pestcontrol99.com/blog/category/{category-slug}/`  
**Example:** `https://www.pestcontrol99.com/blog/category/cockroach-control/`

#### APIs Used

**1. Fetch all categories (for sidebar/menu):**
```
GET https://api.vacationbna.site/api/public/categories/
```

**2. Fetch blogs filtered by category:**
```
GET https://api.vacationbna.site/api/public/blogs/?category={slug}&page=1
```

#### SEO Implementation
```html
<title>{category.name} Blogs | PestControl99</title>
<meta name="description" content="{category.meta_description || 'Expert ' + category.name + ' guides, tips and services from PestControl99.'}" />
<link rel="canonical" href="https://www.pestcontrol99.com/blog/category/{category.slug}/" />
<meta property="og:type" content="website" />
```

---

### Page 4: Tag Page
**URL:** `https://www.pestcontrol99.com/blog/tag/{tag-slug}/`  
**Example:** `https://www.pestcontrol99.com/blog/tag/mumbai/`

#### APIs Used

**1. Fetch blogs filtered by tag:**
```
GET https://api.vacationbna.site/api/public/blogs/?tag={slug}&page=1
```

**2. Fetch all tags (for tag cloud):**
```
GET https://api.vacationbna.site/api/public/tags/
```

#### SEO Implementation
```html
<title>Blogs tagged "{tag.name}" | PestControl99</title>
<meta name="description" content="All pest control blogs tagged {tag.name}." />
<link rel="canonical" href="https://www.pestcontrol99.com/blog/tag/{tag.slug}/" />
<meta name="robots" content="noindex, follow" />  <!-- Tag pages: noindex to avoid thin content -->
```

---

### Page 5: Search Page
**URL:** `https://www.pestcontrol99.com/blog/search/?q={query}`

#### API Used
```
GET https://api.vacationbna.site/api/public/blogs/?q={search_term}&page=1
```

#### SEO Implementation
```html
<title>Search results for "{query}" | PestControl99 Blog</title>
<meta name="robots" content="noindex, follow" />  <!-- Search results: noindex -->
<link rel="canonical" href="https://www.pestcontrol99.com/blog/" />
```

---

## SEO ENDPOINTS (Served from backend)

### Sitemap
```
GET https://api.vacationbna.site/sitemap.xml
```

**What's included:**
- Homepage: `/` — priority 1.0, changefreq daily
- Blog listing: `/blog/` — priority 0.9, changefreq daily
- Each published blog: `/blog/{slug}/` — priority 0.8, changefreq weekly, lastmod = updated_at
- Each active category: `/blog/category/{slug}/` — priority 0.6, changefreq weekly

**Important:** Submit this sitemap URL to Google Search Console:  
`https://api.vacationbna.site/sitemap.xml`

### Robots.txt
```
GET https://api.vacationbna.site/robots.txt
```

**Content Generated:**
```
User-agent: *
Allow: /
Disallow: /admin/
Disallow: /api/token/
Disallow: /api/schema/
Disallow: /api/docs/
Allow: /api/public/
Sitemap: https://www.pestcontrol99.com/sitemap.xml
```

**Note:** The website frontend should also have its own `/robots.txt` at `pestcontrol99.com/robots.txt`. Serve the same content or reference the sitemap from the frontend domain.

---

## COMPLETE API REFERENCE

### Public Blog APIs (No Authentication Required)

| # | Method | Endpoint | Purpose |
|---|---|---|---|
| 1 | GET | `/api/public/blogs/` | List all published blogs (paginated, filterable) |
| 2 | GET | `/api/public/blogs/{slug}/` | Single blog detail by SEO slug |
| 3 | GET | `/api/public/categories/` | All active categories |
| 4 | GET | `/api/public/tags/` | All tags |
| 5 | GET | `/api/public/related-blogs/?slug={slug}&limit=4` | Related blogs for a post |
| 6 | POST | `/api/blogs/view/` | Track page view (body: `{"slug": "..."}`) |
| 7 | GET | `/sitemap.xml` | Dynamic XML sitemap |
| 8 | GET | `/robots.txt` | Robots instructions |

### Query Parameters for Blog List
```
/api/public/blogs/?page=1&page_size=10&category=cockroach-control&tag=mumbai&q=pest+control
```

---

## CORS CONFIGURATION

The backend already allows requests from:
- `https://pestcontrol-crm-frontend.vercel.app` (CRM)
- Any `*.vercel.app` subdomain
- `https://*.pestcontrol99.com` subdomains

**Add your website domain to CORS_ALLOWED_ORIGINS in settings.py:**
```python
CORS_ALLOWED_ORIGINS = [
    "https://pestcontrol-crm-frontend.vercel.app",
    "https://www.pestcontrol99.com",      # Add this
    "https://pestcontrol99.com",           # Add this (non-www)
]
```

**Also add to CSRF_TRUSTED_ORIGINS:**
```python
CSRF_TRUSTED_ORIGINS = [
    "https://api.vacationbna.site",
    "https://pestcontrol-crm-frontend.vercel.app",
    "https://www.pestcontrol99.com",      # Add this
    "https://pestcontrol99.com",           # Add this
]
```

---

## NEXT.JS IMPLEMENTATION APPROACH (Recommended)

Use **Next.js with App Router** for the best SEO:

### Why Next.js
- Server-Side Rendering (SSR) — Google crawls fully rendered HTML
- `generateMetadata()` function — dynamic meta tags from API
- `generateStaticParams()` — pre-generate blog pages at build time
- Image optimization via `next/image`
- Built-in sitemap support

### Folder Structure
```
src/
  app/
    blog/
      page.tsx                    → /blog/ (listing)
      [slug]/
        page.tsx                  → /blog/{slug}/ (detail)
      category/
        [slug]/
          page.tsx                → /blog/category/{slug}/
      tag/
        [slug]/
          page.tsx                → /blog/tag/{slug}/
      search/
        page.tsx                  → /blog/search/
    sitemap.ts                    → /sitemap.xml (or use backend one)
    robots.ts                     → /robots.txt
  lib/
    api.ts                        → API wrapper functions
  components/
    blog/
      BlogCard.tsx
      BlogDetail.tsx
      RelatedBlogs.tsx
      TableOfContents.tsx
      BlogPagination.tsx
      CategorySidebar.tsx
      TagCloud.tsx
      ShareButtons.tsx
      FeaturedImage.tsx
```

### API Wrapper (lib/api.ts)
```typescript
const API_BASE = "https://api.vacationbna.site";

export async function getBlogs(params?: {
  page?: number;
  page_size?: number;
  category?: string;
  tag?: string;
  q?: string;
}) {
  const query = new URLSearchParams(params as Record<string, string>);
  const res = await fetch(`${API_BASE}/api/public/blogs/?${query}`, {
    next: { revalidate: 300 }, // ISR: revalidate every 5 minutes
  });
  if (!res.ok) throw new Error("Failed to fetch blogs");
  return res.json();
}

export async function getBlog(slug: string) {
  const res = await fetch(`${API_BASE}/api/public/blogs/${slug}/`, {
    next: { revalidate: 300 },
  });
  if (res.status === 404) return null;
  if (!res.ok) throw new Error("Failed to fetch blog");
  return res.json();
}

export async function getRelatedBlogs(slug: string, limit = 4) {
  const res = await fetch(
    `${API_BASE}/api/public/related-blogs/?slug=${slug}&limit=${limit}`,
    { next: { revalidate: 300 } }
  );
  return res.json();
}

export async function getCategories() {
  const res = await fetch(`${API_BASE}/api/public/categories/`, {
    next: { revalidate: 600 }, // 10 minutes
  });
  return res.json();
}

export async function getTags() {
  const res = await fetch(`${API_BASE}/api/public/tags/`, {
    next: { revalidate: 600 },
  });
  return res.json();
}

export async function trackView(slug: string) {
  // Call from client-side useEffect only
  await fetch(`${API_BASE}/api/blogs/view/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ slug }),
  });
}
```

### Blog Detail Page — generateMetadata
```typescript
// app/blog/[slug]/page.tsx

import type { Metadata } from "next";
import { getBlog } from "@/lib/api";

export async function generateMetadata({ params }: { params: { slug: string } }): Promise<Metadata> {
  const blog = await getBlog(params.slug);
  if (!blog) return { title: "Not Found" };

  return {
    title: blog.meta_title || `${blog.title} | PestControl99`,
    description: blog.meta_description || blog.excerpt,
    keywords: blog.target_keywords,
    alternates: {
      canonical: blog.canonical_url || `https://www.pestcontrol99.com/blog/${blog.slug}/`,
    },
    openGraph: {
      title: blog.og_title || blog.meta_title,
      description: blog.og_description || blog.meta_description,
      type: "article",
      url: `https://www.pestcontrol99.com/blog/${blog.slug}/`,
      images: [{ url: blog.featured_image, alt: blog.featured_image_alt }],
      publishedTime: blog.publish_date,
      modifiedTime: blog.updated_at,
      authors: [blog.author_name],
      section: blog.category?.name,
      tags: blog.tags?.map((t: any) => t.name),
    },
    twitter: {
      card: "summary_large_image",
      title: blog.og_title,
      description: blog.og_description,
      images: [blog.featured_image],
    },
  };
}
```

---

## TABLE OF CONTENTS — Auto-Generation

Extract headings from blog HTML content on the frontend:

```typescript
// lib/toc.ts
export interface TocItem {
  id: string;
  text: string;
  level: number;
}

export function extractToc(html: string): TocItem[] {
  if (typeof window === "undefined") {
    // Server-side: use regex
    const matches = [...html.matchAll(/<h([2-4])[^>]*id="([^"]*)"[^>]*>([^<]*)<\/h\d>/gi)];
    return matches.map(([, level, id, text]) => ({
      id,
      text: text.replace(/<[^>]+>/g, ""),
      level: parseInt(level),
    }));
  }
  // Client-side: use DOM
  const div = document.createElement("div");
  div.innerHTML = html;
  return Array.from(div.querySelectorAll("h2, h3, h4")).map((el) => ({
    id: el.id || el.textContent!.toLowerCase().replace(/\s+/g, "-"),
    text: el.textContent || "",
    level: parseInt(el.tagName[1]),
  }));
}
```

**Note:** The blog content from the CKEditor/TipTap rich editor must add `id` attributes to headings for TOC anchors to work. Configure the editor to auto-add heading IDs.

---

## SHARE BUTTONS — Social Sharing URLs

```typescript
// components/blog/ShareButtons.tsx
const shareUrls = {
  whatsapp: `https://api.whatsapp.com/send?text=${encodeURIComponent(blog.title + " " + pageUrl)}`,
  twitter:  `https://twitter.com/intent/tweet?text=${encodeURIComponent(blog.title)}&url=${encodeURIComponent(pageUrl)}`,
  facebook: `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(pageUrl)}`,
  linkedin: `https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(pageUrl)}`,
  copy:     pageUrl, // copy to clipboard
};
```

---

## PERFORMANCE CHECKLIST

| Item | How |
|---|---|
| Images served as WebP | Backend auto-converts to WebP |
| Responsive images | Use `srcset` with thumbnail/medium/full from API |
| Lazy load images | `loading="lazy"` on all blog card images |
| ISR (Incremental Static Regen) | `next: { revalidate: 300 }` in fetch calls |
| Cached API responses | Backend caches all public APIs for 5 minutes |
| Preconnect to API | `<link rel="preconnect" href="https://api.vacationbna.site" />` in `<head>` |
| Compress HTML | Next.js does this automatically |
| CDN-ready images | Media URLs are absolute — can be proxied through Cloudflare |

---

## GOOGLE SEARCH CONSOLE SETUP

After deploying:

1. Add property `https://www.pestcontrol99.com` in Google Search Console
2. Submit sitemap: `https://api.vacationbna.site/sitemap.xml`
3. Or generate frontend sitemap at `https://www.pestcontrol99.com/sitemap.xml` pointing to the same URLs
4. Request indexing for blog listing page: `/blog/`
5. Monitor Coverage report for any crawl errors

---

## ENVIRONMENT VARIABLES (Frontend)

```env
# .env.local (Next.js)
NEXT_PUBLIC_API_URL=https://api.vacationbna.site
NEXT_PUBLIC_SITE_URL=https://www.pestcontrol99.com
```

---

## BACKEND ENV VARIABLE TO ADD

Add this to your Railway environment variables:
```
SITE_BASE_URL=https://www.pestcontrol99.com
```

This ensures the sitemap.xml generates correct `<loc>` URLs pointing to `pestcontrol99.com`, not the API domain.

---

## DEPLOYMENT CHECKLIST

- [ ] Add `SITE_BASE_URL=https://www.pestcontrol99.com` to Railway env vars
- [ ] Add `pestcontrol99.com` to `CORS_ALLOWED_ORIGINS` in settings.py
- [ ] Add `pestcontrol99.com` to `CSRF_TRUSTED_ORIGINS` in settings.py
- [ ] Run `py manage.py migrate` on production to apply blog migrations
- [ ] Submit sitemap to Google Search Console
- [ ] Add Google Analytics / GTM to website frontend
- [ ] Test view tracking API from website domain
- [ ] Test all public API endpoints from website domain
- [ ] Verify WebP images load correctly from `api.vacationbna.site/media/`
- [ ] Check robots.txt is accessible at `api.vacationbna.site/robots.txt`
- [ ] Test sitemap at `api.vacationbna.site/sitemap.xml` — all URLs should have `pestcontrol99.com` as base
