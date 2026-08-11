# Project 5: mewatch AI - Conversational OTT Chatbot & EPG Engine

**Link/Repo:** Private (Client: Mediacorp / Searce Inc)
**Company:** Searce Inc (Client: Mediacorp Singapore)
**Period:** May 2026 – Present
**Tech Stack:** Python, LangGraph, Gemini 2.5 Flash, Vertex AI Search, Cloud Run, Cloud SQL, BigQuery, Apigee, Model Armor, Cloud Trace

---

## 1. Executive Summary & Architecture
Built a production-grade conversational AI assistant for Mediacorp's Singapore OTT streaming platform (**mewatch**). The assistant handles multilingual user queries, live Electronic Program Guide (EPG) schedules, and Video-on-Demand (VOD) recommendations across complex multi-agent workflows.

---

## 2. Core Technical Breakthroughs

### Decoupled Multilingual Routing Node (LangGraph)
- **Problem:** As new agent nodes (Subscription, VOD, EPG) were added, the orchestrator prompt grew massively, causing LLM attention decay in `gemini-2.5-flash`. The model failed to consistently follow complex multilingual rules (e.g. distinguishing Malay vs. Indonesian, handling follow-up queries, or falling back to English for unsupported languages).
- **Solution:** Removed prompt-level multilingual rules entirely and built a dedicated `language_detector` node in LangGraph. Programmatically evaluated language support (supported: Mandarin, Chinese, Tamil, English, Malay, Singlish; fallback: English).
- **Recency-Prompt Injection & Cost ROI:** Appended detected language instructions as a dynamic `[Note]` alongside the *latest user message payload*, exploiting recency bias so low-cost models (`gemini-2.5-flash`) follow formatting rules with 100% adherence—reducing LLM token costs by 80% compared to upgrading models.

### EPG Search Engine Migration (NL2SQL → Vertex AI Search)
- **Problem:** Legacy NL2SQL queries failed on semantic queries ("any cricket matches on TV?"), show description lookups, and fuzzy titles.
- **Solution:** Replaced NL2SQL entirely with **Vertex AI Search (GCP Data Store)** backed by a curated BigQuery schema (rolling 15-day window: past 7 days + current day + upcoming 7 days).
- **Custom Rulebook & Cards:** Added metadata fields (`mewatch_url`, `image_url` for content cards) and authored a deterministic rulebook for temporal filtering (past/present/future shows) and channel constraints.

### VOD Recommendation Agent Pagination
- **Problem:** Users asking for "more Tamil shows" or "more like this" received duplicate show recommendations across conversational turns.
- **Solution:** Implemented stateful pagination and context-aware deduplication filters in the VOD agent state, guaranteeing fresh, unique show recommendations per turn.
