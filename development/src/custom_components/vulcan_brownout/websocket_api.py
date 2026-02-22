"""WebSocket API handlers for Vulcan Brownout integration."""

import logging
import uuid
from typing import Any, Dict, Optional

from homeassistant.core import HomeAssistant
from homeassistant.components import websocket_api
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
import voluptuous as vol

from .const import (
    COMMAND_QUERY_DEVICES,
    COMMAND_SUBSCRIBE,
    COMMAND_SET_THRESHOLD,
    COMMAND_GET_NOTIFICATION_PREFERENCES,
    COMMAND_SET_NOTIFICATION_PREFERENCES,
    DOMAIN,
    MAX_PAGE_SIZE,
    BATTERY_THRESHOLD_MIN,
    BATTERY_THRESHOLD_MAX,
    MAX_DEVICE_RULES,
    SORT_KEY_PRIORITY,
    SORT_ORDER_ASC,
    SUPPORTED_SORT_KEYS,
    SUPPORTED_SORT_ORDERS,
    NOTIFICATION_FREQUENCY_CAP_OPTIONS,
    NOTIFICATION_SEVERITY_FILTER_OPTIONS,
)
from .battery_monitor import BatteryMonitor
from .subscription_manager import WebSocketSubscriptionManager

_LOGGER = logging.getLogger(__name__)


def register_websocket_commands(hass: HomeAssistant) -> None:
    """Register WebSocket command handlers."""
    websocket_api.async_register_command(hass, handle_query_devices)
    websocket_api.async_register_command(hass, handle_subscribe)
    websocket_api.async_register_command(hass, handle_set_threshold)
    websocket_api.async_register_command(hass, handle_get_notification_preferences)
    websocket_api.async_register_command(hass, handle_set_notification_preferences)


@websocket_api.websocket_command(
    {
        vol.Required("type"): COMMAND_QUERY_DEVICES,
        vol.Optional("limit", default=50): vol.All(vol.Coerce(int), vol.Range(min=1, max=100)),
        vol.Optional("offset", default=0): vol.All(vol.Coerce(int), vol.Range(min=0)),
        vol.Optional("cursor"): str,
        vol.Optional("sort_key", default=SORT_KEY_PRIORITY): vol.In(SUPPORTED_SORT_KEYS),
        vol.Optional("sort_order", default=SORT_ORDER_ASC): vol.In(SUPPORTED_SORT_ORDERS),
    }
)
@websocket_api.async_response
async def handle_query_devices(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: Dict[str, Any]
) -> None:
    """Handle vulcan-brownout/query_devices WebSocket command.

    Sprint 3: Updated to support cursor-based pagination with backward compatibility
    for offset-based requests.
    """
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

        # Extract parameters (validated by schema)
        limit = msg.get("limit", 50)
        offset = msg.get("offset", 0)
        cursor = msg.get("cursor")
        sort_key = msg.get("sort_key", SORT_KEY_PRIORITY)
        sort_order = msg.get("sort_order", SORT_ORDER_ASC)

        # Query devices (supports both cursor and offset pagination)
        result = await battery_monitor.query_devices(
            limit=limit,
            offset=offset,
            cursor=cursor,
            sort_key=sort_key,
            sort_order=sort_order,
        )

        # Send successful response
        connection.send_result(msg["id"], result)

    except ValueError as e:
        _LOGGER.warning(f"Query validation error: {e}")
        connection.send_error(msg["id"], "invalid_request", str(e))
    except Exception as e:
        _LOGGER.error(f"Error handling query_devices command: {e}")
        connection.send_error(
            msg["id"],
            "internal_error",
            "Failed to query devices",
        )


