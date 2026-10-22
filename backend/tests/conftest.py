from __future__ import annotations

import random
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from app.chat import TurnRunner
from app.config import Settings
from app.data import get_knowledge
from app.graph.build import build_graph
from app.graph.prompts import facts_flat
from app.graph.state import Deps
from app.intelligence.jev import ChoiceAnswer, JevError, JevResult, ScoreAnswer
from app.intelligence.llm import LLMError
from app.retrieval.checks import known_entities
from app.runtime import protected_terms
from app.storage.crypto import Box
from app.storage.db import DB

IST = ZoneInfo("Asia/Kolkata")


class FakeJev:
    """Answers J1 from `turns` (substring of message -> overrides); other questions from `extra`."""

    def __init__(self):
        self.turns: dict[str, dict] = {}
        self.extra: dict[str, object] = {}
        self.calls: list[dict] = []
        self.fail = False

    async def decide(self, state, questions, session_id=None, timeout=None):
        self.calls.append({"state": state, "questions": list(questions)})
        if self.fail:
            raise JevError("down")
        msg = (state.get("message") or state.get("visitor_reply") or "") if isinstance(state, dict) else ""
        over = {}
        for k, v in self.turns.items():
            if k.lower() in msg.lower():
                over = v
        answers = {}
        for key, q in questions.items():
            val = over.get(key, self.extra.get(key))
            if q["type"] == "choice":
                crit = list(q["criteria"])
                default = next((c for c in ("unknown", "none", "unclear", "neither") if c in crit), crit[0])
                choice = val if val is not None else default
                answers[key] = ChoiceAnswer(choice=choice, probabilities={choice: 0.9}, confidence=0.9)
            elif q["type"] == "noul":
                answers[key] = float(val if val is not None else (1.0 if key == "ok" else 0.0))
            else:
                answers[key] = ScoreAnswer(score=float(val if val is not None else 1), probabilities={}, confidence=0.9)
        return JevResult(answers=answers, model="fake-jev", latency_ms=1.0)


class FakeLLM:
    def __init__(self):
        self.replies: list[list[str]] = []
        self.json_replies: list[dict] = []
        self.prompts: list[list[dict]] = []

    async def stream_lines(self, messages, *, max_tokens, stats, models=None, temperature=None, tools=None):
        """A reply is either a list of lines, or {"lines": [...], "tools": [{"name": ..., "arguments": {...}}]}."""
        self.prompts.append(messages)
        stats.ttft_ms = 5.0
        stats.model = "fake-llm"
        reply = self.replies.pop(0) if self.replies else ["ok"]
        lines, calls = (reply.get("lines", []), reply.get("tools", [])) if isinstance(reply, dict) else (reply, [])
        for line in lines:
            yield line
        stats.tool_calls = list(calls) if tools else []

    async def complete_json(self, messages, *, model=None, max_tokens=400, timeout=10.0):
        if not self.json_replies:
            raise LLMError("no fake json")
        return self.json_replies.pop(0)


@pytest.fixture
def kb():
    return get_knowledge()


@pytest.fixture
def now_box():
    return {"now": datetime(2026, 10, 21, 15, 0, tzinfo=IST)}  # Wednesday, working hours


@pytest.fixture
async def env(tmp_path, kb, now_box):
    s = Settings(_env_file=None, db_path=tmp_path / "app.db", allow_unreviewed_cards=True, seed=7,
                 openrouter_api_key="test")
    db = await DB.open(s.db_path)
    jev, llm = FakeJev(), FakeLLM()
    deps = Deps(settings=s, kb=kb, jev=jev, llm=llm, store=None, db=db, box=Box("", prod=False),
                protected=protected_terms(kb), entities=known_entities(kb), facts_text=facts_flat(kb),
                now=lambda: now_box["now"], rng=random.Random(7))

    async def no_sleep(_):
        return None

    runner = TurnRunner(build_graph(InMemorySaver()), deps, sleep=no_sleep)

    class Env:
        pass

    e = Env()
    e.deps, e.jev, e.llm, e.runner, e.db, e.sid = deps, jev, llm, runner, db, str(uuid.uuid4())

    async def say(text, **kw):
        events = []

        async def send(ev):
            events.append(ev)

        rec = await runner.run(e.sid, text, send, **kw)
        bursts = [ev["text"] for ev in events if ev["type"] == "burst"]
        cards = [ev for ev in events if ev["type"] == "card"]
        return bursts, cards, rec

    e.say = say
    yield e
    await db.close()
