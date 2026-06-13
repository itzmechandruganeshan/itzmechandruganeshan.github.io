## Project Name: Hybrid Automotive Search Engine (Conversational Query API)
**Link/Repo:** Private (ISPG Technologies)

### 1. The Problem
The core issue was building an intelligent product search engine capable of understanding complex, messy automotive queries (part numbers, car models, abbreviations, typos) and accurately returning product matches from a massive catalogue of nearly 1.39 million data points. Standard keyword searches failed on domain-specific terminology, and pure vector searches often returned irrelevant results ("false positives") when queries were obscure.

### 2. The Architecture & Approach
I architected a 3-stage hybrid search pipeline to maximize retrieval accuracy and handle edge cases:
- **Stage 1 (Intelligent Extraction):** An LLM (Mistral-7B via Bedrock) parses the query to extract precise domain keywords, while a fuzzy string matcher (RapidFuzz) normalizes misspelled brand names (e.g., "fprd" to "Ford").
- **Stage 2 (Parallel Vector Search):** Sentence Transformers calculate cosine similarity concurrently across 22K+ pre-computed product title and category embeddings using Python threading.
- **Stage 3 (Fallback Cascade):** If vector similarity fails to find a strong match above a 55% confidence threshold, the system gracefully falls back to a purely lexical BM25 search to guarantee exact part number retrieval.

### 3. Tech Stack
Python, FastAPI, Mistral-7B-Instruct (Amazon Bedrock), Sentence Transformers (`all-mpnet-base-v2`), BM25 (`rank_bm25`), RapidFuzz, Pandas, NumPy, Docker, Jenkins.

### 4. The Hardest Technical Hurdle
The hardest bottleneck was dealing with unpredictable LLM outputs during keyword extraction. When I replaced a brittle `spaCy` implementation with Mistral-7B to better understand automotive context, the LLM would occasionally return conversational filler alongside the requested JSON, crashing the downstream pipeline. 

I solved this by building a two-layer defense: a strict JSON-only system prompt coupled with a robust regex extractor (`re.search(r'\{.*\}', s, re.DOTALL)`). This aggressively parses only the JSON block from the LLM's raw response, bypassing any hallucinated text entirely. Additionally, calculating cosine similarity across 22,000+ embeddings was slow; I fixed this by implementing parallel processing for title and category searches, and utilizing O(1) Pandas set lookups to dramatically cut response times.

### 5. The Outcome
- **Scale:** Successfully indexed and searched across ~1.39 million fitment combinations (part ↔ car model ↔ year mappings).
- **Quality:** Eliminated vector false positives by enforcing a strict 55% cosine similarity cutoff.
- **Speed:** Cut vector search latency significantly using concurrent threading, and guaranteed fast frontend rendering by hard-capping API response payloads to a maximum of 30 exact part matches.