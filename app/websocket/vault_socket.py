# app/websocket/vault_socket.py
"""
WebSocket endpoints for SmartVault real-time communication.

Endpoints:
1. /ws/user - User clients (web app, mobile)
2. /ws/vault - Vault devices (ESP32)
"""

import json
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query, status
from fastapi.exceptions import WebSocketException

from app.infrastructure.messaging.websocket_manager import manager
from app.domain.value_objects.websocket_messages import MessageType
from app.application.use_cases.process_vault_state_update import ProcessVaultStateUpdate
from app.application.ports.vault_repository import VaultRepository
from app.api.deps.vaults import get_vault_repo
from app.api.deps.common import get_user_id_from_header

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================
# User WebSocket Endpoint
# ============================================

@router.websocket("/ws/user")
async def websocket_user_endpoint(
    websocket: WebSocket,
    token: str | None = Query(None, description="JWT access token (optional)"),
    repo: VaultRepository = Depends(get_vault_repo),
):
    """
    WebSocket endpoint for user clients (web app, mobile app).
    
    Clients can:
    - Subscribe to vault updates
    - Receive real-time status changes
    - Receive notifications
    
    Authentication: JWT token in query parameter
    """
    
    # Dummy auth for now (backward compatible)
    user_id = get_user_id_from_header()
    
    # Connect
    await manager.connect_user(websocket, user_id)
    
    try:
        # Send welcome message
        await websocket.send_json({
            "type": MessageType.NOTIFICATION.value,
            "payload": {
                "title": "Connected",
                "message": "WebSocket connection established",
                "severity": "success",
            },
        })
        
        # Message handling loop
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                message_type = message.get("type")
                payload = message.get("payload", {})
                
                logger.debug(f"User {user_id} sent: {message_type}")
                
                # Route message by type
                if message_type == MessageType.SUBSCRIBE.value:
                    # Client wants to subscribe to vault updates
                    vault_ids = payload.get("vault_ids", [])
                    
                    if not vault_ids:
                        # Subscribe to all vaults owned by user
                        # TODO: Fetch user's vaults from repository
                        logger.warning("Subscribe to all vaults not implemented yet")
                    else:
                        for vault_id in vault_ids:
                            # TODO: Verify user owns or has access to vault
                            manager.subscribe_to_vault(user_id, vault_id)
                    
                    await websocket.send_json({
                        "type": MessageType.NOTIFICATION.value,
                        "payload": {
                            "title": "Subscribed",
                            "message": f"Subscribed to {len(vault_ids)} vaults",
                            "severity": "info",
                        },
                    })
                
                elif message_type == MessageType.UNSUBSCRIBE.value:
                    vault_ids = payload.get("vault_ids", [])
                    for vault_id in vault_ids:
                        manager.unsubscribe_from_vault(user_id, vault_id)
                    
                    await websocket.send_json({
                        "type": MessageType.NOTIFICATION.value,
                        "payload": {
                            "title": "Unsubscribed",
                            "message": f"Unsubscribed from {len(vault_ids)} vaults",
                            "severity": "info",
                        },
                    })
                
                else:
                    logger.warning(f"Unknown message type from user {user_id}: {message_type}")
                    await websocket.send_json({
                        "type": MessageType.ERROR.value,
                        "payload": {
                            "error_code": "UNKNOWN_MESSAGE_TYPE",
                            "message": f"Unknown message type: {message_type}",
                        },
                    })
            
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON from user {user_id}")
                await websocket.send_json({
                    "type": MessageType.ERROR.value,
                    "payload": {
                        "error_code": "INVALID_JSON",
                        "message": "Message must be valid JSON",
                    },
                })
            
            except Exception as e:
                logger.error(f"Error processing message from user {user_id}: {e}")
    
    except WebSocketDisconnect:
        logger.info(f"User {user_id} disconnected")
    
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
    
    finally:
        manager.disconnect_user(websocket, user_id)


# ============================================
# Vault Device WebSocket Endpoint
# ============================================

@router.websocket("/ws/vault")
async def websocket_vault_endpoint(
    websocket: WebSocket,
    hardware_uuid: str = Query(..., description="Vault hardware UUID"),
    vault_secret: str = Query(..., description="Pre-shared vault secret"),
    repo: VaultRepository = Depends(get_vault_repo),
):
    """
    WebSocket endpoint for vault devices (ESP32 hardware).
    
    Devices can:
    - Receive unlock/lock commands
    - Send state updates
    - Send heartbeats
    - Report tamper events
    
    Authentication: Hardware UUID + pre-shared secret
    """
    
    raise WebSocketException(
        code=status.WS_1008_POLICY_VIOLATION,
        reason="Vault device websocket not wired yet",
    )


# ============================================
# Management/Monitoring Endpoints (HTTP)
# ============================================

@router.get("/ws/stats")
async def get_websocket_stats():
    """Get WebSocket connection statistics (admin/monitoring)"""
    return manager.get_connection_stats()


@router.get("/ws/vaults/online")
async def get_online_vaults():
    """Get list of currently online vaults"""
    return {
        "online_vaults": manager.get_online_vaults(),
        "count": len(manager.get_online_vaults()),
    }
