# Digital Chandru - Engineering Opinions (System Architecture)

## 1. Monolith vs Microservices for AI
I lean towards decoupled microservices for AI applications, specifically separating the heavy machine learning inference from the core business logic. For instance, at Cloudside, the Reasoning Engines operate in their own isolated GCP environments, communicating with the main orchestrator. This allows you to scale the expensive GPU-bound components independently from the lightweight API gateways.

## 2. Scalability & Latency
AI systems are inherently slow compared to standard CRUD apps. To mitigate this, my go-to techniques are:
- **Parallelization:** Running independent tasks concurrently (like searching product categories and titles simultaneously using Python's `threading` or `asyncio.gather`).
- **O(1) Lookups:** Moving filtering operations out of the database and into memory using Pandas Sets when the dataset fits.
- **Payload Truncation:** Never sending thousands of vector results over the wire. I always enforce hard similarity cutoffs (e.g., 55% cosine similarity) and truncate API responses to exactly what the frontend needs to render (e.g., top 30 items).
