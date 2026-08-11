from typing import List, Dict, Any, Literal, Optional
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from app.config import settings
from app.schemas import IntentClassification

ROUTER_MODEL = "google/gemini-2.5-flash-lite"

class BaseIntent(BaseModel):
    intent: Literal[
        "PROFILE_FAQ",
        "TECHNICAL_DEEP_DIVE",
        "BEHAVIORAL_STORY",
        "TOOL_SCHEDULING",
        "CASUAL",
        "OUT_OF_DOMAIN"
    ]
    confidence: float
    is_recruiter: bool

class Entities(BaseModel):
    target_companies: Optional[List[str]] = None
    target_tech: Optional[List[str]] = None

class QueryRewrite(BaseModel):
    search_query: str

class IntentRouter:
    def __init__(self):
        self.llm = ChatOpenAI(
            model=ROUTER_MODEL,
            api_key=settings.openrouter_api_key,
            base_url="https://openrouter.ai/api/v1",
            temperature=0.0
        )
        self.intent_llm = self.llm.with_structured_output(BaseIntent)
        self.entity_llm = self.llm.with_structured_output(Entities)
        self.rewrite_llm = self.llm.with_structured_output(QueryRewrite)
        
    async def route_query(self, user_message: str, history_list: List[Dict[str, str]]) -> IntentClassification:
        # Step 1: Intent Routing
        intent_system = """You are an Intent Router. Classify the user query into:
- PROFILE_FAQ: Jobs, companies, timeline, bio.
- TECHNICAL_DEEP_DIVE: Projects, architecture, tech stack, RAG/Agent opinions.
- BEHAVIORAL_STORY: Failures, bugs, teamwork.
- TOOL_SCHEDULING: Book meeting or time.
- CASUAL: Small talk.
- OUT_OF_DOMAIN: Unrelated to Chandru.
Also determine if the user is acting as a recruiter (is_recruiter=true)."""
        intent_prompt = f"User Query: {user_message}"
        try:
            base_intent = await self.intent_llm.ainvoke([SystemMessage(content=intent_system), HumanMessage(content=intent_prompt)])
        except Exception as e:
            print(f"Intent routing failed: {e}")
            return IntentClassification(intent="CASUAL", confidence=0.0, search_query=None)

        if base_intent.intent not in ["PROFILE_FAQ", "TECHNICAL_DEEP_DIVE", "BEHAVIORAL_STORY"]:
            return IntentClassification(
                intent=base_intent.intent,
                confidence=base_intent.confidence,
                is_recruiter=base_intent.is_recruiter
            )

        # Step 2: Entity Extraction
        entity_system = "Extract explicit companies (e.g. ISPG, Searce) and technologies (e.g. Python, FastAPI) from the user query. If none, return null."
        try:
            entities = await self.entity_llm.ainvoke([SystemMessage(content=entity_system), HumanMessage(content=intent_prompt)])
        except Exception:
            entities = Entities()

        # Step 3: Query Rewriting (using last 3-5 turns)
        rewrite_system = """You are a Query Rewriter. Given the recent chat history, user query, intent, and extracted entities, rewrite the user's query into an optimized search query for a vector database. Combine key nouns and technical terms. Do not use conversational filler."""
        
        history_str = ""
        for msg in history_list[-4:]: # Only last 4 messages to avoid retrieval drift
            history_str += f"{msg['role']}: {msg['content']}\n"
            
        rewrite_prompt = f"Recent History:\n{history_str}\n\nIntent: {base_intent.intent}\nEntities: {entities.model_dump()}\n\nUser Query: {user_message}"
        try:
            rewritten = await self.rewrite_llm.ainvoke([SystemMessage(content=rewrite_system), HumanMessage(content=rewrite_prompt)])
            search_query = rewritten.search_query
        except Exception:
            search_query = user_message

        # Combine into Final Schema
        return IntentClassification(
            intent=base_intent.intent,
            confidence=base_intent.confidence,
            search_query=search_query,
            target_companies=entities.target_companies,
            target_tech=entities.target_tech,
            is_recruiter=base_intent.is_recruiter
        )

intent_router = IntentRouter()
