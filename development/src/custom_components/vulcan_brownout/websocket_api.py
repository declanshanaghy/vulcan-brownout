"""WebSocket API handlers for Vulcan Brownout integration."""

import logging
import uuid
from typing import Any, Dict

from homeassistant.core import HomeAssistant
from homeassistant.components import websocket_api
import voluptuous as vol

from .const import COMMAND_QUERY_ENTITIES, COMMAND_SUBSCRIBE, DOMAIN
from .battery_monitor import BatteryMonitor
from .subscription_manager import WebSocketSubscriptionManager

_LOGGER = logging.getLogger(__name__)


def register_websocket_commands(hass: HomeAssistant) -> None:
    """Register WebSocket command handlers."""
    websocket_api.async_register_command(hass, handle_query_entities)
    websocket_api.async_register_command(hass, handle_subscribe)


@websocket_api.websocket_command(
    {vol.Required("type"): COMMAND_QUERY_ENTITIES}
)
@websocket_api.async_response
async def handle_query_entities(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: Dict[str, Any],
) -> None:
    """Handle vulcan-brownout/query_entities — no parameters."""
    try:
        battery_monitor: BatteryMonitor = hass.data.get(DOMAIN)
        if battery_monitor is None:
            connection.send_error(
                msg["id"],
                "integration_not_loaded",
                "Vulcan Brownout integration not loaded",
            )
            return

        result = await battery_monitor.query_entities()
        connection.send_result(msg["id"], result)

    except Exception as e:
        _LOGGER.error("Error handling query_entities command: %s", e)
        connection.send_error(
            msg["id"], "internal_error", "Failed to query entities"
        )


@websocket_api.websocket_command(
    {vol.Required("type"): COMMAND_SUBSCRIBE}
)
@websocket_api.async_response
async def handle_subscribe(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: Dict[str, Any],
) -> None:
    """Handle vulcan-brownout/subscribe."""
    try:
        subscription_manager: WebSocketSubscriptionManager = hass.data.get(
            f"{DOMAIN}_subscriptions"
        )
        if subscription_manager is None:
            connection.send_error(
                msg["id"],
                "integration_not_loaded",
                "Subscription manager not initialized",
            )
            return

        battery_monitor: BatteryMonitor = hass.data.get(DOMAIN)
        if battery_monitor is None:
            connection.send_error(
                msg["id"],
                "integration_not_loaded",
                "Battery monitor not loaded",
            )
            return

        subscription_id = f"sub_{uuid.uuid4().hex[:12]}"
        entity_ids = list(battery_monitor.entities.keys())

        if not subscription_manager.subscribe(
            subscription_id, connection, entity_ids
        ):
            connection.send_error(
                msg["id"],
                "subscription_limit_exceeded",
                "Maximum subscriptions reached",
            )
            return

        connection.send_result(
            msg["id"],
            {"subscription_id": subscription_id, "status": "subscribed"},
        )

        async def on_disconnect():
            subscription_manager.unsubscribe(subscription_id)

        connection.subscriptions[msg["id"]] = on_disconnect

    except Exception as e:
        _LOGGER.error("Error handling subscribe command: %s", e)
        connection.send_error(
            msg["id"], "internal_error", "Failed to subscribe"
        )
