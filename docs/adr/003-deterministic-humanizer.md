# ADR-003: Humanization in deterministic code, not the LLM

**Status:** Proposed · **Date:** 2026-10-21

## Context
Replies must feel like WhatsApp texting: bursts, pacing, lowercase, slang, the odd typo. Asking the LLM to "add typos" is unreliable: it over-does them, puts them in names and numbers, and varies run to run. A second "humanizer LLM" call adds latency and cost.

## Decision
The LLM writes short bursts in Chandru's voice (style card + few-shots); a deterministic `humanizer/` module then enforces burst count/length, strips AI-isms and markdown, applies casing, injects ≤ 1 typo per reply at a configured rate (never on protected tokens), optionally adds a `*correction` burst, and computes typing delays. Pacing hides system latency (delay counts from message received).

## Consequences
- \+ Testable with property tests (protected tokens never mutated); zero added LLM latency; tunable from `style.yaml`.
- \+ Grounding checks run on the pre-typo text, so typos can't break citation checks.
- − Rules can feel formulaic → seeded jitter per session, and rates come from Chandru's real voice corpus.
