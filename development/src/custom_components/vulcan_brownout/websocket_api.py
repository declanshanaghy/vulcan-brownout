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
    _LOGGER.debug(
        "register_websocket_commands: registering commands=%s",
        [COMMAND_QUERY_ENTITIES, COMMAND_SUBSCRIBE],
    )
    websocket_api.async_register_command(hass, handle_query_entities)
    websocket_api.async_register_command(hass, handle_subscribe)
    _LOGGER.info(
        "register_websocket_commands: registered command_count=2 "
        "commands=[%s, %s]",
        COMMAND_QUERY_ENTITIES, COMMAND_SUBSCRIBE,
    )


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
    msg_id = msg["id"]
    _LOGGER.debug(
        "handle_query_entities: msg_id=%s command=%s",
        msg_id, COMMAND_QUERY_ENTITIES,
    )
    try:
        battery_monitor: BatteryMonitor = hass.data.get(DOMAIN)
        if battery_monitor is None:
            _LOGGER.warning(
                "handle_query_entities: msg_id=%s error=integration_not_loaded",
                msg_id,
            )
            connection.send_error(
                msg_id,
                "integration_not_loaded",
                "Vulcan Brownout integration not loaded",
            )
            return

        result = await battery_monitor.query_entities()
        entity_count = result.get("total", 0)
        _LOGGER.debug(
            "handle_query_entities: msg_id=%s result_total=%d sending_response=true",
            msg_id, entity_count,
        )
        connection.send_result(msg_id, result)
        _LOGGER.info(
            "handle_query_entities: msg_id=%s entities_returned=%d",
            msg_id, entity_count,
        )

    except Exception as e:
        _LOGGER.error(
            "handle_query_entities: msg_id=%s error=%s",
            msg_id, e, exc_info=True,
        )
        connection.send_error(
            msg_id, "internal_error", "Failed to query entities"
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
    msg_id = msg["id"]
    _LOGGER.debug(
        "handle_subscribe: msg_id=%s command=%s",
        msg_id, COMMAND_SUBSCRIBE,
    )
    try:
        subscription_manager: WebSocketSubscriptionManager = hass.data.get(
            f"{DOMAIN}_subscriptions"
        )
        if subscription_manager is None:
            _LOGGER.warning(
                "handle_subscribe: msg_id=%s error=subscription_manager_not_loaded",
                msg_id,
            )
            connection.send_error(
                msg_id,
                "integration_not_loaded",
                "Subscription manager not initialized",
            )
            return

        battery_monitor: BatteryMonitor = hass.data.get(DOMAIN)
        if battery_monitor is None:
            _LOGGER.warning(
                "handle_subscribe: msg_id=%s error=battery_monitor_not_loaded",
                msg_id,
            )
            connection.send_error(
                msg_id,
                "integration_not_loaded",
                "Battery monitor not loaded",
            )
            return

        subscription_id = f"sub_{uuid.uuid4().hex[:12]}"
        entity_ids = list(battery_monitor.entities.keys())
        _LOGGER.debug(
            "handle_subscribe: msg_id=%s subscription_id=%s entity_count=%d",
            msg_id, subscription_id, len(entity_ids),
        )

        if not subscription_manager.subscribe(
            subscription_id, connection, entity_ids
        ):
            current_count = subscription_manager.get_subscription_count()
            _LOGGER.warning(
                "handle_subscribe: msg_id=%s error=subscription_limit_exceeded "
                "current_count=%d",
                msg_id, current_count,
            )
            connection.send_error(
                msg_id,
                "subscription_limit_exceeded",
                "Maximum subscriptions reached",
            )
            return

        connection.send_result(
            msg_id,
            {"subscription_id": subscription_id, "status": "subscribed"},
        )
        _LOGGER.info(
            "handle_subscribe: msg_id=%s subscription_id=%s "
            "entity_count=%d total_subscribers=%d",
            msg_id, subscription_id, len(entity_ids),
            subscription_manager.get_subscription_count(),
        )

        async def on_disconnect():
            _LOGGER.debug(
                "handle_subscribe.on_disconnect: subscription_id=%s cleaning_up=true",
                subscription_id,
            )
            subscription_manager.unsubscribe(subscription_id)
            _LOGGER.info(
                "handle_subscribe.on_disconnect: subscription_id=%s unsubscribed=true "
                "remaining_subscribers=%d",
                subscription_id, subscription_manager.get_subscription_count(),
            )

        connection.subscriptions[msg_id] = on_disconnect

    except Exception as e:
        _LOGGER.error(
            "handle_subscribe: msg_id=%s error=%s",
            msg_id, e, exc_info=True,
        )
        connection.send_error(
            msg_id, "internal_error", "Failed to subscribe"
        )
