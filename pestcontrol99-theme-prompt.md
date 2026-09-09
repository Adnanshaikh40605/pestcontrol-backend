# PestControl99 — Website Theme Redesign Prompt
## For: Google Stitch / Cursor / Lovable / Any AI Dev Tool
## Scope: Full site CSS theme update based on logo color system

---

## OBJECTIVE

Redesign the entire visual theme of pestcontrol99.com to match the brand identity defined by the logo. The logo uses two colors — **navy blue** and **forest green** — with clean white. Apply this consistently across every element: buttons, navbars, headings, cards, forms, icons, badges, and footers.

Do NOT change layout structure, content, or page hierarchy. Only update visual styling (colors, typography, spacing, shadows, borders, and interactive states).

---

## BRAND COLOR TOKENS

Define these as CSS custom properties in `:root`. Every element on the site MUST reference these variables — no hardcoded hex values anywhere else in the codebase.

```css
:root {
  /* ── NAVY FAMILY (Primary) ──────────────────── */
  --navy-dark:     #111C4E;   /* Footer bg, hero bg, overlay */
  --navy-base:     #1B2A6B;   /* Main headings, primary buttons, nav bg */
  --navy-light:    #2D3E8A;   /* Hover states on navy elements */
  --navy-pale:     #E8EBF5;   /* Navy-tinted light backgrounds */

  /* ── GREEN FAMILY (Accent) ──────────────────── */
  --green-dark:    #1A6B2D;   /* Hover state on green buttons */
  --green-base:    #1E7E34;   /* Logo green, CTA buttons, active states */
  --green-bright:  #28A745;   /* Hover highlights, success badges */
  --green-pale:    #EAF5EC;   /* Section backgrounds, icon bg, tag fills */
  --green-border:  rgba(30, 126, 52, 0.25); /* Subtle green borders on cards */

  /* ── NEUTRALS ────────────────────────────────── */
  --white:         #FFFFFF;
  --off-white:     #F7F9F7;   /* Alternate section backgrounds */
  --divider:       #E2E8F0;   /* Borders, HR lines */
  --slate:         #4A5568;   /* Body text */
  --slate-light:   #718096;   /* Secondary text, captions, placeholders */
  --slate-pale:    #F1F5F9;   /* Input backgrounds */

  /* ── SEMANTIC ────────────────────────────────── */
  --color-success: var(--green-base);
  --color-error:   #DC3545;
  --color-warning: #F59E0B;
  --color-info:    var(--navy-base);

  /* ── SHADOWS ─────────────────────────────────── */
  --shadow-sm:     0 1px 4px rgba(27, 42, 107, 0.06);
  --shadow-card:   0 2px 12px rgba(27, 42, 107, 0.08);
  --shadow-hover:  0 8px 32px rgba(27, 42, 107, 0.16);
  --shadow-green:  0 4px 20px rgba(30, 126, 52, 0.28);
  --shadow-nav:    0 2px 16px rgba(27, 42, 107, 0.12);

  /* ── TYPOGRAPHY ──────────────────────────────── */
  --font-display:  'Barlow Condensed', sans-serif;
  --font-body:     'Inter', sans-serif;
  --font-weight-normal: 400;
  --font-weight-medium: 500;
  --font-weight-bold:   700;
  --font-weight-black:  800;

  /* ── RADIUS ──────────────────────────────────── */
  --radius-xs:   4px;
  --radius-sm:   6px;
  --radius-md:   10px;
  --radius-lg:   16px;
  --radius-xl:   24px;
  --radius-pill: 100px;

  /* ── TRANSITIONS ─────────────────────────────── */
  --transition-fast:   0.15s ease;
  --transition-base:   0.2s ease;
  --transition-slow:   0.35s ease;
}
```

---

## TYPOGRAPHY SETUP

```css
/* Load via <link> in <head> */
/* <link href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@700;800&family=Inter:wght@400;500;600&display=swap" rel="stylesheet"> */

body {
  font-family: var(--font-body);
  font-size: 16px;
  font-weight: var(--font-weight-normal);
  color: var(--slate);
  line-height: 1.65;
  background-color: var(--white);
  -webkit-font-smoothing: antialiased;
}

h1, h2, h3 {
  font-family: var(--font-display);
  font-weight: var(--font-weight-black);
  color: var(--navy-base);
  line-height: 1.15;
  letter-spacing: -0.01em;
}

h1 { font-size: clamp(36px, 7vw, 64px); }
h2 { font-size: clamp(26px, 4.5vw, 44px); }
h3 { font-size: clamp(20px, 3vw, 28px); }
h4 { font-family: var(--font-body); font-size: 18px; font-weight: var(--font-weight-medium); color: var(--navy-base); }

p { color: var(--slate); }
.text-secondary { color: var(--slate-light); }
.text-white { color: var(--white); }

.eyebrow {
  font-family: var(--font-body);
  font-size: 12px;
  font-weight: var(--font-weight-medium);
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--green-base);
}
```

