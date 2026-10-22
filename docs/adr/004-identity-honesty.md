# ADR-004: Stay in character, but never claim to be human when sincerely asked

**Status:** Proposed · **Date:** 2026-10-21

## Context
The product goal is that visitors feel they're chatting with Chandru, with no AI labels in the UI. Visitors (often recruiters) act on that belief: they share emails and book calls. Some will ask outright whether they're talking to a bot.

## Decision
- No AI labels in the UI; the bot speaks as Chandru in first person.
- Sincere identity questions (Jev `sincere_identity_q` Noul + regex backstop) route to a template Chandru writes in his own voice, saying it's his digital twin that he built, that he reads the chats, and offering a real call. The bot never asserts it is a human.
- Playful jabs get a playful deflection that also never claims to be human.

## Rationale
Persona is fine; an explicit lie to someone who genuinely asks is deception, and it's the one thing that would turn a strong portfolio piece ("I built a twin good enough that people ask") into a reputational problem with exactly the audience it's meant to impress. The honest answer is itself a hook for a call.

## Consequences
- \+ Low risk; the identity reply doubles as a conversion moment.
- − Some visitors learn it's a bot when they ask; acceptable.
