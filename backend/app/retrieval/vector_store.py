import os
import uuid
import httpx
from typing import List, Dict, Any, Optional
from qdrant_client import AsyncQdrantClient, models
from app.config import settings

COLLECTION_NAME = "digital_chandru_knowledge"

async def get_openrouter_embeddings(texts: List[str]) -> List[List[float]]:
    """Fetch embeddings from OpenRouter using google/gemini-embedding-2."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://openrouter.ai/api/v1/embeddings",
            headers={
                "Authorization": f"Bearer {settings.openrouter_api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "google/gemini-embedding-2",
                "input": texts
            },
            timeout=60.0
        )
        response.raise_for_status()
        data = response.json()
        
        # Sort by index just in case they return out of order
        embeddings = sorted(data["data"], key=lambda x: x["index"])
        return [emb["embedding"] for emb in embeddings]

class VectorStore:
    def __init__(self):
        # Default to a local persistent directory if qdrant_host is localhost
        if settings.qdrant_host == "localhost":
            db_path = os.path.join(os.getcwd(), "data", "qdrant")
            os.makedirs(db_path, exist_ok=True)
            self.client = AsyncQdrantClient(path=db_path)
        else:
            self.client = AsyncQdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
        
    async def ensure_collection(self):
        """Creates the collection if it doesn't exist."""
        try:
            # gemini-embedding-2 produces 3072 dimensional vectors
            await self.client.get_collection(collection_name=COLLECTION_NAME)
        except Exception:
            await self.client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=models.VectorParams(
                    size=3072,
                    distance=models.Distance.COSINE
                )
            )

    async def add_chunks(self, chunks: List[Dict[str, Any]]):
        """Adds text chunks with metadata to Qdrant."""
        await self.ensure_collection()
        if not chunks:
            return
            
        texts = [chunk["content"] for chunk in chunks]
        metadatas = [chunk["metadata"] for chunk in chunks]
        
        # Depending on chunk size, it's safer to batch them or send them all if small
        # Our chunks are usually < 50
        embeddings_gen = await get_openrouter_embeddings(texts)
        
        points = []
        for i, (emb, text, meta) in enumerate(zip(embeddings_gen, texts, metadatas)):
            payload = meta.copy()
            payload["content"] = text
            points.append(
                models.PointStruct(
                    id=str(uuid.uuid4()),
                    vector=emb,
                    payload=payload
                )
            )
            
        await self.client.upsert(
            collection_name=COLLECTION_NAME,
            points=points
        )

    async def search(self, query: str, limit: int = 5, category_filter: Optional[List[str]] = None, target_companies: Optional[List[str]] = None, target_tech: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Searches the vector DB, optionally filtering by category, companies, or tech."""
        await self.ensure_collection()
        
        query_vector = (await get_openrouter_embeddings([query]))[0]
        
        must_conditions = []
        if category_filter:
            must_conditions.append(models.FieldCondition(key="category", match=models.MatchAny(any=category_filter)))
        if target_companies:
            # We lowercase the targets just to be safe, though Qdrant match is case-sensitive by default unless text indexed.
            # Assuming basic exact match for arrays of strings.
            must_conditions.append(models.FieldCondition(key="companies", match=models.MatchAny(any=target_companies)))
        if target_tech:
            must_conditions.append(models.FieldCondition(key="tech_stack", match=models.MatchAny(any=target_tech)))
            
        query_filter = models.Filter(must=must_conditions) if must_conditions else None

        response = await self.client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            query_filter=query_filter,
            limit=limit,
            score_threshold=0.35 # Gemini-embedding-2 at 3072 dims has a wider cosine distribution
        )
        
        return [hit.payload for hit in response.points]

vector_store = VectorStore()