@websocket_api.websocket_command(
    {
        vol.Required("type"): COMMAND_SUBSCRIBE,
    }
)
@websocket_api.async_response
async def handle_subscribe(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: Dict[str, Any]
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
        connection.send_result(
            msg["id"],
            {
                "subscription_id": subscription_id,
                "status": "subscribed",
            },
        )

        # Prepare disconnect handler
        async def on_disconnect():
            """Called when WebSocket disconnects."""
            subscription_manager.unsubscribe(subscription_id)

        connection.subscriptions[msg["id"]] = on_disconnect

    except Exception as e:
        _LOGGER.error(f"Error handling subscribe command: {e}")
        connection.send_error(
            msg["id"],
            "internal_error",
            "Failed to subscribe",
        )


@websocket_api.websocket_command(
    {
        vol.Required("type"): COMMAND_SET_THRESHOLD,
        vol.Optional("global_threshold"): vol.All(
            vol.Coerce(int), vol.Range(min=BATTERY_THRESHOLD_MIN, max=BATTERY_THRESHOLD_MAX)
        ),
        vol.Optional("device_rules"): vol.Schema(
            {str: vol.All(vol.Coerce(int), vol.Range(min=BATTERY_THRESHOLD_MIN, max=BATTERY_THRESHOLD_MAX))}
        ),
    }
)
@websocket_api.async_response
async def handle_set_threshold(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: Dict[str, Any]
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

        # Extract data (validated by schema)
        global_threshold = msg.get("global_threshold")
        device_rules = msg.get("device_rules", {})

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
            _LOGGER.warning("No config entry found for threshold update")

        # Send response to requester
        connection.send_result(
            msg["id"],
            {
                "message": "Thresholds updated",
                "global_threshold": battery_monitor.global_threshold,
                "device_rules": battery_monitor.device_rules,
            },
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


@websocket_api.websocket_command(
    {
        vol.Required("type"): COMMAND_GET_NOTIFICATION_PREFERENCES,
    }
)
@websocket_api.async_response
async def handle_get_notification_preferences(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: Dict[str, Any]
) -> None:
    """Handle vulcan-brownout/get_notification_preferences WebSocket command.

    Sprint 3: Retrieve current notification preferences and history.
    """
    try:
        # Get notification manager
        from .notification_manager import NotificationManager

        notification_manager: NotificationManager = hass.data.get(
            f"{DOMAIN}_notifications"
        )
        if notification_manager is None:
            connection.send_error(
                msg["id"],
                "integration_not_loaded",
                "Notification manager not initialized",
            )
            return

        # Get preferences
        prefs = notification_manager.get_notification_preferences()

        # Send successful response
        connection.send_result(msg["id"], prefs)

    except Exception as e:
        _LOGGER.error(f"Error handling get_notification_preferences command: {e}")
        connection.send_error(
            msg["id"],
            "internal_error",
            "Failed to get notification preferences",
        )


@websocket_api.websocket_command(
    {
        vol.Required("type"): COMMAND_SET_NOTIFICATION_PREFERENCES,
        vol.Required("enabled"): bool,
        vol.Required("frequency_cap_hours"): vol.In(NOTIFICATION_FREQUENCY_CAP_OPTIONS),
        vol.Required("severity_filter"): vol.In(NOTIFICATION_SEVERITY_FILTER_OPTIONS),
        vol.Optional("per_device"): dict,
    }
)
@websocket_api.async_response
async def handle_set_notification_preferences(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: Dict[str, Any]
) -> None:
    """Handle vulcan-brownout/set_notification_preferences WebSocket command.

    Sprint 3: Update notification preferences and validate them.
    """
    try:
        # Get notification manager
        from .notification_manager import NotificationManager

        notification_manager: NotificationManager = hass.data.get(
            f"{DOMAIN}_notifications"
        )
        if notification_manager is None:
            connection.send_error(
                msg["id"],
                "integration_not_loaded",
                "Notification manager not initialized",
            )
            return

        # Extract parameters
        enabled = msg.get("enabled", True)
        frequency_cap_hours = msg.get("frequency_cap_hours", 6)
        severity_filter = msg.get("severity_filter", "critical_only")
        per_device = msg.get("per_device", {})

        # Validate and update preferences
        await notification_manager.set_notification_preferences(
            enabled=enabled,
            frequency_cap_hours=frequency_cap_hours,
            severity_filter=severity_filter,
            per_device=per_device,
        )

        # Update config entry
        battery_monitor: BatteryMonitor = hass.data.get(DOMAIN)
        if battery_monitor and battery_monitor.config_entry:
            new_options = dict(battery_monitor.config_entry.options)
            new_options["notification_preferences"] = {
                "enabled": enabled,
                "frequency_cap_hours": frequency_cap_hours,
                "severity_filter": severity_filter,
                "per_device": per_device,
            }
            hass.config_entries.async_update_entry(
                battery_monitor.config_entry,
                options=new_options,
            )

        # Send successful response
        connection.send_result(
            msg["id"],
            {
                "message": "Notification preferences updated",
                "enabled": enabled,
                "frequency_cap_hours": frequency_cap_hours,
                "severity_filter": severity_filter,
            },
        )

        # Broadcast status update to all subscribers
        subscription_manager: WebSocketSubscriptionManager = hass.data.get(
            f"{DOMAIN}_subscriptions"
        )
        if subscription_manager:
            subscription_manager.broadcast_status(
                status="connected",
                threshold=battery_monitor.global_threshold if battery_monitor else 15,
                device_rules=battery_monitor.device_rules if battery_monitor else {},
                device_statuses=battery_monitor.get_device_statuses() if battery_monitor else {},
            )

    except ValueError as e:
        _LOGGER.warning(f"Validation error in set_notification_preferences: {e}")
        connection.send_error(msg["id"], "invalid_notification_preferences", str(e))
    except Exception as e:
        _LOGGER.error(f"Error handling set_notification_preferences command: {e}")
        connection.send_error(
            msg["id"],
            "internal_error",
            "Failed to set notification preferences",
        )


async def send_status_event(hass: HomeAssistant, status: str = "connected") -> None:
    """Send status event to all connected WebSocket clients.

    Sprint 3: Includes theme and notification status.
    """
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
