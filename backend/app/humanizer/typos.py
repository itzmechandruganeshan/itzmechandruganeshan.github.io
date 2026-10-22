"""Rare, realistic typos (FR B2). Never touches names, numbers, URLs, emails, code or tech terms."""

from __future__ import annotations

import random
import re

KEYBOARD_NEIGHBOURS = {
    "a": "qwsz", "b": "vghn", "c": "xdfv", "d": "serfcx", "e": "wsdr", "f": "drtgvc",
    "g": "ftyhbv", "h": "gyujnb", "i": "ujko", "j": "huikmn", "k": "jiolm", "l": "kop",
    "m": "njk", "n": "bhjm", "o": "iklp", "p": "ol", "q": "wa", "r": "edft", "s": "awedxz",
    "t": "rfgy", "u": "yhji", "v": "cfgb", "w": "qase", "x": "zsdc", "y": "tghu", "z": "asx",
}
WORD_RE = re.compile(r"[A-Za-z]+")
UNSAFE_TOKEN = re.compile(r"(https?://|www\.|@|\d|[_/\\`<>{}\[\]=])")


def _protected_word(word: str, protected: set[str]) -> bool:
    w = word.lower()
    return w in protected or word[:1].isupper() or word.isupper()


def candidates(text: str, protected: set[str], min_len: int) -> list[tuple[int, int]]:
    spans = []
    for token in re.finditer(r"\S+", text):
        if UNSAFE_TOKEN.search(token.group(0)):
            continue
        for m in WORD_RE.finditer(token.group(0)):
            word = m.group(0)
            if len(word) >= min_len and not _protected_word(word, protected):
                spans.append((token.start() + m.start(), token.start() + m.end()))
    return spans


def mutate(word: str, op: str, rng: random.Random) -> str:
    i = rng.randrange(1, len(word) - 1)  # keep first and last letters, like real typos
    if op == "adjacent_swap":
        c = word[i].lower()
        n = KEYBOARD_NEIGHBOURS.get(c)
        if n:
            return word[:i] + rng.choice(n) + word[i + 1:]
    if op == "transpose" and i < len(word) - 1:
        return word[:i] + word[i + 1] + word[i] + word[i + 2:]
    if op == "drop_letter":
        return word[:i] + word[i + 1:]
    if op == "double_letter":
        return word[:i] + word[i] + word[i:]
    return word[:i] + word[i + 1:]


def maybe_typo(
    bursts: list[str],
    *,
    style: dict,
    protected: set[str],
    rng: random.Random,
) -> tuple[list[str], str | None]:
    """Returns (bursts, correction_burst_or_None). At most one typo per reply."""
    cfg = style["typos"]
    if not bursts or rng.random() >= float(cfg["reply_rate"]):
        return bursts, None
    options = [
        (bi, span) for bi, b in enumerate(bursts)
        for span in candidates(b, protected, int(cfg.get("min_word_len", 4)))
    ]
    if not options:
        return bursts, None
    bi, (s, e) = rng.choice(options)
    word = bursts[bi][s:e]
    typo = mutate(word, rng.choice(cfg["ops"]), rng)
    if typo == word:
        return bursts, None
    out = list(bursts)
    out[bi] = out[bi][:s] + typo + out[bi][e:]
    correction = f"*{word}" if rng.random() < float(cfg["correction_rate"]) else None
    return out, correction
