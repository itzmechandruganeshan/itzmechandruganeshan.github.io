import os
import uuid
import httpx
import asyncio
from typing import List, Dict, Any, Optional
from qdrant_client import AsyncQdrantClient, models
from app.config import settings

from fastembed import SparseTextEmbedding
from flashrank import Ranker, RerankRequest

COLLECTION_NAME = "digital_chandru_knowledge"

# Initialize local models for sparse search and reranking
sparse_model = SparseTextEmbedding("prithivida/Splade_PP_en_v1")
reranker = Ranker(model_name="ms-marco-MiniLM-L-12-v2")

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
                vectors_config={
                    "dense": models.VectorParams(
                        size=3072,
                        distance=models.Distance.COSINE
                    )
                },
                sparse_vectors_config={
                    "sparse": models.SparseVectorParams(
                        modifier=models.Modifier.IDF
                    )
                }
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
        dense_embeddings = await get_openrouter_embeddings(texts)
        
        # Generate sparse embeddings synchronously using fastembed
        sparse_embeddings_gen = list(sparse_model.embed(texts))
        
        points = []
        for i, (dense_emb, sparse_emb, text, meta) in enumerate(zip(dense_embeddings, sparse_embeddings_gen, texts, metadatas)):
            payload = meta.copy()
            payload["content"] = text
            points.append(
                models.PointStruct(
                    id=str(uuid.uuid4()),
                    vector={
                        "dense": dense_emb,
                        "sparse": models.SparseVector(
                            indices=sparse_emb.indices.tolist(),
                            values=sparse_emb.values.tolist()
                        )
                    },
                    payload=payload
                )
            )
            
        await self.client.upsert(
            collection_name=COLLECTION_NAME,
            points=points
        )

    async def search(self, query: str, limit: int = 5, category_filter: Optional[List[str]] = None, target_companies: Optional[List[str]] = None, target_tech: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Searches the vector DB using Hybrid Search (Dense + Sparse) with RRF, then Reranks."""
        await self.ensure_collection()
        
        query_dense_vector = (await get_openrouter_embeddings([query]))[0]
        query_sparse_vector = list(sparse_model.embed([query]))[0]
        
        must_conditions = []
        if category_filter:
            must_conditions.append(models.FieldCondition(key="category", match=models.MatchAny(any=category_filter)))
        if target_companies:
            must_conditions.append(models.FieldCondition(key="companies", match=models.MatchAny(any=target_companies)))
        if target_tech:
            must_conditions.append(models.FieldCondition(key="tech_stack", match=models.MatchAny(any=target_tech)))
            
        query_filter = models.Filter(must=must_conditions) if must_conditions else None

        # Fetch more candidates for reranking
        prefetch_limit = limit * 4 

        # Using Qdrant's Query API for Reciprocal Rank Fusion (Hybrid Search)
        response = await self.client.query_points(
            collection_name=COLLECTION_NAME,
            prefetch=[
                models.Prefetch(
                    query=query_dense_vector,
                    using="dense",
                    limit=prefetch_limit,
                    filter=query_filter,
                ),
                models.Prefetch(
                    query=models.SparseVector(
                        indices=query_sparse_vector.indices.tolist(),
                        values=query_sparse_vector.values.tolist(),
                    ),
                    using="sparse",
                    limit=prefetch_limit,
                    filter=query_filter,
                )
            ],
            query=models.FusionQuery(fusion=models.Fusion.RRF),
            limit=prefetch_limit
        )
        
        candidates = [hit.payload for hit in response.points]
        if not candidates:
            return []

        # Rerank using Flashrank
        for idx, c in enumerate(candidates):
            c["id"] = idx
            c["text"] = c["content"]
            
        rerank_request = RerankRequest(query=query, passages=candidates)
        reranked_results = reranker.rerank(rerank_request)
        
        # Take the top `limit` results
        top_results = reranked_results[:limit]
        
        # Parent-Child Expansion: Fetch adjacent chunks
        expanded_results = await self._expand_context(top_results)
        
        return expanded_results

    async def _expand_context(self, top_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Expands context by fetching chunk_index - 1 and chunk_index + 1 for each chunk."""
        # Use a dict to deduplicate chunks by parent_doc_id and chunk_index
        expanded_chunks_map = {}
        
        for result in top_results:
            parent_doc_id = result.get("parent_doc_id")
            chunk_index = result.get("chunk_index")
            total_chunks = result.get("total_chunks", 1)
            
            if parent_doc_id is None or chunk_index is None:
                continue
                
            # Keep the original chunk
            chunk_key = f"{parent_doc_id}_{chunk_index}"
            if chunk_key not in expanded_chunks_map:
                expanded_chunks_map[chunk_key] = result
                
            # Fetch neighbors
            neighbors_to_fetch = []
            if chunk_index > 0:
                neighbors_to_fetch.append(chunk_index - 1)
            if chunk_index < total_chunks - 1:
                neighbors_to_fetch.append(chunk_index + 1)
                
            for neighbor_idx in neighbors_to_fetch:
                neighbor_key = f"{parent_doc_id}_{neighbor_idx}"
                if neighbor_key not in expanded_chunks_map:
                    # Query Qdrant for this specific neighbor
                    filter_query = models.Filter(
                        must=[
                            models.FieldCondition(key="parent_doc_id", match=models.MatchValue(value=parent_doc_id)),
                            models.FieldCondition(key="chunk_index", match=models.MatchValue(value=neighbor_idx))
                        ]
                    )
                    neighbor_response = await self.client.scroll(
                        collection_name=COLLECTION_NAME,
                        scroll_filter=filter_query,
                        limit=1
                    )
                    if neighbor_response and neighbor_response[0]:
                        expanded_chunks_map[neighbor_key] = neighbor_response[0][0].payload

        # Group by parent_doc_id and sort by chunk_index
        grouped = {}
        for chunk in expanded_chunks_map.values():
            pid = chunk.get("parent_doc_id")
            if pid not in grouped:
                grouped[pid] = []
            grouped[pid].append(chunk)
            
        final_results = []
        for pid, chunks in grouped.items():
            # Sort chunks by index to maintain logical order
            chunks.sort(key=lambda x: x.get("chunk_index", 0))
            # Merge them into a continuous block conceptually or just return them sorted
            # Here we just extend the final results list so the LLM gets them in order
            final_results.extend(chunks)
            
        return final_results

vector_store = VectorStore()
