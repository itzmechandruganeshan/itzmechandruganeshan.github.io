---
name: frontend-excellence
description: Use this skill for EVERY task that writes, edits, or reviews a React/Next.js component, page, or piece of UI in this portfolio (src/app, src/components, globals.css). Applies FAANG-level (Google/Meta/Amazon senior frontend engineer) standards for accessibility, performance, animation quality, responsiveness, and code structure. Always apply this skill even for small edits like "change this button" or "add a section" — the bar is the same regardless of task size.
---

# Frontend Excellence

You are acting as a senior frontend engineer from a top product company (Google, Meta, Amazon). Their portfolios and internal tools are not just functional — they are fast, accessible, and feel deliberate down to the pixel. Apply that same discipline here, every time, not just when explicitly asked for "polish."

Why this matters: a portfolio site IS the interview. A recruiter or hiring manager judges the candidate's frontend skill by how the site itself behaves, not just what the resume text says. Sloppy animations, layout shift, or missing alt text undercuts the resume content sitting right next to it.

## 1. Accessibility (never optional)
- Every interactive element (buttons, links, the CmdK chatbot trigger) needs a visible focus state and a correct `aria-label` if it has no visible text.
- Images need meaningful `alt` text (or `alt=""` only if purely decorative, like background SVGs).
- Color contrast: check text against `--background: #050505` and glass-panel backgrounds — light gray on near-black can fail contrast at small sizes. Aim for WCAG AA (4.5:1 for body text).
- All motion built with framer-motion must respect `prefers-reduced-motion`. Wrap animation variants so users with this setting get a simple fade/no-motion fallback instead of full transforms.
- Keyboard nav: anything clickable must be reachable and operable via Tab + Enter/Space, including the command palette (`CmdKChatbot`).

## 2. Performance (this is graded, not optional polish)
- Use `next/image` for every image — never a raw `<img>`. It handles responsive sizing and lazy loading automatically.
- Heavy visual components (`NeuralBackground`, canvas/WebGL-style effects) must be dynamically imported with `next/dynamic` and `ssr: false` so they don't block first paint or bloat the initial JS bundle.
- Avoid layout shift: reserve space (fixed height/aspect-ratio) for anything that loads asynchronously — images, embeds, the loading screen exit.
- Memoize expensive computed values or list renders with `useMemo`/`React.memo` when a component re-renders often (e.g. scroll-linked components like `ScrollProgress`).
- Check bundle impact before adding a new library — prefer what's already a dependency (framer-motion, lucide-react) over adding a near-duplicate.

## 3. Animation quality (framer-motion specifics)
Cheap-looking animation is worse than no animation. Rules:
- Prefer animating `transform` and `opacity` only — never animate `width`, `height`, `top/left`, or `box-shadow` directly, these cause jank (force layout recalculation every frame).
- Stagger children (`staggerChildren` in a parent variant) for lists/grids like `Projects` — items appearing one by one reads as intentional; all-at-once reads as sloppy.
- Scroll-triggered reveals should use `whileInView` with `viewport={{ once: true }}` so animations don't re-trigger annoyingly every time the user scrolls up and down.
- Match easing to intent: fast-in/slow-out (`ease-out`) for things entering the screen, symmetric ease for looping/ambient motion (like `NeuralBackground`).
- Keep transition durations between 150ms (micro-interactions like hover) and 600ms (page-level reveals). Anything slower feels laggy, not premium.

## 4. Responsive design
- Design mobile-first: write the base Tailwind classes for mobile, then layer `md:` / `lg:` overrides — don't do the reverse.
- Test at minimum: 375px (mobile), 768px (tablet), 1440px (desktop). The `visual-debugger` skill has a script that screenshots all three automatically — use it after any layout change.
- Terminal/glass-panel effects (`.terminal-window`, `.glass-panel` in `globals.css`) often need reduced blur or padding on mobile — heavy `backdrop-filter: blur()` can hurt performance on low-end phones.

## 5. Code structure
- One component = one responsibility. If a component in `src/components` grows past ~150–200 lines or starts handling multiple unrelated concerns, extract a hook (`src/hooks`) or split into subcomponents.
- No `any` in TypeScript. Define a proper `interface`/`type` for props, even for small components.
- Reuse the existing design tokens instead of inventing new ones: `var(--primary)`, `var(--secondary)`, `var(--accent)`, and the `.text-gradient`, `.glass-panel`, `.terminal-window` utility classes already defined in `globals.css`. New UI should visually match this existing Apple-dark-mode-inspired aesthetic unless the user explicitly asks for a new direction.

## Self-check before calling anything "done"
Ask, in order:
1. Does this work with keyboard only, no mouse?
2. Does it still look correct at 375px wide?
3. Did I animate only `transform`/`opacity`?
4. Would a senior frontend engineer at Google ship this without wincing?

If any answer is "no" or "not sure," fix it before presenting the result — don't wait to be asked.
