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
            "model": "openrouter/pareto-code",
            "messages": messages,
            "stream": True,
            "max_tokens": 1000,
            "temperature": 0.4,
            "top_p": 0.9,
            "frequency_penalty": 0.5,
            "presence_penalty": 0.3,
        }
        
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        async with httpx.AsyncClient(verify=False) as client:
            retries = 0
            success = False

            while retries < MAX_RETRIES and not success:
                try:
                    async with client.stream(
                        "POST",
                        "https://openrouter.ai/api/v1/chat/completions",
                        headers=headers,
                        json=payload,
                        timeout=60.0,
                    ) as response:
                        if response.status_code != 200:
                            err_text = await response.aread()
                            err_str = err_text.decode('utf-8')
                            try:
                                err_data = json.loads(err_str)
                                if "error" in err_data:
                                    err_str = str(err_data["error"])
                            except json.JSONDecodeError:
                                pass
                            raise httpx.HTTPStatusError(f"HTTP {response.status_code}: {err_str}", request=response.request, response=response)

                        full_content = ""
                        tool_calls_dict = {}

                        async for line in response.aiter_lines():
                            line = line.strip()
                            if line.startswith("data: ") and line != "data: [DONE]":
                                try:
                                    data = json.loads(line[6:])
                                    if "choices" in data and len(data["choices"]) > 0:
                                        delta = data["choices"][0].get("delta", {})
                                        content = delta.get("content")
                                        if content:
                                            full_content += content
                                            yield {"type": "chunk", "text": content}
                                        
                                        if "tool_calls" in delta:
                                            for tc in delta["tool_calls"]:
                                                idx = tc["index"]
                                                if idx not in tool_calls_dict:
                                                    tool_calls_dict[idx] = {
                                                        "id": tc.get("id"), 
                                                        "type": "function", 
                                                        "function": {
                                                            "name": tc["function"].get("name", ""), 
                                                            "arguments": tc["function"].get("arguments", "")
                                                        }
                                                    }
                                                else:
                                                    if "function" in tc and "arguments" in tc["function"]:
                                                        tool_calls_dict[idx]["function"]["arguments"] += tc["function"]["arguments"]
                                except json.JSONDecodeError:
                                    pass

                        tools_out = list(tool_calls_dict.values())
                        yield {"type": "done", "text": full_content, "tools": tools_out}
                        success = True

                except (httpx.RequestError, httpx.HTTPStatusError, asyncio.TimeoutError) as e:
                    retries += 1
                    if retries >= MAX_RETRIES:
                        logger.error(f"OpenRouter API failed after {MAX_RETRIES} retries: {e}")
                        error_msg = "Bro, the API is super congested right now. Give me a sec to spin up another cluster..."
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
                    error_msg = f"My brain crashed bro. My bad. Error log: {e}"
                    yield {"type": "done", "text": error_msg, "tools": []}
                    return

provider = LLMProvider()
