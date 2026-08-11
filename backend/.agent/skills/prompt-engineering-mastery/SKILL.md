---
name: prompt-engineering-mastery
description: Defines the standard for crafting and injecting system prompts to maintain persona authenticity and output quality. Use this when editing app/agents/composer.py or any LLM interaction layer.
---

# Prompt Engineering Mastery

To ensure the AI chatbot perfectly mimics Chandru's authentic, 24-year-old tech-bro WhatsApp persona, adhere to the following prompt engineering standards:

## 1. Dynamic Persona Assembly
- **Rule:** Do not hardcode massive personas in strings.
- **Implementation:** Load traits dynamically from the `persona/` YAML files (`identity.yaml`, `communication_style.yaml`, etc.) at startup and compile them into the system prompt.
- **Why:** Keeps code clean and allows non-engineers to tweak the personality easily by editing YAML files.

## 2. Temporal & Environmental Context
- **Rule:** The agent must always be aware of time.
- **Implementation:** Inject a `<system_clock>` block containing the current date and time (in IST) into the system prompt on every generation.
- **Why:** Allows the agent to accurately say "Good morning" or reference weekend plans (e.g., "It's Saturday, just cleaning my bike").

## 3. The "Plain Text" WhatsApp Constraint
- **Rule:** The chatbot must never talk like a Markdown-generating corporate AI.
- **Implementation:** Strictly enforce the `<tone_rules>` section in the prompt:
  - "PLAIN TEXT ONLY — no markdown, no bold, no bullet lists."
  - "ADAPTIVE TONE — mirror the user's formality. Use slang ('bro', 'macha') only if the user is casual."
  - "Keep responses short (under 50 words) unless specifically asked for details."
  - "NEVER explain reasoning (e.g., avoid 'Based on your question...')."

## 4. Few-Shot Structural Prompting
- **Rule:** When the agent needs to return JSON (like calling the `RenderUIComponent` tool), guarantee structure.
- **Implementation:** Use `bind_tools()` in LangChain/LangGraph, but also provide 1-2 few-shot examples in the system prompt to demonstrate exactly when to trigger the UI tool vs. when to just chat.
