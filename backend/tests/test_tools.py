import pytest
from app.tools import execute_native_tool, execute_mcp_tool
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


@pytest.fixture
def orchestrator():
    return AgentOrchestrator()


@pytest.mark.asyncio
async def test_mcp_call_success(orchestrator):
    """Test successful MCP tool execution with mocked httpx."""
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_response = AsyncMock(spec=Response)
        mock_response.raise_for_status.return_value = None
        mock_response.text = "Success!"
        mock_post.return_value = mock_response

        result = await execute_mcp_tool("TEST_TOOL", {"key": "value"})

        assert result == "Success!"
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "https://backend.composio.dev/api/v1/actions/execute"
        assert call_args[1]["json"]["action"] == "TEST_TOOL"
