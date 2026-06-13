## Project Name: Pay-in-3 (in3) Multi-Agent AI Marketing & Sales System
**Link/Repo:** Private(Cloudside Technologies)

### 1. The Problem
Traditional marketing and sales workflows required significant manual effort—from generating cohesive video ad campaigns to finding, enriching, and logging B2B leads. Simple LLM chatbots were insufficient for this because they couldn't autonomously execute complex, multi-step workflows across different APIs, enforce visual continuity in video generation, or safely merge relational data into a live CRM without creating a mess of duplicates.

### 2. The Architecture & Approach
I designed an autonomous multi-agent orchestration system deployed natively on Google Cloud's Agent Builder (Reasoning Engines). 
  **Marketing Pipeline:** I built a root agent that coordinates an objective_finder_agent and a script_writer_agent to break an ad campaign down into a detailed scene-by-scene script. It then generates the video sequentially using the Veo model.
  **Sales Pipeline:** I built a sales root agent that orchestrates specialized tools to extract webshop URLs, run bulk enrichment via the Apollo API, and execute relational API calls to Pipedrive to create Organizations, Persons, and Leads.
  **Deployment:** I built a custom deployment pipeline ("AgentSpace") to automate packaging and deploying these Python LlmAgent classes directly onto Google Cloud.

### 3. Tech Stack
  **Languages:** Python
  **AI/ML:** Google Cloud Vertex AI, Gemini 2.5 Pro & Flash, Google Veo Model (veo-3.0-generate-001), Google ADK
  **Data & Infrastructure:** Google Cloud Storage, BigQuery, Cloud Run
  **Libraries/APIs:** OpenCV, MoviePy, Apollo API, Pipedrive API, Google Custom Search

### 4. The Hardest Technical Hurdle
**Hurdle 1: Maintaining stylistic continuity in AI video generation.** 
Generating a coherent multi-scene ad campaign is incredibly difficult because generative video models (like Veo) tend to lose visual context and style between isolated scenes. 
  **The Fix:** I engineered a programmatic feedback loop inside the video generation tool. Using **OpenCV**, the system automatically extracts the very last frame of the previously generated video scene and feeds it back into the multimodal prompt as the initial_frame for the next scene. This forced the model to maintain stylistic consistency and smooth transitions across the entire ad sequence, which I then stitched together with audio using **MoviePy**.

**Hurdle 2: Safely merging enriched leads into a live CRM.** 
Blindly pushing AI-gathered data into a CRM leads to massive duplication and broken relational data.
  **The Fix:** I implemented a robust, multi-stage deduplication pipeline. Before creating any records, the agent checks the enriched leads against both existing Pipedrive records and a historical BigQuery table. Only after passing the checks does it sequentially map and create the Organization, the Person, and finally the Lead, ensuring perfect data integrity.

### 5. The Outcome
  Successfully transitioned from static LLM prompts to a fully autonomous, production-ready multi-agent system on Google Cloud.
  Automated the creation of stylistically consistent, multi-scene ad campaign videos, drastically reducing content generation time.
  Streamlined the B2B lead generation pipeline, automatically enriching webshop contacts and flawlessly integrating them into Pipedrive without manual data entry or duplication errors.
