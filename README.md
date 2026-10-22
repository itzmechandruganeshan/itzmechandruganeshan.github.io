# itzmechandruganeshan.github.io

This is my portfolio site, plus the thing I actually wanted to build: a chat on the site that texts like me.

Not a chatbot that says "Great question! As an AI engineer, Chandru has extensive experience in…". I mean the way I'd reply on WhatsApp. Short messages, a few bubbles, a bit of slang, sometimes a typo, and I don't write an essay when someone asks something simple.

I'm calling it **Virtual Me**.

- `frontend/` is the Next.js portfolio (static, on GitHub Pages). Press ⌘K to open the chat.
- `backend/` is the Virtual Me service (FastAPI + LangGraph, meant for Fly.io in Singapore).
- `docs/` has the requirements, the architecture, and the decisions I made along the way (ADRs), including the ones I changed my mind on.

---

## What I wanted from it

When I sat down to write the requirements, these were the non-negotiables:

1. **It should feel like texting me.** Bursts of 1-3 messages, casual, tech jargon when the other person is technical, friendly, and no long answers unless they ask for more.
2. **It should only say true things about me.** If it doesn't know, it says "don't remember that part tbh", like I would. It shouldn't make up a metric or a tool I never used.
3. **It should feel like a person, not a support bot.** It knows what time it is in Coimbatore, roughly what I'd be doing (office, tea break, Sunday biryani), follows a bit of tech news and TN politics, and dodges personal questions the way people do.
4. **It shouldn't lie about being human.** This one I had to think about. I didn't want any "AI" label in the UI. But if someone *sincerely* asks "am I talking to a bot?", it says it's my digital twin and offers a call with the real me. People share their email and book calls based on this chat, and lying at that point isn't something I want my name on. Casual jokes like "lol r u a bot" can get a playful dodge.
5. **It should be fast.** The first bubble should arrive in about the time a person takes to start typing.
6. **Recruiters should be able to actually do something.** Get my resume, leave their details, book a call on my calendar.

---

## How a message flows (current design)

```
visitor message
  ├─► LLM (full conversation + everything I know, in a cached prompt + tools)   ── streams bubbles ──┐
  └─► Jev gates in parallel: sincere "are you a bot?" · prompt injection ·                            │
      confidential ask · personal question · wants to connect                                         │
         a gate trips? → drop the LLM's reply, use the line I wrote for that case                     │
  every bubble → code checks (numbers, names, citations) + Jev grounding check → humanizer → visitor ◄┘
  tool call (resume / connect / book a call / news / ask me) → Jev verifies the visitor really asked → code runs it
  booking or saving their details → pause, ask them to confirm → Jev reads "yes / no / change it" → code acts
```

In one line: **the LLM talks, Jev guards, code enforces, code humanizes.**

---

## Why I built it this way

### I started with Jev routing everything, and changed it

