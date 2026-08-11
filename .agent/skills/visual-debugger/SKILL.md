---
name: visual-debugger
description: Use this skill whenever the user reports a visual, layout, or interaction bug ("this looks broken," "misaligned," "the animation is janky," "doesn't look right on mobile"), and whenever verifying that a new UI change actually looks correct before calling it done. Always capture a real screenshot or recording FIRST and reason from what's actually rendered, instead of guessing the cause from source code alone.
---

# Visual Debugger

Why this matters: CSS and layout bugs are usually invisible from reading code — a flex container can look fine in JSX and still overflow at 375px wide. The reliable way to debug a UI issue is the same way a human developer does: look at the actual rendered page, not just the source.

## Workflow (always follow this order)

1. **Reproduce.** Identify the exact URL/route and, if possible, the exact viewport width or interaction sequence that triggers the issue.
2. **Capture.** Take a screenshot or short recording of the actual rendered page — see methods below. Do this *before* forming a theory about the cause.
3. **Compare.** Look at the captured image against what's expected (the design tokens in `globals.css`, or a description of the intended layout).
4. **Diagnose from evidence.** Only now reason about which CSS/JSX is responsible, using what's visible in the screenshot (overflow, wrong spacing, broken animation frame, wrong color) to narrow down the cause.
5. **Fix, then re-capture.** After making a change, capture again to confirm the fix visually — don't assume a code change worked without seeing it rendered.

## Method 1: Antigravity's built-in browser preview
If working inside Antigravity IDE with the local dev server running (`npm run dev`), use the built-in browser/preview panel to open the affected route directly and take a screenshot through it — this is the fastest option for a one-off check during active development.

## Method 2: Automated multi-viewport capture (bundled script)
For anything involving responsiveness, or when you need a record of before/after, use the bundled script instead of a single manual screenshot:

```bash
npx playwright install chromium   # once, if not already installed
npm run dev                       # in a separate terminal, keep it running
node .agent/skills/visual-debugger/scripts/capture.mjs http://localhost:3000 ./screenshots
```

This captures full-page screenshots at mobile (375px), tablet (768px), and desktop (1440px), and prints any browser console errors it caught along the way. Always check the console errors it reports — a visual bug is often caused by a silent JS error (e.g. a failed dynamic import of `NeuralBackground`), not just CSS.

To check a specific route: `node .agent/skills/visual-debugger/scripts/capture.mjs http://localhost:3000/projects ./screenshots`

## Method 3: Recording for animation/interaction bugs
Static screenshots can't show a janky animation, a broken scroll-triggered reveal, or a hover state. For these:
- Prefer a short screen recording (a few seconds) over a screenshot, either through Antigravity's browser tooling if it supports recording, or by extending the Playwright script with `page.video` capture.
- Watch specifically for: dropped frames, animation restarting unexpectedly on scroll (usually a missing `viewport={{ once: true }}` in framer-motion), or elements popping in without a transition.

## What to look for in the captured image
- **Overflow / horizontal scroll** at mobile width — the most common bug, usually from a fixed-width element or unclamped text.
- **Layout shift** — compare an early vs. late screenshot of the same load to see if content jumped.
- **Contrast issues** — text that's technically "on the page" per code but nearly invisible against `--background: #050505`.
- **Z-index/stacking bugs** — `NeuralBackground` or `.glass-panel` overlapping content incorrectly.
- **Broken responsive breakpoints** — a component that looks right at 1440px and 375px but breaks somewhere in between (check 768px specifically, it's the most commonly missed breakpoint).

## After fixing
Always re-run the capture and explicitly state what changed between the "before" and "after" screenshot — don't just say "fixed it," show the evidence.
