"""Deterministic burst shaping (FR A2, B3). The prompt already asks for this; this is the safety net."""

from __future__ import annotations

import random
import re

MD_PATTERNS = [
    (re.compile(r"^\s{0,3}#{1,6}\s*", re.M), ""),          # headings
    (re.compile(r"^\s*[-*•]\s+", re.M), ""),                 # bullets
    (re.compile(r"^\s*\d+[.)]\s+", re.M), ""),               # numbered lists
    (re.compile(r"\*\*(.+?)\*\*"), r"\1"),                   # bold
    (re.compile(r"(?<!\w)__(.+?)__(?!\w)"), r"\1"),
    (re.compile(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])"), r"\1"),  # italics
    (re.compile(r"`([^`]+)`"), r"\1"),
]
HIDDEN_TAG = re.compile(r"\s*⟦[^⟧]*⟧")
UNCLOSED_TAG = re.compile(r"\s*⟦[^⟧]*$")
TAG_THEN_TEXT = re.compile(r"(?<=⟧)\s+(?=[^\s⟦])")
EMOJI_RE = re.compile("[\U0001F300-\U0001FAFF☀-➿]")


def strip_markdown(text: str) -> str:
    for pat, rep in MD_PATTERNS:
        text = pat.sub(rep, text)
    return text


def strip_hidden_tags(text: str) -> str:
    return UNCLOSED_TAG.sub("", HIDDEN_TAG.sub("", text)).strip()


def split_at_tags(raw: str) -> list[str]:
    """A tag ends a thought: 'nice to meet u ⟦v:name=X⟧ what brings u here?' is two bubbles."""
    return [p for p in TAG_THEN_TEXT.split(raw) if p.strip()]


def remove_banned(text: str, banned: list[str]) -> str:
    out = text
    for phrase in banned:
        out = re.sub(rf"(?i)\b{re.escape(phrase)}\b[!,.]?\s*", "", out)
    return out.strip()


def lowercase_start(text: str, protected: set[str]) -> str:
    """Lowercase the first letter unless the first word is a name/acronym/tech term."""
    if not text:
        return text
    first = text.split()[0]
    bare = first.strip(",.!?:;").lower()
    if bare in protected or (len(first) > 1 and first[:2].isupper()) or first == "I":
        return text
    return text[0].lower() + text[1:]


def drop_trailing_period(text: str) -> str:
    if text.endswith(".") and not text.endswith("..") and len(text.split()) <= 25:
        return text[:-1]
    return text


def split_long(text: str, max_words: int) -> list[str]:
    words = text.split()
    if len(words) <= max_words:
        return [text]
    # split at a sentence or clause boundary near the middle
    parts = re.split(r"(?<=[.!?])\s+|(?<=,)\s+(?=and |but |so |then )", text)
    out, cur = [], ""
    for p in parts:
        if cur and len((cur + " " + p).split()) > max_words:
            out.append(cur.strip())
            cur = p
        else:
            cur = f"{cur} {p}".strip()
    if cur:
        out.append(cur)
    final: list[str] = []
    for chunk in out:  # still too long: split into even pieces, so no lonely one-word bubble
        w = chunk.split()
        if len(w) <= max_words:
            final.append(chunk)
            continue
        n = -(-len(w) // max_words)
        size = -(-len(w) // n)
        final += [" ".join(w[i:i + size]) for i in range(0, len(w), size)]
    return final


def shape(
    bursts: list[str],
    *,
    style: dict,
    protected: set[str],
    max_bursts: int,
) -> list[str]:
    max_words = int(style["burst"]["max_words"])
    banned = list(style.get("banned_phrases", []))
    out: list[str] = []
    for raw in bursts:
        text = strip_markdown(raw)
        text = remove_banned(text, banned)
        text = " ".join(text.split())
        if not text:
            continue
        for piece in split_long(text, max_words):
            piece = lowercase_start(piece, protected)
            if not style.get("punctuation", {}).get("trailing_period_short", False):
                piece = drop_trailing_period(piece)
            if piece:
                out.append(piece)
    return out[:max_bursts]


def limit_emoji(bursts: list[str], rate: float, rng: random.Random) -> list[str]:
    """At most one emoji per reply, and only `rate` of replies keep it."""
    seen = False
    keep = rng.random() < rate
    out = []
    for b in bursts:
        def repl(m):
            nonlocal seen
            if seen or not keep:
                return ""
            seen = True
            return m.group(0)
        out.append(" ".join(EMOJI_RE.sub(repl, b).split()) or b)
    return out
