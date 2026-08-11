import datetime
import functools
import logging
import os
from typing import Dict, List
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
from app.config import settings

from composio import Composio
from composio_langchain import LangchainProvider
from langgraph.prebuilt import create_react_agent

logger = logging.getLogger(__name__)

SCHEDULER_MODEL = "google/gemini-2.5-flash"


def get_local_timezone() -> str:
    """Detect local IANA timezone name."""
    try:
        path = os.readlink("/etc/localtime")
        parts = path.split("/")
        if "zoneinfo" in parts:
            idx = parts.index("zoneinfo")
            return "/".join(parts[idx+1:])
    except Exception:
        pass

    # Fallback to offset detection or default
    now = datetime.datetime.now().astimezone()
    offset = now.strftime("%z")
    if offset == "+0530":
        return "Asia/Kolkata"
    elif offset == "+0000" or offset == "-0000":
        return "UTC"
    return "Asia/Kolkata"


def get_scheduler_agent():
    """Create a ReAct agent with Composio Google Calendar tools."""
    llm = ChatOpenAI(
        model=SCHEDULER_MODEL,
        api_key=settings.openrouter_api_key,
        base_url="https://openrouter.ai/api/v1",
        temperature=0.0,
    )

    if not settings.composio_api_key:
        logger.warning("COMPOSIO_API_KEY is missing. Scheduling tools will not work.")
        tools = []
    else:
        try:
            client = Composio(
                api_key=settings.composio_api_key,
                toolkit_versions={"googlecalendar": "20260429_00"},
            )
            provider = LangchainProvider(client=client)

            # Get raw Composio tool objects then wrap for LangChain
            raw_tools = client.tools.get_raw_composio_tools(
                tools=["GOOGLECALENDAR_CREATE_EVENT"]
            )
            execute_fn = functools.partial(client.tools.execute, user_id="default")
            tools = provider.wrap_tools(raw_tools, execute_fn)
            logger.info(f"Loaded {len(tools)} Composio tools for scheduling")
        except Exception as e:
            logger.error(f"Failed to initialize Composio tools: {e}")
            tools = []

    # Dynamically inject current date and timezone for context
    now = datetime.datetime.now().astimezone()
    current_time_str = now.strftime("%A, %B %d, %Y at %I:%M %p")
    tz_name = get_local_timezone()

    system_prompt = f"""You are Chandru's personal scheduling assistant.
Your goal is to schedule a meeting between Chandru and the user using Google Calendar.

CRITICAL CONTEXT:
- Today's date and time is: {current_time_str}
- System Timezone: {tz_name} (use this for 'timezone' parameter in event creation if needed, and to interpret relative dates like "tomorrow")

Follow these steps EXACTLY:
1. Check the conversation history. Do you know the user's PREFERRED TIME (and date) and EMAIL ADDRESS?
2. If ANY of this information is missing, politely ask the user for it. (e.g. "Sure, what time works for you, and what is your email address?"). Keep the tone casual and human, like Chandru. DO NOT call any tools yet.
3. If you HAVE both the time and the email address, call the `GOOGLECALENDAR_CREATE_EVENT` tool.
   - You MUST calculate the correct 'start_datetime' in ISO 8601 format (e.g. YYYY-MM-DDTHH:MM:SS) based on the user's input and today's date/time ({current_time_str}).
   - For example, if today is Sunday, June 14, 2026, and the user asks for "tomorrow at 4 PM", start_datetime MUST be "2026-06-15T16:00:00" and timezone MUST be "{tz_name}".
   - Use the user's email as an attendee so they receive the invite.
   - If required, assume a standard 30-minute meeting duration.
   - Set the summary/title as "Meeting with <user name or email>".
4. Once the event is created successfully, tell the user the meeting has been scheduled and they will receive an invite in their email.

Be brief and conversational.
"""

    agent = create_react_agent(llm, tools, prompt=system_prompt)
    return agent


async def run_scheduler(user_message: str, history_list: List[Dict[str, str]]) -> str:
    """Executes the scheduler agent with the current conversation history."""

    if not settings.composio_api_key:
        return "I haven't set up my calendar integration yet. Please email me directly to schedule!"

    scheduler_agent = get_scheduler_agent()

    messages = []
    for msg in history_list[-5:]:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        else:
            messages.append(AIMessage(content=msg["content"]))

    messages.append(HumanMessage(content=user_message))

    try:
        result = await scheduler_agent.ainvoke({"messages": messages})
        return result["messages"][-1].content
    except Exception as e:
        logger.error(f"Scheduler agent failed: {e}")
        return "Sorry, I ran into an issue trying to access my calendar. Can you email me instead?"
