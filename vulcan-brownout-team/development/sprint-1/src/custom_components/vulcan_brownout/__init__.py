"""Vulcan Brownout: Battery device monitoring for Home Assistant."""

import logging
from typing import Any, Dict

from homeassistant.core import HomeAssistant, Event, callback
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_STATE_CHANGED
from homeassistant.helpers.entity_registry import EntityRegistry

from .const import (
    DOMAIN,
    VERSION,
    PANEL_NAME,
    PANEL_TITLE,
    PANEL_ICON,
    BATTERY_THRESHOLD,
)
from .battery_monitor import BatteryMonitor
from .websocket_api import register_websocket_commands

_LOGGER = logging.getLogger(__name__)

PLATFORMS = []


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Vulcan Brownout from a config entry."""
    try:
        _LOGGER.info("Setting up Vulcan Brownout integration")

        # Initialize data store for domain
        if DOMAIN not in hass.data:
            hass.data[DOMAIN] = {}

        # Create and initialize battery monitor service
        battery_monitor = BatteryMonitor(hass, threshold=BATTERY_THRESHOLD)
        await battery_monitor.discover_entities()

        # Store in hass.data for access from WebSocket handlers
        hass.data[DOMAIN] = battery_monitor

        # Register WebSocket command handlers
        register_websocket_commands(hass)

        # Register event listener for state changes
        @callback
        def on_state_changed(event: Event) -> None:
            """Handle HA state_changed events."""
            entity_id = event.data.get("entity_id")
            new_state = event.data.get("new_state")

            # Update battery monitor cache (synchronous, called from event handler)
            hass.create_task(battery_monitor.on_state_changed(entity_id, new_state))

        hass.bus.async_listen(EVENT_STATE_CHANGED, on_state_changed)

        # Register sidebar panel
        try:
            # Get frontend component
            frontend = hass.components.frontend

            # Register custom panel
            frontend.async_register_built_in_panel(
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

        _LOGGER.info(
            f"Vulcan Brownout integration setup complete. "
            f"Discovered {len(battery_monitor.entities)} battery entities."
        )
        return True

    except Exception as e:
        _LOGGER.error(f"Error setting up Vulcan Brownout: {e}")
        return False


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload Vulcan Brownout from a config entry."""
    try:
        _LOGGER.info("Unloading Vulcan Brownout integration")

        # Remove WebSocket command handlers (HA handles this automatically)
        # Clean up data
        hass.data.pop(DOMAIN, None)

        _LOGGER.info("Vulcan Brownout integration unloaded")
        return True
    except Exception as e:
        _LOGGER.error(f"Error unloading Vulcan Brownout: {e}")
        return False


async def async_setup(hass: HomeAssistant, config: Dict[str, Any]) -> bool:
    """Set up Vulcan Brownout from YAML configuration (if present)."""
    # YAML configuration not used in Sprint 1
    # But we still support the config flow
    return True
