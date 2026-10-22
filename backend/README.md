# Virtual Me — backend

Texts visitors as Chandru. **The LLM converses, Jev guards, code enforces, code humanizes** ([ADR-008](../docs/adr/008-llm-converses-jev-guards.md)).
Design: [requirements](../docs/virtual-me/requirements.md) · [architecture](../docs/virtual-me/architecture.md) · [data spec](../docs/virtual-me/data-spec.md) · [ADRs](../docs/adr/)

## Run locally

```bash
cd backend
cp .env.template .env          # add OPENROUTER_API_KEY; embedded Qdrant needs nothing else
uv sync
uv run python scripts/ingest.py --allow-unreviewed   # build the local card index
uv run python scripts/chat_cli.py --fast             # chat in the terminal
uv run uvicorn app.main:app --port 8000              # WebSocket at ws://localhost:8000/ws/chat
uv run pytest                                        # ~70 tests, fully offline (fake Jev + LLM)
uv run python eval/golden/run.py --only meet- --only lead-   # golden cases on the real APIs: run the affected ones
```

The frontend dev server (`cd frontend && npm run dev`) connects to `ws://localhost:8000/ws/chat` by default.

## Layout

| Path | What |
|---|---|
| `app/graph/` | LangGraph: `guard → converse (LLM ‖ Jev gates) → [tools] → who_hook → finalize`; side effects pause on an `interrupt` for Jev-checked confirmation |
| `app/graph/converse.py` | One streamed LLM call with history, all cards and tools; gates checked before the first bubble; per-bubble checks and repair |
| `app/graph/gates.py` | One parallel Jev call: sincere identity, injection, off-limits, personal category, wants_connect |
| `app/intelligence/` | The only code that calls OpenRouter: `jev.py` (Decisions API), `decisions.py` (J3, J4, J6, J7, J8, J9, slot pick), `llm.py` (streaming + tool calls) |
| `app/retrieval/` | Qdrant store (news; cards are in the prompt, with hybrid search kept as the scale path), deterministic grounding checks |
| `app/humanizer/` | Burst shaping, one typo per reply at most, typing pacing that hides system latency |
| `app/context/clock.py` | IST "now", weekly routine, TN holidays, visitor local time |
| `app/persona_rules/` | Personal-question dodges, politics neutrality guard, "who's this?" hook |
| `app/integrations/composio_mcp.py` | Composio MCP client: Google Calendar + Gmail, tools resolved from the live tool list ([ADR-010](../docs/adr/010-composio-mcp-and-ask-the-real-me.md)) |
| `app/tools/` | Resume, lead capture, calendar booking and email alerts (via Composio), "ask the real me" questions |
| `app/news/` + `app/jobs/` | Twice-daily news ingest, keepalive, purge, email outbox worker |
| `data/` | Everything the bot knows and how it talks: facts, projects, claim cards, voice, style, routine, policy, feeds. **Not in git** (personal data); format in [data-spec](../docs/virtual-me/data-spec.md) |

## Before it goes live (your to-do)

1. **Review every claim card** in `data/cards/*.yaml` and set `reviewed: true`. The deploy's release step (`scripts/ingest.py`) refuses to run while any public card is unreviewed. Add `negative: true` cards for things you *didn't* do.
2. **Record your voice:** `uv run python scripts/voice_questionnaire.py` (~70 prompts). Then delete `data/voice/seed.jsonl` — those are placeholder examples I wrote, not you.
3. **Edit `data/policy.yaml`** so every dodge, identity and politics line sounds like you. Fill `data/politics_banned_terms.txt`.
4. **News feeds:** check each URL in `data/news/feeds.yaml` (real RSS, terms allow automated reading), then set `enabled: true`.
5. **Holidays:** check `verified: false` dates in `data/persona/holidays.yaml` against the official TN list.
6. **Accounts and secrets** (all free tiers):
   - OpenRouter key → `OPENROUTER_API_KEY`
   - Qdrant Cloud free cluster in an AWS/GCP Singapore region → `QDRANT_URL`, `QDRANT_API_KEY`
   - Composio account → `COMPOSIO_API_KEY` in `.env`, then `uv run python scripts/composio_connect.py` and open the two links (Google Calendar, Gmail). Re-run it to confirm "connected" and see which MCP tools were resolved
   - `LEAD_KEY_B64`: `python -c "import os,base64;print(base64.b64encode(os.urandom(32)).decode())"`
7. **Calibrate** with the real APIs: `uv run python eval/run_eval.py gates` and `identity` (Jev gate thresholds), and `bench` (pick the LLM by measured TTFT, ideally from the Fly machine).

## Deploy (Fly.io, `sin`)

```bash
fly launch --no-deploy --copy-config
fly volumes create vm_data --region sin --size 1
fly secrets set OPENROUTER_API_KEY=... QDRANT_URL=... QDRANT_API_KEY=... COMPOSIO_API_KEY=... LEAD_KEY_B64=...
fly deploy
```

The GitHub Pages build already points the site at `wss://virtual-me-chandru.fly.dev/ws/chat` (`.github/workflows/deploy.yml`); change it if you pick another Fly app name.

## Admin

```bash
uv run python scripts/admin.py leads | bookings | flagged --days 7 | stats | transcript <session_id>
uv run python scripts/admin.py questions | learned      # "ask the real me" queue, and your answers as draft cards
```
