"""RCA 2026-10-22 (first prod chat): booking crashed on the browser's legacy zone "Asia/Calcutta", the
name typo "bye kaaviya", and the LLM narrating "the connect flow" / asking permission to start it."""

import random
from datetime import datetime, timezone

from app.graph.converse import META_RE, PERMISSION_RE
from app.humanizer.typos import maybe_typo
from app.tools.calendar import Slot
from app.ws import valid_tz


def test_legacy_browser_zone_resolves_and_labels_slots():
    assert valid_tz("Asia/Calcutta") == "Asia/Calcutta"  # needs the tzdata package (slim images lack aliases)
    slot = Slot("s1", datetime(2026, 10, 23, 5, 30, tzinfo=timezone.utc), datetime(2026, 10, 23, 6, tzinfo=timezone.utc))
    assert slot.label("Asia/Calcutta") == slot.label("Asia/Kolkata") == "Fri 23 Oct, 11:00 AM"


def test_unknown_zone_falls_back_instead_of_crashing():
    for bad in ("Mars/Olympus", "../etc/passwd", "", None, 5, "x" * 80):
        assert valid_tz(bad) is None


def test_visitor_name_is_never_typoed(kb):
    style = {**kb.style, "typos": {**kb.style["typos"], "reply_rate": 1.0, "correction_rate": 0.0}}
    for seed in range(200):
        out, _ = maybe_typo(["bye kaviya, take care"], style=style, protected={"kaviya"}, rng=random.Random(seed))
        assert "kaviya" in out[0]


def test_flow_narration_and_permission_asks_are_caught():
    assert META_RE.search("my bad, the connect flow only starts from here")
    assert META_RE.search("that flow will take your details")
    assert not META_RE.search("the flow routes each question across FAQ retrieval and SQL agents")
    assert PERMISSION_RE.search("Want me to kick that off?")
