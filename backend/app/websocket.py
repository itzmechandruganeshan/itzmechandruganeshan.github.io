"""
WebSocket transport layer — connection management and real-time chat endpoint.
"""

import logging
import random
import asyncio
import traceback
from typing import Dict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.session import SessionService
from app.orchestrator import orchestrator

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Connection Manager
# ---------------------------------------------------------------------------

class ConnectionManager:
    """Manages active WebSocket connections with graceful lifecycle control."""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.active_tasks: Dict[str, set[asyncio.Task]] = {}
        self._lock = asyncio.Lock()

    async def disconnect(self, session_id: str):
        """Removes a connection and cancels any running tasks for this session."""
        async with self._lock:
            self.active_connections.pop(session_id, None)

            if session_id in self.active_tasks:
                for task in self.active_tasks.pop(session_id):
                    if not task.done():
                        logger.warning(f"Cancelling orphaned task for {session_id[:8]}")
                        task.cancel()

        logger.info(f"Session {session_id[:8]} disconnected & cleaned up.")

    async def send_json(self, data: dict, session_id: str):
        """Sends a JSON message to a specific session."""
        ws = self.active_connections.get(session_id)
        if ws:
            try:
                await ws.send_json(data)
            except WebSocketDisconnect:
                await self.disconnect(session_id)
            except Exception as e:
                logger.error(f"Error sending JSON to {session_id[:8]}: {e}")
                await self.disconnect(session_id)


manager = ConnectionManager()

IDLE_NUDGE_MESSAGES = [
    "Anyway, take your time looking around! Let me know if you want to see my GitHub.",
    "You still there man? Feel free to ask if you need anything specific.",
    "Just chilling here. Let me know if you wanna chat.",
    "Brb, grabbing a coffee... Drop a message if you need something when I'm back.",
    "All good? Feel free to poke around the site.",
    "Ugh, zoning out a bit here lol. What's up?",
    "Let me know if you're stuck or just exploring!",
]

# ---------------------------------------------------------------------------
# WebSocket Endpoint
# ---------------------------------------------------------------------------

@router.websocket("/ws/chat")
async def websocket_chat_endpoint(websocket: WebSocket):
    """
    Real-time agentic chat over WebSocket.
    Handles session resume, streaming responses, tool calling, and idle nudges.
    """
    await websocket.accept()

    # Get session ID from query params
    client_session_id = websocket.query_params.get("session_id")

    # Resume or create session
    session_id, history, conversation_summary = await SessionService.get_or_create_session(client_session_id)
    is_returning = len(history) > 0

    # Register connection
    async with manager._lock:
        manager.active_connections[session_id] = websocket
        if session_id not in manager.active_tasks:
            manager.active_tasks[session_id] = set()

    logger.info(f"Session {session_id[:8]} connected. Active: {len(manager.active_connections)}")
    
    # Send the session ID back to the client so they can save it
    await websocket.send_json({"type": "session_id", "session_id": session_id})

    if is_returning:
        try:
            await websocket.send_json({"type": "status", "action": "typing"})
            full_response = ""
            prompt = "System: The user just returned to the chat. Greet them casually, acknowledging they are back (e.g. 'Hey hi, glad that you are returning back'). Keep it short, 1 or 2 sentences."
            
            async for item in orchestrator.generate_response(session_id, prompt):
                if item.get("type") == "control":
                    await websocket.send_json({"type": "status", "action": item.get("action")})
                elif item.get("type") == "chunk":
                    msg_text = item.get("text", "")
                    full_response += msg_text
                    await websocket.send_json({"type": "message", "text": msg_text})
                elif item.get("type") == "message":
                    msg_text = item.get("text", "")
                    full_response += msg_text + " "
                    await websocket.send_json({"type": "message", "text": msg_text})
            
            if full_response.strip():
                history.append({"role": "assistant", "content": full_response.strip()})

            await websocket.send_json({"type": "status", "action": "idle"})
            await websocket.send_json({"type": "turn_complete"})
        except Exception as e:
            logger.error(f"Welcome back error for {session_id[:8]}: {e}")

    try:
        while True:
            # Wait for user message with 60s idle timeout
            try:
                user_message = await asyncio.wait_for(
                    websocket.receive_text(), timeout=60.0
                )
            except asyncio.TimeoutError:
                if len(history) >= 2:
                    nudge = random.choice(IDLE_NUDGE_MESSAGES)
                    await websocket.send_text(nudge)
                    history.append({"role": "assistant", "content": nudge})
                continue

            logger.info(f"Message from {session_id[:8]}: {user_message[:50]}...")

            try:
                await websocket.send_json({"type": "status", "action": "typing"})

                full_response = ""
                async for item in orchestrator.generate_response(session_id, user_message):
                    if item.get("type") == "control":
                        await websocket.send_json({"type": "status", "action": item.get("action")})
                    elif item.get("type") == "chunk":
                        msg_text = item.get("text", "")
                        full_response += msg_text
                        await websocket.send_json({"type": "message", "text": msg_text})
                    elif item.get("type") == "message":
                        msg_text = item.get("text", "")
                        full_response += msg_text + " "
                        await websocket.send_json({"type": "message", "text": msg_text})
                    elif item.get("type") == "ui_component":
                        # Forward the UI component event directly to the frontend
                        await websocket.send_json(item)

                history.append({"role": "user", "content": user_message})
                if full_response.strip():
                    history.append({"role": "assistant", "content": full_response.strip()})

                await websocket.send_json({"type": "status", "action": "idle"})
                await websocket.send_json({"type": "turn_complete"})

            except Exception as e:
                traceback.print_exc()
                logger.error(f"Orchestrator error for {session_id[:8]}: {e}")
                await manager.send_json(
                    {"error": "I encountered a logical paradox. Rebooting personality...|split|"},
                    session_id,
                )

    except WebSocketDisconnect:
        logger.info(f"Session {session_id[:8]} disconnected.")
        await manager.disconnect(session_id)

    except Exception as e:
        logger.error(f"WebSocket error for {session_id[:8]}: {e}")
        await manager.disconnect(session_id)
