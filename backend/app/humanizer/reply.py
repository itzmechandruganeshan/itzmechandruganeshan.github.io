"""Per-reply humanization in the WS consumer: emoji budget, filler budget, one typo, pacing."""

from __future__ import annotations

import random

from app.humanizer.bursts import EMOJI_RE
from app.humanizer.fillers import FillerBudget
from app.humanizer.pacing import burst_delay
from app.humanizer.typos import maybe_typo


class ReplyHumanizer:
    def __init__(self, style: dict, protected: set[str], rng: random.Random, multiplier: float,
                 fillers: FillerBudget | None = None):
        self.style = style
        self.protected = protected
        self.rng = rng
        self.mult = multiplier
        self.typo_pending = rng.random() < float(style["typos"]["reply_rate"])
        self.emoji_keep = rng.random() < float(style["emoji"]["rate_per_reply"])
        self.emoji_used = False
        self.first = True
        self.fillers = fillers
        self.trace: list[dict] = []

    def _emoji(self, text: str, src: str) -> str:
        if src != "llm":
            return text  # curated policy lines keep their emoji

        def repl(m):
            if self.emoji_used or not self.emoji_keep:
                return ""
            self.emoji_used = True
            return m.group(0)

        return " ".join(EMOJI_RE.sub(repl, text).split()) or text

    def process(self, text: str, src: str = "llm") -> list[tuple[str, float]]:
        original = text
        text = self._emoji(text, src)
        removed: list[str] = []
        if self.fillers is not None:
            text, removed = self.fillers.apply(text)
        correction, typo = None, False
        if self.typo_pending:
            forced = {**self.style, "typos": {**self.style["typos"], "reply_rate": 1.0}}
            new, correction = maybe_typo([text], style=forced, protected=self.protected, rng=self.rng)
            if new[0] != text:
                self.typo_pending, typo, text = False, True, new[0]
        out = [(text, burst_delay(text, first=self.first, style=self.style, multiplier=self.mult, rng=self.rng))]
        self.first = False
        if correction:
            out.append((correction, burst_delay(correction, first=False, style=self.style,
                                                multiplier=self.mult, rng=self.rng) * 0.6))
        self.trace.append({"step": "humanize", "src": src, "in": original, "out": [t for t, _ in out],
                           "fillers_removed": removed, "typo": typo, "delays_s": [round(d, 2) for _, d in out]})
        return out
