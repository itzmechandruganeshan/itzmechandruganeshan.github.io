"""Qdrant-backed store for claim cards and news (ADR-002).

Cloud free tier first; falls back to embedded local mode (same API) if the cloud
cluster is unreachable at startup.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime

from qdrant_client import AsyncQdrantClient, models

from app.config import Settings
from app.data import Card
from app.retrieval.embed import embed_query

log = logging.getLogger(__name__)
DENSE, SPARSE = "dense", "bm25"
DENSE_DIM = 384
NAMESPACE = uuid.UUID("6f1c7c2e-6f0a-4c38-9d55-7a8f2a1f0b10")


def point_id(key: str) -> str:
    return str(uuid.uuid5(NAMESPACE, key))


@dataclass
class NewsCard:
    id: str
    topic: str
    headline: str
    gist: str
    source: str
    url: str
    published_at: datetime
    score: float = 0.0


def card_from_payload(p: dict) -> Card:
    return Card(
        id=p["card_id"], project_id=p["project_id"], aspect=p["aspect"], text=p["text"],
        tech=tuple(p.get("tech") or ()), metrics=tuple(p.get("metrics") or ()),
        negative=bool(p.get("negative")), visibility=p.get("visibility", "public"), reviewed=True,
    )


async def connect(settings: Settings) -> tuple[AsyncQdrantClient, str]:
    if settings.retrieval_backend == "cloud" and settings.qdrant_url:
        client = AsyncQdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key or None, timeout=5)
        try:
            await client.get_collections()
            return client, "cloud"
        except Exception as e:  # noqa: BLE001 - any failure means fall back
            log.error("qdrant cloud unreachable (%s); using embedded", e)
    settings.qdrant_local_path.mkdir(parents=True, exist_ok=True)
    return AsyncQdrantClient(path=str(settings.qdrant_local_path)), "embedded"


async def ensure_collection(client: AsyncQdrantClient, name: str, keyword_fields: list[str],
                            datetime_fields: list[str] = (), float_fields: list[str] = ()) -> None:
    if not await client.collection_exists(name):
        await client.create_collection(
            name,
            vectors_config={DENSE: models.VectorParams(size=DENSE_DIM, distance=models.Distance.COSINE)},
            sparse_vectors_config={SPARSE: models.SparseVectorParams(modifier=models.Modifier.IDF)},
        )
    if not hasattr(client, "_client") or type(client._client).__name__ == "AsyncQdrantLocal":
        return  # payload indexes are a no-op in embedded mode
    for f in keyword_fields:
        await client.create_payload_index(name, f, field_schema=models.PayloadSchemaType.KEYWORD)
    for f in datetime_fields:
        await client.create_payload_index(name, f, field_schema=models.PayloadSchemaType.DATETIME)
    for f in float_fields:
        await client.create_payload_index(name, f, field_schema=models.PayloadSchemaType.FLOAT)


def _match(field: str, value) -> models.FieldCondition:
    if isinstance(value, (list, tuple, set)):
        return models.FieldCondition(key=field, match=models.MatchAny(any=list(value)))
    return models.FieldCondition(key=field, match=models.MatchValue(value=value))


class KnowledgeStore:
    def __init__(self, client: AsyncQdrantClient, settings: Settings, backend: str):
        self.client = client
        self.s = settings
        self.backend = backend

    async def hybrid(self, query: str, *, k: int | None = None, project_id: str | None = None) -> list[Card]:
        """Scale path (ADR-008): unused while all cards fit in the prompt; switch back above ~20k tokens."""
        dense, sparse = await embed_query(query)
        must = [_match("visibility", "public")]
        if project_id:
            must.append(_match("project_id", project_id))
        flt = models.Filter(must=must)
        k = k or self.s.hybrid_top_k
        res = await self.client.query_points(
            self.s.cards_collection,
            prefetch=[
                models.Prefetch(query=dense, using=DENSE, limit=k * 3, filter=flt),
                models.Prefetch(query=sparse, using=SPARSE, limit=k * 3, filter=flt),
            ],
            query=models.FusionQuery(fusion=models.Fusion.RRF),
            limit=k, with_payload=True,
        )
        return [card_from_payload(p.payload) for p in res.points]

    async def news(self, query: str, topic: str, *, now: datetime, k: int | None = None) -> list[NewsCard]:
        dense, sparse = await embed_query(query)
        flt = models.Filter(must=[_match("topic", topic)])
        k = k or self.s.news_top_k
        res = await self.client.query_points(
            self.s.news_collection,
            prefetch=[
                models.Prefetch(query=dense, using=DENSE, limit=k * 4, filter=flt),
                models.Prefetch(query=sparse, using=SPARSE, limit=k * 4, filter=flt),
            ],
            query=models.FusionQuery(fusion=models.Fusion.RRF),
            limit=k * 4, with_payload=True,
        )
        cards = []
        for p in res.points:
            pl = p.payload
            published = datetime.fromisoformat(pl["published_at"])
            age_days = max(0.0, (now - published).total_seconds() / 86400)
            decay = 0.5 ** (age_days / self.s.news_half_life_days)
            cards.append(NewsCard(
                id=pl["news_id"], topic=pl["topic"], headline=pl["headline"], gist=pl["gist"],
                source=pl["source"], url=pl["url"], published_at=published, score=p.score * decay,
            ))
        cards.sort(key=lambda c: c.score, reverse=True)
        return cards[:k]

    async def keepalive(self) -> None:
        await self.client.count(self.s.cards_collection, exact=False)
