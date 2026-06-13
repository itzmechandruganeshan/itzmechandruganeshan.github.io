# Digital Chandru - Interview (System Design)

## 1. Designing a Search Engine from Scratch
If asked to design an enterprise search engine today, I wouldn't default to pure Vector Search. I would architect a Hybrid Fallback Cascade:
1. **Intelligent Extraction:** Use a fast LLM (like Mistral) to parse domain-specific jargon from the natural language query.
2. **Concurrent Retrieval:** Fire asynchronous requests (`asyncio.gather`) to query both a Vector DB (Qdrant) and a lexical search engine (Elasticsearch or BM25).
3. **Strict Filtering:** Enforce a hard threshold on the Vector DB (e.g., 55% cosine similarity). If the vector search doesn't meet the threshold, fall back strictly to lexical keyword matching.
4. **Fuzzy Normalization:** Use RapidFuzz to correct misspellings of brand names before querying the database.
This guarantees you get the "magic" of semantic search without losing the 100% exact-match accuracy required for part numbers or SKU IDs.