---
name: backend-langgraph-optimization
description: Guidelines for managing the LangGraph orchestrator, state transitions, and tool integrations (like Composio). Use this when modifying app/graph.py, app/orchestrator.py, or adding new nodes to the AI graph.
---

# Backend LangGraph Optimization

The core of the backend is the LangGraph orchestrator (`app/orchestrator.py`). To keep it highly performant, maintainable, and robust against infinite loops, follow these rules:

## 1. Strictly Typed State Management
- **Rule:** The Graph State (`AgentState`) must be strongly typed using `TypedDict` or Pydantic.
- **Implementation:** Explicitly define `messages: Annotated[Sequence[BaseMessage], operator.add]` and strict fields for `context` and `ui_actions`.
- **Why:** Prevents state corruption across complex routing jumps and ensures the UI tool calls don't bleed into standard conversation memory.

## 2. Deterministic Routing
- **Rule:** Avoid relying solely on LLM self-routing if the logic is binary.
- **Implementation:** Use deterministic conditional edges for basic checks. Only use the LLM `Router` node for complex intent classification (e.g., "Does this require Calendar access?" vs "Is this a RAG query?").
- **Why:** Reduces unnecessary LLM calls, lowers latency, and prevents getting stuck in an LLM reasoning loop.

## 3. Tool Execution & Composio
- **Rule:** Isolate third-party API dependencies.
- **Implementation:** When integrating external tools (like the Composio Google Calendar integration), wrap the execution in a dedicated LangGraph node (`ToolExecutor`). Handle timeouts and authentication errors gracefully within that node, returning a friendly error message to the state rather than raising an unhandled exception.

## 4. Graph Compilation & Checkpointing
- **Rule:** State must persist across WebSocket reconnects.
- **Implementation:** Compile the graph with a `MemorySaver` checkpointer keyed by the `session_id` from the SQLite database.
- **Why:** Allows users to refresh the page, reconnect the WebSocket, and instantly resume their complex multi-turn conversation.
