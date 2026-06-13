import pytest
from app.tools import execute_native_tool
from app.orchestrator import AgentOrchestrator
from httpx import AsyncClient, Response, Request
from unittest.mock import AsyncMock, patch


def test_get_current_time():
    """Test that the native time tool returns a valid IST string."""
    result = execute_native_tool("get_current_time", {})
    assert result is not None
    assert "IST" in result
    assert "Current date and time" in result


def test_schedule_meeting():
    """Test that the meeting tool generates a valid Calendly link."""
    result = execute_native_tool("schedule_meeting", {"name": "John", "email": "john@test.com"})
    assert result is not None
    assert "calendly.com" in result
    assert "John" in result
    assert "john%40test.com" in result


def test_unknown_tool_returns_none():
    """Native executor returns None for unrecognized tools."""
    result = execute_native_tool("unknown_tool", {})
    assert result is None
