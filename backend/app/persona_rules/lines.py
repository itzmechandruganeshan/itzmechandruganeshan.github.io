"""Pick policy lines without repeating within a session."""

from __future__ import annotations

import random


def pick(options: list[list[str]], used: set[str], key: str, rng: random.Random) -> list[str]:
    """`options` is a list of replies (each a list of bursts). Marks the choice in `used`."""
    fresh = [(i, o) for i, o in enumerate(options) if f"{key}#{i}" not in used]
    i, choice = rng.choice(fresh or list(enumerate(options)))
    used.add(f"{key}#{i}")
    return list(choice)


def fill(bursts: list[str], **values: str) -> list[str]:
    out = []
    for b in bursts:
        for k, v in values.items():
            b = b.replace("{" + k + "}", v)
        out.append(b)
    return out
