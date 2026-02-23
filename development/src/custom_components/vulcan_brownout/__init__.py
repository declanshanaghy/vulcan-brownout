"""Vulcan Brownout: Battery entity monitoring for Home Assistant."""

import logging
from typing import Any, Dict, Optional

from homeassistant.core import HomeAssistant, Event, State, callback
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
    _LOGGER.debug(
        "async_setup_entry: entry_id=%s domain=%s version=%s",
        entry.entry_id, DOMAIN, VERSION,
    )
    try:
        _LOGGER.info(
            "async_setup_entry: starting setup version=%s threshold=%d%%",
            VERSION, BATTERY_THRESHOLD,
        )

        # Create and initialize battery monitor
        battery_monitor = BatteryMonitor(hass)
        await battery_monitor.discover_entities()
        hass.data[DOMAIN] = battery_monitor
        _LOGGER.debug(
            "async_setup_entry: battery_monitor=ready discovered=%d",
            len(battery_monitor.entities),
        )

        # Create subscription manager
        subscription_manager = WebSocketSubscriptionManager(hass)
        hass.data[f"{DOMAIN}_subscriptions"] = subscription_manager
        _LOGGER.debug(
            "async_setup_entry: subscription_manager=ready max_subscriptions=%d",
            len(subscription_manager.subscribers),
        )

        # Register WebSocket commands
        register_websocket_commands(hass)
        _LOGGER.debug("async_setup_entry: websocket_commands=registered")

        # Listen for state changes
        @callback
        def on_state_changed(event: Event) -> None:
            entity_id = event.data.get("entity_id")
            new_state = event.data.get("new_state")
            new_state_value = new_state.state if new_state else None
            _LOGGER.debug(
                "on_state_changed: entity_id=%s new_state=%s",
                entity_id, new_state_value,
            )
            hass.create_task(
                _on_battery_state_changed(
                    hass, battery_monitor, subscription_manager,
                    entity_id, new_state,
                )
            )

        hass.bus.async_listen(EVENT_STATE_CHANGED, on_state_changed)
        _LOGGER.debug("async_setup_entry: state_change_listener=registered")

        # Register sidebar panel
        try:
            import pathlib
            from homeassistant.components.http import StaticPathConfig
            from homeassistant.components.frontend import (
                async_register_built_in_panel,
            )

            frontend_path = pathlib.Path(__file__).parent / "frontend"
            _LOGGER.debug(
                "async_setup_entry: registering_static_path path=%s",
                str(frontend_path),
            )
            try:
                await hass.http.async_register_static_paths(
                    [StaticPathConfig(
                        "/vulcan_brownout_panel",
                        str(frontend_path),
                        False,
                    )]
                )
                _LOGGER.debug(
                    "async_setup_entry: static_path=registered url=/vulcan_brownout_panel"
                )
            except RuntimeError:
                _LOGGER.debug(
                    "async_setup_entry: static_path=already_registered url=/vulcan_brownout_panel"
                )

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
                "async_setup_entry: panel=registered url=/%s title=%s icon=%s",
                PANEL_NAME, PANEL_TITLE, PANEL_ICON,
            )
        except Exception as e:
            _LOGGER.warning(
                "async_setup_entry: panel_registration=failed error=%s", e
            )

        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

        # Send initial status
        subscription_manager.broadcast_status("connected")

        _LOGGER.info(
            "async_setup_entry: setup=complete version=%s "
            "discovered_entities=%d threshold=%d%%",
            VERSION, len(battery_monitor.entities), BATTERY_THRESHOLD,
        )
        return True

    except Exception as e:
        _LOGGER.error(
            "async_setup_entry: setup=failed error=%s", e, exc_info=True
        )
        return False


async def _on_battery_state_changed(
    hass: HomeAssistant,
    battery_monitor: BatteryMonitor,
    subscription_manager: WebSocketSubscriptionManager,
    entity_id: str,
    new_state: Optional[State],
) -> None:
    """Handle battery entity state changes and broadcast to subscribers."""
    new_state_value = new_state.state if new_state else None
    _LOGGER.debug(
        "_on_battery_state_changed: entity_id=%s new_state=%s",
        entity_id, new_state_value,
    )
    try:
        await battery_monitor.on_state_changed(entity_id, new_state)

        is_battery = battery_monitor._is_battery_entity(entity_id)
        in_tracker = entity_id in battery_monitor.entities
        _LOGGER.debug(
            "_on_battery_state_changed: entity_id=%s is_battery=%s in_tracker=%s",
            entity_id, is_battery, in_tracker,
        )

        if is_battery and in_tracker:
            entity = battery_monitor.entities[entity_id]
            sub_count = subscription_manager.get_subscription_count()
            _LOGGER.debug(
                "_on_battery_state_changed: broadcasting entity_id=%s "
                "battery_level=%.1f%% subscriber_count=%d",
                entity_id, entity.battery_level, sub_count,
            )

            if sub_count > 0:
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
        _LOGGER.error(
            "_on_battery_state_changed: entity_id=%s error=%s",
            entity_id, e, exc_info=True,
        )


async def async_unload_entry(
    hass: HomeAssistant, entry: ConfigEntry
) -> bool:
    """Unload Vulcan Brownout."""
    _LOGGER.debug(
        "async_unload_entry: entry_id=%s", entry.entry_id
    )
    try:
        _LOGGER.info("async_unload_entry: unloading integration entry_id=%s", entry.entry_id)

        sub_mgr: WebSocketSubscriptionManager = hass.data.get(
            f"{DOMAIN}_subscriptions"
        )
        if sub_mgr:
            sub_count = sub_mgr.get_subscription_count()
            sub_mgr.cleanup()
            _LOGGER.debug(
                "async_unload_entry: subscription_manager=cleaned subscribers_closed=%d",
                sub_count,
            )

        hass.data.pop(DOMAIN, None)
        hass.data.pop(f"{DOMAIN}_subscriptions", None)

        _LOGGER.info("async_unload_entry: unload=complete entry_id=%s", entry.entry_id)
        return True
    except Exception as e:
        _LOGGER.error(
            "async_unload_entry: unload=failed entry_id=%s error=%s",
            entry.entry_id, e, exc_info=True,
        )
        return False


async def async_setup(hass: HomeAssistant, config: Dict[str, Any]) -> bool:
    """Set up from YAML (not used)."""
    _LOGGER.debug("async_setup: yaml_config=ignored using_config_entries=true")
    return True
