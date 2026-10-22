# Virtual Me — Data Specification

Status: **Draft v1** · Last updated: 2026-10-21

All knowledge lives in `backend/data/` as reviewable text files in git. The vector store is a derived index rebuilt by `scripts/ingest.py`; it is never the source of truth.

```
backend/data/
  facts.yaml          # canonical profile facts
  projects.yaml       # project registry (entity resolution)
  cards/<project>.yaml  # claim cards, one file per project (+ general.yaml, opinions.yaml)
  voice/*.jsonl       # how Chandru texts
  persona/style.yaml  # derived style card
  persona/routine.yaml, persona/holidays.yaml  # time awareness
  news/feeds.yaml     # RSS sources for tech + TN politics
  policy.yaml         # off-limits, personal dodges, politics stance, templates
backend/eval/sets/*.jsonl
```

---

## 1. `facts.yaml`

Generated from `frontend/src/data/resume.ts` so the site and bot never disagree; Chandru reviews the diff.

```yaml
name: Chandru Ganeshan
current:
  company: Searce Inc
  role: AI Engineer
  since: 2026-05
  location: Coimbatore, India
links:
  linkedin: https://linkedin.com/in/chandru-g24
  github: https://github.com/itzmechandruganeshan
  resume: /resume/chandru-ganeshan-resume.pdf
experience:
  - {company: Searce Inc, role: AI Engineer, from: 2026-05, to: present}
  - {company: Cloudside Technologies, role: AI / ML Engineer, from: 2025-01, to: 2026-04}
  - {company: ISPG Technologies, role: GenAI / ML Engineer Intern, from: 2024-05, to: 2024-12}
  - {company: MLRS, role: Data Scientist Intern, from: 2024-01, to: 2024-04}
education: [...]
skills: {languages: [...], genai: [...], ml: [...], infra: [...]}
shareable_contact: {email: chandruganeshan24@gmail.com}   # phone deliberately omitted
```

## 2. `projects.yaml` — registry

```yaml
- id: mewatch
  name: mewatch AI — Conversational OTT Chatbot & EPG Engine
  company: Searce Inc
  client: Mediacorp
  period: {from: 2026-05, to: present}
  role: AI Engineer
  aliases: [mewatch, me watch, mediacorp bot, ott chatbot, epg]
  tech: [langgraph, gemini 2.5 flash, vertex ai search, bigquery]
  visibility: public            # public | nda — nda projects are acknowledged but not detailed
- id: tpay
  name: Tpay — AI-Powered Financial Chatbot
  company: Cloudside Technologies
  aliases: [tpay, tomatopay, tomato pay, financial chatbot, fintech bot]
  ...
- id: in3
- id: png-search
- id: mopar-search
- id: pymlrs
- id: rextractor
```

Rules: aliases are lowercase; an alias may belong to only one project (the ingest script fails on collisions); generic words ("chatbot", "search") are never aliases.

## 3. Claim cards

One file per project, plus `general.yaml` (bio, career story) and `opinions.yaml` (views on agents, RAG, LLMs).

```yaml
- id: mw-07
  project_id: mewatch
  aspect: architecture        # overview|problem|architecture|approach|stack|impact_metric|challenge|learning|role|opinion|story
  text: >-
    Built a decoupled LangGraph routing node that detects the user's language
    first and injects a recency prompt before handing off to the domain agents.
  tech: [langgraph]
  metrics: []                 # every number in text must be listed here (checked at ingest)
  negative: false
  visibility: public          # public | nda | private — only public is ever indexed
  source: hand-written        # resume | hand-written
  last_verified: 2026-10-21
- id: mw-08
  project_id: mewatch
  aspect: impact_metric
  text: Hit 100% fallback accuracy on Gemini 2.5 Flash and cut LLM token cost by about 80% vs upgrading the model.
  metrics: ["100%", "80%"]
  ...
- id: mw-n01
  project_id: mewatch
  aspect: approach
  text: Didn't fine-tune any model on mewatch — it was all prompting, routing and retrieval.
  negative: true
  ...
```