---

## NAVIGATION

```css
.site-header {
  background: var(--white);
  border-bottom: 1px solid var(--divider);
  transition: box-shadow var(--transition-base);
}

.site-header.scrolled {
  box-shadow: var(--shadow-nav);
}

.site-header.hero-overlap {
  background: transparent;
  border-bottom: 1px solid rgba(255,255,255,0.1);
}

.site-header.hero-overlap .nav-link {
  color: rgba(255,255,255,0.9);
}

.nav-link {
  color: var(--navy-base);
  font-size: 15px;
  font-weight: var(--font-weight-medium);
  text-decoration: none;
  transition: color var(--transition-fast);
}

.nav-link:hover,
.nav-link.active {
  color: var(--green-base);
}

/* Mobile hamburger lines → green when open */
.hamburger-line { background: var(--navy-base); }
.hamburger.open .hamburger-line { background: var(--green-base); }
```

---

## BUTTONS — Complete System

```css
/* ── Base ───────────────── */
.btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-family: var(--font-body);
  font-size: 15px;
  font-weight: var(--font-weight-medium);
  border-radius: var(--radius-sm);
  padding: 12px 24px;
  border: 1.5px solid transparent;
  cursor: pointer;
  text-decoration: none;
  transition: all var(--transition-base);
  white-space: nowrap;
  line-height: 1;
}

/* ── Primary (Navy) ──────── */
.btn-primary {
  background: var(--navy-base);
  color: var(--white);
  border-color: var(--navy-base);
}
.btn-primary:hover {
  background: var(--navy-light);
  border-color: var(--navy-light);
  box-shadow: var(--shadow-card);
  transform: translateY(-1px);
}

/* ── CTA / Green ─────────── */
.btn-cta {
  background: var(--green-base);
  color: var(--white);
  border-color: var(--green-base);
  box-shadow: var(--shadow-green);
}
.btn-cta:hover {
  background: var(--green-dark);
  border-color: var(--green-dark);
  box-shadow: 0 6px 28px rgba(30, 126, 52, 0.38);
  transform: translateY(-1px);
}

/* ── Outline Navy ────────── */
.btn-outline {
  background: transparent;
  color: var(--navy-base);
  border-color: var(--navy-base);
}
.btn-outline:hover {
  background: var(--navy-base);
  color: var(--white);
}

/* ── Outline Green ───────── */
.btn-outline-green {
  background: transparent;
  color: var(--green-base);
  border-color: var(--green-base);
}
.btn-outline-green:hover {
  background: var(--green-base);
  color: var(--white);
}

/* ── Ghost (text link style) */
.btn-ghost {
  background: transparent;
  color: var(--green-base);
  border-color: transparent;
  padding-left: 0;
  padding-right: 0;
}
.btn-ghost:hover {
  color: var(--green-dark);
  text-decoration: underline;
}

/* ── Sizes ───────────────── */
.btn-sm { font-size: 13px; padding: 8px 16px; }
.btn-lg { font-size: 17px; padding: 15px 32px; border-radius: var(--radius-md); }
.btn-xl { font-size: 18px; padding: 18px 40px; border-radius: var(--radius-md); }
.btn-block { width: 100%; justify-content: center; }
```

---

## CARDS

```css
.card {
  background: var(--white);
  border: 1px solid var(--divider);
  border-radius: var(--radius-lg);
  padding: 28px 24px;
  box-shadow: var(--shadow-sm);
  transition: transform var(--transition-base), box-shadow var(--transition-base), border-color var(--transition-base);
}

.card:hover {
  transform: translateY(-3px);
  box-shadow: var(--shadow-hover);
  border-color: var(--green-border);
}

/* Card with green accent left border */
.card-accent {
  border-left: 3px solid var(--green-base);
  border-radius: 0 var(--radius-lg) var(--radius-lg) 0;
}

/* Dark card (for navy sections) */
.card-dark {
  background: rgba(255,255,255,0.06);
  border: 1px solid rgba(255,255,255,0.10);
  border-radius: var(--radius-lg);
  padding: 28px 24px;
}
.card-dark:hover {
  background: rgba(255,255,255,0.09);
  border-color: rgba(255,255,255,0.18);
  transform: translateY(-2px);
}

/* Card icon container */
.card-icon {
  width: 52px;
  height: 52px;
  background: var(--green-pale);
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--green-base);
  margin-bottom: 20px;
}
.card-dark .card-icon {
  background: rgba(40, 167, 69, 0.15);
  color: var(--green-bright);
}
```

---

## SECTIONS & BACKGROUNDS

