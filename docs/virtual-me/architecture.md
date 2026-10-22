# Virtual Me — Architecture

Status: **Draft v1** · Last updated: 2026-10-21 · Requirements: [requirements.md](requirements.md)

> **Superseded in part by [ADR-008](../adr/008-llm-converses-jev-guards.md) (2026-10-21):** the LLM now converses with the
> full history and all cards in context, plus tools. Jev **guards** instead of routing: parallel gates
> (identity, injection, off-limits, personal, wants_connect), J3/J7 checks, J4 confirmation, J8 tool verification,
> J9 answered-the-question, and J6 offline. The J1 routing, prefetch/resolver, J2, fastpath and clarify sections
> below describe the previous design.
>
> **The LLM converses. Jev guards. Code enforces. Code humanizes.**

---

## 1. High-level view

```
 Browser (Next.js static site on GitHub Pages)
   │  wss://virtual-me.fly.dev/ws/chat?session_id=<uuid>
   ▼
 ┌──────────────────────── Fly.io machine, region sin (FastAPI) ──────────────────┐
 │  WS handler ── session load (SQLite) ── LangGraph graph ── burst emitter        │
 │                                             │                                   │
 │        intelligence/ gateway ───────────────┼──────────── retrieval/            │
 │        ├─ Jev  (OpenRouter Decisions API)   │             ├─ Qdrant Cloud (free)│
 │        └─ LLM  (OpenRouter chat, streaming) │             │   cards · news      │
 │                                             │             └─ Qdrant embedded    │
 │        context/ ── clock (IST) · routine · TN holiday calendar   (fallback)     │
 │        tools/ ── Google Calendar · Gmail API alerts · leads store                │
 │        jobs/ (APScheduler) ── news ingest 06:00/18:00 IST · keepalive · purge   │
 └─────────────────────────────────────────────────────────────────────────────────┘
                     │ Gmail API                       │ RSS (tech + TN politics)
                     ▼                                 ▼
          chandruganeshan24@gmail.com           news feeds (feeds.yaml)
```

| Component | Responsibility | Tech |
|---|---|---|
| WS handler | Auth-less session handshake, origin check, rate limit, event protocol, idle nudge timer | FastAPI WebSocket |
| LangGraph graph | Turn orchestration, routing, tool subgraphs with `interrupt`, checkpointed state | `langgraph` + `AsyncSqliteSaver` |
| `intelligence/` | The **only** place that calls OpenRouter. Timeouts, retries, fallbacks, cost/latency logging | `httpx` async |
| `retrieval/` | Entity-scoped card loading + hybrid search | `qdrant-client`, `fastembed` |
| `humanizer/` | Deterministic burst shaping, casing, typos, pacing | pure Python |
| `context/` | Server-side "now": IST date/time, day part, weekend/holiday, routine status, visitor local time | `zoneinfo`, `holidays.yaml` |
| `news/` | Ingest job + news retrieval (tech, TN politics) | `feedparser`, cheap LLM summarizer, Jev filter |
| `tools/` | Resume, lead capture, calendar booking, email alerts | Google Calendar API, Gmail API (`gmail.send`) |
| `jobs/` | In-process scheduler: news ingest, Qdrant keepalive, retention purge, daily digest | APScheduler (single machine) |
| Storage | Sessions, messages, leads, bookings, checkpoints | SQLite (WAL) on Fly volume |

---

## 2. Turn pipeline (LangGraph)