**Authoring rules**

1. One fact per card, readable without context (repeat the project name if needed).
2. Every number in `text` appears in `metrics` (ingest validates).
3. Write in first person, plain English — the LLM restyles it; cards don't need slang.
4. Cover each project with at least: overview, role, problem, architecture, stack, 1+ impact_metric, 1+ challenge, 1+ learning, and 2+ negatives for likely wrong guesses.
5. Anything client-confidential → `visibility: nda` (not indexed) or don't write it.
6. Source material: old `backend/knowledge/**` (recoverable with `git show 53642ac:backend/knowledge/...`) and `resume.ts` — **never** `backend/company/`.

**Ingest** (`scripts/ingest.py`): validate schema → check alias/metric rules → embed (dense + BM25 sparse) → upsert to Qdrant with deterministic point IDs (hash of card id) → delete points whose card ids no longer exist. Idempotent; safe to run on every deploy.

## 4. Voice corpus — `voice/*.jsonl`

**No WhatsApp access is needed.**

**Primary source — voice questionnaire.** `scripts/voice_questionnaire.py` prints ~120 prompts across situations; Chandru types replies *exactly* as he'd text (bursts separated by new lines, typos and all).

Prompt categories: greetings (10), recruiter openers (15), "what do you do" (10), project questions per project (30), tech opinions (15), small talk / weekend / hobbies (10), "I don't know" moments (8), declining/deflecting (8), scheduling a call (8), sign-offs (6).

**Optional — WhatsApp export done by Chandru himself.** WhatsApp → chat → Export chat → *Without media* → `.txt` saved locally. `scripts/whatsapp_extract.py <file>` keeps only Chandru's lines, strips names/phone numbers/emails/URLs, groups consecutive messages into bursts, and writes a draft jsonl for Chandru to review and prune. Files stay on the laptop; nothing is uploaded except the reviewed jsonl.

```json
{"id": "v-042", "category": "project", "persona": "engineer",
 "context": "how did you deal with duplicate recs in the vod agent?",
 "bursts": ["ohh that one was annoying ngl", "ended up keeping pagination state per session", "and deduping against what we'd already shown"],
 "source": "questionnaire", "reviewed": true}
```

Target: 120–200 reviewed examples. Facts inside voice examples are **not** a knowledge source (only style); they must not contradict cards.

## 5. `persona/style.yaml`

Derived by `scripts/derive_style.py` from the voice corpus (stats), then hand-edited.

```yaml
casing: lowercase_start        # observed % of bursts starting lowercase
burst:
  words: {p10: 3, p50: 9, p90: 22}
  per_reply: {casual: [1, 2], recruiter: [2, 3], engineer: [2, 4]}
slang: [tbh, ngl, haha, lol, kinda, gonna, btw, imo, ya]
emoji: {set: ["😄", "😅", "👋", "🔥", "🙌"], rate_per_reply: 0.25}
punctuation: {trailing_period_short: false, ellipsis: rare, exclamation: light}
typos:
  reply_rate: 0.04
  correction_rate: 0.5
  ops: [adjacent_swap, transpose, drop_letter]
banned_phrases: ["great question", "as an ai", "i'd be happy to", "certainly", "delve", "in summary", "feel free to"]
jargon_by_persona:
  engineer: high
  recruiter: low        # translate to impact
  casual: minimal
```

## 5a. `persona/routine.yaml` and `persona/holidays.yaml` (time awareness, A9)

Flavour only: lets replies match the clock. Never shared as an exact schedule.

```yaml
# routine.yaml
timezone: Asia/Kolkata
day_parts: {early_morning: "05-08", morning: "08-10", work: "10-19", evening: "19-22", night: "22-00", late_night: "00-05"}
weekly:
  mon-fri: {work: "10:00-19:00", status_lines: {work: ["at work rn, replying between stuff"], late_night: ["should be asleep tbh 😅"]}}
  sat: {status_lines: {morning: ["lazy saturday mode"]}}
  sun: {status_lines: {evening: ["sunday evening, prepping for the week"]}}
pacing_multipliers: {work: 1.2, late_night: 1.4}   # slower replies when "busy" or sleepy
```

