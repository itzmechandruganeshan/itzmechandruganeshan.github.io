"""Filler words ("haha", "lol", "tbh"...) are what make bot texting sound like a bot when repeated.

Rule: each filler at most once per reply, and not if it was used in the last `cooldown` replies.
"""

from __future__ import annotations

import re
from collections import deque

FILLERS = ("haha", "hahaha", "lol", "tbh", "ngl", "hehe", "lmao")
_FILLER_RE = {w: re.compile(rf"(?i)(^|[\s,])({w})\b[,!.]*") for w in FILLERS}


def found(text: str) -> set[str]:
    return {w for w, rx in _FILLER_RE.items() if rx.search(text)}


def drop(text: str, word: str) -> str:
    def keep(m):
        if m.start() == 0:
            return ""
        return m.group(1) + ("," if "," in m.group(0)[len(m.group(1)) + len(m.group(2)):] else "")

    out = _FILLER_RE[word].sub(keep, text)
    out = re.sub(r"\s+,", ",", " ".join(out.split())).strip(" ,")
    return out


class FillerBudget:
    """One per reply (per session), with a cooldown across the previous replies."""

    def __init__(self, recent: deque[set[str]]):
        self.recent = recent
        self.blocked = set().union(*recent) if recent else set()
        self.used: set[str] = set()

    def apply(self, text: str) -> tuple[str, list[str]]:
        removed = []
        for w in found(text):
            if w in self.used or w in self.blocked:
                candidate = drop(text, w)
                if candidate:  # never empty a bubble that was only "haha"
                    text = candidate
                    removed.append(w)
            else:
                self.used.add(w)
        return text, removed

    def close(self) -> None:
        self.recent.append(self.used)