```
                 ┌──────────────────┐
  user msg ─────►│ guard + context  │  code: length, rate limit, regex backstops;
                 └────────┬─────────┘  build clock block (IST now, day part, holiday, routine)
            ┌─────────────┴──────────┐            (parallel fan-out)
            ▼                        ▼
     ┌────────────┐           ┌────────────┐
     │ jev_decide │           │  prefetch  │  speculative: alias match → project cards;
     └─────┬──────┘           └─────┬──────┘  news-ish keywords → recent news; else hybrid top-8
            └──────────┬─────────────┘
                       ▼
                  ┌─────────┐
                  │  route  │  code: thresholds + priority rules
                  └────┬────┘
 ┌────────┬────────┬───┴────┬─────────┬─────────┬─────────┬─────────┐
 ▼        ▼        ▼        ▼         ▼         ▼         ▼         ▼
fastpath answer  news     personal  tools    identity  deflect   clarify
(templ.) (cards  (news    (dodge    subgraph (D2)      (policy)  (ask back)
          +LLM)   cards    engine)  (lead/
                  +LLM)             meeting/resume)
 └────────┴────────┴───┬────┴─────────┴─────────┴─────────┴─────────┘
                       ▼
               ┌────────────────┐
               │ who's-this hook│  code: append "btw who's this?" once (A10)
               └───────┬────────┘
                       ▼
               ┌─────────────┐
               │  humanize   │  code → bursts + delays → WS events
               └─────────────┘
```

### 2.1 Graph state

```python
class TurnState(TypedDict):
    session_id: str
    user_message: str
    history: list[Msg]                 # last N turns (trimmed by token budget)
    active_project: str | None         # sticky across turns for follow-ups
    persona: Literal["recruiter", "engineer", "casual", "unknown"]  # sticky once confident
    decision: JevDecision | None       # typed answers + probabilities
    evidence: list[Card]               # retrieved claim cards
    draft_bursts: list[Burst]          # LLM/template output, pre-humanize
    tool_ctx: ToolCtx | None           # slot-filling state for lead/meeting
    visitor: Visitor                   # name, company, role, email, tz — learned so far (A10/C2)
    asked_who: bool                    # A10: "who's this?" asked once per session
    clock: ClockContext                # IST now, day part, weekend/holiday, routine status, visitor local time
    dodges: dict[str, int]             # FR-G: personal category → times pressed (escalation)
    used_dodges: set[str]              # FR-G: avoid repeating the same dodge line
    news: list[NewsCard]               # FR-F: retrieved news cards
    flags: list[str]                   # grounding_fail, injection, low_conf, partisan ...
    timings: dict[str, float]
```

### 2.2 Node contracts

| Node | Input → Output | Budget | Failure behaviour |
|---|---|---|---|
| `guard` | message → pass / reject / `identity_hint` / `injection_hint` | < 5 ms | reject → in-character "slow down a bit haha" |
| `jev_decide` | message + last 3 turns + active_project → `JevDecision` | 300 ms (timeout 800) | timeout → `rules_decide()` (keywords + aliases) |
| `prefetch` | message + active_project → candidate cards | 60 ms | Cloud down → embedded; both down → fact sheet only |
| `route` | decision + guard hints → next node | < 1 ms | below threshold → `answer` (safe generic) or `clarify` |
| `fastpath` | intent → templated bursts from `policy.yaml` / `facts.yaml` | < 5 ms | — |
| `answer` | evidence + history + style → streamed bursts with hidden citations | TTFT 700 ms | primary model fails → fallback list → canned apology |
| `tools/*` | slot state → prompts / `interrupt` / side effects | per tool | external API error → "calendar's being weird, mind if i email u instead?" |
| `identity` | → D2 template bursts | < 5 ms | — |
| `humanize` | draft bursts → final bursts + delays | < 2 ms | — |

### 2.3 Routing rules (code, after Jev)

Priority order — first match wins:

1. `guard` hard reject → reject.
2. `sincere_identity_q.noul ≥ T_id` **or** regex identity hit with `noul ≥ T_id_low` → `identity`.
3. `injection_attempt.noul ≥ T_inj` → `deflect` (stay in character, ignore instructions).
4. `off_limits.noul ≥ T_off` → `deflect`.
5. Active tool flow (`tool_ctx` set) → resume that tool subgraph.
6. `intent ∈ {resume, lead, meeting}` with confidence ≥ T_tool → `tools`.
7. `intent == personal` (or `personal_category ≠ none` ≥ T_pers) → `personal` (dodge engine).
8. `intent == current_affairs`: `news_topic ∈ {tech, tn_politics}` → `news`; `other` → fastpath "not really following that ngl".
9. `intent == small_talk`, time questions ("what u doing?", "u awake?"), or templated profile fact with confidence ≥ T_fast → `fastpath` (templates filled from the clock block).
10. Otherwise → `answer` (if `needs_retrieval`, gated by sufficiency).
11. `intent == unknown` and low confidence → `clarify`.

