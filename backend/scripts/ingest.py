"""Validate cards and (re)build the Qdrant `cards` collection. Idempotent; safe on every deploy.

    uv run python scripts/ingest.py                 # only reviewed cards (prod)
    uv run python scripts/ingest.py --allow-unreviewed   # dev
    uv run python scripts/ingest.py --check         # validate only
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from qdrant_client import models  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.data import get_knowledge, validate  # noqa: E402
from app.retrieval.embed import embed_docs  # noqa: E402
from app.retrieval.store import DENSE, SPARSE, connect, ensure_collection, point_id  # noqa: E402


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--allow-unreviewed", action="store_true")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    s = get_settings()
    kb = get_knowledge(str(s.data_dir))
    problems = validate(kb.projects, kb.cards)
    if problems:
        print("data problems:\n  " + "\n  ".join(problems))
        return 1
    public = [c for c in kb.cards if c.visibility == "public"]
    unreviewed = [c.id for c in public if not c.reviewed]
    print(f"{len(public)} public cards, {len(unreviewed)} unreviewed")
    if unreviewed and not args.allow_unreviewed:
        print("refusing: review these cards (set reviewed: true) or pass --allow-unreviewed in dev:\n  "
              + ", ".join(unreviewed))
        return 2
    if args.check:
        return 0
    cards = public if args.allow_unreviewed else [c for c in public if c.reviewed]
    client, backend = await connect(s)
    await ensure_collection(client, s.cards_collection, ["project_id", "aspect", "visibility", "company", "tech"])
    vecs = embed_docs([c.text for c in cards])
    await client.upsert(s.cards_collection, points=[
        models.PointStruct(id=point_id(c.id), vector={DENSE: d, SPARSE: sp}, payload=c.payload())
        for c, (d, sp) in zip(cards, vecs)
    ])
    keep = {point_id(c.id) for c in cards}
    stale, offset = [], None
    while True:
        pts, offset = await client.scroll(s.cards_collection, limit=256, offset=offset, with_payload=False)
        stale += [p.id for p in pts if str(p.id) not in keep]
        if offset is None:
            break
    if stale:
        await client.delete(s.cards_collection, points_selector=models.PointIdsList(points=stale))
    print(f"upserted {len(cards)} cards to {backend}, removed {len(stale)} stale")
    await client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
