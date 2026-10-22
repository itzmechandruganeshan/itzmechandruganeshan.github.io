"""Regressions from the live chat on 2026-10-22 ("would like to connect with you tmrw" never booked)."""

from tests.test_composio import FakeCX


async def _state(env):
    return (await env.runner.graph.aget_state({"configurable": {"thread_id": env.sid, "deps": env.deps}})).values


async def test_gate_alone_does_not_start_a_flow_on_i_love_you(env):
    env.jev.turns["love"] = {"wants_connect": 0.71}
    env.llm.replies.append(["aw that's sweet haha"])
    _, _, rec = await env.say("i love you")
    assert "connect_by_gate" not in rec["flags"] and not (await _state(env)).get("tool")


async def test_volunteering_ai_is_dropped_before_disclosure(env):
    env.llm.replies.append(["aw that's sweet haha", "i'm an AI though, so I can't love back", "anyway what's up?"])
    bursts, _, _ = await env.say("i love you")
    assert not any("ai" in b.lower().split() for b in bursts)


async def test_meeting_request_during_a_stuck_lead_flow_switches_and_asks_email(env):
    env.deps.actions = FakeCX()
    # a lead flow is open and waiting for a name...
    env.llm.replies.append({"lines": ["sure"], "tools": [{"name": "start_connect", "arguments": {"kind": "lead"}}]})
    env.llm.json_replies.append({"name": None})
    await env.say("want to connect")
    # ...visitor ignores it and asks for a call: the tool request must not be dropped
    env.llm.json_replies.append({"name": None})  # nothing name-like in it: the flow hands off to the LLM
    env.llm.replies.append({"lines": ["sounds good, a call tmrw afternoon"],
                            "tools": [{"name": "start_connect", "arguments": {"kind": "meeting", "about": "hiring"}}]})
    bursts, cards, rec = await env.say("set up call, tmrw afternoon any time works for me")
    assert rec["route"] == "tools" and any(c["kind"] == "slots" for c in cards)
    assert (await _state(env))["tool"]["kind"] == "meeting"


async def test_yep_with_only_a_tool_call_is_not_ignored(env):
    env.llm.replies.append({"lines": [], "tools": [{"name": "start_connect", "arguments": {"kind": "lead", "about": "hiring"}}]})
    env.llm.json_replies.append({"name": None})
    bursts, _, rec = await env.say("yep")
    assert rec["route"] == "tools" and not any("not sure" in b for b in bursts)


async def test_email_given_while_name_was_asked_is_kept(env):
    env.llm.replies.append({"lines": ["sure"], "tools": [{"name": "start_connect", "arguments": {"kind": "lead", "about": "a role"}}]})
    env.llm.json_replies.append({"name": None})
    await env.say("want to connect about a role")
    env.jev.turns["@"] = {"ok": 0.1}  # J9: an email is not a name
    env.llm.json_replies.append({"name": None})
    env.llm.replies.append(["thanks, and ur name?"])
    await env.say("varadha@deloitte.com")
    assert (await _state(env))["tool"]["slots"].get("email") == "varadha@deloitte.com"


async def test_ignored_flow_is_parked_after_two_handoffs(env):
    env.llm.replies.append({"lines": ["sure"], "tools": [{"name": "start_connect", "arguments": {"kind": "lead"}}]})
    env.llm.json_replies.append({"name": None})
    await env.say("want to connect")
    env.jev.extra["ok"] = 0.1
    for msg in ("what's your stack?", "and your favourite project?"):
        env.llm.json_replies.append({"name": None})
        env.llm.replies.append(["langgraph mostly"])
        await env.say(msg)
    assert (await _state(env))["tool"]["stage"] == "parked"
