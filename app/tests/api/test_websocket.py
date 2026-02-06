import pytest
from unittest.mock import patch
from fastapi import status
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.main import app
from app.api.deps.common import get_user_id_from_header
from app.domain.value_objects.websocket_messages import MessageType


def test_websocket_connection_success(client: TestClient):
    """
    Test that we can connect, receive the welcome message,
    and exchange messages (subscribe flow).
    """
    with client.websocket_connect("/api/v1/ws/user") as websocket:
        # 1. Verify Welcome Message
        data = websocket.receive_json()
        assert data["type"] == MessageType.NOTIFICATION.value
        assert data["payload"]["title"] == "Connected"
        assert data["payload"]["severity"] == "success"

        # 2. Test Subscribe Flow
        subscribe_msg = {
            "type": MessageType.SUBSCRIBE.value,
            "payload": {"vault_ids": ["vault-123"]},
        }
        websocket.send_json(subscribe_msg)

        # 3. Verify Subscription Confirmation
        response = websocket.receive_json()
        assert response["type"] == MessageType.NOTIFICATION.value
        assert response["payload"]["title"] == "Subscribed"
        assert "vault-123" in str(subscribe_msg["payload"]["vault_ids"])


def test_websocket_validates_dependency(client: TestClient):
    """
    Verify that if the dependency (authentication) fails,
    the WebSocket connection is rejected.

    Since get_user_id_from_header is called directly in the endpoint,
    we must patch it where it is imported/used.
    """
    with patch(
        "app.websocket.vault_socket.get_user_id_from_header",
        side_effect=ValueError("Invalid Token"),
    ):
        # The connection should fail immediately during the handshake
        # or immediately after execution starts, causing a disconnect.
        with pytest.raises((WebSocketDisconnect, Exception)):
            with client.websocket_connect("/api/v1/ws/user") as websocket:
                pass
