"""Graph wiring (ADR-008): guard → converse (LLM ‖ Jev gates) → [tools] → who_hook → finalize → [confirm]."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.graph import converse as c
from app.graph import tools_flow as t
from app.graph.state import TurnState


def _after_converse(state: TurnState) -> str:
    return "tools" if state.get("tool_request") else "who_hook"


def _after_tools(state: TurnState) -> str:
    return "converse" if state.get("handoff") and not state.get("out") else "who_hook"


def _after_finalize(state: TurnState) -> str:
    return "await_confirm" if (state.get("tool") or {}).get("stage") == "confirm" else END


def build_graph(checkpointer=None):
    g = StateGraph(TurnState)
    g.add_node("guard", c.guard)
    g.add_node("converse", c.converse)
    g.add_node("tools", t.tools)
    g.add_node("who_hook", c.who_hook)
    g.add_node("finalize", c.finalize)
    g.add_node("await_confirm", t.await_confirm)
    g.add_node("confirm_handle", t.confirm_handle)
    g.add_node("execute", t.execute)
    g.add_node("reask", t.reask)
    g.add_node("cancel", t.cancel)

    g.add_edge(START, "guard")
    g.add_conditional_edges("guard", c.entry, ["tools", "converse"])
    g.add_conditional_edges("converse", _after_converse, ["tools", "who_hook"])
    g.add_conditional_edges("tools", _after_tools, ["converse", "who_hook"])
    g.add_edge("who_hook", "finalize")
    g.add_conditional_edges("finalize", _after_finalize, ["await_confirm", END])

    g.add_edge("await_confirm", "confirm_handle")
    g.add_conditional_edges("confirm_handle", t.after_confirm, {
        "execute": "execute", "tools_again": "tools", "reask": "reask", "cancel": "cancel", "converse": "converse",
    })
    for k in ("execute", "reask", "cancel"):
        g.add_edge(k, "finalize")
    return g.compile(checkpointer=checkpointer)
