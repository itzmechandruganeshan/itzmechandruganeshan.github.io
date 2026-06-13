from typing import TypedDict, List, Dict, Any, Optional
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage

from app.schemas import IntentClassification
from app.agents.router import intent_router
from app.retrieval.vector_store import vector_store
from app.tools import execute_native_tool
from app.agents.composer import get_composer_llm, build_system_message

class GraphState(TypedDict):
    session_id: str
    user_message: str
    history_list: List[Dict[str, str]]
    intent: Optional[IntentClassification]
    user_persona: str
    retrieved_context: str
    messages: List[Any] # For langgraph compatibility

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
            
            header = f"[Source: {source}"
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

async def execute_tool_node(state: GraphState):
    user_message = state["user_message"]
    if "time" in user_message.lower():
        retrieved_context = f"Tool output: {execute_native_tool('get_current_time', {})}"
    else:
        retrieved_context = "User asked for scheduling. Ask them to email or provide a calendly link."
    return {"retrieved_context": retrieved_context}

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

workflow = StateGraph(GraphState)

workflow.add_node("router", route_intent_node)
workflow.add_node("retriever", retrieve_knowledge_node)
workflow.add_node("tool", execute_tool_node)
workflow.add_node("composer", compose_response_node)

workflow.set_entry_point("router")
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
workflow.add_edge("composer", END)

graph = workflow.compile()
