"""Deterministic grounding checks on each burst (architecture §4.3)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.data import Card, Knowledge

CITE_RE = re.compile(r"⟦c:([^⟧]+)⟧")
VISITOR_RE = re.compile(r"⟦v:([^⟧]*)⟧")
LOOSE_NUMBER = re.compile(r"\d+(?:[.,]\d+)*")
NEG_HINTS = re.compile(r"\b(didn'?t|did not|no|never|not)\b", re.I)


def citations(raw: str) -> list[str]:
    ids = []
    for group in CITE_RE.findall(raw):
        ids.extend(i.strip() for i in group.split(",") if i.strip())
    return ids


# The LLM sometimes writes the hidden tag as plain text ("visitor tag: name=Surya;company=Zoho").
PLAIN_TAG_RE = re.compile(r"(?:visitor\s*tag\s*:?\s*)?((?:\b(?:name|company|role)\s*=\s*[^;⟧\n]+;?\s*){1,3})", re.I)
LEAKED_TAG_RE = re.compile(r"\bvisitor\s*tag\b|\b(?:name|company|role)\s*=\s*\S", re.I)


def visitor_tag(raw: str) -> dict[str, str]:
    out = {}
    groups = VISITOR_RE.findall(raw)
    if not groups and LEAKED_TAG_RE.search(raw):
        groups = [m.group(1) for m in PLAIN_TAG_RE.finditer(raw)]
    for group in groups:
        for part in group.split(";"):
            if "=" in part:
                k, v = part.split("=", 1)
                if k.strip() in ("name", "company", "role") and v.strip():
                    out[k.strip()] = v.strip()[:80]
    return out


def _numbers(text: str) -> set[str]:
    return {n.replace(",", "") for n in LOOSE_NUMBER.findall(text)}


NUMBER = re.compile(r"\d+(?:,\d{3})*(?:\.\d+)?")
UNIT = re.compile(r"\s*(k|mn|m|million|lakhs?|crores?|bn|billion|thousand)\b", re.I)
SCALE = {"k": 1e3, "thousand": 1e3, "m": 1e6, "mn": 1e6, "million": 1e6, "lakh": 1e5, "lakhs": 1e5,
         "crore": 1e7, "crores": 1e7, "bn": 1e9, "billion": 1e9}


def quantities(text: str) -> list[tuple[str, float]]:
    """Every number in the text (incl. '3x', '7B', '22k', '1.37 million'), scaled by its unit if any."""
    out = []
    for m in NUMBER.finditer(text):
        unit = UNIT.match(text, m.end())
        u = unit.group(1).lower() if unit else ""
        out.append((m.group(0) + u, float(m.group(0).replace(",", "")) * SCALE.get(u, 1.0)))
    return out


def _supported(value: float, support: list[float], tol: float = 0.03) -> bool:
    """Exact for small integers (years, counts); within 3% for big numbers people round (22k, 1.37M)."""
    for s in support:
        if value == s or (value >= 100 and s and abs(value - s) / s <= tol):
            return True
    return False


@dataclass
class CheckResult:
    ok: bool
    problems: list[str] = field(default_factory=list)


def known_entities(kb: Knowledge) -> set[str]:
    """Company and tech names that, if mentioned, must be backed by evidence."""
    ents = {p.company.lower() for p in kb.projects} | {p.client.lower() for p in kb.projects if p.client}
    for p in kb.projects:
        ents |= {t.lower() for t in p.tech}
    for c in kb.cards:
        ents |= set(c.tech)
    ents -= {"python", "open source", "personal"}
    return {e for e in ents if len(e) >= 3}


def check_burst(raw: str, clean: str, evidence: list[Card], facts_text: str, entities: set[str]) -> CheckResult:
    probs: list[str] = []
    by_id = {c.id: c for c in evidence}
    cited = citations(raw)
    for cid in cited:
        if cid not in by_id and not cid.lower().startswith("facts"):  # ⟦c:facts⟧ = the fact sheet
            probs.append(f"cites unknown card {cid}")
    cited_cards = [by_id[c] for c in cited if c in by_id]
    # Numbers must come from the cards the burst cites (or any evidence if it cites none);
    # entities may come from any evidence card or the fact sheet.
    number_text = " ".join(c.text + " " + " ".join(c.metrics) for c in (cited_cards or evidence)) + " " + facts_text
    support_lower = (" ".join(c.text + " " + " ".join(c.tech) for c in evidence) + " " + facts_text).lower()
    support = [v for _, v in quantities(number_text)]
    for label, v in quantities(clean):
        if not _supported(v, support):
            probs.append(f"number {label} not in evidence")
    low = clean.lower()
    for e in entities:
        if re.search(rf"(?<![\w]){re.escape(e)}(?![\w])", low) and e not in support_lower:
            probs.append(f"entity '{e}' not in evidence")
    for c in cited_cards:
        if c.negative and not NEG_HINTS.search(clean):
            probs.append(f"contradicts negative card {c.id}")
    return CheckResult(ok=not probs, problems=probs)