```yaml
# holidays.yaml (Tamil Nadu + national), reviewed yearly
2026:
  - {date: 2026-01-14, name: Pongal, lines: ["happy pongal!! 🌾"]}
  - {date: 2026-11-08, name: Deepavali, lines: ["happy deepavali 🪔"]}   # verify dates against the official TN govt holiday list
```

## 5b. News: `news/feeds.yaml` and news cards (FR-F)

```yaml
# feeds.yaml: the URLs must be verified to be real RSS feeds whose terms allow automated reading
tech:
  - {name: TechCrunch AI, url: <rss url>, weight: 1.0}
  - {name: The Verge AI, url: <rss url>, weight: 0.8}
  - {name: Hacker News front page, url: <rss url>, weight: 0.6}
  - {name: Inc42 / YourStory (Indian startups), url: <rss url>, weight: 0.8}
tn_politics:
  - {name: The Hindu — Tamil Nadu, url: <rss url>, weight: 1.0}
  - {name: The News Minute — Tamil Nadu, url: <rss url>, weight: 0.9}
  - {name: DT Next — Tamil Nadu, url: <rss url>, weight: 0.7}
limits: {max_items_per_feed: 20, keep_days: 30}
```

Use several sources for TN politics so no single outlet's framing dominates. Summaries are neutral and factual by instruction, and opinion pieces are dropped by the J6 filter.

News card (Qdrant `news` collection, generated by the job, not hand-written):

```json
{"id": "n-2026-10-20-3f9a", "topic": "tech_industry",
 "headline": "…", "gist": "two neutral sentences", "entities": ["…"],
 "published_at": "2026-10-20T09:15:00+05:30", "source": "TechCrunch",
 "url": "…", "ingested_at": "…", "expires_at": "…"}
```

## 6. `policy.yaml`

```yaml
off_limits:
  - topic: client confidential internals
    reply: ["can't go too deep on client internals tbh, NDA stuff", "but i can tell u how i approached it"]

personal:                     # FR-G: one entry per Jev personal_category; levels escalate on repeated pressing
  relationship:
    playful: [["lol that's classified 😄"], ["haha next question"]]
    vague_redirect: [["all good on that front haha", "anyway what are u working on these days?"]]
    boundary: [["haha let's keep it to work stuff 😄"]]
  religion_caste:
    playful: [["haha i'm more into debugging than debating"]]
    vague_redirect: [["i keep that stuff personal tbh", "but ask me anything tech"]]
    boundary: [["let's skip that one haha 🙏"]]
  political_allegiance:
    playful: [["haha i'm team whoever fixes the roads 😄"]]
    vague_redirect: [["honestly i see points on all sides", "not gonna pick a team in a chat lol"]]
    boundary: [["i'll stay neutral on that one haha"]]
  # job_switch is NOT here: open to AI Engineer roles → answered directly (facts.yaml: open_to)
  salary:
    playful: [["haha that's a call convo"]]
    vague_redirect: [["happy to talk numbers properly on a call", "want me to set one up?"]]   # offers meeting tool
    boundary: [["let's keep that for a proper chat 🙂"]]
  family / health / address / age / other:
    ...

politics_stance:              # F5: TN politics neutrality
  allowed: [acknowledge events, neutral reactions, "interesting times", "both sides have a point"]
  forbidden: [endorse or attack any party/leader, mock any caste/religion/community, say who he votes for, predict elections]
  fence_lines: [["ya saw that", "interesting times for TN politics for sure"], ["honestly both sides have a point there"]]
  banned_terms: [list of party-attack slurs and nicknames kept in a separate file]

who_hook: [["btw who's this? 😄"], ["wait who am i talking to haha"]]   # A10
not_following: [["not really following that ngl"], ["haven't caught up on that one tbh"]]   # F3 / out-of-beat news
identity_sincere:            # FR-D2 — Chandru writes this in his own voice
  - ["haha fair q", "this is my digital twin replying, built it myself 😄", "real me reads these tho, want me to set up a quick call?"]
identity_playful:            # FR-D3 — must not claim to be human
  - ["lol that's a whole story", "ask me something about my projects and judge for urself 😄"]
insufficient_evidence:
  - ["hmm don't remember that detail tbh", "happy to go deeper on a call if u want"]
outage:
  - ["ugh my phone's acting up 😅", "try again in a sec?"]
fastpath_templates:
  greeting: [["heyy 👋", "what's up?"], ["hey hey", "how's it going"]]
  location: [["coimbatore rn", "{{current.location}}"]]
```

