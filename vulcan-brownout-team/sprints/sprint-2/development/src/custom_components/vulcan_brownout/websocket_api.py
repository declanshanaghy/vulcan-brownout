"""WebSocket API handlers for Vulcan Brownout integration."""

import logging
import uuid
from typing import Any, Dict, Optional

from homeassistant.core import HomeAssistant
from homeassistant.components.websocket_api import (
    WebSocketError,
    async_register_command,
    websocket_command,
)
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
import voluptuous as vol

from .const import (
    COMMAND_QUERY_DEVICES,
    COMMAND_SUBSCRIBE,
    COMMAND_SET_THRESHOLD,
    DOMAIN,
    MAX_PAGE_SIZE,
    BATTERY_THRESHOLD_MIN,
    BATTERY_THRESHOLD_MAX,
    MAX_DEVICE_RULES,
    SORT_KEY_BATTERY_LEVEL,
    SORT_ORDER_ASC,
    SUPPORTED_SORT_KEYS,
    SUPPORTED_SORT_ORDERS,
)
from .battery_monitor import BatteryMonitor
from .subscription_manager import WebSocketSubscriptionManager

_LOGGER = logging.getLogger(__name__)

# WebSocket command schemas
QUERY_DEVICES_SCHEMA = vol.Schema(
    {
        vol.Optional("limit", default=20): vol.All(vol.Coerce(int), vol.Range(min=1, max=100)),
        vol.Optional("offset", default=0): vol.All(vol.Coerce(int), vol.Range(min=0)),
        vol.Optional("sort_key", default=SORT_KEY_BATTERY_LEVEL): vol.In(SUPPORTED_SORT_KEYS),
        vol.Optional("sort_order", default=SORT_ORDER_ASC): vol.In(SUPPORTED_SORT_ORDERS),
    }
)

SUBSCRIBE_SCHEMA = vol.Schema({})

SET_THRESHOLD_SCHEMA = vol.Schema(
    {
        vol.Optional("global_threshold"): vol.All(
            vol.Coerce(int), vol.Range(min=BATTERY_THRESHOLD_MIN, max=BATTERY_THRESHOLD_MAX)
        ),
        vol.Optional("device_rules"): vol.Schema(
            {str: vol.All(vol.Coerce(int), vol.Range(min=BATTERY_THRESHOLD_MIN, max=BATTERY_THRESHOLD_MAX))}
        ),
    }
)


def register_websocket_commands(hass: HomeAssistant) -> None:
    """Register WebSocket command handlers."""
    async_register_command(hass, handle_query_devices)
    async_register_command(hass, handle_subscribe)
    async_register_command(hass, handle_set_threshold)


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


@websocket_command(
    {
        "type": COMMAND_SUBSCRIBE,
        "data": SUBSCRIBE_SCHEMA,
    }
)
async def handle_subscribe(
    hass: HomeAssistant, connection: Any, msg: Dict[str, Any]
) -> None:
    """Handle vulcan-brownout/subscribe WebSocket command."""
    try:
        # Get subscription manager
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

        # Get battery monitor for entity list
        battery_monitor: BatteryMonitor = hass.data.get(DOMAIN)
        if battery_monitor is None:
            connection.send_error(
                msg["id"],
                "integration_not_loaded",
                "Battery monitor not loaded",
            )
            return

        # Create subscription
        subscription_id = f"sub_{uuid.uuid4().hex[:12]}"
        entity_ids = list(battery_monitor.entities.keys())

        if not subscription_manager.subscribe(subscription_id, connection, entity_ids):
            connection.send_error(
                msg["id"],
                "subscription_limit_exceeded",
                f"Maximum subscriptions ({100}) reached",
            )
            return

        # Send successful response
        connection.send_json_message(
            {
                "type": "result",
                "id": msg["id"],
                "success": True,
                "data": {
                    "subscription_id": subscription_id,
                    "status": "subscribed",
                },
            }
        )

        # Prepare disconnect handler
        async def on_disconnect():
            """Called when WebSocket disconnects."""
            subscription_manager.unsubscribe(subscription_id)

        connection.subscriptions = connection.subscriptions or []
        connection.subscriptions.append(on_disconnect)

    except Exception as e:
        _LOGGER.error(f"Error handling subscribe command: {e}")
        connection.send_error(
            msg["id"],
            "internal_error",
            "Failed to subscribe",
        )


