import json
import logging
import asyncio
from typing import AsyncGenerator, Dict

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
MIN_BACKOFF = 2
MAX_BACKOFF = 10


class LLMProvider:
    """Manages streaming interactions with the OpenRouter API including tool calling."""

    def __init__(self):
        self.api_key = settings.openrouter_api_key

    async def generate_stream(
        self, messages: list[dict], tools: list[dict]
    ) -> AsyncGenerator[dict, None]:
        """
        Streams an LLM completion from OpenRouter.
        Yields dicts: {"type": "chunk", "text": ...} during generation,
        and {"type": "done", "text": ..., "tools": [...]} at the end.
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/chandruganeshan",
            "X-Title": "PortfolioBot",
        }

        payload = {
            "model": "stepfun/step-3.5-flash:free",
            "messages": messages,
            "stream": False,
            "max_tokens": 1000,
            "tools": tools,
            "tool_choice": "auto",
            "temperature": 0.4,
            "top_p": 0.9,
            "frequency_penalty": 0.5,
            "presence_penalty": 0.3,
        }

        async with httpx.AsyncClient(verify=False) as client:
            retries = 0
            success = False

            while retries < MAX_RETRIES and not success:
                try:
                    response = await client.post(
                        "https://openrouter.ai/api/v1/chat/completions",
                        headers=headers,
                        json=payload,
                        timeout=60.0,
                    )
                    
                    if response.status_code != 200:
                        err_text = response.text
                        try:
                            err_data = response.json()
                            if "error" in err_data:
                                err_text = str(err_data["error"])
                        except json.JSONDecodeError:
                            pass
                        raise httpx.HTTPStatusError(f"HTTP {response.status_code}: {err_text}", request=response.request, response=response)

                    data = response.json()
                    if "choices" not in data or len(data["choices"]) == 0:
                        raise httpx.RequestError("Empty choices from OpenRouter.")

                    message_data = data["choices"][0].get("message", {})
                    content = message_data.get("content") or ""
                    
                    # Convert newlines to split markers like the streaming version did
                    content = content.replace("\n", "|split|").replace("\r", "")
                    
                    # Tool calls format out from standard API
                    tools_out = []
                    if "tool_calls" in message_data:
                        tools_out = message_data["tool_calls"]
                        
                    yield {"type": "done", "text": content, "tools": tools_out}
                    success = True

                except (httpx.RequestError, httpx.HTTPStatusError, asyncio.TimeoutError) as e:
                    retries += 1
                    if retries >= MAX_RETRIES:
                        logger.error(f"OpenRouter API failed after {MAX_RETRIES} retries: {e}")
                        error_msg = "Bro, the API is super congested right now. Give me a sec to spin up another cluster...|split|"
                        yield {"type": "done", "text": error_msg, "tools": []}
                        return

                    wait_time = min(MAX_BACKOFF, MIN_BACKOFF * (2 ** (retries - 1)))
                    logger.warning(f"OpenRouter request failed. Retry {retries}/{MAX_RETRIES} in {wait_time}s")
                    await asyncio.sleep(wait_time)

                except asyncio.CancelledError:
                    logger.warning("LLM request cancelled. Cleaning up.")
                    raise

                except Exception as e:
                    logger.error(f"Unexpected LLM error: {e}")
                    error_msg = f"My brain crashed bro. My bad. Error log: {e}|split|"
                    yield {"type": "done", "text": error_msg, "tools": []}
                    return


provider = LLMProvider()
