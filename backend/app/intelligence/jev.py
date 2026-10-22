"""Jev via OpenRouter's Decisions API (alpha): POST {base}/alpha/decisions.

Schema follows OpenRouter's decisions-api reference: `questions` keyed by our ids,
types `choice` (criteria: object), `noul` (criteria optional, true/false),
`score` (criteria: ordered array, lowest first). Every answer carries `type`;
anything unexpected is an error, never a silent default.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

import httpx

from app.config import Settings

log = logging.getLogger(__name__)


class JevError(RuntimeError):
    pass


@dataclass
class ChoiceAnswer:
    choice: str
    probabilities: dict[str, float]
    confidence: float


@dataclass
class ScoreAnswer:
    score: float
    probabilities: dict[str, float]
    confidence: float


@dataclass
class JevResult:
    answers: dict[str, Any]
    model: str = ""
    cost: float = 0.0
    latency_ms: float = 0.0
    raw: dict = field(default_factory=dict)

    def choice(self, key: str) -> ChoiceAnswer:
        a = self.answers[key]
        if not isinstance(a, ChoiceAnswer):
            raise JevError(f"{key} is not a choice answer")
        return a

    def noul(self, key: str) -> float:
        a = self.answers[key]
        if not isinstance(a, float):
            raise JevError(f"{key} is not a noul answer")
        return a

    def score(self, key: str) -> ScoreAnswer:
        a = self.answers[key]
        if not isinstance(a, ScoreAnswer):
            raise JevError(f"{key} is not a score answer")
        return a


def q_choice(instructions: str, criteria: dict[str, str]) -> dict:
    return {"type": "choice", "instructions": instructions, "criteria": criteria}


def q_noul(instructions: str, true: str | None = None, false: str | None = None) -> dict:
    q: dict[str, Any] = {"type": "noul", "instructions": instructions}
    if true and false:
        q["criteria"] = {"true": true, "false": false}
    return q


def q_score(instructions: str, levels: list[str]) -> dict:
    return {"type": "score", "instructions": instructions, "criteria": levels}


def parse_answers(questions: dict[str, dict], body: dict) -> dict[str, Any]:
    answers = body.get("answers")
    if not isinstance(answers, dict):
        raise JevError("response has no answers")
    out: dict[str, Any] = {}
    for key, q in questions.items():
        a = answers.get(key)
        if not isinstance(a, dict) or a.get("type") != q["type"]:
            raise JevError(f"answer {key!r} missing or wrong type: {a!r}")
        if q["type"] == "noul":
            out[key] = float(a["noul"])
        elif q["type"] == "choice":
            if a["choice"] not in q["criteria"]:
                raise JevError(f"{key}: choice {a['choice']!r} outside criteria")
            out[key] = ChoiceAnswer(
                choice=a["choice"],
                probabilities={k: float(v) for k, v in (a.get("probabilities") or {}).items()},
                confidence=float(a.get("confidence", 0.0)),
            )
        else:
            out[key] = ScoreAnswer(
                score=float(a["score"]),
                probabilities={k: float(v) for k, v in (a.get("probabilities") or {}).items()},
                confidence=float(a.get("confidence", 0.0)),
            )
    return out


class JevClient:
    def __init__(self, settings: Settings, client: httpx.AsyncClient):
        self.s = settings
        self.http = client

    async def decide(
        self,
        state: dict | str,
        questions: dict[str, dict],
        *,
        session_id: str | None = None,
        timeout: float | None = None,
    ) -> JevResult:
        if not self.s.openrouter_api_key:
            raise JevError("no OpenRouter key configured")
        payload: dict[str, Any] = {"model": self.s.jev_model, "state": state, "questions": questions}
        if session_id:
            payload["session_id"] = session_id
        t0 = time.perf_counter()
        try:
            resp = await self.http.post(
                f"{self.s.openrouter_base}/alpha/decisions",
                json=payload,
                headers={"Authorization": f"Bearer {self.s.openrouter_api_key}"},
                timeout=timeout or self.s.jev_timeout_s,
            )
        except httpx.HTTPError as e:
            raise JevError(f"transport: {e!r}") from e
        latency = (time.perf_counter() - t0) * 1000
        if resp.status_code != 200:
            raise JevError(f"http {resp.status_code}: {resp.text[:200]}")
        body = resp.json()
        return JevResult(
            answers=parse_answers(questions, body),
            model=body.get("model", ""),
            cost=float((body.get("usage") or {}).get("cost", 0.0)),
            latency_ms=latency,
            raw=body,
        )
