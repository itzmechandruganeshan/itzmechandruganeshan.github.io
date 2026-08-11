---
name: modern-stack-scout
description: Use this skill BEFORE adding any new dependency, choosing between two implementation approaches, or whenever the user asks to use "latest," "trending," "modern," or "cutting-edge" tech. Frontend tooling (React, Next.js, Tailwind) changes fast enough that training-data memory of "current best practice" goes stale within months — always verify current version/API info via search rather than assuming.
---

# Modern Stack Scout

Why this matters: an AI agent's built-in knowledge of "the latest React pattern" is frozen at its training cutoff. In frontend development specifically, APIs, defaults, and recommended patterns change every few months (React Server Components patterns, Next.js App Router conventions, Tailwind's engine itself went through a major rewrite between v3 and v4). Confidently applying an outdated pattern looks worse than asking to check — a senior engineer verifies before committing to an approach on a fast-moving stack, they don't recite from memory.

## The rule
Before writing code that depends on a specific library API, version-specific syntax, or "current best practice" claim, search for the current documentation/state rather than relying on memory — especially for:
- React (currently on 19 in this project — Server Components, `use()`, form actions, hooks)
- Next.js (currently on 16 — App Router conventions, Metadata API, Image/Font optimization, caching model)
- Tailwind CSS (currently on v4 — the CSS-first config, `@theme` directive already used in `globals.css`, no more `tailwind.config.js` by default)
- Any animation/UI library before adding it as a new dependency

## Checklist before adding a new dependency
1. **Is it actively maintained?** Check the last release date and open-issue activity, not just star count.
2. **Does the platform already do this natively?** Modern browsers and CSS now natively handle things that used to need a library — check before reaching for a package:
   - Native CSS scroll-driven animations / `animation-timeline` for scroll effects, instead of a heavy JS scroll library.
   - The View Transitions API for page/section transitions.
   - CSS `:has()` for parent-based conditional styling instead of a JS workaround.
   - `<dialog>` element for modals instead of a modal library.
3. **Does it overlap with an existing dependency?** This project already has `framer-motion` for animation and `lucide-react` for icons — don't add a second animation or icon library without a specific reason.
4. **Bundle size impact.** A new dependency for a small effect is rarely worth the download cost on a portfolio, where fast load time itself is part of the impression being made.

## Staying current on this specific project
Current confirmed stack (from `package.json`): Next.js 16.1.6, React 19.2.3, Tailwind CSS 4, framer-motion 12, TypeScript 5. When suggesting new patterns:
- Don't suggest `pages/` router patterns — this project uses the App Router (`src/app`).
- Don't suggest a `tailwind.config.js`-centric approach for new design tokens — Tailwind 4 in this project uses the `@theme` block directly inside `globals.css`; add new tokens there, consistent with the existing `--primary`/`--secondary`/`--accent` pattern.
- When suggesting a "modern" technique (e.g. a new CSS feature), check current browser support before recommending it as a primary implementation rather than a progressive enhancement.

## When the user asks for "the latest trending stack"
Don't default to naming whatever was trending at training time. Search for current (this month/quarter) frontend tooling discussion — release notes, framework blogs, "state of frontend" surveys — and present a couple of grounded, verified options rather than one confident guess.
