"""Core battery monitoring service for Vulcan Brownout integration."""

import logging
from typing import Any, Dict, List, Optional, Tuple

from homeassistant.core import HomeAssistant, State
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.helpers import (
    area_registry as ar,
    device_registry as dr,
    entity_registry as er,
)
from homeassistant.helpers.device_registry import DeviceRegistry
from homeassistant.helpers.entity_registry import EntityRegistry
from homeassistant.helpers.area_registry import AreaRegistry

from .const import BATTERY_DEVICE_CLASS, BATTERY_THRESHOLD, STATUS_CRITICAL

_LOGGER = logging.getLogger(__name__)

# Type alias for device info tuple: (device_name, manufacturer, model, area_name)
DeviceInfo = Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]


class BatteryEntity:
    """Represents a battery entity with parsed data."""

    entity_id: str
    state: State
    device_name: str
    battery_level: float
    manufacturer: Optional[str]
    model: Optional[str]
    area_name: Optional[str]

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
        _LOGGER.debug(
            "BatteryEntity.__init__: entity_id=%s device_name=%s "
            "battery_level=%.1f manufacturer=%s model=%s area_name=%s",
            entity_id, self.device_name, self.battery_level,
            manufacturer, model, area_name,
        )

    def _parse_battery_level(self, state_value: str) -> float:
        if state_value in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            _LOGGER.debug(
                "_parse_battery_level: entity_id=%s state=%s result=-1.0 (unavailable/unknown)",
                self.entity_id, state_value,
            )
            return -1.0
        try:
            level = max(0.0, min(100.0, float(state_value)))
            _LOGGER.debug(
                "_parse_battery_level: entity_id=%s raw_state=%s parsed_level=%.1f",
                self.entity_id, state_value, level,
            )
            return level
        except (ValueError, TypeError):
            _LOGGER.debug(
                "_parse_battery_level: entity_id=%s state=%s result=-1.0 (parse_error)",
                self.entity_id, state_value,
            )
            return -1.0

    def to_dict(self) -> Dict[str, Any]:
        state = self.state
        result = {
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
        _LOGGER.debug(
            "BatteryEntity.to_dict: entity_id=%s battery_level=%.1f "
            "manufacturer=%s model=%s area_name=%s",
            self.entity_id, self.battery_level,
            self.manufacturer, self.model, self.area_name,
        )
        return result


class BatteryMonitor:
    """Discovers battery entities and returns those below the fixed threshold."""

    hass: HomeAssistant
    entities: Dict[str, BatteryEntity]

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self.entities = {}
        _LOGGER.debug(
            "BatteryMonitor.__init__: threshold=%d%% device_class=%s",
            BATTERY_THRESHOLD, BATTERY_DEVICE_CLASS,
        )

    def _resolve_device_info(
        self,
        entity_id: str,
        device_id: Optional[str],
        entity_area_id: Optional[str],
        device_registry: DeviceRegistry,
        area_registry: AreaRegistry,
    ) -> DeviceInfo:
        """Resolve device name, manufacturer, model, and area name from registries.

        Returns (device_name, manufacturer, model, area_name).
        """
        device_name: Optional[str] = None
        manufacturer: Optional[str] = None
        model: Optional[str] = None
        area_id: Optional[str] = entity_area_id

        if device_id:
            device = device_registry.async_get(device_id)
            if device:
                device_name = device.name
                manufacturer = device.manufacturer
                model = device.model
                if not area_id:
                    area_id = device.area_id
                _LOGGER.debug(
                    "_resolve_device_info: entity_id=%s device_id=%s "
                    "device_name=%s manufacturer=%s model=%s area_id=%s",
                    entity_id, device_id, device_name, manufacturer, model, area_id,
                )
            else:
                _LOGGER.debug(
                    "_resolve_device_info: entity_id=%s device_id=%s device=not_found",
                    entity_id, device_id,
                )
        else:
            _LOGGER.debug(
                "_resolve_device_info: entity_id=%s device_id=none (standalone entity)",
                entity_id,
            )

        area_name = None
        if area_id:
            area = area_registry.async_get_area(area_id)
            if area:
                area_name = area.name
                _LOGGER.debug(
                    "_resolve_device_info: entity_id=%s area_id=%s area_name=%s",
                    entity_id, area_id, area_name,
                )
            else:
                _LOGGER.debug(
                    "_resolve_device_info: entity_id=%s area_id=%s area=not_found",
                    entity_id, area_id,
                )

        return device_name, manufacturer, model, area_name

    def _get_cached_or_lookup_device_info(self, entity_id: str) -> DeviceInfo:
        """Return (device_name, manufacturer, model, area_name) for an entity.

        Uses the cached BatteryEntity if already tracked, otherwise performs a
        fresh registry lookup for newly seen entities.
        """
        if entity_id in self.entities:
            existing = self.entities[entity_id]
            _LOGGER.debug(
                "_get_cached_or_lookup_device_info: entity_id=%s source=cache "
                "device_name=%s manufacturer=%s model=%s area_name=%s",
                entity_id, existing.device_name, existing.manufacturer,
                existing.model, existing.area_name,
            )
            return (
                existing.device_name, existing.manufacturer,
                existing.model, existing.area_name,
            )

        _LOGGER.debug(
            "_get_cached_or_lookup_device_info: entity_id=%s source=registry_lookup",
            entity_id,
        )
        entity_registry = er.async_get(self.hass)
        entry = entity_registry.entities.get(entity_id)
        if not entry:
            _LOGGER.debug(
                "_get_cached_or_lookup_device_info: entity_id=%s registry_entry=not_found",
                entity_id,
            )
            return None, None, None, None

        return self._resolve_device_info(
            entity_id,
            entry.device_id,
            entry.area_id,
            dr.async_get(self.hass),
            ar.async_get(self.hass),
        )

    def _get_valid_battery_state(self, entity_id: str) -> Optional[State]:
        """Return a state object for entity_id if it is a valid numeric battery entity.

        Returns None (and logs the reason) if the entity should be skipped.
        """
        if entity_id.startswith("binary_sensor."):
            _LOGGER.debug(
                "_get_valid_battery_state: entity_id=%s skip=binary_sensor", entity_id
            )
            return None

        state = self.hass.states.get(entity_id)
        if state is None:
            _LOGGER.debug(
                "_get_valid_battery_state: entity_id=%s skip=no_state", entity_id
            )
            return None

        if state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            _LOGGER.debug(
                "_get_valid_battery_state: entity_id=%s skip=state=%s",
                entity_id, state.state,
            )
            return None

        try:
            float(state.state)
        except (ValueError, TypeError):
            _LOGGER.debug(
                "_get_valid_battery_state: entity_id=%s skip=non_numeric state=%s",
                entity_id, state.state,
            )
            return None

        return state

    async def discover_entities(self) -> None:
        """Discover all battery entities from the HA registry."""
        _LOGGER.debug("discover_entities: starting entity discovery")
        try:
            entity_registry = er.async_get(self.hass)
            device_registry = dr.async_get(self.hass)
            area_registry = ar.async_get(self.hass)

            total_checked = 0
            skipped_device_class = 0
            accepted = 0

            for entity_entry in entity_registry.entities.values():
                total_checked += 1
                device_class = (
                    entity_entry.device_class
                    or entity_entry.original_device_class
                )
                if device_class != BATTERY_DEVICE_CLASS:
                    skipped_device_class += 1
                    continue

                entity_id = entity_entry.entity_id
                state = self._get_valid_battery_state(entity_id)
                if state is None:
                    continue

                device_name, manufacturer, model, area_name = (
                    self._resolve_device_info(
                        entity_id,
                        entity_entry.device_id,
                        entity_entry.area_id,
                        device_registry,
                        area_registry,
                    )
                )

                try:
                    entity = BatteryEntity(
                        entity_id, state, device_name,
                        manufacturer, model, area_name,
                    )
                    self.entities[entity_id] = entity
                    accepted += 1
                except Exception as e:
                    _LOGGER.warning(
                        "discover_entities: entity_id=%s parse=failed error=%s",
                        entity_id, e,
                    )

            skipped = total_checked - skipped_device_class - accepted
            _LOGGER.info(
                "discover_entities: complete total_checked=%d accepted=%d "
                "skipped_device_class=%d skipped_other=%d",
                total_checked, accepted, skipped_device_class, skipped,
            )
        except Exception as e:
            _LOGGER.error(
                "discover_entities: discovery=failed error=%s", e, exc_info=True
            )
            raise

    async def on_state_changed(
        self, entity_id: str, new_state: Optional[State]
    ) -> None:
        """Handle state change events from HA."""
        _LOGGER.debug(
            "on_state_changed: entity_id=%s new_state=%s",
            entity_id, new_state.state if new_state else None,
        )

        if not self._is_battery_entity(entity_id):
            _LOGGER.debug(
                "on_state_changed: entity_id=%s is_battery=false skipping",
                entity_id,
            )
            return

        if new_state is None:
            was_tracked = entity_id in self.entities
            self.entities.pop(entity_id, None)
            _LOGGER.debug(
                "on_state_changed: entity_id=%s new_state=None was_tracked=%s removed=%s",
                entity_id, was_tracked, was_tracked,
            )
            return

        # Skip unavailable entities
        if new_state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            was_tracked = entity_id in self.entities
            self.entities.pop(entity_id, None)
            _LOGGER.debug(
                "on_state_changed: entity_id=%s state=%s was_tracked=%s removed=%s",
                entity_id, new_state.state, was_tracked, was_tracked,
            )
            return

        device_name, manufacturer, model, area_name = (
            self._get_cached_or_lookup_device_info(entity_id)
        )

        try:
            entity = BatteryEntity(
                entity_id, new_state, device_name,
                manufacturer, model, area_name,
            )
            self.entities[entity_id] = entity
            _LOGGER.debug(
                "on_state_changed: entity_id=%s updated battery_level=%.1f%%",
                entity_id, entity.battery_level,
            )
        except Exception as e:
            _LOGGER.warning(
                "on_state_changed: entity_id=%s update=failed error=%s",
                entity_id, e,
            )

    def _is_battery_entity(self, entity_id: str) -> bool:
        """Check if entity is a tracked battery entity."""
        if entity_id in self.entities:
            _LOGGER.debug(
                "_is_battery_entity: entity_id=%s result=true source=tracker_cache",
                entity_id,
            )
            return True
        if entity_id.startswith("binary_sensor."):
            _LOGGER.debug(
                "_is_battery_entity: entity_id=%s result=false reason=binary_sensor",
                entity_id,
            )
            return False
        try:
            entity_registry = er.async_get(self.hass)
            entry = entity_registry.entities.get(entity_id)
            if entry:
                dc = entry.device_class or entry.original_device_class
                result = dc == BATTERY_DEVICE_CLASS
                _LOGGER.debug(
                    "_is_battery_entity: entity_id=%s device_class=%s result=%s source=entity_registry",
                    entity_id, dc, result,
                )
                return result
            state = self.hass.states.get(entity_id)
            result = (
                state is not None
                and state.attributes.get("device_class") == BATTERY_DEVICE_CLASS
            )
            _LOGGER.debug(
                "_is_battery_entity: entity_id=%s result=%s source=state_attributes",
                entity_id, result,
            )
            return result
        except Exception:
            _LOGGER.debug(
                "_is_battery_entity: entity_id=%s result=false reason=exception",
                entity_id,
            )
            return False

    async def query_entities(self) -> Dict[str, Any]:
        """Return all battery entities below the fixed threshold.

        For each entity selected below the threshold, performs a fresh lookup
        against the device, entity, and area registries to attach the owning
        device's manufacturer, model, and area name to the response payload.

        Sorted by battery level ascending (lowest first).
        """
        _LOGGER.debug(
            "query_entities: starting threshold=%d%% tracked_total=%d",
            BATTERY_THRESHOLD, len(self.entities),
        )

        entity_registry = er.async_get(self.hass)
        device_registry = dr.async_get(self.hass)
        area_registry = ar.async_get(self.hass)

        low_battery: List[Dict[str, Any]] = []

        for entity in self.entities.values():
            if not (0 <= entity.battery_level < BATTERY_THRESHOLD):
                _LOGGER.debug(
                    "query_entities: entity_id=%s battery_level=%.1f%% above_threshold=true skipping",
                    entity.entity_id, entity.battery_level,
                )
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
                        _LOGGER.debug(
                            "query_entities: entity_id=%s device_id=%s "
                            "manufacturer=%s model=%s area_id=%s",
                            entity.entity_id, entry.device_id,
                            device.manufacturer, device.model, area_id,
                        )
                    else:
                        _LOGGER.debug(
                            "query_entities: entity_id=%s device_id=%s device=not_found",
                            entity.entity_id, entry.device_id,
                        )
                if area_id:
                    area = area_registry.async_get_area(area_id)
                    if area:
                        data["area_name"] = area.name
                        _LOGGER.debug(
                            "query_entities: entity_id=%s area_id=%s area_name=%s",
                            entity.entity_id, area_id, area.name,
                        )
            else:
                _LOGGER.debug(
                    "query_entities: entity_id=%s registry_entry=not_found "
                    "using_cached_device_info=true",
                    entity.entity_id,
                )

            low_battery.append(data)

        low_battery.sort(
            key=lambda d: (d["battery_level"], d.get("device_name") or d["entity_id"])
        )

        result_count = len(low_battery)
        _LOGGER.info(
            "query_entities: complete below_threshold=%d tracked_total=%d threshold=%d%%",
            result_count, len(self.entities), BATTERY_THRESHOLD,
        )
        _LOGGER.debug(
            "query_entities: result entity_ids=%s",
            [d["entity_id"] for d in low_battery],
        )

        return {
            "entities": low_battery,
            "total": result_count,
        }
