---
name: portfolio-innovation
description: Use this skill whenever brainstorming, planning, or scoping a NEW section, feature, or interaction for the portfolio — and whenever the user's request includes words like "creative," "innovative," "different," "stand out," "unique," or "impressive." Always consult this skill before implementing a new feature idea, even a small one, so the result is memorable rather than a generic template pattern.
---

# Portfolio Innovation

Why this matters: this portfolio already has above-average bones (a neural background, a command-palette chatbot, terminal-styled UI). The goal is not to add more features for their own sake — it's to make choices a generic "AI-generated portfolio" wouldn't make. Recruiters and engineers see hundreds of portfolios; the ones that get remembered took one real risk well, rather than adding ten safe widgets.

## Core principles

1. **One signature moment beats ten small ones.** A portfolio doesn't need every trendy effect. Pick the single most fitting idea for this project and execute it extremely well, instead of spreading effort thin.
2. **The site should demonstrate skill, not just describe it.** A resume says "I know React and animation." The site *proving* that by how it behaves is far more convincing than the sentence. If a section could be static text, ask: "could this instead *be* a small interactive proof?"
3. **Story over list.** "Experience" sections that are just a bulleted job history read like a PDF. A scroll-driven narrative — where the page reveals context as you scroll, like a short story of the person's growth — is far more memorable than a repeated card layout.
4. **Restraint is a skill.** Before adding a new animation/effect, ask "does this serve the content, or is it decoration for its own sake?" Autoplay video/audio, gratuitous parallax, and typing-effect text with no real purpose are anti-patterns — they signal "template," not "craft."

## Idea bank (build on what already exists first)

This project already has strong foundations to extend rather than compete with:
- **`CmdKChatbot`** — already a command-palette + AI chatbot. Extend it: let it answer questions grounded in the resume data (`src/data/resume.ts`), and consider making it discoverable with a subtle on-screen hint (`⌘K`) rather than requiring the visitor to guess.
- **`NeuralBackground`** — already a signature visual. Consider making it subtly react to cursor position or scroll velocity so it feels alive rather than purely decorative (small, cheap change with a big perceived-quality payoff).
- **Scroll-driven `Experience` section** — turn a job history into a vertical timeline where each entry animates in with `whileInView`, tied to real scroll position rather than a generic fade grid.
- **Terminal easter egg** — since `.terminal-window` styling already exists, a hidden "type `help` to see commands" mini-terminal is thematically consistent (not bolted-on) and gives technical visitors something to poke at.
- **Live, real data over static claims** — e.g. pulling live GitHub contribution/stars data for `Projects` instead of hardcoded numbers, so the site visibly stays current.
- **Custom cursor or subtle cursor-trail effect** — cheap to build, high perceived polish, but must respect `prefers-reduced-motion` (see `frontend-excellence` skill) and be disabled on touch devices.

## Anti-patterns to actively avoid
- Stock photography or generic icon-grid "skills" sections — prefer typographic or data-driven treatments.
- Parallax on every section (causes motion sickness for some users and reads as dated, ~2015-era design).
- Long autoplay intro animations that block the visitor from reaching content — always allow skip, and keep any intro (see `LoadingScreen.tsx`) under ~1.5 seconds.
- Adding an effect purely because it's trending on Dribbble/Twitter without checking it fits the site's existing Apple-dark-mode aesthetic (see `globals.css` tokens).

## Process before building a new idea
1. State the idea in one sentence and what specific impression it's meant to create.
2. Check it against the anti-pattern list above.
3. Ask: "Would a senior frontend engineer at Google/Meta screenshot this and share it unprompted?" If the honest answer is no, either sharpen the idea or drop it in favor of a stronger one.
4. Only then move into implementation, applying the `frontend-excellence` and `seo-optimization` skills as you build.
