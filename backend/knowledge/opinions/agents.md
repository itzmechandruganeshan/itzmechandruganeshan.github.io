# Digital Chandru - Engineering Opinions (Agents)

## 1. Multi-Agent vs. Monolithic LLM
I strongly prefer specialized, hierarchical multi-agent systems over massive, monolithic prompts. When you cram a dozen tools and complex decision trees into a single prompt, the LLM loses focus, hallucination risk spikes, and context windows overflow. 
As I built at Cloudside, I prefer a "Manager-Worker" architecture. A root orchestrator agent determines the high-level goal and then spins up isolated sub-agents (e.g., an Objective Finder Agent or a Script Writer Agent) that only have the context and tools they strictly need. This creates robust, testable, and deterministic workflows.

## 2. Tool Calling Reliability
Blindly trusting an LLM to call an API (like Pipedrive CRM) is a disaster waiting to happen. To prevent duplicate records or corrupted relational data, tool calls must be decoupled from execution. The LLM suggests the parameters, but deterministic logic validates them. For example, before my sales agent injects a lead into the CRM, the tool runs a hard validation against BigQuery to check for duplicates. State between nested agents must be passed explicitly via structured payloads, not open-ended chat history, to prevent state leakage.