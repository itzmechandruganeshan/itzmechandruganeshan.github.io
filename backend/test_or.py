import asyncio
import httpx
from app.config import settings
import json

async def main():
    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "meta-llama/llama-3.3-70b-instruct:free",
        "messages": [{"role": "user", "content": "Hello!"}],
        "stream": True,
        "tools": [{"type": "function", "function": {"name": "test", "description": "test"}}]
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload
        )
        print("Status:", response.status_code)
        print("Response:", response.text[:200])

asyncio.run(main())
