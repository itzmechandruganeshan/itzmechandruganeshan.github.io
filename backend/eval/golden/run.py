"""Runs the golden set through the REAL graph (Jev + LLM + Qdrant) and scores every step of every turn.

    uv run python eval/golden/run.py                    # all cases
    uv run python eval/golden/run.py --only proj- --only follow-   # id prefixes
    uv run python eval/golden/run.py --category personal

Writes eval/reports/<timestamp>/{results.jsonl, report.md}. Stop the local server first if it uses embedded
Qdrant (only one process can open the local store).
"""

from __future__ import annotations

import argparse
import asyncio
import dataclasses
import json
import random
import re
import sys
import time
import uuid
import zlib
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from langgraph.checkpoint.memory import InMemorySaver  # noqa: E402

from app.chat import TurnRunner  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.graph.build import build_graph  # noqa: E402
from app.humanizer.fillers import FILLERS  # noqa: E402
from app.runtime import build_runtime  # noqa: E402

HERE = Path(__file__).parent
DEFAULT_NOW = "2026-10-21T15:00:00+05:30"
HUMAN_CLAIM = re.compile(r"\bi'?m (a )?(real )?(human|person)\b|\bnot a bot\b|\bi'?m not (an? )?(ai|bot)\b", re.I)
TIME_EXCUSE = re.compile(r"(ask|talk to|text) me (when i'?m awake|tomorrow|later|in the morning)|"
                         r"\bi'?m (asleep|sleeping)\b", re.I)  # refusing because of the time, not mentioning it
MARKDOWN = re.compile(r"\*\*|^\s*[-*•]\s|^\s*#|^\s*\d+[.)]\s", re.M)


def _as_list(v):
    return v if isinstance(v, list) else [v]


def style_checks(replies: list[str], banned: list[str]) -> list[tuple[str, bool, str]]:
    joined = " ".join(replies)
    low = joined.lower()
    out = [("style.non_empty", bool(replies), "")]
    counts = {w: len(re.findall(rf"\b{w}\b", low)) for w in FILLERS}
    rep = {w: n for w, n in counts.items() if n > 1}
    out.append(("style.filler_once", not rep, str(rep) if rep else ""))
    hits = [b for b in banned if re.search(rf"(?<![\w]){re.escape(b)}(?![\w])", low)]  # "was an AI" != "as an ai"
    out.append(("style.no_ai_isms", not hits, ",".join(hits)))
    out.append(("style.no_markdown", not MARKDOWN.search(joined), ""))
    out.append(("style.no_tag_leak", "⟦" not in joined and "⟧" not in joined
                and not re.search(r"\bvisitor\s*tag\b|\b(name|company|role)\s*=|\b(start_connect|share_resume|"
                                  r"get_news|ask_chandru|tool ?call)\b", joined, re.I), ""))
    out.append(("style.no_human_claim", not HUMAN_CLAIM.search(joined), ""))
    out.append(("style.no_time_excuse", not TIME_EXCUSE.search(joined), ""))
    long = [r for r in replies if len(r.split()) > 30]
    out.append(("style.bubble_size", not long, f"{len(long)} bubbles > 30 words" if long else ""))
    out.append(("style.burst_count", len(replies) <= 7, f"{len(replies)} bubbles"))
    return out


_W = re.compile(r"[a-z0-9]{4,}")


def _best_project(text: str, card_text: dict[str, str]) -> str | None:
    words = set(_W.findall(text.lower()))
    scores = {pid: len(words & set(_W.findall(t))) for pid, t in card_text.items()}
    best = max(scores, key=scores.get) if scores else None
    return best if best and scores[best] >= 3 else None


def _cited(trace) -> set[str]:
    return {c for t in trace if t.get("step") == "llm_line" and t.get("ok") for c in t.get("cites") or []}


