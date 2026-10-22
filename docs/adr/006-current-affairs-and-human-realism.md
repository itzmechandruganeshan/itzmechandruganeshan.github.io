# ADR-006: Human realism through server context, a curated news store and policy-driven dodges

**Status:** Proposed · **Date:** 2026-10-21

## Context
To feel human, the twin has to know what time and day it is, follow *some* news (tech industry and Tamil Nadu politics), and handle personal questions the way people do: evasive, slippery, on the fence. LLMs are bad at all three on their own:
- they don't know "now";
- their training memory of news is stale and invents dates;
- they either over-share or refuse in a robotic way.

## Decision
1. **Time comes from code.** `context/clock.py` builds an IST clock block each turn (day part, weekend, TN holiday, routine status, visitor local time). The LLM may refer to it, never compute it.
2. **News comes from a curated store, not the model.**
   - A twice-daily ingest job: RSS → Jev relevance filter → cheap-model neutral summaries → Qdrant `news` with a 30-day TTL.
   - Only two beats (tech industry, TN politics). Everything else gets a human "not following that".
   - Missing coverage gets an admitted gap, never a guess.
3. **Politics is aware but neutral.** Policy-defined fence-sitting, plus a keyword list and a Jev `partisan` gate on every TN politics burst.
4. **Personal questions go through a dodge engine.**
   - Jev classifies the category; Chandru's `policy.yaml` supplies the lines.
   - Responses escalate (playful → vague + redirect → gentle boundary) and rotate so they don't repeat.
   - The LLM may only restyle a line, never add facts.

## Options considered
| Option | Why not |
|---|---|
| Let the LLM answer news from training data | stale, invents dates, can't be audited |
| Live web search per question (search API) | +1–3 s latency, uncontrolled sources, politics risk, cost |
| Prompt-only dodges ("be evasive about personal stuff") | inconsistent, sometimes over-shares, sometimes sounds like a refusal bot |
| **Curated store + policy (chosen)** | adds an ingest job and policy-writing effort |

## Consequences
- \+ Grounded, auditable, fast (news retrieval is the same Qdrant path as cards).
- \+ Chandru controls what "he" says on politics and personal topics.
- − The news store lags reality by up to ~12 h, which a human would too.
- − The feed list and policy lines need occasional upkeep, and holiday dates need a yearly update.
- − Political content is reputationally sensitive. The neutrality gate fails closed: when unsure, it uses a fence-sit line.

## Revisit when
Visitors often ask about news outside the two beats; or partisan flags show up in review.
