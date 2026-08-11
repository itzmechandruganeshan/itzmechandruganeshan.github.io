import os
import json
import asyncio
import sys
from pydantic import BaseModel, Field
from typing import List

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from app.config import settings

class QAPair(BaseModel):
    question: str = Field(description="A question a user or recruiter might ask based on this document.")
    expected_answer: str = Field(description="The factual, detailed answer extracted directly from the document.")
    category: str = Field(description="One of: TECHNICAL_DEEP_DIVE, PROFILE_FAQ, BEHAVIORAL_STORY")

class DatasetChunk(BaseModel):
    qa_pairs: List[QAPair] = Field(description="A list of 5-8 question-answer pairs derived from the document.")

async def generate_dataset():
    knowledge_dir = os.path.join(os.path.dirname(__file__), "..", "knowledge")
    
    llm = ChatOpenAI(
        model="google/gemini-2.5-flash",
        api_key=settings.openrouter_api_key,
        base_url="https://openrouter.ai/api/v1",
        temperature=0.7
    ).with_structured_output(DatasetChunk)
    
    system_prompt = """You are an expert Data Engineer building a Golden Evaluation Dataset for a RAG pipeline.
Your goal is to generate 5 to 8 diverse, high-quality question-and-answer pairs based strictly on the provided markdown document.
Generate a mix of:
- Direct factual questions (e.g., 'What tech stack did you use?')
- Complex analytical questions (e.g., 'How did you solve the latency issue?')
- Behavioral/Experience questions (e.g., 'What was your biggest challenge here?')
Make sure the 'expected_answer' contains the specific technical details mentioned in the text."""

    all_qa_pairs = []
    
    print(f"Scanning {knowledge_dir} for markdown files...")
    
    for root, _, files in os.walk(knowledge_dir):
        for file in files:
            if file.endswith(".md"):
                file_path = os.path.join(root, file)
                print(f"Processing {file}...")
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    
                messages = [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=f"Document:\n{content}")
                ]
                
                try:
                    result = await llm.ainvoke(messages)
                    for pair in result.qa_pairs:
                        all_qa_pairs.append({
                            "question": pair.question,
                            "expected_answer": pair.expected_answer,
                            "category": pair.category
                        })
                    print(f"  -> Generated {len(result.qa_pairs)} pairs.")
                except Exception as e:
                    print(f"  -> Failed: {e}")
                    
    # Add a few out-of-domain questions manually to ensure robustness
    all_qa_pairs.extend([
        {"question": "Can you give me a recipe for pancakes?", "expected_answer": "I don't have that information. I am an AI representing Chandru.", "category": "OUT_OF_DOMAIN"},
        {"question": "Who is the president of the United States?", "expected_answer": "I don't know. Let's talk about Chandru's projects instead.", "category": "OUT_OF_DOMAIN"}
    ])

    out_file = os.path.join(os.path.dirname(__file__), "..", "tests", "golden_dataset.json")
    os.makedirs(os.path.dirname(out_file), exist_ok=True)
    with open(out_file, "w") as f:
        json.dump(all_qa_pairs, f, indent=2)
        
    print(f"\nSuccessfully generated {len(all_qa_pairs)} questions and saved to {out_file}")

if __name__ == "__main__":
    asyncio.run(generate_dataset())
