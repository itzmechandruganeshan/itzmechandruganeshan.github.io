from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Dict, Any

class IntentClassification(BaseModel):
    intent: Literal[
        "PROFILE_FAQ",
        "TECHNICAL_DEEP_DIVE",
        "BEHAVIORAL_STORY",
        "TOOL_SCHEDULING",
        "CASUAL",
        "OUT_OF_DOMAIN"
    ] = Field(..., description="The classified intent of the user's query.")
    confidence: float = Field(..., description="Confidence score of the classification (0.0 to 1.0).")
    search_query: Optional[str] = Field(None, description="If retrieval is needed, the optimized search query to use against the vector database.")
    target_companies: Optional[List[str]] = Field(None, description="A list of companies mentioned in the query to filter on (e.g., ['ISPG', 'Cloudside', 'Searce']).")
    target_tech: Optional[List[str]] = Field(None, description="A list of technologies mentioned in the query to filter on (e.g., ['Python', 'FastAPI', 'LangChain']).")
    is_recruiter: bool = Field(False, description="Set to true if the user implies they are a recruiter, HR, or asking interview-style questions (e.g., 'walk me through your resume', 'years of experience').")

class DocumentChunk(BaseModel):
    chunk_id: str
    content: str
    metadata: Dict[str, Any]

class SessionMemory(BaseModel):
    session_id: str
    inferred_persona: Optional[str] = None
    topics_discussed: List[str] = []
    history: List[Dict[str, str]]

class RenderUIComponent(BaseModel):
    """Call this tool to render an interactive UI component on the user's screen.
    Only call this when the user asks a question where a visual representation (like a project card, timeline, or skill matrix) would be much better than plain text.
    Do NOT call this for casual conversation."""
    component_name: Literal["ProjectCard", "ExperienceTimeline", "SkillMatrix"] = Field(..., description="The name of the component to render.")
    payload: Dict[str, Any] = Field(..., description="The JSON payload containing the data for the component (e.g., title, description, skills).")
