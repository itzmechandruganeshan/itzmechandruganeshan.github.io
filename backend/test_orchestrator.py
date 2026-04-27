import asyncio
from app.orchestrator import orchestrator

async def main():
    session_id = "test_session"
    user_message = "Hello!"
    history = []
    
    print("Starting generation...")
    async for chunk in orchestrator.generate_response(session_id, user_message, history):
        print(f"YIELDED: {repr(chunk)}")
    print("Generation complete.")

if __name__ == "__main__":
    asyncio.run(main())
