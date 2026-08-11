import uuid
from typing import Optional
from qdrant_client import models
from app.retrieval.vector_store import vector_store, get_openrouter_embeddings
import logging

logger = logging.getLogger(__name__)

CACHE_COLLECTION = "semantic_cache"

async def check_semantic_cache(query: str, threshold: float = 0.95) -> Optional[str]:
    """Checks if a semantically similar query was already answered."""
    try:
        await vector_store.client.get_collection(collection_name=CACHE_COLLECTION)
    except Exception:
        try:
            await vector_store.client.create_collection(
                collection_name=CACHE_COLLECTION,
                vectors_config=models.VectorParams(size=3072, distance=models.Distance.COSINE)
            )
        except Exception:
            pass # might have been created concurrently
            
    try:
        query_emb = (await get_openrouter_embeddings([query]))[0]
        
        response = await vector_store.client.query_points(
            collection_name=CACHE_COLLECTION,
            query=query_emb,
            limit=1,
            score_threshold=threshold
        )
        
        if response.points:
            logger.info(f"SEMANTIC CACHE HIT! Score: {response.points[0].score}")
            return response.points[0].payload.get("response")
    except Exception as e:
        logger.error(f"Semantic Cache Error: {e}")
        
    return None

async def add_to_semantic_cache(query: str, response: str):
    """Caches the response for a given query."""
    try:
        query_emb = (await get_openrouter_embeddings([query]))[0]
        
        await vector_store.client.upsert(
            collection_name=CACHE_COLLECTION,
            points=[
                models.PointStruct(
                    id=str(uuid.uuid4()),
                    vector=query_emb,
                    payload={"query": query, "response": response}
                )
            ]
        )
    except Exception as e:
        logger.error(f"Failed to add to semantic cache: {e}")
