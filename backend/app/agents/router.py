from typing import List, Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from app.config import settings
from app.schemas import IntentClassification

ROUTER_MODEL = "google/gemini-2.5-flash-lite"

SYSTEM_PROMPT = """You are an Intent Router for a Digital Twin AI system representing Chandru, an AI Engineer.
Analyze the user's query and history. Output a JSON object matching the requested schema.

Intent Guide:
- PROFILE_FAQ: Questions about current job, companies worked for, location, experience timeline, bio, current status.
- TECHNICAL_DEEP_DIVE: Questions about specific projects, system architectures, tech stacks, or engineering opinions (RAG, Agents, LLMs).
- BEHAVIORAL_STORY: Questions about failures, bugs, teamwork, or resolving conflicts.
- TOOL_SCHEDULING: Requests to book a meeting or get the current time.
- CASUAL: Purely small talk (e.g. "hi", "what's up", "had dinner"). DO NOT use for questions about jobs, companies, or professional background.
- OUT_OF_DOMAIN: Questions completely unrelated to Chandru.

If intent needs retrieval (PROFILE_FAQ, TECHNICAL_DEEP_DIVE, BEHAVIORAL_STORY), provide an optimized 'search_query' combining key nouns.
Additionally, extract any explicit companies mentioned (e.g., "ISPG", "Searce", "Cloudside") into 'target_companies' and any explicit technologies mentioned (e.g., "Python", "FastAPI") into 'target_tech'. Otherwise, leave them null.
Finally, if the user explicitly says they are a recruiter, or asks typical HR/interview questions (e.g., "walk me through your resume", "what is your expected salary", "years of experience"), set 'is_recruiter' to true.
"""

class IntentRouter:
    def __init__(self):
        # OpenRouter wrapper using langchain_openai
        self.llm = ChatOpenAI(
            model=ROUTER_MODEL,
            api_key=settings.openrouter_api_key,
            base_url="https://openrouter.ai/api/v1",
            temperature=0.0
        )
        self.structured_llm = self.llm.with_structured_output(IntentClassification)
        
    async def route_query(self, user_message: str, history_list: List[Dict[str, str]]) -> IntentClassification:
        messages = [SystemMessage(content=SYSTEM_PROMPT)]
        
        # Flatten history for the router (it just needs context)
        history_str = ""
        for msg in history_list[-5:]: # Only last 5 messages for context
            history_str += f"{msg['role']}: {msg['content']}\n"
            
        prompt = f"Recent History:\n{history_str}\n\nUser Query: {user_message}"
        messages.append(HumanMessage(content=prompt))
        
        try:
            result = await self.structured_llm.ainvoke(messages)
            return result
        except Exception as e:
            print(f"Router failed: {e}. Falling back to CASUAL.")
            return IntentClassification(intent="CASUAL", confidence=0.0, search_query=None)

intent_router = IntentRouter()