def expect_checks(exp: dict, rec: dict, card_project: dict[str, str],
                  card_text: dict[str, str]) -> list[tuple[str, bool, str]]:
    out = []
    trace = rec.get("trace") or []
    joined = " ".join(rec.get("replies") or [])
    cited = _cited(trace)
    if "route" in exp:
        out.append(("route", rec.get("route") in _as_list(exp["route"]), f"got {rec.get('route')}"))
    if exp.get("project"):
        # ADR-008 has no resolver. "Right project" = the reply cites it, or its content matches that project's
        # cards best (follow-ups like "what was the hardest part there?" rarely repeat the name).
        projects = {card_project.get(c) for c in cited}
        best = _best_project(joined, card_text)
        ok = exp["project"] in projects or best == exp["project"]
        out.append(("project", ok, f"cited={sorted(p for p in projects if p)} content≈{best}"))
    if "evidence_any" in exp:
        ctx = next((t for t in trace if t.get("step") == "context"), {})
        ev = set(ctx.get("evidence") or [])
        out.append(("retrieval", bool(ev & set(exp["evidence_any"])) or not ctx, f"{len(ev)} cards in context"))
    if "cites_any" in exp:
        out.append(("grounding.cites", bool(cited & set(exp["cites_any"])), f"cited={sorted(cited)}"))
    for rx in exp.get("match", []):
        out.append((f"content.match:{rx[:30]}", bool(re.search(rx, joined, re.I)), joined[:160]))
    for rx in exp.get("no_match", []):
        m = re.search(rx, joined, re.I)
        out.append((f"content.no_match:{rx[:30]}", not m, m.group(0) if m else ""))
    flags = rec.get("flags") or []
    if "flags_any" in exp:
        out.append(("flags.any", any(f.startswith(p) for f in flags for p in exp["flags_any"]), str(flags)))
    if "flags_none" in exp:
        bad = [f for f in flags for p in exp["flags_none"] if f.startswith(p)]
        out.append(("flags.none", not bad, str(bad)))
    return out


async def run_case(case: dict, graph, base_deps, sem: asyncio.Semaphore) -> dict:
    async with sem:
        now = datetime.fromisoformat(case.get("now") or DEFAULT_NOW)
        deps = dataclasses.replace(base_deps, now=lambda: now, rng=random.Random(zlib.crc32(case["id"].encode())))

        async def no_sleep(_):
            return None

        runner = TurnRunner(graph, deps, sleep=no_sleep)
        sid = str(uuid.uuid4())
        await deps.db.execute("INSERT INTO conversations(id, visitor_id, started_at) VALUES (?,?,?)",
                              (sid, f"golden-{sid}", time.time()))  # so "ask the real me" can attach a visitor
        turns = []
        banned = deps.kb.style.get("banned_phrases", [])

        async def send(_):
            return None

        for t in case["turns"]:
            t0 = time.perf_counter()
            try:
                rec = await runner.run(sid, t["say"], send, visitor_tz=case.get("tz"))
            except Exception as e:  # noqa: BLE001
                rec = {"error": repr(e), "replies": [], "trace": [], "flags": ["runner_error"]}
            card_project = {c.id: c.project_id for c in deps.kb.cards}
            card_text: dict[str, str] = {}
            for c in deps.kb.cards:
                if c.project_id not in ("general", "opinions"):
                    card_text[c.project_id] = card_text.get(c.project_id, "") + " " + c.text.lower()
            checks = style_checks(rec.get("replies") or [], banned) + expect_checks(t["expect"], rec, card_project,
                                                                                     card_text)
            turns.append({"say": t["say"], "replies": rec.get("replies"), "route": rec.get("route"),
                          "gates": rec.get("gates"), "flags": rec.get("flags"), "trace": rec.get("trace"),
                          "timings": rec.get("timings"), "ms": round((time.perf_counter() - t0) * 1000),
                          "checks": [{"name": n, "ok": ok, "detail": det} for n, ok, det in checks]})
        ok = all(c["ok"] for tr in turns for c in tr["checks"])
        return {"id": case["id"], "category": case["category"], "sub": case["sub"], "ok": ok, "turns": turns}


