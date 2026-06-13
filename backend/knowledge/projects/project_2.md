## Project Name: PNG Jewellery - Conversational Query System
**Link/Repo:** Private (ISPG Technologies)

### 1. The Problem
E-commerce search engines for jewelry often struggle with conversational or natural language queries, such as "gold necklaces under 2 lakhs" or "diamond rings between 2 and 5 million". Traditional keyword matching fails to accurately extract numerical price constraints embedded within natural language text (e.g., parsing "lakhs" or "million" with typos) and struggles with semantic similarities, returning irrelevant products.

### 2. The Architecture & Approach
I built a 2-stage conversational query pipeline served via a high-performance REST API.
1. **Logical Extraction Engine:** Uses a custom regex and Spacy-based NLP pipeline to parse the user's natural language query. It specifically extracts and normalizes textual number formats (e.g., mapping "two lakhs" to 200,000), identifying boundaries for `priceFrom` and `priceTo`, along with core product `keywords`.
2. **Semantic Search & Similarity Checking Engine:** Uses a locally hosted `SentenceTransformers` model (`all-MiniLM-L6-v2`) to perform semantic search over pre-embedded product categories. To refine results further, the pipeline passes the output through a similarity checker using `rapidfuzz` to calculate partial string match ratios between the user query and the category hierarchy, ensuring only highly relevant categories are returned.
These processes run concurrently using asynchronous tasks (`asyncio.gather`), significantly boosting API response times.

### 3. Tech Stack
- **Languages:** Python
- **Frameworks:** FastAPI, Uvicorn, LangChain
- **Machine Learning & NLP:** SentenceTransformers, spaCy, RapidFuzz, Pandas, NumPy
- **Infrastructure & Deployment:** Docker, Jenkins pipelines, Bitbucket pipelines, Kubernetes

### 4. The Hardest Technical Hurdle
One of the most complex challenges was dealing with latency and accurate numerical data extraction from unstructured conversational text. Initially, users often provided price constraints in colloquial Indian numbering systems (e.g., "lakhs") with multiple spelling variations ("lkh", "lakh") which standard NER models failed to parse consistently alongside the semantic intent. Furthermore, processing semantic search synchronously with text extraction was causing latency spikes.
**The Fix:** I decoupled the logical extraction (which handles colloquial terms using custom regex mapping and the `numerizer` library) from the semantic category search. I then restructured the FastAPI endpoints to execute these two heavy operations asynchronously using `asyncio.gather`. I also pre-computed embeddings for the entire product category catalog (`product_embeddings.npy`), completely removing the overhead of embedding the corpus at runtime.

### 5. The Outcome
The conversational query system was successfully deployed in a production-grade Kubernetes environment. It reliably translates complex, unstructured natural language queries into structured search criteria (price boundaries and exact product categories), vastly improving the search experience. The asynchronous architecture ensured minimal latency, and the custom text extraction captured nearly 100% of colloquial pricing inputs. All queries and performance metrics are logged concurrently to a JSON file via an async locking mechanism to continuously monitor and improve the system.
