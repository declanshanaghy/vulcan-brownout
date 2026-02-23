"""Vulcan Brownout: Battery entity monitoring for Home Assistant."""

import logging
from typing import Any, Dict

from homeassistant.core import HomeAssistant, Event, callback
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_STATE_CHANGED

from .const import (
    BATTERY_THRESHOLD,
    DOMAIN,
    STATUS_CRITICAL,
    VERSION,
    PANEL_NAME,
    PANEL_TITLE,
    PANEL_ICON,
)
from .battery_monitor import BatteryMonitor
from .websocket_api import register_websocket_commands
from .subscription_manager import WebSocketSubscriptionManager

_LOGGER = logging.getLogger(__name__)

PLATFORMS = []


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Vulcan Brownout from a config entry."""
    try:
        _LOGGER.info("Setting up Vulcan Brownout integration v%s", VERSION)

        # Create and initialize battery monitor
        battery_monitor = BatteryMonitor(hass)
        await battery_monitor.discover_entities()
        hass.data[DOMAIN] = battery_monitor

        # Create subscription manager
        subscription_manager = WebSocketSubscriptionManager(hass)
        hass.data[f"{DOMAIN}_subscriptions"] = subscription_manager

        # Register WebSocket commands
        register_websocket_commands(hass)

        # Listen for state changes
        @callback
        def on_state_changed(event: Event) -> None:
            entity_id = event.data.get("entity_id")
            new_state = event.data.get("new_state")
            hass.create_task(
                _on_battery_state_changed(
                    hass, battery_monitor, subscription_manager,
                    entity_id, new_state,
                )
            )

        hass.bus.async_listen(EVENT_STATE_CHANGED, on_state_changed)

        # Register sidebar panel
        try:
            import pathlib
            from homeassistant.components.http import StaticPathConfig
            from homeassistant.components.frontend import (
                async_register_built_in_panel,
            )

            frontend_path = pathlib.Path(__file__).parent / "frontend"
            try:
                await hass.http.async_register_static_paths(
                    [StaticPathConfig(
                        "/vulcan_brownout_panel",
                        str(frontend_path),
                        False,
                    )]
                )
            except RuntimeError:
                _LOGGER.debug("Static path already registered")

            async_register_built_in_panel(
                hass,
                component_name="custom",
                sidebar_title=PANEL_TITLE,
                sidebar_icon=PANEL_ICON,
                frontend_url_path=PANEL_NAME,
                require_admin=False,
                config={
                    "_panel_custom": {
                        "name": "vulcan-brownout-panel",
                        "module_url":
                            "/vulcan_brownout_panel/vulcan-brownout-panel.js",
                    }
                },
            )
            _LOGGER.info(
                "Registered Vulcan Brownout sidebar panel at /%s", PANEL_NAME
            )
        except Exception as e:
            _LOGGER.warning("Could not register custom panel: %s", e)

        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

        # Send initial status
        subscription_manager.broadcast_status("connected")

        _LOGGER.info(
            "Vulcan Brownout setup complete. "
            "Discovered %d battery entities. Threshold: %d%%",
            len(battery_monitor.entities), BATTERY_THRESHOLD,
        )
        return True

    except Exception as e:
        _LOGGER.error("Error setting up Vulcan Brownout: %s", e)
        return False


async def _on_battery_state_changed(
    hass: HomeAssistant,
    battery_monitor: BatteryMonitor,
    subscription_manager: WebSocketSubscriptionManager,
    entity_id: str,
    new_state: Any,
) -> None:
    """Handle battery entity state changes and broadcast to subscribers."""
    try:
        await battery_monitor.on_state_changed(entity_id, new_state)

        if (
            battery_monitor._is_battery_entity(entity_id)
            and entity_id in battery_monitor.entities
        ):
            entity = battery_monitor.entities[entity_id]

            if subscription_manager.get_subscription_count() > 0:
                subscription_manager.broadcast_entity_changed(
                    entity_id=entity_id,
                    battery_level=entity.battery_level,
                    status=STATUS_CRITICAL,
                    last_changed=(
                        entity.state.last_changed.isoformat()
                        if entity.state.last_changed else None
                    ),
                    last_updated=(
                        entity.state.last_updated.isoformat()
                        if entity.state.last_updated else None
                    ),
                    attributes=dict(entity.state.attributes),
                )
    except Exception as e:
        _LOGGER.error("Error in battery state change handler: %s", e)


async def async_unload_entry(
    hass: HomeAssistant, entry: ConfigEntry
) -> bool:
    """Unload Vulcan Brownout."""
    try:
        _LOGGER.info("Unloading Vulcan Brownout integration")

        sub_mgr: WebSocketSubscriptionManager = hass.data.get(
            f"{DOMAIN}_subscriptions"
        )
        if sub_mgr:
            sub_mgr.cleanup()

        hass.data.pop(DOMAIN, None)
        hass.data.pop(f"{DOMAIN}_subscriptions", None)

        return True
    except Exception as e:
        _LOGGER.error("Error unloading Vulcan Brownout: %s", e)
        return False


async def async_setup(hass: HomeAssistant, config: Dict[str, Any]) -> bool:
    """Set up from YAML (not used)."""
    return True
