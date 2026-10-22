# ADR-001: Jev for decisions, LLM for language

**Status:** Proposed · **Date:** 2026-10-21 · **Deciders:** Chandru Ganeshan

## Context
Every turn needs several decisions before any text is written: intent, which project, visitor persona, reply depth, whether retrieval is needed, sincere identity probe, injection attempt, off-limits topic. The previous backend used an LLM router call for this (structured output), costing ~1 s and an extra generation per turn. The latency target (first burst p50 ≤ 900 ms) leaves no room for two sequential LLM calls.

Jev (TypeSafe, launched 2026-09-15) is a decision model served via OpenRouter's Decisions API. It answers multiple typed questions (Choice / Score / Noul) about a `state` in one parallel pass and returns probability distributions; it never generates text. TypeSafe reports 70–500 ms end to end; output tokens are free, input $0.042/M.

## Decision
Use Jev (`typesafe/jev-1.14`, pinned) for all semantic decisions: one call per turn (J1), plus evidence sufficiency (J2), per-burst grounding (J3), tool confirmation (J4), and offline style judging (J5). Use an OpenRouter chat LLM only for writing replies. Deterministic rules (validation, thresholds, routing priority, numeric checks) stay in code.

## Options considered
| Option | Latency | Cost | Reliability | Notes |
|---|---|---|---|---|
| **Jev + LLM (chosen)** | ~300 ms decision | ~$0.00003/turn | typed output, no parse errors; alpha API | calibrated probabilities enable per-route thresholds |
| LLM router (structured output) + LLM | ~800–1200 ms | ~$0.0001/turn | JSON parse/schema failures possible | what the old backend did |
| Single LLM call decides + answers | lowest call count | lowest | no separable routing, can't gate tools/identity before generation | weakest control |
| Embedding classifier (semantic-router style) | ~20 ms | ~0 | needs per-route utterance sets; weak on multi-label flags | good fallback candidate |

## Consequences
- \+ Decisions before generation → tools, identity and off-limits are gated by code, not by hoping the LLM complies.
- \+ Probabilities are logged → thresholds tuned on data; shadow-test new versions.
- − Decisions API is **alpha**: schema may change → thin adapter + contract test + rule fallback.
- − Confidence ≠ correctness; Jev can be overly literal and is weak on numbers/dates → numbers checked in code; thresholds per route.
- − English-primary training: fine for v1 (English only).

## Revisit when
Jev leaves alpha; route accuracy < 95%; p95 Jev latency > 500 ms from Fly region.
