import contextlib
import json
import random
import uuid
from datetime import datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient
from langgraph.checkpoint.memory import InMemorySaver

from app.chat import TurnRunner
from app.config import Settings
from app.data import get_knowledge
from app.graph.build import build_graph
from app.graph.prompts import facts_flat
from app.graph.state import Deps
from app.memory import VisitorMemory
from app.retrieval.checks import known_entities
from app.runtime import protected_terms
from app.storage.crypto import Box
from app.storage.db import DB
from app.ws import router
from tests.conftest import IST, FakeJev, FakeLLM


def make_app(tmp_path):
    @contextlib.asynccontextmanager
    async def lifespan(app):
        kb = get_knowledge()
        s = Settings(_env_file=None, db_path=tmp_path / "ws.db", allow_unreviewed_cards=True, idle_nudge_s=0.3)
        db = await DB.open(s.db_path)
        deps = Deps(settings=s, kb=kb, jev=FakeJev(), llm=FakeLLM(), store=None, db=db, box=Box("", prod=False),
                    protected=protected_terms(kb), entities=known_entities(kb), facts_text=facts_flat(kb),
                    now=lambda: datetime(2026, 10, 21, 15, 0, tzinfo=IST), rng=random.Random(1))

        async def no_sleep(_):
            return None

        class RT:
            pass

        rt = RT()
        rt.deps = deps
        app.state.runtime = rt
        saver = InMemorySaver()
        graph = build_graph(saver)
        app.state.runner = TurnRunner(graph, deps, sleep=no_sleep)
        app.state.memory = VisitorMemory(deps, graph, saver)
        yield
        await db.close()

    app = FastAPI(lifespan=lifespan)
    app.include_router(router)
    return app


def recv_turn(ws):
    events = []
    while True:
        ev = json.loads(ws.receive_text())
        events.append(ev)
        if ev["type"] == "turn_complete":
            return events


def test_protocol_roundtrip_and_dedupe(tmp_path):
    with TestClient(make_app(tmp_path)) as client, client.websocket_connect("/ws/chat") as ws:
        ws.send_text(json.dumps({"type": "hello", "visitor_id": str(uuid.uuid4()), "tz": "Asia/Kolkata"}))
        ws.send_text(json.dumps({"type": "message", "text": "hey", "client_msg_id": "m1"}))
        events = recv_turn(ws)
        kinds = [e["type"] for e in events]
        assert kinds[0] == "typing" and "burst" in kinds and kinds[-1] == "turn_complete"
        bursts = [e for e in events if e["type"] == "burst"]
        assert [b["seq"] for b in bursts] == list(range(len(bursts)))
        # same client_msg_id again is ignored; the idle nudge arrives instead of a second reply
        ws.send_text(json.dumps({"type": "message", "text": "hey", "client_msg_id": "m1"}))
        nudge = json.loads(ws.receive_text())
        assert nudge["type"] == "burst" and nudge["turn_id"] == "nudge"


def test_rejects_bad_hello(tmp_path):
    with TestClient(make_app(tmp_path)) as client, client.websocket_connect("/ws/chat") as ws:
        ws.send_text(json.dumps({"type": "hello", "session_id": "not-a-uuid"}))
        try:
            ws.receive_text()
            raise AssertionError("expected close")
        except Exception as e:  # noqa: BLE001
            assert "1008" in repr(e) or "Disconnect" in type(e).__name__


def test_forget_over_websocket(tmp_path):
    with TestClient(make_app(tmp_path)) as client, client.websocket_connect("/ws/chat") as ws:
        ws.send_text(json.dumps({"type": "hello", "visitor_id": str(uuid.uuid4())}))
        ws.send_text(json.dumps({"type": "message", "text": "hey"}))
        recv_turn(ws)
        ws.send_text(json.dumps({"type": "forget"}))
        events = []
        while True:
            ev = json.loads(ws.receive_text())
            events.append(ev)
            if ev["type"] == "forgotten":
                break
        assert any("wiped" in e.get("text", "") for e in events)


def test_waiting_answer_is_texted_first_on_hello(tmp_path):
    app = make_app(tmp_path)
    vid = str(uuid.uuid4())
    with TestClient(app) as client:
        deps = app.state.runtime.deps

        async def seed():
            await deps.db.execute(
                "INSERT INTO questions(id, visitor_id, question_enc, answer_enc, status, created_at, answered_at) "
                "VALUES (?,?,?,?,?,?,?)",
                ("q1", vid, deps.box.seal("did you use kubernetes?"), deps.box.seal("no, cloud run"), "answered", 0, 1))
            deps.llm.json_replies.append({"bubbles": ["oh btw, about ur kubernetes question", "nope, cloud run"]})

        client.portal.call(seed)
        with client.websocket_connect("/ws/chat") as ws:
            ws.send_text(json.dumps({"type": "hello", "visitor_id": vid}))
            first = []
            while len(first) < 2:
                ev = json.loads(ws.receive_text())
                if ev["type"] == "burst":
                    first.append(ev["text"])
            assert "kubernetes" in first[0] and "cloud run" in first[1]
            # it becomes part of the conversation the visitor continues
            ws.send_text(json.dumps({"type": "message", "text": "oh nice, thanks"}))
            recv_turn(ws)
        prompt = deps.llm.prompts[-1]
        assert any(m["role"] == "assistant" and "cloud run" in m["content"] for m in prompt)
