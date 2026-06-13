import logging
from typing import AsyncGenerator
from app.memory import memory_manager
from app.graph import graph

logger = logging.getLogger(__name__)

class AgentOrchestrator:
    async def generate_response(self, session_id: str, user_message: str) -> AsyncGenerator[dict, None]:
        # 1. Memory Gateway
        history_list = await memory_manager.get_history(session_id)
        await memory_manager.add_message(session_id, "user", user_message)
        
        # 2. Graph Initialization
        initial_state = {
            "session_id": session_id,
            "user_message": user_message,
            "history_list": history_list,
            "intent": None,
            "retrieved_context": "",
            "messages": []
        }
        
        full_reply = ""
        # 3. Stream Execution via LangGraph
        async for event in graph.astream_events(initial_state, version="v2"):
            kind = event["event"]
            
            # Only stream tokens from the composer node (ignore router LLM JSON tokens)
            if kind == "on_chat_model_stream":
                node = event.get("metadata", {}).get("langgraph_node")
                if node == "composer":
                    chunk = event["data"]["chunk"]
                    if chunk.content:
                        full_reply += chunk.content
                        yield {"type": "chunk", "text": chunk.content}
                        
            elif kind == "on_chat_model_end":
                node = event.get("metadata", {}).get("langgraph_node")
                if node == "composer":
                    msg = event["data"].get("output")
                    if msg and hasattr(msg, "tool_calls") and msg.tool_calls:
                        for tool_call in msg.tool_calls:
                            if tool_call["name"] == "RenderUIComponent":
                                args = tool_call["args"]
                                yield {
                                    "type": "ui_component",
                                    "component": args.get("component_name"),
                                    "data": args.get("payload", {})
                                }
            elif kind == "on_custom_event" or kind.startswith("on_chain_"):
                # We can log other events if needed
                pass
                
        if full_reply:
            await memory_manager.add_message(session_id, "assistant", full_reply)

orchestrator = AgentOrchestrator()
