# PestControl99.com — "/e-card" Digital Business Card Page
### Developer Brief for AI-Assisted Build (Cursor / Lovable / Google Stitch)

---

## 1. Why This Page Exists

We currently use a **third-party digital business card tool (tapmo.me)** to share our company profile, contact details, services, and enquiry form via QR code / link. This looks unprofessional and untrustworthy to customers because:

- The URL is `tapmo.me/pestcontrol` — a random third-party domain, not our own brand
- It signals we don't have our own website/tech capability
- Large competitors (HiCare, Rentokil, PCI) never rely on third-party tools like this

**Goal:** Rebuild the exact same content and function as a **native page on our own domain**: `pestcontrol99.com/e-card`. This becomes our official digital visiting card — the link/QR code we put on print materials, WhatsApp, email signatures, and vehicle branding.

---

## 2. Route & Access

- **URL:** `pestcontrol99.com/e-card`
- Standalone page, lightweight, mobile-first (90% of traffic will be mobile — scanned via QR code or opened from WhatsApp)
- No header/footer nav from the main site needed — this is a self-contained "digital card" experience, similar to a Linktree/vCard page but fully branded
- Should load fast, minimal JS, works well even on average mobile networks

---

## 3. Design Direction (Important)

**Do NOT make this look like a generic AI-generated template.** Avoid:
- Default centered-everything layouts with generic rounded cards and drop shadows everywhere
- Overused gradient backgrounds (light green/purple blur gradients)
- Stock "SaaS landing page" look with emoji icons

**Instead aim for:**
- Clean, professional, trustworthy — feels like a government-licensed service company, not a startup app
- Strong brand consistency: use our navy blue (#1a1a5e / dark navy from logo) + white + a single accent green (from logo shield) — no rainbow of colors
- Real typography hierarchy (one distinct heading font or weight system, not default system font look)
- Tight, confident spacing — not everything floating in whitespace
- Photography of actual pests should look clean and professionally cropped/lit, not clip-art like
- Reference: look at how HiCare or Rentokil PCI present their "quick contact" sections — confident, not flashy

---

## 4. Page Structure & Exact Content

### 4.1 Header / Brand Block
- Logo: PestControl99.com logo (healthy home, safe family, pest-free living tagline)
- Badge: "Government Licensed Professional Pest Management Company"
- Badge: "100% Guaranteed Results"
- Optional: small banner photo of a technician at work (we have existing brand photography — reuse from site)

### 4.2 Action Buttons (below header)
Two buttons side by side:
- **Save Contact** → downloads a `.vcf` file (vCard) with our business contact so it saves directly into the customer's phone contacts
- **Share** → uses native Web Share API (`navigator.share`) to let the user share the page link via WhatsApp/SMS/etc. Fallback: copy link to clipboard with a toast confirmation.

### 4.3 Quick Contact List
Vertical list, each row = icon + label + value (label and value both tappable where relevant — phone numbers should be `tel:` links, WhatsApp should deep-link to `wa.me`, email should be `mailto:`):

| Icon | Label | Value | Link behavior |
|---|---|---|---|
| Phone | 24×7 Customer Care | 8080 74 8282 | `tel:` link |
| WhatsApp | WhatsApp Booking | 8080 74 8282 | `https://wa.me/918080748282` |
| Mail | Customer Support Email | accounts@pestcontrol99.com | `mailto:` link |
| Link/Globe | Official Website | www.pestcontrol99.com | links to homepage |
| Location Pin | Service Locations | Mumbai • Navi Mumbai • Thane • Lonavala • Pune | plain text |

Below that: social icons — Facebook, Instagram, YouTube (linking to our actual profiles, open in new tab)

### 4.4 About Us
Section heading: **About Us**

> PestControl99.com is a Government Licensed Professional Pest Management Company providing safe, effective, and reliable pest control solutions for residential and commercial properties. Our trained technicians specialize in Cockroach, Termite, Bed Bug, Rodent, Mosquito, and General Pest Control using modern treatment methods and quality products. We proudly serve Mumbai, Navi Mumbai, Thane, Lonavala, and Pune with one-time and AMC services.

### 4.5 Products & Services
Section heading: **Products and Services**

Each service = a card with: pest image, price line, service name, short description, "Enquiry →" link (scrolls to or opens the Enquiry Form at bottom, pre-filling the "message" field with the service name if possible).

1. **Cockroach & General Pest Control**
   - Price: Starting From ₹1,000
   - Description: Safe & effective treatment for Cockroaches, Ants, Spiders, Silverfish & House Lizards. Free inspection available.

2. **Termite Treatment**
   - Price: Starting From ₹2,000
   - Description: Protect your property from termite damage with safe, effective and long-lasting anti-termite treatment.

3. **Bed Bugs Treatment**
   - Price: Starting From ₹2,000
   - Description: Safe and effective bed bug treatment with professional inspection and 2-visit service.

4. **Mosquito Control**
   - Price: Starting From ₹800 *(verify — source shows "₹8,00", confirm correct amount before publishing)*
   - Description: Advanced mosquito control with spray and fogging solutions for homes, societies, hotels and commercial premises.

5. **Rodent Control**
   - Price: Starting From ₹1,000
   - Description: Safe and effective rat & mouse control with professional inspection and treatment.

**Image note:** Use sharp, well-lit, real macro pest photography for each (cockroach, termite, bed bug, mosquito, rat) — matching quality/style already used on our main site's hero slider and brochure page. Do not use cartoon/illustrated pest icons.

### 4.6 Gallery
Section heading: **Gallery**
Grid of our branded service graphics (Rodent Control, Bed Bugs Treatment, Mosquito Control, Cockroach & Ant Control creatives — reuse existing branded social media graphics). Tapping an image opens a lightbox/full view.

### 4.7 Profile QR Code
Section heading: **Profile QR Code**
- Auto-generated QR code that encodes the page's own URL (`pestcontrol99.com/e-card`) — so anyone who has the physical card/printout can scan and reach this same page
- Button: **Download Profile QR Code** → downloads the QR as a PNG

### 4.8 Enquiry Form
Section heading: **Enquiry Form**
Fields:
- Name (text, required)
- Email (email, required)
- Mobile (tel, required)
- Message (textarea)
- **Send** button

On submit: send to our existing enquiry handling (same backend/email endpoint used on the main site contact form — confirm with dev which endpoint that is) and show a success confirmation message in place of the form.

---

## 5. Technical Notes

- Framework: match existing site stack (Vite + React) so this is just a new route/page component, not a separate app
- Fully responsive, but **mobile is the primary target** — most traffic arrives via QR scan or WhatsApp share
- `vcf` file for Save Contact should be generated client-side or as a static downloadable file with our details pre-filled
- Ensure the page has correct meta tags (title: "PestControl99 — Digital Business Card", noindex is optional — decide if we want this indexed by Google or treated as a private card link)
- Keep total page weight low — this needs to open instantly when scanned from a QR code with a customer standing in front of a technician

---

## 6. What "Done" Looks Like

- All content above live at `pestcontrol99.com/e-card`
- Save Contact and Share buttons work correctly on mobile
- Enquiry form submits and reaches our team
- Design looks like an extension of our real brand — not a generic template, not third-party
- We stop distributing the tapmo.me link entirely and replace it everywhere (WhatsApp, print, signage, vehicle QR) with our own link
