"""Admin CLI (E3).

    uv run python scripts/admin.py leads | bookings | flagged [--days 7] | transcript <session_id> | stats
    uv run python scripts/admin.py trace [session_id]   # every step of every turn (latest session if omitted)
    uv run python scripts/admin.py questions             # "ask the real me" questions and their status
    uv run python scripts/admin.py learned               # answered questions as draft cards (review, then add)
"""

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings  # noqa: E402
from app.storage.crypto import Box  # noqa: E402
from app.storage.db import DB  # noqa: E402


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["leads", "bookings", "flagged", "transcript", "stats", "trace", "questions", "learned"])
    ap.add_argument("arg", nargs="?")
    ap.add_argument("--days", type=int, default=7)
    a = ap.parse_args()
    s = get_settings()
    db = await DB.open(s.db_path)
    box = Box(s.lead_key_b64, prod=False)
    since = time.time() - a.days * 86400
    if a.cmd == "leads":
        for r in await db.fetchall("SELECT * FROM leads ORDER BY created_at DESC"):
            print(time.strftime("%Y-%m-%d %H:%M", time.localtime(r["created_at"])), box.open(r["name_enc"]),
                  "|", box.open(r["company_enc"]), "|", box.open(r["email_enc"]), "|", box.open(r["about_enc"]),
                  "| session", r["session_id"])
    elif a.cmd == "bookings":
        for r in await db.fetchall("SELECT * FROM bookings ORDER BY start DESC"):
            print(r["start"], box.open(r["attendee_email_enc"]), r["status"], r["meet_url"])
    elif a.cmd == "flagged":
        for r in await db.fetchall("SELECT * FROM turn_logs WHERE created_at > ? ORDER BY created_at", (since,)):
            d = json.loads(r["json"])
            bad = [f for f in d.get("flags") or [] if not f.startswith(("dodge", "confirm", "lead_saved", "booked"))]
            if bad:
                print(r["session_id"], d["turn_id"], d.get("route"), bad)
    elif a.cmd == "transcript":
        for r in await db.fetchall("SELECT * FROM messages WHERE session_id=? ORDER BY id", (a.arg,)):
            print(f"{r['role']:>8}: {r['text']}")
    elif a.cmd == "trace":
        sid = a.arg or (await db.fetchone("SELECT session_id FROM turn_logs ORDER BY created_at DESC LIMIT 1"))[0]
        print(f"session {sid}")
        for r in await db.fetchall("SELECT json FROM turn_logs WHERE session_id=? ORDER BY created_at", (sid,)):
            d = json.loads(r["json"])
            print(f"\n> {d.get('message')}")
            for b in d.get("replies") or []:
                print(f"  < {b}")
            for st in d.get("trace") or []:
                name = st.get("step")
                rest = {k: v for k, v in st.items() if k != "step"}
                print(f"    [{name}] {json.dumps(rest, ensure_ascii=False)[:220]}")
    elif a.cmd == "questions":
        for r in await db.fetchall("SELECT * FROM questions ORDER BY created_at DESC"):
            print(time.strftime("%Y-%m-%d %H:%M", time.localtime(r["created_at"])), r["status"], "|",
                  box.open(r["question_enc"]), "|", box.open(r["answer_enc"]) if r["answer_enc"] else "-")
    elif a.cmd == "learned":
        import yaml
        cards = []
        for i, r in enumerate(await db.fetchall("SELECT * FROM questions WHERE answer_enc IS NOT NULL"), 1):
            cards.append({"id": f"lr-{i:02d}", "project_id": "general", "aspect": "story", "tech": [], "metrics": [],
                          "negative": False, "text": f"Q: {box.open(r['question_enc'])} A: {box.open(r['answer_enc'])}",
                          "visibility": "public", "source": "chandru-reply", "reviewed": False})
        print("# Draft cards from your own answers. Edit into one fact each, fix project_id/aspect, then add to data/cards/.")
        print(yaml.safe_dump(cards, sort_keys=False, allow_unicode=True))
    elif a.cmd == "stats":
        rows = [json.loads(r["json"]) for r in await db.fetchall("SELECT json FROM turn_logs WHERE created_at > ?", (since,))]
        firsts = sorted(x["timings"].get("first_burst_sent_ms") or 0 for x in rows)
        jev = sorted(x["timings"].get("jev_ms") or 0 for x in rows)
        def pct(v, p):
            return v[min(len(v) - 1, int(len(v) * p))] if v else 0
        cost = sum((x.get("llm") or {}).get("usage", {}).get("cost", 0) or 0 for x in rows)
        print(f"turns {len(rows)} · first burst p50 {pct(firsts, .5):.0f}ms p95 {pct(firsts, .95):.0f}ms · "
              f"jev p50 {pct(jev, .5):.0f}ms p95 {pct(jev, .95):.0f}ms · llm cost ${cost:.4f}")
        routes = {}
        for x in rows:
            routes[x.get("route")] = routes.get(x.get("route"), 0) + 1
        print("routes", routes)
    await db.close()


if __name__ == "__main__":
    asyncio.run(main())
