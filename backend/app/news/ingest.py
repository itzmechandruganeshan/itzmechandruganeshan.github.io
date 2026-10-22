"""E5 / FR-F: RSS → dedupe → Jev relevance (J6) → neutral summary → Qdrant `news` (30-day TTL)."""

from __future__ import annotations

import asyncio
import calendar
import hashlib
import logging
import re
import time
import uuid
from datetime import datetime, timedelta, timezone

import feedparser
import httpx
from qdrant_client import models

from app.graph.state import Deps
from app.intelligence import decisions as dec
from app.intelligence.jev import JevError
from app.intelligence.llm import LLMError
from app.retrieval.embed import embed_docs
from app.retrieval.store import DENSE, SPARSE, point_id
from app.tools import notify

log = logging.getLogger(__name__)
TAG_RE = re.compile(r"<[^>]+>")


def _clean(s: str) -> str:
    return " ".join(TAG_RE.sub(" ", s or "").split())


def _canonical(url: str) -> str:
    return re.sub(r"[?#].*$", "", url or "").rstrip("/").lower()


def _published(entry) -> datetime:
    for key in ("published_parsed", "updated_parsed"):
        t = entry.get(key)
        if t:
            return datetime.fromtimestamp(calendar.timegm(t), tz=timezone.utc)
    return datetime.now(timezone.utc)


async def fetch_feed(http: httpx.AsyncClient, url: str) -> list:
    resp = await http.get(url, timeout=10, follow_redirects=True,
                          headers={"User-Agent": "VirtualMe-NewsBot/0.1 (+https://itzmechandruganeshan.github.io)"})
    resp.raise_for_status()
    parsed = await asyncio.to_thread(feedparser.parse, resp.content)
    return list(parsed.entries)


async def summarize(deps: Deps, title: str, desc: str) -> dict:
    return await deps.llm.complete_json([
        {"role": "system", "content": (
            "Summarise this news item neutrally and factually for a news card. No opinions, no adjectives about "
            "parties or people. Return JSON {\"headline\": str (max 14 words), \"gist\": str (max 2 sentences), "
            "\"entities\": [str]}.")},
        {"role": "user", "content": f"Title: {title}\nDescription: {desc[:1200]}"},
    ], max_tokens=200, timeout=10.0)


async def run_ingest(deps: Deps, http: httpx.AsyncClient) -> dict:
    s = deps.settings
    run_id = f"news-{uuid.uuid4().hex[:8]}"
    feeds = deps.kb.feeds
    limits = feeds.get("limits", {})
    keep_days = int(limits.get("keep_days", 30))
    fetched, kept, upserted, status, error = 0, 0, 0, "ok", None
    try:
        if deps.store is None:
            raise RuntimeError("vector store unavailable")
        client = deps.store.client
        existing = set()
        cutoff = time.time() - float(limits.get("dedupe_hours", 72)) * 3600
        points, _ = await client.scroll(s.news_collection, limit=2000, with_payload=["url", "headline", "ingested_ts"])
        for p in points:
            if p.payload.get("ingested_ts", 0) >= cutoff:
                existing.add(_canonical(p.payload.get("url", "")))
        items = []
        for beat in ("tech_industry", "tn_politics"):
            for f in feeds.get(beat, []):
                if not f.get("enabled"):
                    continue
                try:
                    entries = await fetch_feed(http, f["url"])
                except Exception as e:  # noqa: BLE001
                    log.warning("feed %s failed: %s", f["name"], e)
                    continue
                for e in entries[: int(limits.get("max_items_per_feed", 20))]:
                    fetched += 1
                    url = _canonical(e.get("link", ""))
                    if not url or url in existing:
                        continue
                    existing.add(url)
                    items.append((beat, f["name"], e))
        cards = []
        for beat, source, e in items:
            title, desc = _clean(e.get("title", "")), _clean(e.get("summary", ""))
            try:
                topic, conf, worth = await dec.news_relevance(deps.jev, title, desc)
            except JevError as err:
                log.warning("J6 failed for %s: %s", title[:60], err)
                continue
            if topic != beat or conf < s.t_news_relevant or worth < 1.0:
                continue
            try:
                summ = await summarize(deps, title, desc)
            except LLMError as err:
                log.warning("summary failed: %s", err)
                continue
            published = _published(e)
            cards.append({
                "news_id": "n-" + hashlib.sha1(_canonical(e.get("link", "")).encode()).hexdigest()[:12],
                "topic": beat, "headline": str(summ.get("headline", title))[:160],
                "gist": str(summ.get("gist", ""))[:500], "entities": summ.get("entities") or [],
                "source": source, "url": e.get("link", ""), "published_at": published.isoformat(),
                "ingested_ts": time.time(),
                "expires_ts": (published + timedelta(days=keep_days)).timestamp(),
            })
        kept = len(cards)
        if cards:
            vecs = await asyncio.to_thread(embed_docs, [f"{c['headline']}. {c['gist']}" for c in cards])
            await client.upsert(s.news_collection, points=[
                models.PointStruct(id=point_id(c["news_id"]), vector={DENSE: d, SPARSE: sp}, payload=c)
                for c, (d, sp) in zip(cards, vecs)
            ])
            upserted = len(cards)
        await client.delete(s.news_collection, points_selector=models.FilterSelector(filter=models.Filter(
            must=[models.FieldCondition(key="expires_ts", range=models.Range(lt=time.time()))])))
    except Exception as e:  # noqa: BLE001
        status, error = "failed", str(e)[:300]
        log.exception("news ingest failed")
    if deps.db is not None:
        await deps.db.execute(
            "INSERT INTO news_runs(run_id, started_at, fetched, kept, upserted, status, error) VALUES (?,?,?,?,?,?,?)",
            (run_id, time.time(), fetched, kept, upserted, status, error))
        last2 = await deps.db.fetchall("SELECT status FROM news_runs ORDER BY started_at DESC LIMIT 2")
        if len(last2) == 2 and all(r["status"] == "failed" for r in last2):
            await notify.enqueue(deps.db, deps.box, f"news_ingest.failing:{run_id}", "news_ingest.failing",
                                 {"error": error, "run_id": run_id})
    return {"run_id": run_id, "fetched": fetched, "kept": kept, "upserted": upserted, "status": status}
