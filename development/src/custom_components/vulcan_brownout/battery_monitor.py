"""Core battery monitoring service for Vulcan Brownout integration."""

import logging
from typing import Any, Dict, List, Optional

from homeassistant.core import HomeAssistant, State
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.helpers import (
    area_registry as ar,
    device_registry as dr,
    entity_registry as er,
)

from .const import BATTERY_DEVICE_CLASS, BATTERY_THRESHOLD, STATUS_CRITICAL

_LOGGER = logging.getLogger(__name__)


class BatteryEntity:
    """Represents a battery entity with parsed data."""

    def __init__(
        self,
        entity_id: str,
        state: State,
        device_name: Optional[str] = None,
        manufacturer: Optional[str] = None,
        model: Optional[str] = None,
        area_name: Optional[str] = None,
    ) -> None:
        self.entity_id = entity_id
        self.state = state
        self.device_name = (
            device_name or state.attributes.get("friendly_name", entity_id)
        )
        self.battery_level = self._parse_battery_level(state.state)
        self.manufacturer = manufacturer
        self.model = model
        self.area_name = area_name

    def _parse_battery_level(self, state_value: str) -> float:
        if state_value in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            return -1.0
        try:
            return max(0.0, min(100.0, float(state_value)))
        except (ValueError, TypeError):
            return -1.0

    def to_dict(self) -> Dict[str, Any]:
        state = self.state
        return {
            "entity_id": self.entity_id,
            "state": state.state,
            "attributes": dict(state.attributes),
            "last_changed": (
                state.last_changed.isoformat() if state.last_changed else None
            ),
            "last_updated": (
                state.last_updated.isoformat() if state.last_updated else None
            ),
            "device_name": self.device_name,
            "battery_level": self.battery_level,
            "status": STATUS_CRITICAL,
            "manufacturer": self.manufacturer,
            "model": self.model,
            "area_name": self.area_name,
        }


class BatteryMonitor:
    """Discovers battery entities and returns those below the fixed threshold."""

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self.entities: Dict[str, BatteryEntity] = {}

    async def discover_entities(self) -> None:
        """Discover all battery entities from the HA registry."""
        try:
            entity_registry = er.async_get(self.hass)
            device_registry = dr.async_get(self.hass)
            area_registry = ar.async_get(self.hass)

            for entity_entry in entity_registry.entities.values():
                device_class = (
                    entity_entry.device_class
                    or entity_entry.original_device_class
                )
                if device_class != BATTERY_DEVICE_CLASS:
                    continue

                entity_id = entity_entry.entity_id

                # Skip binary_sensors (on/off, not %)
                if entity_id.startswith("binary_sensor."):
                    continue

                state = self.hass.states.get(entity_id)
                if state is None:
                    continue

                # Skip unavailable / unknown entities
                if state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
                    continue

                # Validate numeric battery level
                try:
                    float(state.state)
                except (ValueError, TypeError):
                    continue

                # Get device info from device registry
                device_name = None
                manufacturer = None
                model = None
                area_id = entity_entry.area_id
                if entity_entry.device_id:
                    device = device_registry.async_get(entity_entry.device_id)
                    if device:
                        device_name = device.name
                        manufacturer = device.manufacturer
                        model = device.model
                        if not area_id:
                            area_id = device.area_id

                # Resolve area name
                area_name = None
                if area_id:
                    area = area_registry.async_get_area(area_id)
                    if area:
                        area_name = area.name

                try:
                    entity = BatteryEntity(
                        entity_id, state, device_name,
                        manufacturer, model, area_name,
                    )
                    self.entities[entity_id] = entity
                except Exception as e:
                    _LOGGER.warning(
                        "Failed to parse battery entity %s: %s",
                        entity_id, e,
                    )

            _LOGGER.info("Discovered %d battery entities", len(self.entities))
        except Exception as e:
            _LOGGER.error("Error during entity discovery: %s", e)
            raise

    async def on_state_changed(
        self, entity_id: str, new_state: Optional[State]
    ) -> None:
        """Handle state change events from HA."""
        if not self._is_battery_entity(entity_id):
            return

        if new_state is None:
            self.entities.pop(entity_id, None)
            return

        # Skip unavailable entities
        if new_state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            self.entities.pop(entity_id, None)
            return

        device_name = None
        manufacturer = None
        model = None
        area_name = None
        if entity_id in self.entities:
            existing = self.entities[entity_id]
            device_name = existing.device_name
            manufacturer = existing.manufacturer
            model = existing.model
            area_name = existing.area_name
        else:
            entity_registry = er.async_get(self.hass)
            entry = entity_registry.entities.get(entity_id)
            if entry:
                area_id = entry.area_id
                if entry.device_id:
                    device_registry = dr.async_get(self.hass)
                    device = device_registry.async_get(entry.device_id)
                    if device:
                        device_name = device.name
                        manufacturer = device.manufacturer
                        model = device.model
                        if not area_id:
                            area_id = device.area_id
                if area_id:
                    area_registry = ar.async_get(self.hass)
                    area = area_registry.async_get_area(area_id)
                    if area:
                        area_name = area.name

        try:
            entity = BatteryEntity(
                entity_id, new_state, device_name,
                manufacturer, model, area_name,
            )
            self.entities[entity_id] = entity
        except Exception as e:
            _LOGGER.warning(
                "Failed to update battery entity %s: %s", entity_id, e
            )

    def _is_battery_entity(self, entity_id: str) -> bool:
        """Check if entity is a tracked battery entity."""
        if entity_id in self.entities:
            return True
        if entity_id.startswith("binary_sensor."):
            return False
        try:
            entity_registry = er.async_get(self.hass)
            entry = entity_registry.entities.get(entity_id)
            if entry:
                dc = entry.device_class or entry.original_device_class
                return dc == BATTERY_DEVICE_CLASS
            state = self.hass.states.get(entity_id)
            return (
                state is not None
                and state.attributes.get("device_class") == BATTERY_DEVICE_CLASS
            )
        except Exception:
            return False

    async def query_entities(self) -> Dict[str, Any]:
        """Return all battery entities below the fixed threshold.

        For each entity selected below the threshold, performs a fresh lookup
        against the device, entity, and area registries to attach the owning
        device's manufacturer, model, and area name to the response payload.

        Sorted by battery level ascending (lowest first).
        """
        entity_registry = er.async_get(self.hass)
        device_registry = dr.async_get(self.hass)
        area_registry = ar.async_get(self.hass)

        low_battery: List[Dict[str, Any]] = []

        for entity in self.entities.values():
            if not (0 <= entity.battery_level < BATTERY_THRESHOLD):
                continue

            data = entity.to_dict()

            # Fresh device registry lookup for each selected entity
            entry = entity_registry.entities.get(entity.entity_id)
            if entry:
                area_id = entry.area_id
                if entry.device_id:
                    device = device_registry.async_get(entry.device_id)
                    if device:
                        if device.name:
                            data["device_name"] = device.name
                        data["manufacturer"] = device.manufacturer
                        data["model"] = device.model
                        if not area_id:
                            area_id = device.area_id
                if area_id:
                    area = area_registry.async_get_area(area_id)
                    if area:
                        data["area_name"] = area.name

            low_battery.append(data)

        low_battery.sort(
            key=lambda d: (d["battery_level"], d.get("device_name") or d["entity_id"])
        )

        return {
            "entities": low_battery,
            "total": len(low_battery),
        }
