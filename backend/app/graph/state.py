"""Graph state. Persistent fields survive across turns (checkpointed per session thread)."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Annotated, Any, Callable, TypedDict

from app.config import Settings
from app.data import Knowledge


RESET = "__reset__"


def add_or_reset(a: list | None, b: list | str) -> list:
    """List reducer that parallel nodes can append to, and `guard` can clear with RESET."""
    if b == RESET:
        return []
    return (a or []) + list(b)


def merge_or_reset(a: dict | None, b: dict | str) -> dict:
    if b == RESET:
        return {}
    return {**(a or {}), **b}


class TurnState(TypedDict, total=False):
    # ---- persistent across turns
    session_id: str
    history: list[dict]            # [{"role": "visitor"|"chandru", "text": str}]
    visitor: dict                  # name, company, role, email, tz
    asked_who: bool
    visitor_msgs: int
    dodges: dict                   # personal category -> times pressed
    used_lines: list[str]          # policy lines already used this session
    tool: dict | None              # active lead/meeting flow, see tools_flow
    identity_probes: int           # FR-D2: a second probe always gets the honest answer
    identity_disclosed: bool       # told them it's the twin: don't repeat it, keep texting as Chandru
    connected: bool                # a lead was saved / call booked: the gate must not restart the flow
    memory: dict                   # returning visitor: {"note": prompt note} built from their profile

    # ---- per turn (reset by `guard` / `await_confirm`)
    message: str
    turn_id: str
    action: dict | None            # structured client action, e.g. {"action": "pick_slot", "slot_id": "s2"}
    hints: dict
    gates: dict | None             # Jev gate answers for this turn
    tool_request: dict | None      # start_connect args from the LLM, consumed by tools_flow
    reading: str | None            # project page the visitor is on this turn (resolved server-side)
    handoff: bool                  # tools_flow -> converse: visitor went off-topic mid-flow
    route: str
    out: Annotated[list[str], add_or_reset]   # bursts emitted this turn (for history)
    flags: Annotated[list[str], add_or_reset]
    timings: Annotated[dict, merge_or_reset]
    trace: Annotated[list[dict], add_or_reset]   # every step's inputs/outputs for this turn (eval + debugging)
    llm: dict


@dataclass
class Deps:
    settings: Settings
    kb: Knowledge
    jev: Any
    llm: Any
    store: Any | None
    db: Any | None
    box: Any | None
    protected: set[str]
    entities: set[str]
    facts_text: str
    now: Callable
    rng: random.Random = field(default_factory=random.Random)
    actions: Any = None   # ComposioMCP (calendar + gmail); None or unconfigured -> fallbacks
