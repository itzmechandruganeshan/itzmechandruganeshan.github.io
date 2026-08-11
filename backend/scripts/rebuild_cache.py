import os
import json
import httpx
import asyncio

EVALUATE_URL = "http://127.0.0.1:8000/api/evaluate"

async def get_agent_response(question: str, session_id: str):
    async with httpx.AsyncClient(timeout=120.0) as client:
        payload = {
            "query": question,
            "session_id": session_id,
            "stream": False
        }
        try:
            response = await client.post(EVALUATE_URL, json=payload)
            response.raise_for_status()
            data = response.json()
            
            # Use correct schema keys based on the API response
            answer = data.get("actual_answer", "")
            
            # The API returns retrieved_context as a string or empty string
            ctx = data.get("retrieved_context", "")
            if not ctx:
                contexts = ["NO CONTEXT RETRIEVED"]
            else:
                contexts = [ctx]
            
            return answer, contexts
        except Exception as e:
            print(f"Error querying {question}: {e}")
            return "", ["ERROR"]

async def main():
    dataset_path = os.path.join(os.path.dirname(__file__), "..", "tests", "advanced_golden_dataset.json")
    with open(dataset_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    print(f"Found {len(data['entries'])} test cases. Rebuilding cache from backend API...")
    
    results = []
    
    # We query sequentially to avoid overloading the backend LLM (rate limits)
    for i, row in enumerate(data["entries"]):
        print(f"[{i+1}/{len(data)}] Querying: {row['question'][:50]}...")
        answer, contexts = await get_agent_response(row["question"], row["session_id"])
        
        results.append({
            "category": row["category"],
            "session_id": row["session_id"],
            "question": row["question"],
            "answer": answer,
            "contexts": contexts,
            "ground_truth": row["expected_answer"]
        })
        
    out_path = os.path.join(os.path.dirname(__file__), "ragas_raw_results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
        
    print(f"\nSuccessfully wrote {len(results)} responses to {out_path}!")

if __name__ == "__main__":
    asyncio.run(main())
