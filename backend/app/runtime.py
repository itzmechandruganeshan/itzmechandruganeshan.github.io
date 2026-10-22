"""Builds the long-lived dependencies once per process."""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

import httpx

from app.config import Settings
from app.data import Knowledge, get_knowledge
from app.graph.prompts import facts_flat
from app.graph.state import Deps
from app.intelligence.jev import JevClient
from app.integrations.composio_mcp import ComposioMCP
from app.intelligence.llm import LLMClient
from app.retrieval.checks import known_entities
from app.retrieval.store import KnowledgeStore, connect, ensure_collection
from app.storage.crypto import Box
from app.storage.db import DB

log = logging.getLogger(__name__)


def protected_terms(kb: Knowledge) -> set[str]:
    terms = {"chandru", "searce", "cloudside", "ispg", "mlrs", "coimbatore", "chennai", "kochi", "bharathiar",
             "langgraph", "langchain", "gemini", "vertex", "bigquery", "qdrant", "openrouter", "jev", "fastapi",
             "python", "docker", "kubernetes", "rag", "llm", "llms", "nl2sql", "epg", "vod", "ott", "faiss"}
    for p in kb.projects:
        terms |= {a for a in p.aliases if " " not in a}
        terms |= {w for t in p.tech for w in t.lower().split()}
        terms |= {w.lower() for w in p.company.split()}
    for c in kb.cards:
        terms |= {w for t in c.tech for w in t.split()}
    return terms


@dataclass
class Runtime:
    deps: Deps
    http: httpx.AsyncClient
    store_backend: str

    async def close(self):
        await self.http.aclose()
        if self.deps.db:
            await self.deps.db.close()
        if self.deps.store:
            await self.deps.store.client.close()
        if self.deps.actions:
            await self.deps.actions.close()


async def build_runtime(s: Settings, *, with_store: bool = True) -> Runtime:
    kb = get_knowledge(str(s.data_dir))
    http = httpx.AsyncClient(http2=False, limits=httpx.Limits(max_keepalive_connections=20))
    store, backend = None, "none"
    if with_store:
        try:
            client, backend = await connect(s)
            await ensure_collection(client, s.cards_collection, ["project_id", "aspect", "visibility", "company", "tech"])
            await ensure_collection(client, s.news_collection, ["topic", "source"], ["published_at"],
                                    ["ingested_ts", "expires_ts"])
            store = KnowledgeStore(client, s, backend)
        except Exception as e:  # noqa: BLE001
            log.error("vector store unavailable, answering from in-memory cards: %s", e)
    db = await DB.open(s.db_path)
    zone = ZoneInfo(s.timezone)
    deps = Deps(
        settings=s, kb=kb, jev=JevClient(s, http), llm=LLMClient(s, http), store=store, db=db,
        box=Box(s.lead_key_b64, prod=s.is_prod), protected=protected_terms(kb), entities=known_entities(kb),
        facts_text=facts_flat(kb), now=lambda: datetime.now(zone),
        rng=random.Random(s.seed) if s.seed is not None else random.Random(),
    )
    deps.actions = ComposioMCP(s)
    await deps.actions.start()
    return Runtime(deps=deps, http=http, store_backend=backend)
