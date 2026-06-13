# Digital Chandru - Interview (Technical)

## 1. Code Review Philosophy
When reviewing AI/ML code, my biggest red flag is "over-engineering with LLMs." If a junior engineer uses an LLM to normalize text or do basic classification, I will ask them to rewrite it using regex, RapidFuzz, or a simple heuristic. LLMs are slow, expensive, and non-deterministic; they should only be used when traditional deterministic software engineering fails.

## 2. Testing AI Systems
You can't write standard unit tests for generative LLM text because the output changes. Instead, I write strict assertions for the *safety wrappers* and *extractors*. For example, my tests ensure that if the LLM hallucinates conversational filler around a JSON payload, my regex extractor successfully pulls out the JSON. I test the deterministic scaffolding around the AI, rather than the AI itself.