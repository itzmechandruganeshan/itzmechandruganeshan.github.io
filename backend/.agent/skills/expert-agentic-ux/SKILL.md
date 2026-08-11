---
name: expert-agentic-ux
description: Applies expert-level UI/UX guidelines for real-time agentic chatbots, focusing on WebSocket streaming, UI component triggering, and human-like signaling. Use this skill whenever building or modifying the chat interface or LLM orchestration layers.
---

# Expert Agentic UX Guidelines

When building or modifying the backend chatbot orchestration (FastAPI/LangGraph), you MUST prioritize a seamless, magical user experience that feels human.

## 1. Zero-Latency Streaming (Minimize TTFT)
- **Rule:** Never wait for the entire LLM response to complete before sending data.
- **Implementation:** Immediately stream tokens (`{"type": "chunk", "text": "..."}`) via WebSocket as soon as the LLM yields them. Time-to-First-Token (TTFT) must be under 500ms.
- **Why:** Instant visual feedback reassures the user that the agent is actively thinking and responding.

## 2. Dynamic UI Component Rendering
- **Rule:** Don't dump long lists or complex markdown tables into the chat.
- **Implementation:** Use the `RenderUIComponent` tool (or equivalent structured outputs) to yield custom React components (e.g., `{"type": "ui_component", "payload": ...}`).
- **Why:** A visual `ProjectCard` or `ExperienceTimeline` natively rendered on the frontend provides a significantly richer and more memorable recruiter experience than plain text.

## 3. Human-like State Signaling
- **Rule:** Always emit real-time state changes to the client.
- **Implementation:** 
  - Send `{"type": "control", "action": "typing"}` when the LLM starts processing.
  - Send `{"type": "control", "action": "idle"}` when generation completes.
  - Use randomized, context-aware nudges (e.g., "Just checking in...") if the WebSocket connection is idle for an extended period, simulating a human waiting on the other end.

## 4. Error Gracefulness
- **Rule:** Never crash silently or expose raw Python stack traces to the frontend.
- **Implementation:** Catch exceptions at the orchestrator layer and send a playful, in-character error message (e.g., "Whoops, I short-circuited for a second. Let's try that again!").
