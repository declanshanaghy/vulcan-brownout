"""Core battery monitoring service for Vulcan Brownout integration."""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

from homeassistant.core import HomeAssistant, State
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.helpers.entity_registry import EntityRegistry

from .const import (
    BATTERY_DEVICE_CLASS,
    BATTERY_THRESHOLD,
    DOMAIN,
    SORT_KEY_BATTERY_LEVEL,
    SORT_KEY_AVAILABLE,
    SORT_KEY_DEVICE_NAME,
    SORT_ORDER_ASC,
    SORT_ORDER_DESC,
)

_LOGGER = logging.getLogger(__name__)


class BatteryEntity:
    """Represents a battery entity with parsed data."""

    def __init__(
        self,
        entity_id: str,
        state: State,
        device_name: Optional[str] = None,
    ) -> None:
        """Initialize battery entity."""
        self.entity_id = entity_id
        self.state = state
        self.device_name = device_name or state.attributes.get("friendly_name", entity_id)
        self.available = state.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN)
        self.battery_level = self._parse_battery_level(state.state)

    def _parse_battery_level(self, state_value: str) -> float:
        """Parse battery level from state value."""
        if state_value in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            return 0.0

        try:
            level = float(state_value)
            # Clamp to 0-100 range
            return max(0.0, min(100.0, level))
        except (ValueError, TypeError):
            _LOGGER.warning(f"Could not parse battery level for {self.entity_id}: {state_value}")
            return 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        state = self.state
        return {
            "entity_id": self.entity_id,
            "state": state.state,
            "attributes": dict(state.attributes),
            "last_changed": state.last_changed.isoformat() if state.last_changed else None,
            "last_updated": state.last_updated.isoformat() if state.last_updated else None,
            "device_id": state.attributes.get("device_id"),
            "device_name": self.device_name,
            "battery_level": self.battery_level,
            "available": self.available,
        }


class BatteryMonitor:
    """Service to discover and monitor battery entities."""

    def __init__(self, hass: HomeAssistant, threshold: int = BATTERY_THRESHOLD) -> None:
        """Initialize battery monitor."""
        self.hass = hass
        self.threshold = threshold
        self.entities: Dict[str, BatteryEntity] = {}

    async def discover_entities(self) -> None:
        """Discover all battery entities from HA registry and cache them."""
        try:
            registry: EntityRegistry = self.hass.helpers.entity_registry.async_get(self.hass)

            # Get all entities with device_class=battery
            for entity_entry in registry.entities.values():
                if entity_entry.device_class != BATTERY_DEVICE_CLASS:
                    continue

                entity_id = entity_entry.entity_id
                state = self.hass.states.get(entity_id)

                if state is None:
                    continue

                # Get device name from device registry if available
                device_name = None
                if entity_entry.device_id:
                    device_registry = self.hass.helpers.device_registry.async_get(self.hass)
                    device = device_registry.devices.get(entity_entry.device_id)
                    if device:
                        device_name = device.name

                # Create and cache entity
                try:
                    battery_entity = BatteryEntity(entity_id, state, device_name)
                    self.entities[entity_id] = battery_entity
                except Exception as e:
                    _LOGGER.warning(f"Failed to parse battery entity {entity_id}: {e}")

            _LOGGER.info(f"Discovered {len(self.entities)} battery entities")
        except Exception as e:
            _LOGGER.error(f"Error during entity discovery: {e}")
            raise

    async def on_state_changed(self, entity_id: str, new_state: Optional[State]) -> None:
        """Handle state change events from HA."""
        if not self._is_battery_entity(entity_id):
            return

        if new_state is None:
            # Entity was deleted
            self.entities.pop(entity_id, None)
            _LOGGER.debug(f"Removed deleted battery entity: {entity_id}")
        else:
            # Entity was updated
            try:
                device_name = None
                # Try to get device name from existing entity or registry
                if entity_id in self.entities:
                    device_name = self.entities[entity_id].device_name
                else:
                    registry: EntityRegistry = self.hass.helpers.entity_registry.async_get(
                        self.hass
                    )
                    entity_entry = registry.entities.get(entity_id)
                    if entity_entry and entity_entry.device_id:
                        device_registry = self.hass.helpers.device_registry.async_get(self.hass)
                        device = device_registry.devices.get(entity_entry.device_id)
                        if device:
                            device_name = device.name

                battery_entity = BatteryEntity(entity_id, new_state, device_name)
                self.entities[entity_id] = battery_entity
                _LOGGER.debug(f"Updated battery entity: {entity_id} -> {battery_entity.battery_level}%")
            except Exception as e:
                _LOGGER.warning(f"Failed to update battery entity {entity_id}: {e}")

    def _is_battery_entity(self, entity_id: str) -> bool:
        """Check if entity is a battery entity by checking registry."""
        try:
            registry: EntityRegistry = self.hass.helpers.entity_registry.async_get(self.hass)
            entity_entry = registry.entities.get(entity_id)
            return entity_entry and entity_entry.device_class == BATTERY_DEVICE_CLASS
        except Exception:
            return False

    async def query_devices(
        self,
        limit: int = 20,
        offset: int = 0,
        sort_key: str = SORT_KEY_BATTERY_LEVEL,
        sort_order: str = SORT_ORDER_ASC,
    ) -> Dict[str, Any]:
        """Query and return paginated, sorted battery devices."""
        # Validate parameters
        if limit < 1 or limit > 100:
            raise ValueError("Limit must be between 1 and 100")
        if offset < 0:
            raise ValueError("Offset must be >= 0")
        if sort_key not in [SORT_KEY_BATTERY_LEVEL, SORT_KEY_AVAILABLE, SORT_KEY_DEVICE_NAME]:
            raise ValueError(f"Unknown sort key: {sort_key}")
        if sort_order not in [SORT_ORDER_ASC, SORT_ORDER_DESC]:
            raise ValueError("Sort order must be 'asc' or 'desc'")

        # Convert entities to list
        devices = list(self.entities.values())

        # Sort devices
        reverse = sort_order == SORT_ORDER_DESC
        if sort_key == SORT_KEY_BATTERY_LEVEL:
            # Primary: battery level (ascending = lowest first)
            # Secondary: available (descending = available first)
            # Tertiary: device name (ascending = A-Z)
            devices.sort(
                key=lambda d: (d.battery_level, not d.available, d.device_name),
                reverse=reverse,
            )
        elif sort_key == SORT_KEY_AVAILABLE:
            devices.sort(
                key=lambda d: (d.available, d.battery_level, d.device_name),
                reverse=reverse,
            )
        elif sort_key == SORT_KEY_DEVICE_NAME:
            devices.sort(
                key=lambda d: (d.device_name, d.battery_level, d.available),
                reverse=reverse,
            )

        # Paginate
        total = len(devices)
        paginated_devices = devices[offset : offset + limit]

        return {
            "devices": [device.to_dict() for device in paginated_devices],
            "total": total,
            "offset": offset,
            "limit": limit,
            "has_more": offset + limit < total,
        }
