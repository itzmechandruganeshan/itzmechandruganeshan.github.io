from typing import TypedDict, List, Dict, Any, Optional
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage

from app.schemas import IntentClassification
from app.agents.router import intent_router
from app.retrieval.vector_store import vector_store
from app.tools import execute_native_tool
from app.agents.composer import get_composer_llm, build_system_message
from app.retrieval.semantic_cache import check_semantic_cache, add_to_semantic_cache

class GraphState(TypedDict):
    session_id: str
    user_message: str
    history_list: List[Dict[str, str]]
    intent: Optional[IntentClassification]
    user_persona: str
    retrieved_context: str
    messages: List[Any] # For langgraph compatibility

async def semantic_cache_node(state: GraphState):
    # Only cache check if it's the start of the turn
    cached_response = await check_semantic_cache(state["user_message"])
    if cached_response:
        return {"messages": [AIMessage(content=cached_response)]}
    return {}

def cache_condition(state: GraphState):
    # If messages already exist here, we got a cache hit
    if state.get("messages") and isinstance(state["messages"][-1], AIMessage):
        return "cache_hit"
    return "cache_miss"

async def route_intent_node(state: GraphState):
    classification = await intent_router.route_query(state["user_message"], state["history_list"])
    
    # If the router detects a recruiter, lock in the persona for the rest of the session
    new_persona = state.get("user_persona", "unknown")
    if classification.is_recruiter:
        new_persona = "recruiter"
        
    return {"intent": classification, "user_persona": new_persona}

def route_condition(state: GraphState):
    intent_str = state["intent"].intent
    if intent_str == "TOOL_SCHEDULING":
        return "tool"
    elif intent_str in ["PROFILE_FAQ", "TECHNICAL_DEEP_DIVE", "BEHAVIORAL_STORY"]:
        return "retrieve"
    else:
        return "compose"

async def retrieve_knowledge_node(state: GraphState):
    classification = state["intent"]
    
    # Broader category filters — don't over-constrain, let the vector search do the heavy lifting
    category_filter = None
    if classification.intent == "TECHNICAL_DEEP_DIVE":
        category_filter = ["projects", "opinions", "profile"]
    elif classification.intent == "PROFILE_FAQ":
        category_filter = ["profile", "projects", "communication"]
    elif classification.intent == "BEHAVIORAL_STORY":
        category_filter = ["stories", "interview", "projects"]
        
    query_to_search = classification.search_query if classification.search_query else state["user_message"]
    
    # First attempt: with metadata filters if the router extracted them
    chunks = await vector_store.search(
        query_to_search, 
        limit=8, 
        category_filter=category_filter,
        target_companies=classification.target_companies,
        target_tech=classification.target_tech
    )
    
    # Fallback: if metadata filtering returned nothing, retry without company/tech filters
    if not chunks and (classification.target_companies or classification.target_tech):
        chunks = await vector_store.search(
            query_to_search, 
            limit=8, 
            category_filter=category_filter,
            target_companies=None,
            target_tech=None
        )
    
    if chunks:
        # Format with rich metadata so the LLM knows the provenance of each chunk
        context_parts = []
        for c in chunks:
            source = c.get("source_file", "unknown")
            summary = c.get("document_summary", "")
            companies = c.get("companies", [])
            tech = c.get("tech_stack", [])
            content = c.get("content", "")
            
            header = f"[Source: {source} (Chunk {c.get('chunk_index', 'Unknown')})"
            if companies:
                header += f" | Companies: {', '.join(companies)}"
            if tech:
                header += f" | Tech: {', '.join(tech[:5])}"  # Cap at 5 to avoid noise
            header += "]"
            
            if summary:
                header += f"\nDocument Summary: {summary}"
            
            context_parts.append(f"{header}\n{content}")
        
        retrieved_context = "\n\n---\n\n".join(context_parts)
    else:
        retrieved_context = ""
        
    return {"retrieved_context": retrieved_context}

from app.agents.scheduler import run_scheduler

async def execute_tool_node(state: GraphState):
    response = await run_scheduler(state["user_message"], state.get("history_list", []))
    # Pass the scheduler's conversational response as context so the composer can deliver it in character
    return {"retrieved_context": f"System scheduling update: {response}"}

async def compose_response_node(state: GraphState):
    system_msg = build_system_message(
        retrieved_context=state.get("retrieved_context", ""),
        user_persona=state.get("user_persona", "unknown")
    )
    
    messages = [system_msg]
    for msg in state.get("history_list", []):
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        else:
            messages.append(AIMessage(content=msg["content"]))
    messages.append(HumanMessage(content=state["user_message"]))
    
    llm = get_composer_llm()
    response = await llm.ainvoke(messages)
    return {"messages": [response]}

from app.agents.composer import get_critique_llm, build_critique_message

async def critique_response_node(state: GraphState):
    # Retrieve the last message generated by the composer
    last_message = state["messages"][-1]
    # We only care if it's text. Tool calls don't need tone critique.
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return {} # Pass through
    
    msg_content = last_message.content
    
    critique_llm = get_critique_llm()
    system_msg = build_critique_message()
    messages = [system_msg, HumanMessage(content=msg_content)]
    
    response = await critique_llm.ainvoke(messages)
    critique_output = response.content.strip()
    
    if critique_output.startswith("FAIL"):
        # The bot broke character. We generate an apology/correction dynamically.
        correction_prompt = f"System: You just sent a message that broke character (too formal, used markdown, etc). The critique agent said: '{critique_output}'. Generate a very short, casual 1-sentence follow-up acknowledging you sounded like a robot for a second, and quickly restate it casually."
        
        composer_llm = get_composer_llm()
        correction_response = await composer_llm.ainvoke([HumanMessage(content=correction_prompt)])
        # In a real app we'd probably cache the correct response, but we don't cache corrections to avoid messing up the cache.
        return {"messages": [correction_response]}
        
    # If the critique passes, we can safely cache this response for future users!
    # Background caching prevents slowing down the user response
    import asyncio
    asyncio.create_task(add_to_semantic_cache(state["user_message"], msg_content))
    
    return {}

workflow = StateGraph(GraphState)

workflow.add_node("cache_check", semantic_cache_node)
workflow.add_node("router", route_intent_node)
workflow.add_node("retriever", retrieve_knowledge_node)
workflow.add_node("tool", execute_tool_node)
workflow.add_node("composer", compose_response_node)
workflow.add_node("critique", critique_response_node)

workflow.set_entry_point("cache_check")
workflow.add_conditional_edges(
    "cache_check",
    cache_condition,
    {
        "cache_hit": END,
        "cache_miss": "router"
    }
)
workflow.add_conditional_edges(
    "router",
    route_condition,
    {
        "retrieve": "retriever",
        "tool": "tool",
        "compose": "composer"
    }
)

workflow.add_edge("retriever", "composer")
workflow.add_edge("tool", "composer")
workflow.add_edge("composer", "critique")
workflow.add_edge("critique", END)

graph = workflow.compile()
