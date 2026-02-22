"""Vulcan Brownout: Battery device monitoring for Home Assistant."""

import logging
from typing import Any, Dict

from homeassistant.core import HomeAssistant, Event, callback
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_STATE_CHANGED
from homeassistant.helpers import entity_registry as er

from .const import (
    DOMAIN,
    VERSION,
    PANEL_NAME,
    PANEL_TITLE,
    PANEL_ICON,
)
from .battery_monitor import BatteryMonitor
from .websocket_api import register_websocket_commands, send_status_event
from .subscription_manager import WebSocketSubscriptionManager

_LOGGER = logging.getLogger(__name__)

PLATFORMS = []


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Vulcan Brownout from a config entry."""
    try:
        _LOGGER.info("Setting up Vulcan Brownout integration v%s", VERSION)

        # Initialize data store for domain
        if DOMAIN not in hass.data:
            hass.data[DOMAIN] = {}

        # Create and initialize battery monitor service
        battery_monitor = BatteryMonitor(hass, config_entry=entry)
        await battery_monitor.discover_entities()

        # Store battery monitor in hass.data
        hass.data[DOMAIN] = battery_monitor

        # Create and initialize WebSocket subscription manager
        subscription_manager = WebSocketSubscriptionManager(hass)
        hass.data[f"{DOMAIN}_subscriptions"] = subscription_manager

        # Register WebSocket command handlers
        register_websocket_commands(hass)

        # Register event listener for state changes
        @callback
        def on_state_changed(event: Event) -> None:
            """Handle HA state_changed events."""
            entity_id = event.data.get("entity_id")
            new_state = event.data.get("new_state")

            # Update battery monitor cache and broadcast if subscribed
            hass.create_task(
                _on_battery_state_changed(
                    hass, battery_monitor, subscription_manager, entity_id, new_state
                )
            )

        hass.bus.async_listen(EVENT_STATE_CHANGED, on_state_changed)

        # Listen to config entry option updates
        entry.async_on_unload(
            entry.add_update_listener(async_options_update_listener)
        )

        # Register sidebar panel
        try:
            from homeassistant.components.frontend import async_register_built_in_panel

            async_register_built_in_panel(
                hass,
                component_name=DOMAIN,
                sidebar_title=PANEL_TITLE,
                sidebar_icon=PANEL_ICON,
                frontend_url_path=PANEL_NAME,
                require_admin=False,
                config={"_panel_custom": {"name": PANEL_NAME}},
            )

            _LOGGER.info("Registered Vulcan Brownout sidebar panel")
        except Exception as e:
            _LOGGER.warning(f"Could not register custom panel: {e}")
            # Continue anyway - WebSocket API should still work

        # Mark entry as loaded
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

        # Send initial status event
        await send_status_event(hass, status="connected")

        _LOGGER.info(
            f"Vulcan Brownout integration setup complete. "
            f"Discovered {len(battery_monitor.entities)} battery entities. "
            f"Global threshold: {battery_monitor.global_threshold}%"
        )
        return True

    except Exception as e:
        _LOGGER.error(f"Error setting up Vulcan Brownout: {e}")
        return False


async def _on_battery_state_changed(
    hass: HomeAssistant,
    battery_monitor: BatteryMonitor,
    subscription_manager: WebSocketSubscriptionManager,
    entity_id: str,
    new_state: Any,
) -> None:
    """Handle battery entity state changes."""
    try:
        # Update battery monitor
        await battery_monitor.on_state_changed(entity_id, new_state)

        # If this is a battery entity and we have subscribers, broadcast update
        if battery_monitor._is_battery_entity(entity_id) and entity_id in battery_monitor.entities:
            device = battery_monitor.entities[entity_id]
            status = battery_monitor.get_status_for_device(device)

            # Only broadcast if there are active subscriptions
            if subscription_manager.get_subscription_count() > 0:
                subscription_manager.broadcast_device_changed(
                    entity_id=entity_id,
                    battery_level=device.battery_level,
                    available=device.available,
                    status=status,
                    last_changed=device.state.last_changed.isoformat()
                    if device.state.last_changed
                    else None,
                    last_updated=device.state.last_updated.isoformat()
                    if device.state.last_updated
                    else None,
                    attributes=dict(device.state.attributes),
                )
    except Exception as e:
        _LOGGER.error(f"Error in battery state change handler: {e}")


async def async_options_update_listener(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> None:
    """Listen for config entry option updates."""
    try:
        # Get battery monitor
        battery_monitor: BatteryMonitor = hass.data.get(DOMAIN)
        if battery_monitor:
            # Update thresholds
            battery_monitor.on_options_updated(config_entry.options)

            # Broadcast threshold update to all subscribers
            subscription_manager: WebSocketSubscriptionManager = hass.data.get(
                f"{DOMAIN}_subscriptions"
            )
            if subscription_manager:
                subscription_manager.broadcast_threshold_updated(
                    global_threshold=battery_monitor.global_threshold,
                    device_rules=battery_monitor.device_rules,
                )

            _LOGGER.debug("Options updated for Vulcan Brownout")
    except Exception as e:
        _LOGGER.error(f"Error updating options: {e}")


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload Vulcan Brownout from a config entry."""
    try:
        _LOGGER.info("Unloading Vulcan Brownout integration")

        # Clean up subscription manager
        subscription_manager: WebSocketSubscriptionManager = hass.data.get(
            f"{DOMAIN}_subscriptions"
        )
        if subscription_manager:
            subscription_manager.cleanup()

        # Remove data
        hass.data.pop(DOMAIN, None)
        hass.data.pop(f"{DOMAIN}_subscriptions", None)

        _LOGGER.info("Vulcan Brownout integration unloaded")
        return True
    except Exception as e:
        _LOGGER.error(f"Error unloading Vulcan Brownout: {e}")
        return False


async def async_setup(hass: HomeAssistant, config: Dict[str, Any]) -> bool:
    """Set up Vulcan Brownout from YAML configuration (if present)."""
    # YAML configuration not used in Sprint 2
    # Config flow is the primary method
    return True
