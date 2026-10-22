"""Loads and validates the knowledge + persona files in data/. Cached per process."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import yaml

from app.config import get_settings

ASPECTS = {
    "overview", "problem", "architecture", "approach", "stack", "impact_metric",
    "challenge", "learning", "role", "opinion", "story", "career", "education",
}
NON_PROJECT_IDS = {"general", "opinions"}
STRICT_NUMBER = re.compile(r"(?<![\w.\-/])\d[\d,]*(?:\.\d+)?%?(?![\w\-])")


@dataclass(frozen=True)
class Project:
    id: str
    name: str
    company: str
    aliases: tuple[str, ...]
    tech: tuple[str, ...]
    visibility: str = "public"
    client: str | None = None


@dataclass(frozen=True)
class Card:
    id: str
    project_id: str
    aspect: str
    text: str
    tech: tuple[str, ...] = ()
    metrics: tuple[str, ...] = ()
    negative: bool = False
    visibility: str = "public"
    reviewed: bool = False

    def payload(self) -> dict:
        return {
            "card_id": self.id, "project_id": self.project_id, "aspect": self.aspect,
            "text": self.text, "tech": list(self.tech), "metrics": list(self.metrics),
            "negative": self.negative, "visibility": self.visibility,
        }


@dataclass
class Knowledge:
    facts: dict
    projects: list[Project]
    cards: list[Card]
    policy: dict
    style: dict
    routine: dict
    holidays: list[dict]
    feeds: dict
    voice: list[dict]
    banned_politics_terms: list[str] = field(default_factory=list)

    @property
    def projects_by_id(self) -> dict[str, Project]:
        return {p.id: p for p in self.projects}


class DataError(ValueError):
    pass


def _load_yaml(path: Path):
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_cards(cards_dir: Path) -> list[Card]:
    cards: list[Card] = []
    for path in sorted(cards_dir.glob("*.yaml")):
        for raw in _load_yaml(path) or []:
            cards.append(Card(
                id=raw["id"], project_id=raw["project_id"], aspect=raw["aspect"],
                text=" ".join(str(raw["text"]).split()),
                tech=tuple(str(t).lower() for t in raw.get("tech") or []),
                metrics=tuple(str(m) for m in raw.get("metrics") or []),
                negative=bool(raw.get("negative", False)),
                visibility=raw.get("visibility", "public"),
                reviewed=bool(raw.get("reviewed", False)),
            ))
    return cards


def validate(projects: list[Project], cards: list[Card]) -> list[str]:
    """Returns a list of problems. Ingest refuses to run if any exist."""
    problems: list[str] = []
    seen_alias: dict[str, str] = {}
    for p in projects:
        for a in p.aliases:
            if a != a.lower():
                problems.append(f"{p.id}: alias '{a}' must be lowercase")
            if a in seen_alias and seen_alias[a] != p.id:
                problems.append(f"alias '{a}' used by both {seen_alias[a]} and {p.id}")
            seen_alias[a] = p.id
    ids = {p.id for p in projects} | NON_PROJECT_IDS
    seen_card: set[str] = set()
    for c in cards:
        if c.id in seen_card:
            problems.append(f"duplicate card id {c.id}")
        seen_card.add(c.id)
        if c.project_id not in ids:
            problems.append(f"{c.id}: unknown project_id {c.project_id}")
        if c.aspect not in ASPECTS:
            problems.append(f"{c.id}: unknown aspect {c.aspect}")
        listed = {m.rstrip("%") for m in c.metrics}
        for num in STRICT_NUMBER.findall(c.text):
            if num.rstrip("%") not in listed:
                problems.append(f"{c.id}: number '{num}' in text but not in metrics")
    return problems


@lru_cache
def get_knowledge(data_dir: str | None = None) -> Knowledge:
    root = Path(data_dir) if data_dir else get_settings().data_dir
    p_raw = _load_yaml(root / "projects.yaml") or []
    projects = [
        Project(
            id=r["id"], name=r["name"], company=r["company"],
            aliases=tuple(r.get("aliases") or []), tech=tuple(r.get("tech") or []),
            visibility=r.get("visibility", "public"), client=r.get("client"),
        )
        for r in p_raw
    ]
    voice: list[dict] = []
    for path in sorted((root / "voice").glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                voice.append(json.loads(line))
    banned_path = root / "politics_banned_terms.txt"
    banned = []
    if banned_path.exists():
        banned = [
            ln.strip().lower() for ln in banned_path.read_text(encoding="utf-8").splitlines()
            if ln.strip() and not ln.startswith("#")
        ]
    return Knowledge(
        facts=_load_yaml(root / "facts.yaml"),
        projects=projects,
        cards=load_cards(root / "cards"),
        policy=_load_yaml(root / "policy.yaml"),
        style=_load_yaml(root / "persona" / "style.yaml"),
        routine=_load_yaml(root / "persona" / "routine.yaml"),
        holidays=_load_yaml(root / "persona" / "holidays.yaml") or [],
        feeds=_load_yaml(root / "news" / "feeds.yaml"),
        voice=voice,
        banned_politics_terms=banned,
    )
