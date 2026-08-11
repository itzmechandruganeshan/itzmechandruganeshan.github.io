---
name: advanced-rag-retrieval
description: Implements advanced Retrieval-Augmented Generation (RAG) strategies to guarantee high-precision knowledge retrieval. Use this skill when modifying the ingestor, vector store, or retrieval pipeline (e.g., app/retrieval).
---

# Advanced RAG & Retrieval

To ensure the AI chatbot responds accurately and intelligently to recruiter queries without hallucinating, follow these strict retrieval patterns:

## 1. Hybrid Search Architecture
- **Rule:** Do not rely solely on dense vector embeddings.
- **Implementation:** Implement a two-stage retrieval pipeline.
  - *Stage 1 (Recall):* Use fast dense embeddings (e.g., `text-embedding-3-small` or local HuggingFace embeddings) with a high `top-k` (e.g., 20).
  - *Stage 2 (Precision):* Use a cross-encoder re-ranker (like `FlashRank`) to re-score and filter the top results before passing them to the LLM.
- **Why:** Semantic similarity alone often fails on keyword-heavy tech queries (e.g., distinguishing between "React" and "React Native"). Re-ranking ensures relevance.

## 2. Context-Aware Semantic Chunking
- **Rule:** Never split documents arbitrarily by character count.
- **Implementation:** When parsing the `knowledge/` directory, split markdown files by structural headers (`#`, `##`) using `MarkdownHeaderTextSplitter` or semantic boundaries. Ensure each chunk retains its parent metadata (e.g., `source: experience.md`, `topic: backend`).
- **Why:** The LLM needs complete logical thoughts, not sentences cut in half.

## 3. Strict Context Grounding
- **Rule:** The LLM must not hallucinate facts outside the retrieved context.
- **Implementation:** Enforce strict system prompt boundaries: "If the answer is not in the provided context, state clearly that you don't have that information." 
- **Why:** For a portfolio, accuracy is critical. Claiming skills you don't possess will fail technical interviews.

## 4. Asynchronous Database Lookups
- **Rule:** Retrieval must not block the main event loop.
- **Implementation:** Use async drivers (e.g., `Motor` for MongoDB, `asyncpg` for PostgreSQL, or async SQLite wrappers) and parallelize multiple index searches (e.g., searching `projects` and `experience` concurrently using `asyncio.gather`).
