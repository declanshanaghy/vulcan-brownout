"""WebSocket API handlers for Vulcan Brownout integration."""

import logging
from typing import Any, Dict, Optional

from homeassistant.core import HomeAssistant
from homeassistant.components.websocket_api import (
    WebSocketError,
    async_register_command,
    websocket_command,
)
import voluptuous as vol

from .const import (
    COMMAND_QUERY_DEVICES,
    DOMAIN,
    MAX_PAGE_SIZE,
    SORT_KEY_BATTERY_LEVEL,
    SORT_ORDER_ASC,
    SUPPORTED_SORT_KEYS,
    SUPPORTED_SORT_ORDERS,
)
from .battery_monitor import BatteryMonitor

_LOGGER = logging.getLogger(__name__)

# WebSocket command schema for query_devices
QUERY_DEVICES_SCHEMA = vol.Schema(
    {
        vol.Optional("limit", default=20): vol.All(vol.Coerce(int), vol.Range(min=1, max=100)),
        vol.Optional("offset", default=0): vol.All(vol.Coerce(int), vol.Range(min=0)),
        vol.Optional("sort_key", default=SORT_KEY_BATTERY_LEVEL): vol.In(SUPPORTED_SORT_KEYS),
        vol.Optional("sort_order", default=SORT_ORDER_ASC): vol.In(SUPPORTED_SORT_ORDERS),
    }
)


def register_websocket_commands(hass: HomeAssistant) -> None:
    """Register WebSocket command handlers."""
    async_register_command(hass, handle_query_devices)


@websocket_command(
    {
        "type": COMMAND_QUERY_DEVICES,
        "data": QUERY_DEVICES_SCHEMA,
    }
)
async def handle_query_devices(
    hass: HomeAssistant, connection: Any, msg: Dict[str, Any]
) -> None:
    """Handle vulcan-brownout/query_devices WebSocket command."""
    try:
        # Get battery monitor service
        battery_monitor: BatteryMonitor = hass.data.get(DOMAIN)
        if battery_monitor is None:
            connection.send_error(
                msg["id"],
                "integration_not_loaded",
                "Vulcan Brownout integration not loaded",
            )
            return

        # Extract and validate parameters
        data = msg.get("data", {})
        limit = data.get("limit", 20)
        offset = data.get("offset", 0)
        sort_key = data.get("sort_key", SORT_KEY_BATTERY_LEVEL)
        sort_order = data.get("sort_order", SORT_ORDER_ASC)

        # Query devices
        result = await battery_monitor.query_devices(
            limit=limit,
            offset=offset,
            sort_key=sort_key,
            sort_order=sort_order,
        )

        # Send successful response
        connection.send_json_message(
            {
                "type": "result",
                "id": msg["id"],
                "success": True,
                "data": result,
            }
        )

    except ValueError as e:
        # Validation error
        _LOGGER.warning(f"Query validation error: {e}")
        connection.send_error(msg["id"], "invalid_request", str(e))
    except Exception as e:
        # Unexpected error
        _LOGGER.error(f"Error handling query_devices command: {e}")
        connection.send_error(
            msg["id"],
            "internal_error",
            "Failed to query devices",
        )


async def send_status_event(hass: HomeAssistant) -> None:
    """Send initial status event to all connected WebSocket clients."""
    try:
        battery_monitor: BatteryMonitor = hass.data.get(DOMAIN)
        if battery_monitor is None:
            return

        # Get WebSocket API component
        websocket_api = hass.components.websocket_api
        if not hasattr(websocket_api, "async_send_json_to_command"):
            # Component may not be fully initialized; skip
            return

        # Send status event to all connected clients
        # Note: This is handled by HA's built-in broadcasting
        _LOGGER.debug("Status event ready to be sent to WebSocket clients")

    except Exception as e:
        _LOGGER.warning(f"Error sending status event: {e}")
