"""
Native tool definitions and execution logic.
Tools are registered here and exposed to the LLM via OpenAI function-calling format.
"""

import logging
import urllib.parse
from datetime import datetime, timezone, timedelta

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tool definitions (OpenAI function-calling schema)
# ---------------------------------------------------------------------------

TOOL_DEFINITIONS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": (
                "Returns the current date and time in IST (Indian Standard Time). "
                "Use this whenever the user asks what time or date it is, or whenever "
                "you need to reference the current time to book a meeting."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "schedule_meeting",
            "description": (
                "Generates a Calendly scheduling link pre-filled with the user's name "
                "and email so a recruiter or collaborator can book a meeting with Chandru."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "The full name of the person wanting to book the meeting.",
                    },
                    "email": {
                        "type": "string",
                        "description": "The email address of the person wanting to book the meeting.",
                    },
                },
                "required": ["name", "email"],
            },
        },
    },
]


# ---------------------------------------------------------------------------
# Native tool executors (no external API needed)
# ---------------------------------------------------------------------------

def execute_native_tool(tool_name: str, arguments: dict) -> str | None:
    """
    Executes a locally-implemented tool.
    Returns the result string if handled, else None (indicating an external tool).
    """
    if tool_name == "get_current_time":
        ist = timezone(timedelta(hours=5, minutes=30))
        now = datetime.now(ist)
        return f"Current date and time in IST: {now.strftime('%A, %d %B %Y, %I:%M %p IST')}"

    if tool_name == "schedule_meeting":
        name = arguments.get("name", "")
        email = arguments.get("email", "")
        base_url = "https://calendly.com/chandruganeshan/30min"
        params = urllib.parse.urlencode({"name": name, "email": email})
        full_url = f"{base_url}?{params}"
        return (
            f"Meeting link generated successfully! "
            f"Tell the user: Here's your direct booking link → {full_url} "
            f"They can pick any slot that works for them. "
            f"This link is pre-filled with their name ({name}) and email ({email})."
        )

    return None


# ---------------------------------------------------------------------------
# External tool executor (Composio MCP)
# ---------------------------------------------------------------------------

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError)),
    reraise=True,
)
async def _execute_mcp_with_retry(
    tool_name: str, arguments: dict, client: httpx.AsyncClient
) -> str:
    """Executes a Composio MCP action with exponential backoff."""
    logger.info(f"Executing MCP tool: {tool_name} (Args: {arguments})")
    headers = {
        "Authorization": f"Bearer {settings.composio_api_key}",
        "Content-Type": "application/json",
    }
    response = await client.post(
        "https://backend.composio.dev/api/v1/actions/execute",
        headers=headers,
        json={"action": tool_name, "params": arguments},
        timeout=30.0,
    )
    response.raise_for_status()
    return response.text


async def execute_mcp_tool(tool_name: str, arguments: dict) -> str:
    """Public wrapper for Composio tool execution with retries."""
    try:
        async with httpx.AsyncClient() as client:
            return await _execute_mcp_with_retry(tool_name, arguments, client)
    except Exception as e:
        logger.error(f"Tool execution failed after retries for {tool_name}: {e}")
        return f"Error: Tool execution failed - {str(e)}"
