"""Dense (bge-small) + sparse (BM25) embeddings via fastembed, computed in-process off the event loop."""

from __future__ import annotations

import asyncio
from functools import lru_cache

from qdrant_client import models

from app.config import get_settings


@lru_cache
def _dense():
    from fastembed import TextEmbedding
    s = get_settings()
    return TextEmbedding(s.dense_model, cache_dir=str(s.embed_cache_dir))


@lru_cache
def _sparse():
    from fastembed import SparseTextEmbedding
    s = get_settings()
    return SparseTextEmbedding(s.sparse_model, cache_dir=str(s.embed_cache_dir))


def warm() -> None:
    _dense(), _sparse()


def _to_sparse(e) -> models.SparseVector:
    return models.SparseVector(indices=e.indices.tolist(), values=e.values.tolist())


def embed_docs(texts: list[str]) -> list[tuple[list[float], models.SparseVector]]:
    dense = [v.tolist() for v in _dense().embed(texts)]
    sparse = [_to_sparse(e) for e in _sparse().embed(texts)]
    return list(zip(dense, sparse))


def embed_query_sync(text: str) -> tuple[list[float], models.SparseVector]:
    dense = next(iter(_dense().query_embed(text))).tolist()
    sparse = _to_sparse(next(iter(_sparse().query_embed(text))))
    return dense, sparse


async def embed_query(text: str) -> tuple[list[float], models.SparseVector]:
    return await asyncio.to_thread(embed_query_sync, text)