All `T_*` thresholds start at a placeholder and are **set from the eval set** (precision/recall per route vs cost of a wrong branch). Never hand-tuned in production.

---

## 3. Where Jev is used

Jev = TypeSafe's "System One" decision model. Called through OpenRouter's Decisions API (`POST https://openrouter.ai/api/alpha/decisions`), pinned `typesafe/jev-1.14`. It returns typed answers with probability distributions; it never generates text.

| # | Call site | Questions | Why Jev here |
|---|---|---|---|
| J1 | Every turn, one call | `intent` (Choice), `project` (Choice — registry + `none` + `multiple`), `persona` (Choice), `depth` (Score 1–4), `personal_category` (Choice — G1 list + `none`), `news_topic` (Choice — tech / tn_politics / other / none), `needs_retrieval`, `sincere_identity_q`, `injection_attempt`, `off_limits`, `self_intro` (Noul — "is the visitor telling Chandru who they are?") | 11 decisions in one parallel pass; replaces an LLM router call |
| J2 | RAG path, after retrieval | `evidence_sufficient` (Noul) | Stops the LLM from improvising when cards don't cover the question |
| J3 | Each LLM burst, during the previous burst's typing delay | `burst_grounded` (Noul) | Semantic claim check without a verifier LLM; zero perceived latency |
| J4 | Tool confirmation turns | `confirmation` (Choice: confirm / reject / change / unclear) | Robust to "yeah works", "hmm maybe thursday instead" |
| J5 | Offline eval only | `sounds_human`, `sounds_like_chandru` (Score) | Cheap judge for style regression |
| J6 | News ingest job (offline) | `relevant` (Choice: tech_industry / tn_politics / neither), `newsworthy` (Score) per feed item | Filters ~60 raw items/day before paying for summarization |
| J7 | `news` route, TN politics only, per burst | `partisan` (Noul — "does `burst` endorse, attack or mock a party, leader, caste or religion?") | Hard neutrality gate on top of the prompt + keyword list |

**Not Jev (plain code):** email validation, calendar availability, idempotency, rate limits, numbers/dates/percentages checks, visibility filtering, alias matching, final routing rules, confirmation enforcement.

### 3.1 J1 request shape (verified against OpenRouter's decisions-api reference, 2026-10-21)

```json
{
  "model": "typesafe/jev-1.14",
  "state": {
    "message": "how did u handle the multilingual stuff in mewatch?",
    "recent_turns": ["...", "..."],
    "active_project": "mewatch"
  },
  "questions": {
    "intent": {
      "type": "choice",
      "instructions": "What is the visitor asking Chandru for in `message`?",
      "criteria": {
        "small_talk": "Greeting, banter or chit-chat with no information need",
        "profile_fact": "A simple fact about Chandru: role, location, education, years of experience",
        "project_deep": "How a specific project worked: architecture, problem, approach, impact",
        "opinion": "Chandru's views on tech, tools, AI trends or engineering practice",
        "resume": "Wants Chandru's resume or CV",
        "current_affairs": "Asks about recent news or events, or Chandru's take on them",
        "personal": "Asks about Chandru's private life: relationships, family, religion, salary, politics he supports, health, exact address, age, plans to switch jobs",
        "lead": "Hiring interest or wants to share their contact details",
        "meeting": "Wants to talk live, schedule or book a call",
        "unknown": "None of the above or unclear"
      }
    },
    "sincere_identity_q": {
      "type": "noul",
      "instructions": "In `message`, is the visitor sincerely asking whether they are talking to a bot or AI rather than the real person (not joking)?"
    }
  }
}
```

