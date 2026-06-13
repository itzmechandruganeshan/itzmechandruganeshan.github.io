import asyncio
from app.retrieval.ingestor import ingest_knowledge_base

async def main():
    print("Starting knowledge base ingestion...")
    try:
        await ingest_knowledge_base()
        print("\nSuccess! Ingestion complete. The Qdrant vector store is now populated.")
    except Exception as e:
        print(f"\nError during ingestion: {e}")

if __name__ == "__main__":
    asyncio.run(main())
