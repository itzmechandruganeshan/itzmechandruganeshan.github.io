# Digital Chandru - Professional Experience

*This file captures your career timeline. The Digital Twin will use this to answer questions like "Walk me through your resume," "What did you do at Cloudside?" or "Tell me about a time you scaled a system."*

---

## Cloudside Technologies Pvt. Ltd. (now Searce Inc.) | AI Engineer
**Location:** Coimbatore, Tamil Nadu, India
**Timeline:** ~ Jan 2025 – Present (1.5 years) *(Company acquired by Searce Inc. during tenure)*

### 1. The Core Mission
I was brought in as an AI Engineer at Cloudside — a Google Cloud Partner company — to design and build enterprise-grade Generative AI applications for clients using Google's ecosystem, primarily Vertex AI, Gemini, and GCP. My primary mandate was to move beyond simple chatbots and architect genuinely autonomous, multi-agent AI systems that could replace entire human workflows.

### 2. Architectural & Engineering Contributions

**Hierarchical Multi-Agent System on Vertex AI (Flagship Project)**

Rather than building one monolithic LLM prompt, I architected a hierarchical system of specialized AI agents that orchestrate and delegate tasks to sub-agents — effectively building an autonomous digital employee.

**Marketing Orchestration Layer:**
- Built a primary **Marketing Orchestrator Agent** that acts as a manager, delegating to specialized sub-agents: Ad Campaign Agent, LinkedIn Content Agent, Icon Generation Agent, and a Video Generation Agent.
- The **Video Generation Agent** was the most architecturally complex piece — it doesn't just generate video directly. It first spins up its own nested sub-agents: an **Objective Finder Agent** (to determine the video's goal) and a **Script Writer Agent** (to write the ad script) — before invoking tools to generate the final video content. Coordinating state and context transfer across nested Vertex AI Reasoning Engines was a significant engineering challenge.

**Autonomous Sales Pipeline Agent:**
- Built an end-to-end agent that autonomously handles the entire lead-generation lifecycle without any human intervention:
  - Dynamically searches for relevant webshop URLs using **Google Custom Search API**
  - Discovers and enriches lead data via the **Apollo API**
  - Runs leads through custom business logic filters (prohibited item detection, price threshold verification)
  - Programmatically injects validated organizations, people, and leads directly into **Pipedrive CRM**
  - Uses **BigQuery** for duplicate checking and **Google Cloud Storage (GCS)** for intermediate data storage

**Tech Stack:** Google Vertex AI, Gemini (Enterprise), Agent Builder, Vertex AI Reasoning Engines, LangChain, LlamaIndex, GCP (BigQuery, GCS), Google Custom Search API, Apollo API, Pipedrive API

### 3. Key Metrics & Business Impact
- Fully automated both the **marketing content pipeline** and **sales lead generation lifecycle** — replacing workflows that previously required manual human effort at every step.
- The system autonomously handles everything from researching a cold lead to generating a **personalized targeted video ad** for that lead — end to end, zero human intervention.
- Deployed across isolated environments on **Google Cloud's Agent Builder** with independent deployment pipelines per agent, integrated with multiple external APIs and GCP services simultaneously.

### 4. Challenges & Learnings
The overarching complexity was **multi-agent state management and context transfer across nested Reasoning Engines**. When you have agents spawning sub-agents that spawn further sub-agents, ensuring each layer has the right context — without overloading the LLM's context window or causing state leakage between agent sessions — requires very deliberate architectural design.

Additionally, deploying each agent into isolated GCP environments while keeping them coordinated through shared GCS storage and BigQuery state required careful infrastructure planning — this was as much a DevOps challenge as an AI one.

*Note: Cloudside Technologies was acquired by Searce Inc. during my tenure — a testament to the quality and scale of the work the team was doing.*

---

## ISPG Technologies Pvt. Ltd. | GenAI Engineer
**Location:** Kochi, Kerala, India
**Timeline:** ~ May 2024 – Dec 2025 (8 months)

### 1. The Core Mission
At ISPG Technologies, a product-based startup, I was tasked with building an intelligent **automotive parts search engine** — a customer-facing AI product that could understand complex, messy, domain-specific queries (part numbers, car models, abbreviations, brand names) and return accurate product matches from a catalogue of nearly **1.39 million data points**.

### 2. Architectural & Engineering Contributions

