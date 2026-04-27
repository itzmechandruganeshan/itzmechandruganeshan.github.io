"""
Agent orchestrator — manages the ReAct loop, LLM streaming, and tool dispatch.
"""

import os
import logging
import asyncio
import json
import random
from typing import AsyncGenerator, Dict

import aiosqlite
import httpx

from app.config import settings
from app.database import DB_FILE
from app.session import SessionService
from app.llm import provider as llm_provider
from app.tools import TOOL_DEFINITIONS, execute_native_tool, execute_mcp_tool

logger = logging.getLogger(__name__)

MAX_USER_MESSAGE_LENGTH = 8000
PROMPT_PATH = os.path.join(os.path.dirname(__file__), "prompts", "system.txt")


class AgentOrchestrator:
    """Manages the ReAct loop with streaming, tool calling, and humanizer effects."""

    def __init__(self):
        self._system_prompt: str | None = None

    def _load_system_prompt(self) -> str:
        """Loads and caches the system prompt from disk."""
        if self._system_prompt is None:
            try:
                with open(PROMPT_PATH, "r", encoding="utf-8") as f:
                    self._system_prompt = f.read()
            except Exception as e:
                logger.error(f"Failed to read system prompt: {e}")
                self._system_prompt = "You are Chandru, a 25-year-old AI/ML Engineer from Coimbatore."
        return self._system_prompt

    @staticmethod
    def _simulate_typo(text: str) -> tuple[str, str | None]:
        """
        5% chance to introduce a human-like typo (letter swap) in a word > 5 chars.
        Returns (possibly_modified_text, correction_or_None).
        """
        if len(text) < 15 or random.random() > 0.05:
            return text, None

        words = text.split()
        for i, word in enumerate(words):
            if len(word) > 5 and word.isalpha():
                typo_word = word[:2] + word[3] + word[2] + word[4:]
                words[i] = typo_word
                return " ".join(words), f"*{word.lower()}"

        return text, None

    async def generate_response(
        self,
        session_id: str,
        user_message: str,
        history: list[dict],
        conversation_summary: str | None = None,
    ) -> AsyncGenerator[str, None]:
        """
        Core async generator: streams humanized LLM output with ReAct tool calling.
        Hardened against prompt injection, LLM dropouts, and cancelled tasks.
        """
        if len(user_message) > MAX_USER_MESSAGE_LENGTH:
            logger.warning(f"Session {session_id}: message truncated ({len(user_message)} chars)")
            user_message = user_message[:MAX_USER_MESSAGE_LENGTH]

        await SessionService.save_message(session_id, "user", user_message)

        system_prompt = self._load_system_prompt()
        messages = [{"role": "system", "content": system_prompt}]
        
        if conversation_summary:
            try:
                summary_data = json.loads(conversation_summary)
                topics = ", ".join(summary_data.get("topics_discussed", []))
                intent = ", ".join(summary_data.get("intent_patterns", []))
                if topics or intent:
                    context_msg = (
                        f"Context: This is a returning user.\n"
                        f"Previous topics discussed: {topics}\n"
                        f"Previous intent patterns: {intent}\n"
                        f"Acknowledge them casually if appropriate, but don't force it."
                    )
                    messages.append({"role": "system", "content": context_msg})
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse conversation summary for session {session_id[:8]}")
                
        messages.extend(history)
        messages.append({"role": "user", "content": user_message})

        full_assistant_reply = ""

        for iteration in range(1, 6):
            logger.info(f"ReAct iteration {iteration} for session {session_id[:8]}")

            tool_calls_buffer: Dict[int, dict] = {}

            try:
                async for item in llm_provider.generate_stream(messages, TOOL_DEFINITIONS):
                    if item["type"] == "done":
                        full_assistant_reply += item.get("text", "")
                        tool_calls_buffer = {
                            idx: call for idx, call in enumerate(item.get("tools", []))
                        }
                        
                        text = item.get("text", "")
                        if text:
                            bursts = [t.strip() for t in text.split("|split|") if t.strip()]
                            final_parts = []
                            for i, burst in enumerate(bursts):
                                typo_text, correction = self._simulate_typo(burst)
                                final_parts.append(typo_text)
                                if correction:
                                    final_parts.append(correction)
                                    
                            yield {"type": "message", "text": " |split| ".join(final_parts)}

            except asyncio.CancelledError:
                logger.warning(f"Session {session_id[:8]} cancelled during generation.")
                raise
            except Exception as e:
                logger.error(f"Orchestrator error: {e}")
                yield {"type": "message", "text": f"My brain crashed bro. My bad. Error log: {e}"}
                return

            # Dispatch tool calls if any
            if tool_calls_buffer:
                logger.info(f"Dispatching {len(tool_calls_buffer)} tool call(s)")
                messages.append({
                    "role": "assistant",
                    "content": None,
                    "tool_calls": list(tool_calls_buffer.values()),
                })

                for tool_call in tool_calls_buffer.values():
                    func_name = tool_call["function"]["name"]
                    try:
                        args = json.loads(tool_call["function"]["arguments"])
                    except json.JSONDecodeError:
                        args = {}

                    result = execute_native_tool(func_name, args)
                    if result is None:
                        result = await execute_mcp_tool(func_name, args)

                    logger.info(f"Tool '{func_name}' → {result[:100]}...")
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "name": func_name,
                        "content": result,
                    })
                continue
            else:
                break

        if full_assistant_reply:
            await SessionService.save_message(session_id, "assistant", full_assistant_reply)

    async def summarize_session(self, session_id_str: str):
        """Background task to summarize recent conversation on disconnect."""
        try:
            async with aiosqlite.connect(DB_FILE, timeout=15.0) as db:
                cursor = await db.execute(
                    "SELECT id, conversation_summary FROM session WHERE session_id = ?",
                    (session_id_str,),
                )
                row = await cursor.fetchone()
                if not row:
                    return

                internal_id, _ = row

                hist_cur = await db.execute(
                    """
                    SELECT role, content FROM message
                    WHERE session_id = ? AND role = 'user'
                    ORDER BY created_at DESC LIMIT 10
                    """,
                    (internal_id,),
                )
                rows = await hist_cur.fetchall()
                if not rows:
                    return

                chat_text = "\n".join(r[1] for r in reversed(rows))

                prompt = (
                    "Summarize the user's intent and topics discussed based on these recent messages.\n"
                    "Return ONLY a JSON object with two keys: 'topics_discussed' (list of strings) "
                    "and 'intent_patterns' (list of strings).\n\n"
                    f"Messages:\n{chat_text}"
                )

                async with httpx.AsyncClient() as client:
                    resp = await client.post(
                        "https://openrouter.ai/api/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {settings.openrouter_api_key}",
                            "Content-Type": "application/json",
                            "HTTP-Referer": "https://github.com/chandruganeshan",
                            "X-Title": "Portfolio Agent",
                        },
                        json={
                            "model": "stepfun/step-3.5-flash:free",
                            "messages": [{"role": "user", "content": prompt}],
                        },
                        timeout=30.0,
                    )
                    resp.raise_for_status()
                    summary_json = resp.json()["choices"][0]["message"]["content"]

                    await db.execute(
                        "UPDATE session SET conversation_summary = ? WHERE session_id = ?",
                        (summary_json, session_id_str),
                    )
                    await db.commit()
                    logger.info(f"Summarized session {session_id_str[:8]}")

        except Exception as e:
            logger.error(f"Failed to summarize session {session_id_str[:8]}: {e}")


orchestrator = AgentOrchestrator()
