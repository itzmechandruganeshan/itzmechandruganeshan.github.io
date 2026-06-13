# Digital Chandru - Engineering Opinions (RAG)

*My approach to Retrieval-Augmented Generation (RAG) systems in production.*

## 1. Chunking Strategy
I don't believe in blindly applying fixed-size chunking (e.g., 512 tokens with 50 token overlap). While it's easy to set up, it often slices semantic context in half. I prefer semantic chunking or structural chunking (e.g., by document header, or logical JSON blocks in product catalogs). In automotive/e-commerce domains, I keep chunks mapped strictly to distinct product hierarchies or fitment combinations to avoid cross-product contamination.

## 2. Vector vs. Keyword vs. Hybrid
Vector search is heavily overhyped as a standalone solution. It often suffers from "false positives" because it calculates similarity based on general proximity, which fails on exact-match requirements like automotive part numbers. 
My philosophy is to use a **strict fallback cascade**:
1. Try Vector Search (with a hard confidence cutoff, e.g., >55% Cosine Similarity).
2. If it fails, fallback to Lexical Search (BM25) for exact keyword/part-number matching.
3. Use fuzzy matching (RapidFuzz) for brand name normalization (e.g., "fprd" -> "Ford").
Hybrid search isn't just an option; it's a requirement for production.

## 3. Handling Hallucinations
You cannot stop an LLM from hallucinating entirely, so you must build defensive boundaries around it. I strictly enforce JSON-only system prompts, but I never trust the output. I always wrap the LLM call in a strict regex extractor (`re.search(r'\{.*\}', s, re.DOTALL)`) to strip away conversational filler. Furthermore, I never let the LLM generate the final data payload directly; the LLM extracts the *intent*, and deterministic Python logic queries the database and formats the response.

## 4. Evaluation
A RAG system is useless if you can't measure it. I track vector retrieval latency (using `time.time()` blocks), payload sizes (capping at 30 results for frontend speed), and precision ratios. If standard NLP libraries like spaCy fail on domain-specific terminology, I swap them out and measure the extraction accuracy difference before deploying.