**Hybrid Automotive Search Engine (Core Product):**
- Designed and built a multi-layered semantic search system combining **vector search**, **BM25 lexical search**, and **fuzzy string matching** in a strict fallback cascade to maximize retrieval accuracy.
- **LLM-Powered Keyword Extraction:** Replaced a brittle spaCy POS-tagging approach with **Mistral-7B-Instruct via Amazon Bedrock** to intelligently extract keywords from complex automotive queries (part names, abbreviations, composite terms).
- **Hallucination Control:** Implemented strict JSON-only system prompts and built a robust regex-based JSON extractor (`_extract_json_from_string`) to parse LLM outputs reliably, even when the model returned conversational filler around the JSON block.
- **Fallback Search Cascade:** If vector similarity fails to find a strong match, the system falls back to **BM25 keyword search** (via `rank_bm25`) for exact part number retrieval, and **RapidFuzz** fuzzy matching for brand name normalization (e.g., "fprd" → "Ford").
- **Performance Optimization:** Used Python's `threading` module to run product title and category vector searches in **parallel**, cutting vector search latency significantly. Applied Pandas `set()` lookups for O(1) performance and enforced a 30-item payload limit on API responses for frontend speed.
- Deployed the backend as a **FastAPI** service with a Jenkins-based CI/CD pipeline (`jenkins-agent-pod.yaml`).

**Tech Stack:** Python, FastAPI, Mistral-7B (Amazon Bedrock), Sentence Transformers, BM25 (rank_bm25), RapidFuzz, NumPy, Pandas, LangGraph, LangChain, Llama Models, OpenAI, Vector Databases, Docker, Jenkins

### 3. Key Metrics & Business Impact
- **~1.39 Million data points** searched and cross-referenced in real time:
  - 1,368,648 fitment combination rows (part ↔ car model ↔ year mappings)
  - 22,018 unique core product embeddings
  - 673 universal fitment products
- **55% cosine similarity threshold** enforced to eliminate false positive vector results — only confident matches are returned.
- **Top 7 nearest-neighbor** vector matches retrieved per query across both product titles and categories.
- **65% fuzzy match ratio** threshold for brand name normalization using RapidFuzz.
- Parallel threading cut vector search time significantly by running title and category searches concurrently.
- API response capped at **30 results** maximum, ensuring fast network payloads and smooth frontend rendering.

### 4. Challenges & Learnings

**1. Bad Retrieval Quality from Automotive Queries**
Standard NLP tools like spaCy completely failed on automotive terminology — part abbreviations and composite terms aren't standard English. Switched to Mistral-7B on Bedrock for context-aware extraction, then built the BM25 + fuzzy fallback cascade to handle edge cases the vector search couldn't.

**2. LLM Hallucinations in Structured Output**
Once using an LLM for keyword extraction, unpredictable outputs (conversational filler, wrong formats) would crash the pipeline. Built a two-layer defense: strict JSON-only system prompts + a regex extractor that aggressively finds and parses the JSON block from any raw LLM response.

**3. Performance Bottlenecks on 1.39M Data Points**
Loading large CSVs and running cosine similarity across 22K+ embeddings on every request was slow. Profiled extensively (tracked with `time.time()` blocks), then applied parallel threading, O(1) set lookups, and payload truncation to bring response times to an acceptable level.

**4. False Positives in Vector Search**
Vector embeddings can be "too fuzzy" — returning irrelevant results just because they score highest in the embedding space. Instituted the 0.55 cosine similarity cutoff to hard-filter low-confidence matches before they ever reach the user.

---

## Microbiological Laboratory Pvt. Ltd. | Data Scientist Intern
**Location:** India
**Timeline:** ~ Feb 2024 to May 2024 (3 months)

### 1. The Core Mission
This internship was the direct predecessor to my final year thesis — I was brought in to build an **ML-assisted pathogen detection tool** to help lab technicians identify pathogen presence from PCR data, reducing reliance on manual visual interpretation.

### 2. Architectural & Engineering Contributions
- Built a machine learning classification model using **Scikit-learn** to analyze PCR signal data and predict pathogen presence.
- Developed an interactive **Streamlit** web application as the front-end interface for lab technicians — no coding knowledge required to operate it.
- Integrated **Plotly** visualizations to display PCR curves, signal patterns, and model predictions in a clear, interpretable format for non-technical clinical users.

**Tech Stack:** Python, Scikit-learn, Streamlit, Plotly

### 3. Key Metrics & Business Impact
- Delivered a working end-to-end tool — from raw PCR data input to classification output — within a 3-month internship.
- The tool provided lab technicians with an ML-assisted second opinion, reducing the cognitive load of manual curve interpretation.
- The work directly informed and shaped my final year M.Sc. thesis, where I extended this research into a full three-component framework (REXTRACTOR, PyMLRS, Pathogen Detector).

### 4. Challenges & Learnings
The primary challenge was making the tool genuinely usable for **non-technical lab staff** — the interface had to be simple enough for a clinician with no ML background to operate confidently. This forced me to think carefully about UX, result presentation, and how to communicate model confidence without overwhelming users with technical jargon.

This internship was my first real-world lesson in the difference between a model that works in a notebook and a tool that works in production for real users — a lesson that has defined my engineering philosophy ever since.