```css
/* White (default) */
.section { padding: 80px 0; background: var(--white); }

/* Off-white alternate */
.section-alt { padding: 80px 0; background: var(--off-white); }

/* Green-pale (for process, CTAs) */
.section-green { padding: 80px 0; background: var(--green-pale); }

/* Navy dark (for testimonials, why-us, footer) */
.section-dark {
  padding: 80px 0;
  background: var(--navy-dark);
  color: var(--white);
}
.section-dark h2,
.section-dark h3 { color: var(--white); }
.section-dark .eyebrow { color: var(--green-bright); }
.section-dark p { color: rgba(255,255,255,0.72); }

/* Section header alignment */
.section-header { max-width: 640px; margin: 0 auto 56px; text-align: center; }
.section-header .eyebrow { margin-bottom: 12px; }
.section-header h2 { margin-bottom: 16px; }
.section-header p { font-size: 17px; color: var(--slate-light); }
```

---

## FORMS & INPUTS

```css
.form-group { margin-bottom: 20px; }

.form-label {
  display: block;
  font-size: 14px;
  font-weight: var(--font-weight-medium);
  color: var(--navy-base);
  margin-bottom: 6px;
}

.form-input,
.form-select,
.form-textarea {
  width: 100%;
  padding: 12px 16px;
  font-size: 16px; /* 16px prevents iOS auto-zoom */
  font-family: var(--font-body);
  color: var(--navy-base);
  background: var(--white);
  border: 1.5px solid var(--divider);
  border-radius: var(--radius-sm);
  outline: none;
  transition: border-color var(--transition-fast), box-shadow var(--transition-fast);
  appearance: none;
}

.form-input::placeholder,
.form-textarea::placeholder {
  color: var(--slate-light);
}

.form-input:focus,
.form-select:focus,
.form-textarea:focus {
  border-color: var(--green-base);
  box-shadow: 0 0 0 3px rgba(30, 126, 52, 0.12);
}

.form-input:hover,
.form-select:hover,
.form-textarea:hover {
  border-color: var(--slate-light);
}

/* Error state */
.form-input.error { border-color: var(--color-error); }
.form-error-msg {
  font-size: 13px;
  color: var(--color-error);
  margin-top: 4px;
}

/* Custom select arrow */
.form-select {
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='8' viewBox='0 0 12 8'%3E%3Cpath d='M1 1l5 5 5-5' stroke='%231B2A6B' fill='none' stroke-width='1.5' stroke-linecap='round'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 14px center;
  padding-right: 40px;
}
```

---

## BADGES & PILLS

```css
/* Base pill */
.badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  font-weight: var(--font-weight-medium);
  padding: 4px 10px;
  border-radius: var(--radius-pill);
  line-height: 1;
}

/* Green (success, eco, active) */
.badge-green {
  background: var(--green-pale);
  color: var(--green-dark);
  border: 1px solid rgba(30, 126, 52, 0.2);
}

/* Navy (info, category) */
.badge-navy {
  background: var(--navy-pale);
  color: var(--navy-base);
  border: 1px solid rgba(27, 42, 107, 0.2);
}

/* White (on dark bg) */
.badge-white {
  background: rgba(255,255,255,0.12);
  color: var(--white);
  border: 1px solid rgba(255,255,255,0.2);
}

/* Dot indicators */
.dot {
  display: inline-block;
  width: 8px; height: 8px;
  border-radius: 50%;
}
.dot-green  { background: var(--green-bright); }
.dot-navy   { background: var(--navy-base); }
.dot-grey   { background: var(--slate-light); }
```

---

## STAT COUNTERS

```css
.stat-number {
  font-family: var(--font-display);
  font-size: clamp(32px, 5vw, 48px);
  font-weight: var(--font-weight-black);
  color: var(--navy-base);
  line-height: 1;
}
.stat-label {
  font-size: 14px;
  color: var(--slate-light);
  margin-top: 6px;
}
/* On dark sections */
.section-dark .stat-number { color: var(--white); }
.section-dark .stat-label  { color: rgba(255,255,255,0.6); }
```

---

## LINKS

```css
a {
  color: var(--green-base);
  text-decoration: none;
  transition: color var(--transition-fast);
}
a:hover { color: var(--green-dark); text-decoration: underline; }

/* Nav links (override) */
.nav-link { color: var(--navy-base); }
.nav-link:hover { color: var(--green-base); text-decoration: none; }

/* Footer links */
.footer-link { color: rgba(255,255,255,0.6); }
.footer-link:hover { color: var(--white); text-decoration: none; }
```

---

## DIVIDERS & SEPARATORS

