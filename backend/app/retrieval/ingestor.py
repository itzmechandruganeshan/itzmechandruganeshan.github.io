import os
import asyncio
from typing import List, Dict, Any
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from app.retrieval.vector_store import vector_store
from app.config import settings

class SemanticChunk(BaseModel):
    standalone_content: str = Field(description="The chunk text, completely rewritten to be self-contained. Resolve any pronouns (e.g. 'It' -> 'The Python script'). Make sure it retains all technical details.")
    chunk_summary: str = Field(description="A 1-sentence summary of this chunk.")

class DocumentProcessingResult(BaseModel):
    document_summary: str = Field(description="A dense 1-2 sentence summary of the entire document.")
    tech_stack: List[str] = Field(description="List of technologies mentioned in the document.")
    companies: List[str] = Field(description="List of companies or organizations mentioned in the document.")
    chunks: List[SemanticChunk] = Field(description="The document split into logical semantic units.")

async def process_document_agentically(file_name: str, content: str) -> DocumentProcessingResult:
    llm = ChatOpenAI(
        model="google/gemini-2.5-flash-lite",
        api_key=settings.openrouter_api_key,
        base_url="https://openrouter.ai/api/v1",
        temperature=0.0
    ).with_structured_output(DocumentProcessingResult)
    
    system_prompt = """You are a Principal Data Engineer.
Your job is to read a markdown document from an AI Engineer's portfolio and chunk it agentically.
1. Output a global summary, tech stack, and companies.
2. Break the document down into semantic chunks (usually 1-3 paragraphs per chunk based on topic boundaries).
3. IMPORTANT: Rewrite the `standalone_content` of each chunk so that it is fully self-contained. If the original text says "It increased speed by 20%", rewrite it to "The Hybrid Search Engine increased speed by 20%".
Do not lose any technical details, metrics, or jargon in the rewriting process.
"""
    
    user_prompt = f"File Name: {file_name}\n\nDocument Content:\n{content}"
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]
    
    result = await llm.ainvoke(messages)
    return result

async def ingest_knowledge_base():
    """Reads the knowledge/ directory and inserts agentically chunked documents into Qdrant."""
    knowledge_dir = os.path.join(os.getcwd(), "knowledge")
    
    chunks_to_insert = []
    
    if not os.path.exists(knowledge_dir):
        print(f"Knowledge directory not found at {knowledge_dir}")
        return

    # To avoid rate limits, process files sequentially
    for category in os.listdir(knowledge_dir):
        category_path = os.path.join(knowledge_dir, category)
        if not os.path.isdir(category_path):
            continue
            
        for file_name in os.listdir(category_path):
            if not file_name.endswith(".md"):
                continue
                
            file_path = os.path.join(category_path, file_name)
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                
            print(f"Agentically processing {category}/{file_name}...")
            
            try:
                result = await process_document_agentically(file_name, content)
                
                for index, chunk in enumerate(result.chunks):
                    chunks_to_insert.append({
                        "content": chunk.standalone_content,
                        "metadata": {
                            "category": category,
                            "source_file": file_name,
                            "chunk_index": index,
                            "chunk_summary": chunk.chunk_summary,
                            "document_summary": result.document_summary,
                            "tech_stack": result.tech_stack,
                            "companies": result.companies
                        }
                    })
            except Exception as e:
                print(f"Failed to process {file_name}: {e}")
                
    if chunks_to_insert:
        print("Embedding and inserting into Qdrant...")
        await vector_store.add_chunks(chunks_to_insert)
        print(f"Ingested {len(chunks_to_insert)} agentic chunks into Qdrant.")
