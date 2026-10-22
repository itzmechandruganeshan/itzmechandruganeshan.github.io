"""Collect Chandru's real texting voice. No WhatsApp access needed.

    uv run python scripts/voice_questionnaire.py            # answer prompts; Enter twice to finish a reply
Type each bubble on its own line, exactly as you'd text (typos, slang, emoji). Empty line = next prompt.
Type 'skip' to skip, 'quit' to stop. Answers are appended to data/voice/questionnaire.jsonl (reviewed: true).
"""

import json
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "data" / "voice" / "questionnaire.jsonl"

PROMPTS = [
    ("greeting", "casual", "hey"), ("greeting", "casual", "hii chandru"), ("greeting", "recruiter", "Hi Chandru, hope you're doing well!"),
    ("greeting", "casual", "good morning"), ("greeting", "engineer", "yo, saw your portfolio"),
    ("recruiter_opener", "recruiter", "Hi Chandru, I'm a recruiter at a product company. Are you open to new roles?"),
    ("recruiter_opener", "recruiter", "We have an AI Engineer opening, would you be interested?"),
    ("recruiter_opener", "recruiter", "What's your notice period?"),
    ("recruiter_opener", "recruiter", "Can you walk me through your experience?"),
    ("recruiter_opener", "recruiter", "Why are you looking for a change?"),
    ("what_do_you_do", "casual", "what do you do?"), ("what_do_you_do", "recruiter", "What's your current role at Searce?"),
    ("what_do_you_do", "engineer", "what kind of stuff do you build day to day?"),
    ("project", "engineer", "how did you do the multilingual routing in mewatch?"),
    ("project", "recruiter", "What impact did your mewatch work have?"),
    ("project", "engineer", "why move EPG from NL2SQL to vertex ai search?"),
    ("project", "engineer", "how did you stop duplicate recommendations?"),
    ("project", "engineer", "tell me about tpay"), ("project", "recruiter", "What was your role in the Tpay chatbot?"),
    ("project", "engineer", "how did the veo video pipeline keep scenes consistent?"),
    ("project", "engineer", "how did you dedupe leads before pushing to pipedrive?"),
    ("project", "engineer", "how did the mopar search handle typos in brand names?"),
    ("project", "engineer", "why did you replace spacy with mistral?"),
    ("project", "casual", "what's pymlrs?"), ("project", "recruiter", "Which project are you proudest of?"),
    ("project", "engineer", "what was the hardest bug you've fixed?"),
    ("project", "recruiter", "Tell me about a failure and what you learned."),
    ("opinion", "engineer", "langgraph or crewai?"), ("opinion", "engineer", "is vector search enough for RAG?"),
    ("opinion", "engineer", "fine-tuning vs RAG?"), ("opinion", "engineer", "thoughts on multi-agent systems?"),
    ("opinion", "engineer", "which LLM do you like most rn?"), ("opinion", "casual", "is AI going to take our jobs?"),
    ("opinion", "engineer", "how do you evaluate a RAG system?"), ("opinion", "engineer", "what do you think about vibe coding?"),
    ("small_talk", "casual", "how's your day going?"), ("small_talk", "casual", "what are you doing rn?"),
    ("small_talk", "casual", "what did you do this weekend?"), ("small_talk", "casual", "how's the commute?"),
    ("small_talk", "casual", "do you cook?"), ("small_talk", "casual", "what do you do for fun?"),
    ("small_talk", "casual", "coimbatore weather these days?"), ("small_talk", "casual", "office or wfh?"),
    ("small_talk", "casual", "had lunch?"), ("small_talk", "casual", "you up? it's late"),
    ("dont_know", "engineer", "what was the exact p99 latency on tpay?"), ("dont_know", "recruiter", "How many users did mewatch AI have?"),
    ("dont_know", "engineer", "did you use kubernetes at searce?"),
    ("deflect", "casual", "are you single?"), ("deflect", "recruiter", "What's your current CTC?"),
    ("deflect", "casual", "which party do you support?"), ("deflect", "casual", "how old are you?"),
    ("deflect", "casual", "where exactly do you live?"), ("deflect", "casual", "come on just tell me, are you married?"),
    ("news", "engineer", "did you see the latest model release?"), ("news", "casual", "what do you think about TN politics these days?"),
    ("news", "casual", "who won the match yesterday?"),
    ("scheduling", "recruiter", "Can we set up a quick call?"), ("scheduling", "recruiter", "Does Thursday 4pm work?"),
    ("scheduling", "recruiter", "Can you share your resume?"), ("scheduling", "recruiter", "What's the best way to reach you?"),
    ("who", "casual", "guess who this is 😄"), ("who", "recruiter", "I'm Priya from Zoho, hiring for an AI role"),
    ("sign_off", "casual", "ok bye"), ("sign_off", "recruiter", "Thanks Chandru, talk soon!"), ("sign_off", "casual", "good night"),
]


def main():
    done = set()
    if OUT.exists():
        done = {json.loads(l)["context"] for l in OUT.read_text().splitlines() if l.strip()}
    todo = [p for p in PROMPTS if p[2] not in done]
    print(f"{len(done)} answered, {len(todo)} to go. One bubble per line, empty line to finish.\n")
    with OUT.open("a", encoding="utf-8") as f:
        for i, (cat, persona, ctx) in enumerate(todo, 1):
            print(f"[{i}/{len(todo)}] ({persona}) visitor: {ctx}")
            bursts = []
            while True:
                line = input("  you: ").strip()
                if line in ("quit", "skip") or (not line and bursts):
                    break
                if line:
                    bursts.append(line)
            if line == "quit":
                break
            if bursts and line != "skip":
                f.write(json.dumps({"id": f"q-{len(done) + i:03d}", "category": cat, "persona": persona, "context": ctx,
                                    "bursts": bursts, "source": "questionnaire", "reviewed": True}, ensure_ascii=False) + "\n")
                f.flush()
    print(f"saved to {OUT}")


if __name__ == "__main__":
    sys.exit(main())
