# Portfolio Bot Backend

A lightweight, production-ready AI chatbot backend that serves as an interactive portfolio assistant. Built with **FastAPI + WebSocket** for real-time streaming responses, powered by LLM inference via **OpenRouter**.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                         Client (Browser)                         │
│                      WebSocket: /ws/chat                         │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│  FastAPI Application                                             │
│                                                                  │
│  ┌────────────┐  ┌──────────────┐  ┌──────────────────────────┐ │
│  │ WebSocket  │──│ Orchestrator │──│ LLM Provider (OpenRouter) │ │
│  │ Handler    │  │ (ReAct Loop) │  │ Streaming + Tool Calling  │ │
│  └────────────┘  └──────┬───────┘  └──────────────────────────┘ │
│                         │                                        │
│              ┌──────────┴──────────┐                             │
│              │                     │                             │
│        ┌─────▼─────┐    ┌─────────▼──────────┐                  │
│        │   Tools    │    │  Session Service   │                  │
│        │ • Time     │    │  (SQLite + WAL)    │                  │
│        │ • Meeting  │    └────────────────────┘                  │
│        │ • MCP      │                                            │
│        └────────────┘                                            │
└──────────────────────────────────────────────────────────────────┘
```

**Key design choices:**
- **No RAG / No embeddings** — Resume knowledge is structured and embedded directly in the system prompt for zero-latency retrieval and full-context awareness
- **WebSocket-first** — Persistent connection with real-time token streaming, typing indicators, and idle nudges
- **ReAct loop** — Up to 5 iterations of LLM reasoning + tool calling before final response
- **Humanizer** — Simulates typing bursts (`|split|`), rare typos with corrections, and casual tone

---

## Folder Structure

```
app/
├── main.py              # FastAPI entry point, lifespan, health check
├── config.py            # Environment settings (Pydantic)
├── database.py          # SQLite init (WAL mode, session + message tables)
├── session.py           # Session hashing, creation, resume, message persistence
├── orchestrator.py      # ReAct loop, LLM streaming, tool dispatch
├── llm.py               # OpenRouter API streaming client
├── tools.py             # Tool definitions + native/MCP execution
├── websocket.py         # WebSocket endpoint + connection manager
└── prompts/
    └── system.txt       # System prompt with structured resume knowledge
tests/
├── test_tools.py        # Tool execution unit tests
└── test_websocket.py    # WebSocket protocol integration tests
```

---

## Getting Started

### Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

### Environment Variables

Create a `.env` file:

```env
OPENROUTER_API_KEY=sk-or-v1-your-key-here
COMPOSIO_API_KEY=ak_your-composio-key
```

| Variable             | Required | Description                                                          |
| -------------------- | -------- | -------------------------------------------------------------------- |
| `OPENROUTER_API_KEY` | Yes      | API key for [OpenRouter](https://openrouter.ai) LLM access           |
| `COMPOSIO_API_KEY`   | Yes      | API key for [Composio](https://composio.dev) external tool execution |

### Run Locally

```bash
# Install dependencies
uv sync

# Start the server
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000

# Or with hot reload for development
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Run Tests

```bash
uv run pytest tests/ -v
```

### Docker

```bash
docker compose up --build
```

---

## WebSocket Protocol

### Endpoint

```
ws://localhost:8000/ws/chat
```

### Message Flow

```
CLIENT                          SERVER
  │                               │
  │──── text: "Hello" ───────────▶│
  │                               │
  │◀── json: {type: "status",  ──│   ← typing indicator
  │          action: "typing"}    │
  │                               │
  │◀── text: "Hey bro!" ────────│   ← streamed response chunks
  │◀── text: "|split|" ─────────│   ← burst separator
  │◀── text: "What's up?" ──────│
  │                               │
  │◀── json: {type: "status",  ──│   ← generation complete
  │          action: "idle"}      │
  │◀── json: {type:              ──│   ← turn complete signal
  │          "turn_complete"}     │
  │                               │
  │     (60s idle)                │
  │◀── text: "You still there?" ─│   ← idle nudge
```

### Health Check

```bash
curl http://localhost:8000/health
# {"status": "healthy", "active_websockets": 0}
```

---

## Tools

| Tool               | Type   | Description                             |
| ------------------ | ------ | --------------------------------------- |
| `get_current_time` | Native | Returns current IST date/time           |
| `schedule_meeting` | Native | Generates pre-filled Calendly link      |
| External tools     | MCP    | Routed to Composio API with retry logic |

---

## License

MIT
