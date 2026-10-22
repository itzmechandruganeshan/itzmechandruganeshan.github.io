import time
import uuid

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from app.chat import TurnRunner
from app.graph.build import build_graph
from app.memory import FORGET_RE, VisitorMemory, memory_note


@pytest.fixture
def mem(env):
    saver = InMemorySaver()
    graph = build_graph(saver)

    async def no_sleep(_):
        return None

    env.runner = TurnRunner(graph, env.deps, sleep=no_sleep)
    env.saver = saver
    return VisitorMemory(env.deps, graph, saver)


async def _chat(env, mem, vid, text, reply):
    visit = await mem.open(vid)
    env.llm.replies.append(reply)
    events = []

    async def send(ev):
        events.append(ev)

    note = memory_note(visit.profile, visit.visits, visit.last_seen, time.time()) if visit.new_conversation else ""
    await env.runner.run(visit.conversation_id, text, send,
                         memory={"profile": visit.profile, "note": note} if visit.new_conversation else None)
    await mem.touch(visit)
    return visit, [e["text"] for e in events if e["type"] == "burst"]


async def _age(env, vid, hours):
    old = time.time() - hours * 3600
    await env.db.execute("UPDATE conversations SET last_msg_at=? WHERE visitor_id=?", (old, vid))
    await env.db.execute("UPDATE visitors SET last_seen=? WHERE id=?", (old, vid))


async def test_same_conversation_within_gap(env, mem):
    vid = str(uuid.uuid4())
    v1, _ = await _chat(env, mem, vid, "hi", ["heyy"])
    v2, _ = await _chat(env, mem, vid, "how's it going", ["good"])
    assert v1.conversation_id == v2.conversation_id and v1.visits == v2.visits == 1


async def test_return_after_gap_new_conversation_with_profile(env, mem):
    vid = str(uuid.uuid4())
    await _chat(env, mem, vid, "hey i'm surya", ["hey surya ⟦v:name=Surya⟧"])
    await _chat(env, mem, vid, "how did tpay routing work? and what's your salary", ["it routed across agents ⟦c:tp-02⟧"])
    await _age(env, vid, hours=50)
    env.llm.json_replies.append({"topics": ["tpay agent routing", "salary"], "note": "student curious about agents"})
    v, bursts = await _chat(env, mem, vid, "hi again", ["hey surya, back again 😄"])
    assert v.new_conversation and v.visits == 2
    assert v.profile["name"] == "Surya"
    assert v.profile["topics"] == ["tpay agent routing"]  # "salary" filtered; "tpay" not mistaken for "pay"
    sys = " ".join(p["text"] for p in env.llm.prompts[-1][0]["content"])
    assert "MEMORY: this visitor has chatted with you before (visit 2" in sys and "Surya" in sys
    # fresh thread: the old turns are not in the message history
    assert not any("tpay" in str(m.get("content", "")).lower() for m in env.llm.prompts[-1][1:])


async def test_known_name_skips_whos_this(env, mem):
    vid = str(uuid.uuid4())
    await _chat(env, mem, vid, "i'm surya", ["hey surya ⟦v:name=Surya⟧"])
    await _age(env, vid, hours=3)
    env.llm.json_replies.append({"topics": [], "note": ""})
    for msg in ("hi", "what's up", "cool"):
        _, bursts = await _chat(env, mem, vid, msg, ["nice"])
        assert not any("who" in b for b in bursts)


async def test_forget_wipes_everything_including_checkpoints(env, mem):
    vid = str(uuid.uuid4())
    v, _ = await _chat(env, mem, vid, "hi", ["heyy"])
    cfg = {"configurable": {"thread_id": v.conversation_id, "deps": env.deps}}
    assert (await env.runner.graph.aget_state(cfg)).values
    await mem.forget(vid)
    assert (await env.runner.graph.aget_state(cfg)).values == {}
    for table, col in (("visitors", "id"), ("conversations", "visitor_id")):
        assert await env.db.fetchall(f"SELECT * FROM {table} WHERE {col}=?", (vid,)) == []
    assert await env.db.fetchall("SELECT * FROM messages WHERE session_id=?", (v.conversation_id,)) == []


async def test_purge_forgets_inactive_visitors(env, mem):
    vid = str(uuid.uuid4())
    await _chat(env, mem, vid, "hi", ["heyy"])
    await _age(env, vid, hours=24 * 31)
    assert await mem.purge() == 1
    assert await env.db.fetchone("SELECT * FROM visitors WHERE id=?", (vid,)) is None


def test_forget_phrases():
    assert FORGET_RE.search("forget me") and FORGET_RE.search("please delete my data")
    assert not FORGET_RE.search("don't forget to send the resume")