[Jev](https://openrouter.ai/blog/insights/what-is-jev/) is TypeSafe's decision model. It answers typed questions (pick one, yes/no, a score) with probabilities, fast and cheap. My first design used it as the "control brain": classify every message, then route it to one of eight nodes.

It looked clean on paper. In real chats it kept missing things. "why" got classified as unknown. "what's pymlrs?" also went to unknown, even though Jev itself had picked the project correctly. After the bot told someone it's my twin, "what's ur name" got read as another identity question. Every wrong label sent the whole turn down the wrong path, and I kept adding rules to patch it.

The problem wasn't Jev. I gave it the wrong job. Jev sees one message. The LLM sees the whole conversation. Understanding "why" or "how long?" needs the conversation.

So now ([ADR-008](docs/adr/008-llm-converses-jev-guards.md)):
- The **LLM handles the conversation**, with the full history and all my project facts in the prompt.
- **Jev only does what it's actually good at:** typed yes/no decisions that code has to enforce. Is this a sincere bot question, a prompt injection, a request for confidential stuff, a personal question? Did the visitor really ask for the resume? Does this reply really answer what we asked? Is this bubble backed by the facts?
- The Jev gates run **in parallel** with the LLM, so they add no wait. The old serial routing call is gone, and the first bubble got about 240 ms faster.

### No RAG for my own facts (for now)

All my project facts are around 70 short "cards", about 6k tokens. That fits in the prompt and gets cached, so it costs roughly nothing per message.

With top-k retrieval I kept hitting two problems: facts from one project bleeding into another (two projects both use LangGraph), and the one card with the actual metric not making the top-k. Putting everything in context removes both. Qdrant is still there for news, and as the path back to retrieval if the cards ever get past ~20k tokens.

Every bubble that states a fact cites the card it came from. Code checks that the numbers and tech names really appear there (it accepts sensible rounding like "22k" for 22,018, and blocks invented ones), and Jev checks the claim is supported. A bubble that fails gets one repair attempt, otherwise it's dropped.

### The human feel is mostly code, not prompt

Asking an LLM to "add typos and sound casual" gives you typos in names and numbers and a lot of "haha". So the LLM only writes the content, and code handles the rest:
- splitting into bubbles
- at most one typo per reply, never in names, numbers, links or tech terms, sometimes followed by a `*correction`
- "haha" / "lol" / "tbh" at most once per reply, and not again in the next two replies
- typing delays that cover the time the backend actually needs
- what I'm doing right now, from my weekly routine (office, tea break, gossip, EOD update, Saturday with friends, Sunday biryani)

### Remembering people, carefully

If you come back on the same browser, it remembers your name and roughly what we talked about, and starts a fresh chat with "hey, good to see u back". It does **not** replay the old thread ([ADR-009](docs/adr/009-visitor-memory.md)).

It recognises you only by a random ID stored in your browser. Never by a name someone types (anyone can type "I'm Priya"), never by IP or fingerprinting. It forgets you after 30 days of inactivity, "Forget me" in the chat wipes everything, and the chat says plainly that chats are saved for 30 days.

### Actions through MCP

Booking a call and emailing me go through **Composio's MCP server** (Google Calendar + Gmail) ([ADR-010](docs/adr/010-composio-mcp-and-ask-the-real-me.md)). The LLM doesn't get to book things on its own. It asks to, Jev checks the visitor really wanted that, the visitor confirms, and then code calls the tool. Picking the time slots is plain code: working hours, buffers, and a mix of times across different days, the way a person would offer them.

### "Ask the real me"

If the bot doesn't know something about my work, it says "lemme check and get back to u?". If they say yes, I get an email with the question. When I reply to that email, the next time they open the chat it texts them first with my answer, in my style. My answers also become draft facts for the bot, so it gets better from real questions.

---

## Measuring it, not guessing

Every change gets checked against a **golden set**: about 170 conversations covering everything I could think of. Greetings at 2am, follow-ups like "tell me more abt it", false premises ("you built tpay in rust right?"), questions it shouldn't know the answer to, personal questions, people pressing on them, injection attempts, booking flows, and the actual chats where things broke.

Each turn is checked step by step (did the gate fire, which facts did it cite, did a check drop a bubble) plus a set of style checks on every reply: no "Great question", no markdown, no leaked tags, never claiming to be human, no "ask me when I'm awake", "haha" not repeated.

Where it stood when I last ran the full set (3 runs each):
- 164/165 cases passed every run, 0 failed every time
- all style checks at 100% across 642 turn-runs
- first bubble p50 ~1.4 s (the typing delay on top of that is intentional)

Every turn also stores a full trace, so when a chat goes wrong I can see exactly which step did it. Most of the decisions above came from reading those traces. One example: the bot once dropped a meeting request because an earlier "i love you" had been read as "wants to connect". It's all written up in the commit history and the ADRs.

There are also ~70 offline tests (fake Jev and LLM) that cost nothing to run.

---

## What's not in this repo (on purpose)

- **My data.** `backend/data/` holds my facts, project cards, how I text, and how I want personal questions handled. It stays on my machine and the server. The format is documented in [docs/virtual-me/data-spec.md](docs/virtual-me/data-spec.md) if you want to build your own.
- **Secrets.** Everything goes through `backend/.env` / Fly secrets. See `backend/.env.template`.
- **Anything from my employers or clients.** Project facts are written by me, at the level I'm allowed to talk about.

Since the data isn't here, the backend won't answer anything useful if you just clone and run it, and most tests expect the data folder to exist. That's expected.

---

## Running it

Backend runbook (setup, deploy, admin commands): [backend/README.md](backend/README.md)

```bash
cd backend && uv sync && uv run uvicorn app.main:app --port 8000
cd frontend && npm install && npm run dev   # then open localhost:3000 and press ⌘K
```

Stack: Next.js · FastAPI · LangGraph · OpenRouter (Claude Haiku 5.5 for the chat, Jev for decisions) · Qdrant · Composio MCP · SQLite · Fly.io

---

## Still to do

- Review every fact card myself (the deploy refuses to ship unreviewed ones)
- Record my real texting voice; the current examples are placeholders
- Turn on the news feeds, deploy the backend to Fly, then point the site at it
- Next ideas: a job-description fit check for recruiters, and a nightly job that finds what people ask that the bot can't answer yet

If you're a recruiter and you've read this far, the easiest way to see it is to open the site and text it. Or just ask it to set up a call.