def report(results: list[dict], out_dir: Path) -> str:
    lines = [f"# Golden eval: {sum(r['ok'] for r in results)}/{len(results)} cases pass",
             f"_{datetime.now():%Y-%m-%d %H:%M}_", ""]
    cats: dict[str, list] = {}
    for r in results:
        cats.setdefault(r["category"], []).append(r)
    lines += ["| Category | Pass | Cases |", "|---|---|---|"]
    for k, rs in sorted(cats.items()):
        lines.append(f"| {k} | {sum(r['ok'] for r in rs)}/{len(rs)} | {', '.join(r['id'] for r in rs if not r['ok']) or '—'} |")
    checks: dict[str, list[int]] = {}
    for r in results:
        for t in r["turns"]:
            for c in t["checks"]:
                key = c["name"].split(":")[0]
                checks.setdefault(key, [0, 0])
                checks[key][0] += c["ok"]
                checks[key][1] += 1
    lines += ["", "## By check", "| Check | Pass rate |", "|---|---|"]
    for k, (p, n) in sorted(checks.items(), key=lambda kv: kv[1][0] / kv[1][1]):
        lines.append(f"| {k} | {p}/{n} ({p / n:.0%}) |")
    firsts = sorted((t.get("timings") or {}).get("first_burst_sent_ms") or 0 for r in results for t in r["turns"])
    jev = sorted((t.get("timings") or {}).get("gates_ms") or 0 for r in results for t in r["turns"])
    if firsts:
        p = lambda xs, q: xs[min(len(xs) - 1, int(len(xs) * q))]  # noqa: E731
        lines += ["", f"**System latency (no typing delay):** first bubble p50 {p(firsts, .5):.0f} ms, "
                      f"p95 {p(firsts, .95):.0f} ms · Jev gates p50 {p(jev, .5):.0f} ms, p95 {p(jev, .95):.0f} ms"]
    lines += ["", "## Failures (full step trace)"]
    for r in results:
        if r["ok"]:
            continue
        lines.append(f"\n### {r['id']} ({r['category']}/{r['sub']})")
        for t in r["turns"]:
            bad = [c for c in t["checks"] if not c["ok"]]
            g = t.get("gates") or {}
            lines.append(f"- **visitor:** {t['say']}")
            lines.append(f"  - **reply:** {' · '.join(t['replies'] or ['(none)'])}")
            lines.append(f"  - route `{t['route']}` · gate `{g.get('policy')}` ({g.get('reason')}) · flags `{t['flags']}`")
            for c in bad:
                lines.append(f"  - ❌ `{c['name']}` {c['detail']}")
            if bad:
                lines.append("  <details><summary>trace</summary>\n\n```json\n"
                             + json.dumps(t["trace"], ensure_ascii=False, indent=1)[:6000] + "\n```\n</details>")
    md = "\n".join(lines)
    (out_dir / "report.md").write_text(md, encoding="utf-8")
    return md


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", action="append", default=[])
    ap.add_argument("--category", action="append", default=[])
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--typos", action="store_true", help="keep random typos on (off by default for stable content checks)")
    ap.add_argument("--repeat", type=int, default=1, help="run each case N times to measure flakiness")
    args = ap.parse_args()
    cases = [json.loads(l) for l in (HERE / "golden.jsonl").read_text().splitlines() if l.strip()]
    if args.only:
        cases = [c for c in cases if any(c["id"].startswith(p) for p in args.only)]
    if args.category:
        cases = [c for c in cases if c["category"] in args.category]
    out_dir = HERE.parent / "reports" / datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir.mkdir(parents=True, exist_ok=True)
    # separate DB: eval leads/outbox/transcripts never mix with real visitors
    settings = get_settings().model_copy(update={"db_path": out_dir / "eval.db"})
    rt = await build_runtime(settings)
    if not args.typos:  # deliberate typos would make content checks flaky; style checks still run
        kb = rt.deps.kb
        style = {**kb.style, "typos": {**kb.style["typos"], "reply_rate": 0.0}}
        rt.deps = dataclasses.replace(rt.deps, kb=dataclasses.replace(kb, style=style))
    print(f"{len(cases)} cases · store={rt.store_backend} · jev={rt.deps.settings.jev_model} · llm={rt.deps.settings.llm_models[0]}")
    graph = build_graph(InMemorySaver())
    sem = asyncio.Semaphore(args.concurrency)
    t0 = time.perf_counter()
    results = []
    jobs = [run_case(c, graph, rt.deps, sem) for c in cases for _ in range(args.repeat)]
    for coro in asyncio.as_completed(jobs):
        r = await coro
        results.append(r)
        print(f"{'ok ' if r['ok'] else 'XX '} {r['id']}")
    results.sort(key=lambda r: r["id"])
    if args.repeat > 1:
        rates: dict[str, list[bool]] = {}
        for r in results:
            rates.setdefault(r["id"], []).append(r["ok"])
        flaky = {k: f"{sum(v)}/{len(v)}" for k, v in rates.items() if 0 < sum(v) < len(v)}
        broken = [k for k, v in rates.items() if not any(v)]
        print(f"\nstable pass {sum(all(v) for v in rates.values())}/{len(rates)} · flaky {flaky} · always failing {broken}")
    with (out_dir / "results.jsonl").open("w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False, default=str) + "\n")
    md = report(results, out_dir)
    print("\n" + md.split("## Failures")[0])
    print(f"done in {time.perf_counter() - t0:.0f}s → {out_dir}/report.md")
    await rt.close()


if __name__ == "__main__":
    asyncio.run(main())