## 7. Runtime data (SQLite, WAL, Fly volume)

| Table | Columns | Retention |
|---|---|---|
| `sessions` | id (uuid), created_at, last_seen, persona, active_project, tz, visitor_name_enc, visitor_company_enc, asked_who | 30 days |
| `visitors` | id (browser UUID), created_at, last_seen, visits, tz, profile_enc (name/company/role shared, topics, note, lead_saved), current_conv | forgotten after 30 days inactive, or on "forget me" ([ADR-009](../adr/009-visitor-memory.md)) |
| `conversations` | id (= LangGraph thread), visitor_id, started_at, last_msg_at, msg_count, summarized | with the visitor; checkpoints deleted too |
| `outbox` | event_id (unique), kind (lead.created / booking.created / …), payload_enc, attempts, next_attempt_at, sent_at | 90 days |
| `news_runs` | run_id, started_at, fetched, kept, upserted, status, error | 90 days |
| `messages` | id, session_id, turn_id, role, text, route, created_at | 30 days |
| `leads` | id, session_id, name_enc, company_enc, role_enc, email_enc, created_at, notified_at | until deleted |
| `bookings` | id, session_id, idempotency_key (unique), event_id, start, end, attendee_email_enc, status | until deleted |
| `turn_logs` | turn_id, json | 30 days |
| LangGraph checkpoints | managed by `AsyncSqliteSaver` | 30 days |

`*_enc` fields: AES-GCM with a key from Fly secrets.

## 8. Eval sets — `eval/sets/*.jsonl`

| Set | Size (v1) | Fields | Measures |
|---|---|---|---|
| `routing.jsonl` | 300 | message, history, expected_intent, expected_project, expected_persona | Jev J1 accuracy, thresholds |
| `grounding.jsonl` | 150 | question, project, must_include_card_ids, forbidden_claims | Retrieval recall, grounding precision |
| `adversarial.jsonl` | 80 | question with false premise ("you used Kubernetes at Tpay right?") | 0 fabricated agreement |
| `identity.jsonl` | 60 | sincere + playful probes | D2/D3 compliance |
| `injection.jsonl` | 60 | jailbreak / prompt-leak attempts | A8 |
| `offlimits.jsonl` | 40 | salary, NDA, personal | A7 |
| `multiturn.jsonl` | 40 dialogues | turns + expected resolutions | A4 follow-ups |
| `style_pairs.jsonl` | 100 | prompt + Chandru's real reply (held out from few-shots) | blind test + Jev style score |
| `time.jsonl` | 80 | frozen clock + visitor tz + message, expected/forbidden time claims | A9 |
| `personal.jsonl` | 80 single + 20 pressure dialogues | question, category, press count | FR-G category accuracy, escalation, 0 disclosures |
| `politics.jsonl` | 60 | TN politics questions incl. "who do u support?", baiting | F5: 0 partisan |
| `news.jsonl` | 60 | questions over a frozen news snapshot + fake events + out-of-beat topics | F1–F3 |
| `who_hook.jsonl` | 30 dialogues | with and without self-intro | A10 asked exactly once |

Labelled by hand where it matters (routing, adversarial, identity); others drafted by an LLM and reviewed.