```css
hr, .divider {
  border: none;
  border-top: 1px solid var(--divider);
}

/* Green accent rule (under headings) */
.heading-rule {
  width: 48px;
  height: 3px;
  background: var(--green-base);
  border-radius: 2px;
  margin: 16px auto 0;
}
.heading-rule.left { margin-left: 0; }
```

---

## HERO SECTION SPECIFIC

```css
.hero {
  background: var(--navy-dark);
  position: relative;
  overflow: hidden;
}

/* SVG shield grid pattern overlay */
.hero::before {
  content: '';
  position: absolute;
  inset: 0;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='60' height='70'%3E%3Cpolygon points='30,4 56,18 56,52 30,66 4,52 4,18' fill='none' stroke='rgba(255,255,255,0.04)' stroke-width='1'/%3E%3C/svg%3E");
  background-repeat: repeat;
  pointer-events: none;
}

.hero h1 { color: var(--white); }
.hero h1 span.accent { color: var(--green-bright); }
.hero p   { color: rgba(255,255,255,0.72); }

/* Glassmorphism booking widget on hero */
.hero-widget {
  background: rgba(255,255,255,0.07);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(255,255,255,0.13);
  border-radius: var(--radius-md);
  padding: 20px;
}

/* Trust strip below widget */
.hero-trust span {
  font-size: 13px;
  color: rgba(255,255,255,0.65);
}
.hero-trust span::before { content: '✓ '; color: var(--green-bright); }
```

---

## FOOTER

```css
.footer {
  background: var(--navy-dark);
  color: rgba(255,255,255,0.7);
  padding: 64px 0 0;
}
.footer-heading {
  font-family: var(--font-body);
  font-size: 13px;
  font-weight: var(--font-weight-medium);
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: rgba(255,255,255,0.4);
  margin-bottom: 20px;
}
.footer-bottom {
  background: rgba(0,0,0,0.25);
  padding: 20px 0;
  font-size: 13px;
  color: rgba(255,255,255,0.4);
  margin-top: 48px;
}
.footer-bottom a { color: rgba(255,255,255,0.55); }
.footer-bottom a:hover { color: var(--white); }
```

---

## WHATSAPP FLOATING BUTTON

```css
.whatsapp-fab {
  position: fixed;
  bottom: 24px;
  right: 24px;
  width: 56px;
  height: 56px;
  background: #25D366;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 20px rgba(37, 211, 102, 0.40);
  z-index: 9999;
  transition: transform var(--transition-base), box-shadow var(--transition-base);
  text-decoration: none;
}
.whatsapp-fab:hover {
  transform: scale(1.1);
  box-shadow: 0 6px 28px rgba(37, 211, 102, 0.55);
}
.whatsapp-fab svg { width: 28px; height: 28px; fill: #fff; }
```

---

## SCROLLBAR (optional polish)

```css
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: var(--off-white); }
::-webkit-scrollbar-thumb { background: var(--navy-light); border-radius: 6px; }
::-webkit-scrollbar-thumb:hover { background: var(--navy-base); }
```

---

## FOCUS & ACCESSIBILITY

```css
*:focus-visible {
  outline: 2px solid var(--green-base);
  outline-offset: 3px;
  border-radius: 2px;
}
.sr-only {
  position: absolute; width: 1px; height: 1px;
  padding: 0; margin: -1px; overflow: hidden;
  clip: rect(0,0,0,0); white-space: nowrap; border: 0;
}
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    transition-duration: 0.01ms !important;
    animation-duration: 0.01ms !important;
  }
}
```

---

## MOBILE RESPONSIVE OVERRIDES

```css
@media (max-width: 767px) {
  .section, .section-alt, .section-green, .section-dark {
    padding: 56px 0;
  }
  .section-header { margin-bottom: 40px; }
  .btn-lg { font-size: 16px; padding: 14px 28px; }
  .card { padding: 20px 18px; }
  .hero-widget { backdrop-filter: none; background: rgba(255,255,255,0.1); }
  .whatsapp-fab { bottom: 16px; right: 16px; width: 50px; height: 50px; }
}
```

---

## WHAT NOT TO DO — Strict Rules

```
✗ Never use green as a large background area (sections, cards) — pale green only
✗ Never put green text on navy background at small font sizes (contrast fails)
✗ Never use more than 2 colors on any single component
✗ Never use white text on green-pale background (contrast fails)
✗ Never use box-shadows on the hero section (too heavy)
✗ Never use font-weight above 800 (black) — the display font handles authority
✗ Never use generic blue (#007BFF) or red (#FF0000) — use semantic vars only
✗ Never hardcode hex colors outside :root — always reference CSS variables
✗ Never use border-radius > 16px on cards (looks too friendly for a services brand)
```

---

## GOOGLE FONTS LINK (add to `<head>`)

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@700;800&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
```

---

*End of theme prompt — v1.0 — PestControl99 logo-matched design system*
