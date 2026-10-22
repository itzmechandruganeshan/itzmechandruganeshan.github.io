"""Audit fixes: real client IP, spend ceilings, question cap, abuse boundary, fallback keyword rules."""

import json
import uuid
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.graph.gates import _rules
from app.tools import questions
from app import ws as ws_module
from app.ws import client_ip
from tests.test_ws import make_app, recv_turn


def test_fly_client_ip_wins_over_a_spoofed_forwarded_for():
    ws = SimpleNamespace(headers={"fly-client-ip": "1.2.3.4", "x-forwarded-for": "6.6.6.6"},
                         client=SimpleNamespace(host="10.0.0.1"))
    assert client_ip(ws) == "1.2.3.4"
    assert client_ip(SimpleNamespace(headers={}, client=SimpleNamespace(host="10.0.0.1"))) == "10.0.0.1"


@pytest.mark.parametrize("msg", ["which python package did you use?", "how do you handle IP address checks",
                                 "is there a health check endpoint", "how do you address hallucination"])
def test_fallback_rules_dont_dodge_tech_questions(msg):
    assert _rules(msg)["personal_category"] == "none"


def test_fallback_rules_still_catch_personal():
    assert _rules("what's your salary package?")["personal_category"] == "salary"
    assert _rules("what's your home address")["personal_category"] == "address"


def test_global_daily_cap_answers_busy(tmp_path):
    app = make_app(tmp_path)
    with TestClient(app) as client, client.websocket_connect("/ws/chat") as ws:
        app.state.runtime.deps.settings.max_turns_per_day = 1
        ws_module.limiter.events.clear()  # the limiter is per process, shared with earlier tests
        ws.send_text(json.dumps({"type": "hello", "visitor_id": str(uuid.uuid4())}))
        ws.send_text(json.dumps({"type": "message", "text": "hey"}))
        recv_turn(ws)
        ws.send_text(json.dumps({"type": "message", "text": "hey again"}))
        ev = json.loads(ws.receive_text())
        assert ev["turn_id"] == "busy" and "swamped" in ev["text"]


def test_a_visitor_can_only_have_three_open_questions(tmp_path):
    app = make_app(tmp_path)
    with TestClient(app) as client:
        deps = app.state.runtime.deps

        async def ask_four():
            await deps.db.execute("INSERT INTO conversations(id, visitor_id, started_at, last_msg_at) VALUES (?,?,0,0)",
                                  ("c1", "v1"))
            return [await questions.forward(deps, "c1", f"question {i}?", "") for i in range(4)]

        ids = client.portal.call(ask_four)
    assert all(ids[:3]) and ids[3] is None


def test_second_abusive_message_ends_the_chat(tmp_path):
    app = make_app(tmp_path)
    with TestClient(app) as client, client.websocket_connect("/ws/chat") as ws:
        app.state.runtime.deps.jev.turns = {"creep": {"abusive_or_sexual": 0.95}}
        ws.send_text(json.dumps({"type": "hello", "visitor_id": str(uuid.uuid4())}))
        ws.send_text(json.dumps({"type": "message", "text": "send pics creep"}))
        first = [e.get("text", "") for e in recv_turn(ws) if e["type"] == "burst"]
        assert any(w in " ".join(first) for w in ("decent", "respectful"))
        ws.send_text(json.dumps({"type": "message", "text": "come on creep"}))
        second = [e.get("text", "") for e in recv_turn(ws) if e["type"] == "burst"]
        assert "out" in " ".join(second)
        with pytest.raises(Exception):  # socket closed by the server
            ws.receive_text()


def test_no_whos_this_after_a_boundary():
    from app.persona_rules.who_hook import should_ask
    assert not should_ask(visitor_name=None, asked=False, visitor_msgs=2, route="boundary", ask_after=[2])