State is kept short (message + 3 turns) — long state degrades Jev accuracy and pushes it into slower long-context mode. User text inside `state` is untrusted; the instructions never say "follow the message".

### 3.2 Confidence policy

- Log every distribution (`probabilities`, `confidence`) with the model version.
- `confidence` measures how peaked the distribution is, **not** correctness — thresholds are calibrated per route on labelled data.
- Run new Jev versions in **shadow mode** (log both, act on old) before switching.

---

## 4. Grounded retrieval

Goal: no cross-project blending (false positives) and no missed facts (false negatives). **Structure first, similarity second.**

### 4.1 Corpus

- **Project registry** `projects.yaml` — canonical id, name, company, period, role, aliases, tech.
- **Claim cards** — one atomic, self-contained fact per card, written/approved by Chandru, with metadata (see [data-spec.md](data-spec.md#claim-cards)). Includes **negative cards** ("didn't fine-tune anything on mewatch") so "did you X?" gets a grounded no.

### 4.2 Resolution → retrieval

```
message ──► alias matcher (code, fuzzy) ──┐
active_project (session) ─────────────────┼──► resolved project_id?
Jev J1 `project` Choice (≥ T_proj) ───────┘        │
                                         yes ◄─────┴─────► no
                                          │                 │
             Qdrant scroll: filter project_id,      Qdrant hybrid query
             visibility=public → the WHOLE dossier   (dense + BM25 sparse, RRF)
             (~15–30 cards), ordered by wanted aspect visibility=public, top 8
                                          └────────┬────────┘
                                                   ▼
                          Jev J2 evidence_sufficient — started IN PARALLEL with the LLM call,
                          awaited before the first burst is emitted (0 added latency)
                                     no → "hmm don't remember that detail tbh,
                                           happy to go deeper on a call"
```

Priority for the project: **alias hit > active_project > Jev** (Jev only above threshold). `multiple` → load each project's overview cards and let the LLM compare.

### 4.3 Generation with citations

- The LLM sees evidence as `⟦c:<card_id>⟧ <text>` lines and must end each burst with the ids it used, e.g. `routing node handled lang detection first ⟦c:mw-07⟧`.
- Code strips the tags before sending.
- **Deterministic checks per burst** (in code):
  1. every cited id ∈ retrieved set;
  2. every number, %, date, company, and tech term in the burst appears in a cited card or `facts.yaml`;
  3. no `negative` card is contradicted by keyword (e.g. card says "no fine-tuning", burst says "fine-tuned").
- **Semantic check:** Jev J3 `burst_grounded`, run while the previous burst's typing delay plays.
- On failure: regenerate that burst once with a stricter instruction; if it fails again, drop it (and if it was the only burst, use the insufficient-evidence line). Every failure is flagged in logs for review.

### 4.4 Store

- **Primary: Qdrant Cloud free tier** (1 GB RAM / 0.5 vCPU / 4 GB disk, no card). Corpus ≈ 300 cards ≈ 0.5 MB vectors.
  - Collection `cards`: named dense vector (fastembed `BAAI/bge-small-en-v1.5`, 384-d — verify model availability at build time) + sparse BM25 vector.
  - Payload indexes: `project_id`, `aspect`, `visibility`, `company`, `tech`, `negative`.
- **Free-tier risk:** suspended after 1 week idle, deleted after 4 weeks. Mitigation: daily keepalive query; `ingest.py` rebuilds idempotently from git; `RETRIEVAL_BACKEND=embedded` (`QdrantClient(path=...)`) as automatic fallback at startup — same code path.

---

## 5. LLM (answer node)

| Model (OpenRouter id) | $/M in → out | Role |
|---|---|---|
| `anthropic/claude-haiku-5.5` | 0.10 → 0.50, cache read 0.01 | **Primary candidate** — strong persona + rule following, many providers |
| `deepseek/deepseek-v4.1-flash` | 0.028 → 0.12 | Cost challenger / fallback |
| `openai/gpt-5.6-luna` | 0.20 → 1.20 | Bake-off third |

Prices pulled from the OpenRouter models API on 2026-10-21. Final pick by **bake-off from the Fly region** on TTFT p50/p95, grounding pass rate, style score, cost.

Request settings: `stream: true`, `provider: {sort: "latency"}`, `models: [primary, fallback]`, `max_tokens` from `depth` (≈ 40 tokens/burst), temperature ~0.7.

### 5.1 Prompt layout (cache-friendly)

```
[stable prefix — cached]
  role + hard rules (grounding, identity D2, no AI-isms, burst format with |split|)
  style card (from persona/style.yaml)
  8–12 few-shot exchanges from voice corpus (selected per persona)
  facts.yaml (compact)
[per turn]
  clock block (IST now, day part, holiday, routine status, visitor local time)
  visitor block (name/company if known)
  mode: profile | concept | news | personal   (sets the knowledge horizon, FR-F6)
  persona + depth hint from Jev
  evidence cards with ids
  last N turns
  visitor message
```

---

## 6. Humanizer (deterministic)

Input: draft bursts (strings). Output: `[{text, delay_ms}]`.

1. **Split/merge** to 1–4 bursts (respect `depth`), 3–25 words each.
2. **Strip** markdown and banned phrases (safety net; prompt already forbids them).
3. **Casing/punctuation** per style card: lowercase starts, drop trailing period on short bursts, emoji ≤ 1 per reply at configured rate.
4. **Typo** (3–5% of replies, ≤ 1): pick a non-protected word (not a name/number/URL/email/tech term/cited fact), apply a realistic op (adjacent-key swap, transposition, dropped letter). ~50% chance of a follow-up `*word` burst.
5. **Pacing:** `delay = think_pause(first only) + len(text) / cps`, cps ≈ 6–9 with seeded jitter, clamp [0.6 s, 4 s].
6. **Latency hiding:** the first burst's delay counts from *message received*, not from generation end — if the LLM took 800 ms and the pacing says 1.6 s, the bot waits only 800 ms more.

---

## 6a. Human-realism features

### Time awareness (A9)

The LLM never guesses the date. `context/clock.py` builds a block every turn from the server clock:

```text
now: Tue 21 Oct 2026, 23:42 IST · day_part: late_night · weekend: no
holiday: none (next: Deepavali in 0 days → use holidays.yaml)
routine: off_work (office Mon–Fri 10–19)            # from persona/routine.yaml
visitor_local: 19:12 Europe/London (evening)        # from the browser tz in `hello`
```

- Fast-path templates use it directly ("haha it's almost midnight here 😅", "just wrapped up work").
- The LLM gets it as context with one rule: *mention time only when natural* — at most once every few turns, never "As of 23:42 IST…".
- Relative dates for news and experience ("last week", "since may") are computed in code and passed in, not inferred.
- Pacing gets a small late-night multiplier (slower, shorter replies), so behaviour matches the claimed context.

### "Who's this?" hook (A10)

Deterministic node after routing. If `visitor.name` is unknown, `asked_who` is false, it's the visitor's 2nd–3rd message, and the route isn't a tool/identity/deflect flow → append one burst from a rotating set ("btw who's this? 😄", "wait who am i talking to haha"). When J1 `self_intro` fires, a small extraction step (part of the answer LLM call, emitted as a hidden `⟦v:name=…;company=…⟧` tag, validated in code) fills `visitor`. The lead flow (C2) reuses whatever is known.

### Personal-question dodge engine (FR-G)

```
J1 personal_category ──► policy.yaml[category] ──► escalation level = dodges[category]
                                                    0 → playful   1 → vague+redirect   2+ → gentle boundary
                         pick unused line (used_dodges) ─► optional LLM restyle to fit the exact question
```

- The line comes from Chandru's own `policy.yaml`, so the substance of every dodge is pre-approved. The LLM may only rephrase it to fit the question, and a check rejects any rephrasing that adds a concrete fact.
- Categories that end in "defer to a call" (salary) offer the meeting tool on the 2nd press.

## 6b. Current affairs (FR-F)

### Ingest job (twice daily, `jobs/news_ingest.py`)

```
feeds.yaml (tech + TN politics RSS)
   → fetch (feedparser, If-Modified-Since, 10 s timeout per feed)
   → normalize + dedupe (URL canonical + title simhash, 72 h window)
   → J6 Jev filter: relevant ∈ {tech_industry, tn_politics}, newsworthy ≥ T_news   (~60 → ~15 items)
   → summarize with the cheap model: {headline, 2-sentence gist, entities[], topic, published_at}
     (from title + RSS description only; no full-article scraping)
   → upsert to Qdrant `news` (dense + sparse, payload: topic, published_at, entities, source)
   → purge cards older than 30 days
```

Runs inside the app process on APScheduler (single machine). Failure twice in a row → email alert.

### Online path (`news` route)

1. Retrieve from `news` filtered by `topic`, ranked by hybrid score × recency decay (half-life 7 days), top 5.
2. Jev J2 `evidence_sufficient`. If insufficient → "haven't caught up on that one tbh" (F3).
3. LLM in `news` mode: gist + a light reaction, relative dates from code, 1–2 bursts. Tech → may add an opinion consistent with `opinions` cards (F4). TN politics → neutral template guidance from `policy.yaml` (F5).
4. TN politics bursts pass a keyword list + **Jev J7 `partisan`** gate. A failing burst is replaced with a fence-sit line from policy.

## 6c. Email alerts (C2a)

- `tools/notify.py` uses the Gmail API (`users.messages.send`) with the same Google OAuth refresh token as Calendar, scopes `calendar.events` + `gmail.send`. It sends from and to `chandruganeshan24@gmail.com` (`ALERT_EMAIL`).
- Events: `lead.created`, `booking.created`, `booking.failed`, `news_ingest.failing`; optional daily digest at 21:00 IST of flagged turns.
- Each event is written to an `outbox` table first, then delivered by a worker with exponential backoff, at most 5 attempts. That gives exactly-once from the user's view: the unique key is the event id, so reconnects and retries never double-send.
- Body: who (name, company, role, email), intent, Jev persona, a 3-line chat summary (cheap model), and the admin CLI command to open the transcript. No raw transcript in the email.

## 7. WebSocket protocol

Client → server

```json
{"type": "hello", "session_id": "uuid", "tz": "Asia/Kolkata"}
{"type": "message", "text": "hey!", "client_msg_id": "uuid"}
{"type": "action", "action": "pick_slot", "slot_id": "s2"}
```

Server → client

```json
{"type": "typing", "on": true}
{"type": "burst", "turn_id": "t7", "seq": 0, "text": "heyy 👋"}
{"type": "card", "turn_id": "t7", "kind": "resume", "url": "/resume/chandru-ganeshan-resume.pdf"}
{"type": "card", "turn_id": "t8", "kind": "slots", "slots": [{"id": "s1", "start": "...", "end": "..."}]}
{"type": "card", "turn_id": "t9", "kind": "booking", "meet_url": "...", "start": "..."}
{"type": "turn_complete", "turn_id": "t7"}
{"type": "error", "code": "rate_limited", "text": "slow down a bit haha"}
```

The server owns pacing (sends `typing` and waits before each `burst`); the client just renders. `client_msg_id` makes sends idempotent across reconnects.

Frontend changes required: `NEXT_PUBLIC_WS_URL` env instead of `ws://localhost:8000`; UUID session id (remove ipify); handle `burst`/`card`/`typing` events; remove the client-side `|split|` delay logic.

---

## 8. Latency budget (LLM path)

```
t=0     message received → typing:on                         (≤ 150 ms)
        guard                                                   5 ms
        ┌ jev_decide ............................ 300 ms ┐
        └ prefetch (Qdrant Cloud) ...............  60 ms ┘ parallel → 300 ms
        route                                                   1 ms
        J2 evidence_sufficient (RAG path only)                200 ms
        LLM TTFT                                              600 ms
        first burst complete (~15 tokens streamed)            150 ms
        ───────────────────────────────────────────────────────────────
        first burst ready                                  ≈ 1.25 s (worst-case path)
        humanizer pacing target for that burst             ≈ 1.5–2.5 s
        → system latency is fully hidden inside human pacing
```

Fast path (no LLM, no J2): ≈ 310 ms. J2 runs concurrently with LLM TTFT, so its cost is hidden on the LLM path.

**Implementation note (v1 build):** an aspect *filter* on the dossier caused false negatives in testing ("what did you do on mewatch?" loaded only `role` cards and dropped the 80% metric). Aspects now only **order** the dossier; the whole project dossier is always loaded.

---

## 9. Failure modes

| Failure | Detection | Behaviour |
|---|---|---|
| Jev timeout / 5xx | gateway timeout 800 ms | `rules_decide()`; flag turn |
| Jev alpha API schema change | contract test in CI, 4xx | rules fallback; alert |
| Primary LLM slow/down | TTFT > 2 s or error | OpenRouter `models` fallback; then canned apology |
| Qdrant Cloud suspended/deleted | readiness check, query error | embedded backend; daily keepalive; `ingest.py` restore |
| Grounding check fails | code/J3 | regenerate once → drop burst |
| Prompt injection | J1 + regex | deflect in character; flag |
| Calendar API failure | tool error | offer email follow-up, capture lead instead |
| WS disconnect mid-turn | socket close | finish turn server-side, persist; replay undelivered bursts on reconnect |
| Abuse / flooding | rate limiter | soft in-character limit → close socket |
| News ingest fails | job status | serve existing cards (≤ 30 days); "haven't been following news much this week" if all are stale; email alert after 2 failures |
| Gmail send fails | outbox worker | retry with backoff ×5; lead still stored; shows in admin CLI |
| Partisan burst | keyword + J7 | replace with fence-sit line; flag |

---

## 10. Observability

Per turn JSON log: `session_hash, turn_id, route, jev{model, answers, probs}, timings{guard, jev, prefetch, j2, ttft, total}, llm{model, provider, in_tok, cached_tok, out_tok, cost}, grounding{checks, failures}, flags`. Optional LangSmith tracing in dev only. Daily summary via admin CLI: p50/p95 per node, cost/day, flagged turns.

---

## 11. Repository layout (planned)

```
backend/
  app/
    main.py            # FastAPI app, lifespan, health/ready
    ws.py              # WebSocket handler + protocol
    graph/             # state.py, nodes/*.py, routing.py, build.py
    intelligence/      # gateway.py, jev.py, llm.py, fallbacks.py
    retrieval/         # store.py (cloud|embedded), resolver.py, checks.py
    humanizer/         # bursts.py, typos.py, pacing.py
    context/           # clock.py, routine.py, visitor.py
    persona_rules/     # dodge.py (FR-G), politics_guard.py (F5), who_hook.py (A10)
    news/              # ingest.py, retrieve.py
    jobs/              # scheduler.py (news, keepalive, purge, digest, outbox worker)
    tools/             # resume.py, leads.py, calendar.py, notify.py (Gmail API + outbox)
    storage/           # db.py, models.py, crypto.py
    config.py
  data/                # facts.yaml, projects.yaml, cards/, voice/, persona/{style,routine,holidays}.yaml, policy.yaml, news/feeds.yaml
  eval/                # sets/*.jsonl, run_eval.py, bench_latency.py, bakeoff.py
  scripts/             # ingest.py, voice_questionnaire.py, whatsapp_extract.py, admin.py
  tests/
  Dockerfile, fly.toml, pyproject.toml
```

## 12. What to revisit as it grows

- > 1 machine → Postgres for sessions/checkpoints, Redis for rate limits, move APScheduler jobs to a Fly scheduled machine.
- > ~5k cards or live ingestion → paid Qdrant tier; reconsider full-dossier loading.
- If blind-test fooled-rate plateaus → more voice data before any fine-tuning.
- Jev leaves alpha → re-verify API, re-calibrate thresholds.
