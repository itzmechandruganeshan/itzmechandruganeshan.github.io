# Digital Chandru - Behavioral Story (Failure)

## 1. The Situation
While working at ISPG on the Hybrid Automotive Search Engine, I replaced a brittle spaCy NLP pipeline with a Mistral-7B LLM (via Amazon Bedrock) to extract complex automotive keywords and abbreviations from user queries. The initial tests in the notebook were flawless.

## 2. The Failure
When deployed to staging, the pipeline started crashing sporadically. I had assumed the LLM would strictly return JSON as instructed. However, occasionally, Mistral would output conversational filler like "Here is your JSON:" before the actual payload. Because my downstream code was expecting pure JSON, it threw `JSONDecodeError`s, causing the entire search API to fail for those specific queries. It was a failure of trust—I trusted a non-deterministic model to act like deterministic software.

## 3. The Resolution & Learning
Instead of trying to prompt-engineer the model to be perfect (which is impossible), I built an architectural defense mechanism. I implemented a strict regex extractor (`re.search(r'\{.*\}', s, re.DOTALL)`) that aggressively strips away everything outside the JSON block before parsing. 
This permanently changed my approach: I now assume all LLMs will eventually hallucinate or break format, and I always build deterministic safety wrappers around them in production.