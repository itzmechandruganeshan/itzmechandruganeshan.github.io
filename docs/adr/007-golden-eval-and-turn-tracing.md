# ADR-007: Golden dataset + per-step turn tracing as the regression gate

**Status:** Accepted · **Date:** 2026-10-21 · **Deciders:** Chandru Ganeshan

## Context
The first live chats exposed failures that unit tests with a fake Jev and LLM could not catch:
- intents misrouted to "clarify" when a project was clearly named
- "haha" repeated three times in one reply
- a citation tag leaked to the visitor
- two bubbles merged into one
- an "insufficient evidence" verdict for "tell me more abt it"
- a wrongly corrected project name ("tpay, not tomatopay")

Each needed the *intermediate* state to diagnose: Jev's answer, route reason, evidence ids, each LLM line, each check, each humanizer change. The final reply alone wasn't enough.

## Decision
1. **Per-step trace in every turn.** Every node appends structured steps to `TurnState.trace`: guard, jev_j1, prefetch, route+reason, resolve, j2_gate, llm_line (raw, cites, code checks, J3, J7, emitted), news, dodge, identity, who_hook, llm_done (model, TTFT, finish_reason, tokens, cost). The WS consumer adds humanize steps (fillers removed, typo, delays). The trace is stored in `turn_logs` (30-day retention, never in stdout). Read it with `scripts/admin.py trace`.
2. **Golden dataset** (`eval/golden/build.py` → `golden.jsonl`): 155 cases / 185 turns / 24 categories covering every intent, every project × aspect, follow-ups, false premises, knowledge gaps, personal dodges and pressure, identity, injection, off-limits, time/routine, tools, and robustness.
3. **Runner** (`eval/golden/run.py`): real Jev, LLM and Qdrant, frozen clock per case, typos off, separate DB.
   - Scores each step: route, intent, project, retrieval recall, citation grounding, content, flags.
   - Runs 9 global style checks on every turn: fillers once, no AI-isms, no markdown, no tag leak, no human claim, no time excuse, bubble size and count, non-empty.
   - `--repeat N` reports stable / flaky / always-failing cases.

## Options considered
| Option | Catches routing bugs | Catches style bugs | Cost | Verdict |
|---|---|---|---|---|
| Unit tests with fakes only | partly | no (fake LLM) | free | keep, but insufficient |
| LLM-as-judge on final replies | weakly | yes | higher, noisy | rejected as primary |
| **Deterministic per-step checks on real runs (chosen)** | yes, with the exact failing step | yes | ~$0.10 / 155 cases | chosen |
| Production log review only | after users hit it | after users hit it | free | complement |

## Consequences
- \+ Every fix in this session was found by a failing step and verified by a rerun: 143 → 154/155 stable over 3 repeats; 464/465 case runs pass.
- \+ The cause is visible in the trace (e.g. `max_tokens=70` → `finish_reason=length` → line dropped).
- − Golden expectations need upkeep when cards change; regexes must test behaviour, not wording.
- − LLM sampling makes some cases flaky, so use `--repeat 3` before trusting a single pass or fail.

## Action items
1. [x] Run `eval/golden/run.py --repeat 3` before every deploy; block on "always failing".
2. [ ] Add cases for every new conversation bug found in `admin.py trace` (regression first, then fix).
3. [ ] Calibrate the `T_*` thresholds from golden + routing results once the voice corpus is in.
