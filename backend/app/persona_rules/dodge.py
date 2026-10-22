"""FR-G: evasive, slippery, on-the-fence answers to personal questions, escalating when pressed."""

from __future__ import annotations

import random

from app.persona_rules.lines import pick

LEVELS = ["playful", "vague_redirect", "boundary"]


def dodge(policy: dict, category: str, pressed: dict[str, int], used: set[str],
          rng: random.Random) -> tuple[list[str], int]:
    """Returns (bursts, level_index). Mutates `pressed` and `used`."""
    table = policy["personal"].get(category) or policy["personal"]["other_personal"]
    level = min(pressed.get(category, 0), len(LEVELS) - 1)
    pressed[category] = pressed.get(category, 0) + 1
    name = LEVELS[level]
    return pick(table[name], used, f"personal.{category}.{name}", rng), level
