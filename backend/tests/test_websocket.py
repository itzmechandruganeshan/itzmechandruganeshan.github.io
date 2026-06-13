import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_health_endpoint(client):
    """Health endpoint returns expected JSON."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "active_websockets" in data


def test_websocket_chat(client, mocker):
    """
    Test the WebSocket endpoint: verifies the full message protocol
    (typing → chunks → idle → turn_complete).
    """
    async def mock_generator(session_id, user_message, history, conversation_summary=None, save_user_message=True):
        yield {"type": "message", "text": "Hey bro! Welcome to my portfolio"}

    mocker.patch(
        "app.websocket.orchestrator.generate_response",
        side_effect=mock_generator,
    )

    with client.websocket_connect("/ws/chat") as websocket:
        # Expect session ID first
        session_msg = websocket.receive_json()
        assert session_msg["type"] == "session_id"

        websocket.send_text("Hello")

        # Typing indicator
        typing_status = websocket.receive_json()
        assert typing_status == {"type": "status", "action": "typing"}

        # Single combined response chunk
        chunk1 = websocket.receive_json()
        assert chunk1["type"] == "message"
        assert chunk1["text"] == "Hey bro! Welcome to my portfolio"

        idle_status = websocket.receive_json()
        assert idle_status == {"type": "status", "action": "idle"}

        turn_complete = websocket.receive_json()
        assert turn_complete == {"type": "turn_complete"}

        websocket.close()
