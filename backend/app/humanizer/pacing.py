"""Typing delays (FR B1). System latency hides inside these, it never adds to them."""

from __future__ import annotations

import random


def burst_delay(text: str, *, first: bool, style: dict, multiplier: float, rng: random.Random) -> float:
    t = style["typing"]
    cps = rng.uniform(*t["cps"])
    delay = len(text) / cps
    if first:
        delay += rng.uniform(*t["think_pause"])
    lo, hi = t["clamp"]
    return max(lo, min(hi, delay * multiplier))


def remaining_wait(target_s: float, already_elapsed_s: float) -> float:
    """First burst: the time spent generating counts toward the human delay."""
    return max(0.0, target_s - already_elapsed_s)
