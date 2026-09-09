# SEO Meta Audit & Documentation Task

Analyze the entire website and create a complete SEO metadata documentation file named:

`SEO_META_DOCUMENTATION.md`

## Objective

Perform a full website audit and document all pages, routes, and SEO metadata requirements. The output should be a professional Markdown (.md) file that can be used by developers, SEO teams, and content teams.

---

## Step 1: Crawl Entire Website

Scan and identify all pages including:

### Public Pages

* Home
* About Us
* Contact Us
* Services
* Pricing
* FAQ
* Blog Listing
* Blog Details
* Category Pages
* Search Pages
* Location Pages
* Property Pages
* Landing Pages
* Legal Pages

### Authentication Pages

* Login
* Register
* Forgot Password
* Reset Password
* Verify OTP

### Dashboard Pages

* User Dashboard
* Profile
* Settings
* Notifications
* Bookings
* Leads
* CRM Pages
* Reports
* Analytics

### Dynamic Pages

* Property Details
* Blog Details
* Category Details
* City Pages
* Service Pages
* Product Pages

---

## Step 2: Create SEO Documentation

For every page create a table:

| Page Name | URL | Meta Title | Meta Description | H1 | Canonical URL | Index/NoIndex | Priority |
| --------- | --- | ---------- | ---------------- | -- | ------------- | ------------- | -------- |

Example:

| Home | / | Best Villas & Bungalows Booking Platform in India | VacationBNA | Book villas, bungalows, cottages and resorts directly from owners with zero commission. | Find Your Perfect Stay | Yes | Index | High |

---

## Step 3: SEO Recommendations

For each page provide:

### Meta Title

* 50-60 characters
* Keyword optimized
* Unique

### Meta Description

* 140-160 characters
* Clear CTA
* Keyword optimized

### H1 Tag

* One H1 only
* Relevant to page intent

### URL Structure

Check:

* SEO friendly URLs
* Lowercase URLs
* Hyphen separated slugs
* No duplicate URLs

---

## Step 4: Technical SEO Audit

Check and document:

### Metadata

* Missing title tags
* Missing meta descriptions
* Duplicate titles
* Duplicate descriptions

### Heading Structure

* Missing H1
* Multiple H1 issues
* Incorrect heading hierarchy

### Images

* Missing alt tags
* Large image sizes
* Missing image optimization

### Internal Linking

* Orphan pages
* Broken links
* Missing internal links

### Schema Markup

Recommend schema for:

* Organization
* LocalBusiness
* FAQ
* BlogPosting
* BreadcrumbList
* Product
* Service
* Article
* Review
* AggregateRating

---

## Step 5: Generate SEO Implementation Plan

Create a section:

# SEO Fix Priority

## Critical

Pages that must be fixed immediately

## High Priority

Pages affecting rankings

## Medium Priority

Optimization opportunities

## Low Priority

Nice-to-have improvements

---

## Step 6: Create Next.js/Django Implementation Examples

For every page provide:

### Next.js Metadata Example

```tsx
export const metadata = {
  title: "",
  description: "",
  keywords: [],
  alternates: {
    canonical: ""
  }
};
```

### Django SEO Example

```python
SEO_TITLE = ""
SEO_DESCRIPTION = ""
```

---

## Step 7: Final Deliverables

Generate:

1. SEO_META_DOCUMENTATION.md
2. SEO_AUDIT_REPORT.md
3. SEO_FIXES_CHECKLIST.md
4. SEO_PRIORITY_ROADMAP.md

The documentation must cover 100% of website pages and include all existing and missing SEO metadata with recommendations for improvement.