@websocket_command(
    {
        "type": COMMAND_SET_THRESHOLD,
        "data": SET_THRESHOLD_SCHEMA,
    }
)
async def handle_set_threshold(
    hass: HomeAssistant, connection: Any, msg: Dict[str, Any]
) -> None:
    """Handle vulcan-brownout/set_threshold WebSocket command."""
    try:
        # Get battery monitor
        battery_monitor: BatteryMonitor = hass.data.get(DOMAIN)
        if battery_monitor is None:
            connection.send_error(
                msg["id"],
                "integration_not_loaded",
                "Battery monitor not loaded",
            )
            return

        # Get subscription manager
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

        # Extract data
        data = msg.get("data", {})
        global_threshold = data.get("global_threshold")
        device_rules = data.get("device_rules", {})

        # Validate device rules
        if device_rules:
            if len(device_rules) > MAX_DEVICE_RULES:
                connection.send_error(
                    msg["id"],
                    "too_many_rules",
                    f"Maximum {MAX_DEVICE_RULES} device rules allowed",
                )
                return

            # Validate each entity exists
            for entity_id in device_rules.keys():
                if entity_id not in battery_monitor.entities:
                    connection.send_error(
                        msg["id"],
                        "invalid_device_rule",
                        f"Entity {entity_id} not found",
                    )
                    return

        # Update config entry
        if battery_monitor.config_entry:
            new_options = dict(battery_monitor.config_entry.options)

            if global_threshold is not None:
                new_options["global_threshold"] = global_threshold
            if device_rules:
                new_options["device_rules"] = device_rules

            # Update config entry
            hass.config_entries.async_update_entry(
                battery_monitor.config_entry,
                options=new_options,
            )

            # Update battery monitor in memory
            battery_monitor.on_options_updated(new_options)
        else:
            # No config entry (shouldn't happen in normal operation)
            _LOGGER.warning("No config entry found for threshold update")

        # Send response to requester
        connection.send_json_message(
            {
                "type": "result",
                "id": msg["id"],
                "success": True,
                "data": {
                    "message": "Thresholds updated",
                    "global_threshold": battery_monitor.global_threshold,
                    "device_rules": battery_monitor.device_rules,
                },
            }
        )

        # Broadcast threshold update to all subscribers
        subscription_manager.broadcast_threshold_updated(
            global_threshold=battery_monitor.global_threshold,
            device_rules=battery_monitor.device_rules,
        )

    except vol.Invalid as e:
        _LOGGER.warning(f"Validation error in set_threshold: {e}")
        connection.send_error(msg["id"], "invalid_request", str(e))
    except Exception as e:
        _LOGGER.error(f"Error handling set_threshold command: {e}")
        connection.send_error(
            msg["id"],
            "internal_error",
            "Failed to set thresholds",
        )


async def send_status_event(hass: HomeAssistant, status: str = "connected") -> None:
    """Send status event to all connected WebSocket clients."""
    try:
        battery_monitor: BatteryMonitor = hass.data.get(DOMAIN)
        subscription_manager: WebSocketSubscriptionManager = hass.data.get(
            f"{DOMAIN}_subscriptions"
        )

        if not battery_monitor or not subscription_manager:
            return

        subscription_manager.broadcast_status(
            status=status,
            threshold=battery_monitor.global_threshold,
            device_rules=battery_monitor.device_rules,
            device_statuses=battery_monitor.get_device_statuses(),
        )

    except Exception as e:
        _LOGGER.warning(f"Error sending status event: {e}")
