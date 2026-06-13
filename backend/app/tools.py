"""
Native tool definitions and execution logic.
Tools are registered here and exposed to the LLM via OpenAI function-calling format.
"""

import logging
import urllib.parse
from datetime import datetime, timezone, timedelta

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
