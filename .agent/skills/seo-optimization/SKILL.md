---
name: seo-optimization
description: Use this skill for EVERY task that touches src/app/layout.tsx, adds/edits a page or route, changes page titles/headings, or adds content, images, or links. Also trigger explicitly on words like SEO, metadata, sitemap, robots, Open Graph, structured data, "search engine," or "make this discoverable." Never ship a new page without applying this skill — SEO is a default requirement here, not an optional extra.
---

# SEO Optimization (Next.js App Router)

Why this matters: a portfolio's whole job is to be *found* — by recruiters, on Google, when someone pastes the link in Slack. Good code that nobody sees does nothing. Treat SEO as a first-class requirement on every page, not a final cleanup pass.

## 1. Metadata (the Next.js way, not manual `<head>` tags)
Next.js App Router uses a built-in `Metadata` API instead of hand-written `<head>` tags. In `layout.tsx` or any `page.tsx`, export a `metadata` object (or `generateMetadata()` function if values are dynamic):

```ts
export const metadata: Metadata = {
  title: { default: "Full Name — Frontend Engineer", template: "%s | Full Name" },
  description: "A single, specific sentence describing who this person is and what they build. 150–160 characters.",
  metadataBase: new URL("https://yourdomain.com"),
};
```

**What it is:** a structured object Next.js turns into all the correct `<meta>` tags automatically at build time.
**Why:** hand-written meta tags are error-prone and easy to forget on new pages; the Metadata API guarantees every page gets a title, description, and social preview without repeating boilerplate.

Rules:
- Every page needs a unique, specific `title` and `description` — never copy the homepage's onto a sub-page.
- Use the `title.template` pattern (`%s | Name`) so sub-pages inherit a consistent suffix automatically.

## 2. Open Graph & social previews
When someone pastes the portfolio link into LinkedIn, Twitter/X, or Slack, this is what shows a rich preview card instead of a bare link. Add to `metadata`:

```ts
openGraph: {
  title: "...",
  description: "...",
  images: ["/og-image.png"], // 1200x630px
  type: "website",
},
twitter: {
  card: "summary_large_image",
  images: ["/og-image.png"],
},
```

For an extra-polished touch: Next.js supports generating the OG image dynamically as code (`opengraph-image.tsx` using `next/og`) instead of a static PNG — this lets the preview card show live text (name, role) rendered as an image at request time. Mention this option to the user as a "nice touch" if none exists yet.

## 3. Structured data (JSON-LD)
Search engines understand structured data far better than plain text. For a portfolio, add a `Person` schema (and `WebSite` schema on the homepage) as a JSON-LD `<script>` tag:

```tsx
<script
  type="application/ld+json"
  dangerouslySetInnerHTML={{
    __html: JSON.stringify({
      "@context": "https://schema.org",
      "@type": "Person",
      name: "Full Name",
      jobTitle: "Frontend Engineer",
      url: "https://yourdomain.com",
      sameAs: ["https://github.com/...", "https://linkedin.com/in/..."],
    }),
  }}
/>
```
This is what powers the little "Person" knowledge panel Google sometimes shows for named searches.

## 4. Sitemap & robots
Next.js App Router supports these as **code files**, not static XML you write by hand:
- `src/app/sitemap.ts` exporting a function that returns the list of URLs.
- `src/app/robots.ts` exporting the crawl rules.

Both get built and served automatically at `/sitemap.xml` and `/robots.txt`. If either is missing from the project, add them — a missing sitemap is one of the most common reasons a portfolio doesn't get indexed properly.

## 5. Semantic HTML & heading structure
- Exactly **one** `<h1>` per page (the person's name or the page's main heading — check `Hero.tsx`).
- Section headings (`Experience`, `Projects`) should be `<h2>`, and nothing should skip a level (no jumping from `h2` straight to `h4`).
- Use `<nav>`, `<main>`, `<section>`, `<footer>` landmark elements — check `Navbar.tsx` and `Footer.tsx` use the correct semantic tags, not generic `<div>`s.

## 6. Performance = SEO
Google's ranking algorithm directly factors in Core Web Vitals. This overlaps with the `frontend-excellence` skill — apply both together:
- **LCP** (Largest Contentful Paint): the hero image/text must render fast — avoid blocking it behind heavy JS like `NeuralBackground`.
- **CLS** (Cumulative Layout Shift): no content jumping around as things load.
- **INP** (Interaction to Next Paint): the CmdK chatbot and nav interactions must respond quickly, not freeze the main thread.

## 7. Canonical URLs
Set `alternates: { canonical: "https://yourdomain.com/path" }` in metadata for any page reachable by more than one URL pattern, to avoid duplicate-content confusion.

## Pre-ship checklist
Before treating any new page as finished, confirm:
- [ ] Unique title + description set
- [ ] Open Graph image present
- [ ] Exactly one `h1`, logical heading order
- [ ] `sitemap.ts` includes the new route
- [ ] No layout shift, images use `next/image`
