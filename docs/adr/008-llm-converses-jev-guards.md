# ADR-008: The LLM converses, Jev guards (supersedes the routing part of ADR-001)

**Status:** Accepted · **Date:** 2026-10-21 · **Deciders:** Chandru Ganeshan

## Context
ADR-001 made Jev the "control brain": one J1 call classifies every message (11 typed questions) and a route table sends the turn to one of 8 nodes. Live chats and the golden set showed the weakness:
- **Jev sees one message, not the conversation.** Context-dependent turns get low-confidence or wrong labels: "why" → unknown 0.42; "what's pymlrs?" → unknown 0.47; "what's ur name" after the twin disclosure → identity 0.40.
- **A wrong label is unrecoverable.** The turn lands in clarify / "don't remember" / the identity speech.
- **Rules multiplied to compensate:** named-project rule, contact regex, stale-project TTL, disclosure guard, insufficient→casual fallback.
- **J1 is serial.** The LLM starts ~500 ms later than it could.

## Decision
1. **One conversational LLM call per turn** with the full history, the persona and style card, FACTS, **all public cards** (≈6k tokens, in the cached prompt prefix) and tools: `share_resume`, `start_connect`/`capture_lead`, `find_slots`/`book_meeting`, `get_news(topic, query)`. The LLM decides what the visitor means and what to cite.
2. **Jev gates run in parallel with the LLM stream:** `sincere_identity_q`, `injection_attempt`, `off_limits`, `personal_category`. They finish before the first token in the typical case. If a gate trips, code cancels the stream and takes the policy path: the exact first-disclosure template, an injection/NDA deflection, or a dodge at the escalation level code chose, which the LLM phrases.
3. **Post-generation checks stay:** code (numbers with rounding tolerance, entities, citations, negative cards), Jev J3 grounding, Jev J7 partisan check on TN politics, repair-once.
4. **Side effects stay code-gated:** a tool call → LangGraph `interrupt` → Jev J4 classifies the reply → code executes only on `confirm`.
5. **Jev stays offline** for news relevance (J6) and the eval style judge (J5).
6. **Removed:** J1 intent/project/persona/depth/self-intro/news-topic, J2, prefetch, the route table, project resolver/dossier logic, fastpath templates for small talk, the clarify node.
7. **Qdrant** stays for the news collection, and becomes the scale path for cards (switch back to retrieval above ~20k tokens of cards).

## Options considered
| Option | Context understanding | Policy safety | First-bubble latency | Complexity |
|---|---|---|---|---|
| A. Jev routes every turn (current) | weak on follow-ups | strong | ~1.6 s p50 (serial J1) | high, rules keep growing |
| **B. LLM converses + Jev gates in parallel (chosen)** | strong (full history + all cards) | strong (gates + post-checks + J4) | ~1.1 s expected | lower |
| C. LLM only, no Jev | strong | relies on the prompt for honesty/injection/privacy | ~1.1 s | lowest, but unenforceable guarantees |
| D. LLM router call, then LLM answer | strong | medium | ~2.2 s (two serial LLM calls) | medium |

## Consequences
- \+ Follow-ups, vague messages and post-disclosure chat are understood natively. No stale-context bugs.
- \+ No retrieval false negatives: every card is always visible; citations still verified.
- \+ The serial J1 step disappears, so first bubble ~0.5 s faster; about half the graph code is deleted.
- − The LLM chooses tools and phrasing for dodges. Contained by J4 + code for side effects, and by gates + post-checks for leaks.
- − The prompt grows by ~6k tokens. Fine with caching (~$0.00006/turn); revisit above ~20k.
- − Golden expectations on `route`/`intent` change to the new node names; behaviour checks stay identical.

## Acceptance
**Baseline (ADR-001 design, 2026-10-21, `run.py --repeat 3`, 164 cases / 210 turns):** 163/164 stable,
1 flaky (follow-01, 2/3), 0 always failing; first bubble p50 1683 ms / p95 2653 ms; Jev J1 p50 536 ms.

**Result (ADR-008 build, `run.py --repeat 3`, 165 cases / 214 turns):**
- Best run 164/165 stable, latest 163/165; **0 always failing**.
- All 9 style checks at 100% over 642 turn-runs; route, retrieval and flags at 100%.
- First bubble p50 **1443 ms** (−240 ms vs baseline), p95 2866 ms. Jev gate latency varies by provider: 540–820 ms p50 across runs.

**What it took beyond the original plan** (each found by a failing golden case):
- **J8:** Jev verifies every LLM tool call. Haiku called `start_connect` on "how are you?" and `share_resume` on "asdfgh".
- **J9:** Jev checks a reply answers the lead question. "btw what's your stack?" had been stored as the `about` field.
- **`wants_connect` gate:** the LLM said "want me to start a connect?" instead of calling the tool; code now starts the flow (same parallel Jev call), and permission-asking bubbles are dropped.
- Uncited lines are checked against the cards they're about, plus the project registry, not just FACTS.
- The clock is part of the checkable facts.

Ship only if the golden set (`run.py --repeat 3`) is **≥ the ADR-001 baseline** on stable pass rate, with first-bubble p50 ≤ baseline and no regression in any `style.*` check.

## Action items
1. [x] Cards-in-context prompt builder (reviewed public cards with ids, cached prefix).
2. [x] `converse` node: streaming LLM + tool calls (OpenRouter function calling), history from the checkpointer.
3. [x] Parallel Jev gates with speculative streaming and cancel-on-trip.
4. [x] Tools: resume, connect/lead, slots/book, news. Interrupt + J4 before side effects.
5. [x] Delete J1 routing, prefetch, resolver, fastpath and clarify; keep checks, humanizer, fillers and tracing.
6. [x] Update golden route expectations; run repeat-3 against the baseline; record numbers here.
