# ADR-002: Qdrant Cloud free tier with embedded fallback, structure-first retrieval

**Status:** Proposed · **Date:** 2026-10-21

## Context
Answers must never mix facts across projects (false positives) or miss a relevant fact (false negatives). The corpus is small: ~7 projects, ~300 claim cards, ~0.5 MB of vectors. Budget is free-tier. Chandru wants a real vector DB in the stack.

## Decision
1. **Structure first:** resolve the project (alias match > active project > Jev), then load *all* public cards for that project and aspect via a filtered scroll. Similarity search (hybrid dense + BM25 sparse, RRF) is used only when no project is resolved.
2. **Store:** Qdrant Cloud free tier (1 GB RAM, 0.5 vCPU, 4 GB disk, no card required), cluster in the region nearest the Fly app. Payload indexes on `project_id`, `aspect`, `visibility`, `company`, `tech`, `negative`.
3. **Fallback:** `RETRIEVAL_BACKEND=embedded` uses `QdrantClient(path=...)` in-process with identical code; selected automatically if the cloud cluster is unreachable at startup.

## Options considered
| Option | Latency | Ops | Cost | Notes |
|---|---|---|---|---|
| **Qdrant Cloud free + embedded fallback (chosen)** | +5–30 ms network | low | $0 | real vector DB, survives free-tier suspension |
| Qdrant embedded only | ~1–5 ms | none | $0 | fastest; index lives in the container |
| numpy + BM25 in memory | ~1–5 ms | none | $0 | no vector DB features (filters, hybrid) |
| Top-k similarity as primary selector | — | — | — | rejected: causes cross-project blending |

## Consequences
- \+ Filtered dossier loading removes false negatives for named projects; hard `project_id` filter removes cross-project false positives.
- − Free clusters suspend after 1 week idle and are deleted after 4 → daily keepalive query; `ingest.py` rebuilds idempotently from git in one command.
- − No HA on free tier → embedded fallback.

## Revisit when
> ~5k cards, live ingestion, or > 1 app machine (move to paid tier, drop full-dossier loading).
