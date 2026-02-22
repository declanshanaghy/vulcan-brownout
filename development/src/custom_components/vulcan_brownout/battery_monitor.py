"""Core battery monitoring service for Vulcan Brownout integration."""

import logging
import base64
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

from homeassistant.core import HomeAssistant, State
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.helpers import entity_registry as er, device_registry as dr, area_registry as ar

from .const import (
    BATTERY_DEVICE_CLASS,
    BATTERY_THRESHOLD_DEFAULT,
    BATTERY_THRESHOLD_MAX,
    BATTERY_THRESHOLD_MIN,
    DOMAIN,
    MAX_DEVICE_RULES,
    SORT_KEY_BATTERY_LEVEL,
    SORT_KEY_AVAILABLE,
    SORT_KEY_DEVICE_NAME,
    SORT_KEY_PRIORITY,
    SORT_KEY_ALPHABETICAL,
    SORT_KEY_LEVEL_ASC,
    SORT_KEY_LEVEL_DESC,
    SORT_ORDER_ASC,
    SORT_ORDER_DESC,
    STATUS_CRITICAL,
    STATUS_WARNING,
    STATUS_HEALTHY,
    STATUS_UNAVAILABLE,
    WARNING_BUFFER,
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

    def to_dict(self, status: str = STATUS_HEALTHY) -> Dict[str, Any]:
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
            "status": status,
        }


class BatteryMonitor:
    """Service to discover and monitor battery entities with threshold support."""

    def __init__(self, hass: HomeAssistant, config_entry: Any = None) -> None:
        """Initialize battery monitor."""
        self.hass = hass
        self.config_entry = config_entry
        self.entities: Dict[str, BatteryEntity] = {}

        # Load thresholds from config entry
        if config_entry:
            options = config_entry.options
            self.global_threshold = options.get("global_threshold", BATTERY_THRESHOLD_DEFAULT)
            self.device_rules = options.get("device_rules", {})
        else:
            self.global_threshold = BATTERY_THRESHOLD_DEFAULT
            self.device_rules = {}

    async def discover_entities(self) -> None:
        """Discover all battery entities from HA registry and cache them.

        Sprint 3: Filters out binary_sensors and only includes entities with
        numeric battery_level attributes (0-100).
        """
        try:
            entity_registry = er.async_get(self.hass)
            device_registry = dr.async_get(self.hass)

            # Get all entities with device_class=battery
            for entity_entry in entity_registry.entities.values():
                # Check device_class from entity entry or original_device_class
                device_class = entity_entry.device_class or entity_entry.original_device_class
                if device_class != BATTERY_DEVICE_CLASS:
                    continue

                entity_id = entity_entry.entity_id

                # Sprint 3: Filter out binary_sensors (they report on/off, not %)
                if self._is_binary_sensor(entity_id):
                    _LOGGER.debug(f"Skipping binary_sensor: {entity_id}")
                    continue

                state = self.hass.states.get(entity_id)

                if state is None:
                    continue

                # Also check device_class from state attributes as fallback
                if device_class != BATTERY_DEVICE_CLASS:
                    attr_class = state.attributes.get("device_class")
                    if attr_class != BATTERY_DEVICE_CLASS:
                        continue

                # Sprint 3: Validate battery_level attribute exists and is numeric
                if not self._has_valid_battery_level(state):
                    _LOGGER.debug(f"Skipping entity without valid battery_level: {entity_id}")
                    continue

                # Get device name from device registry if available
                device_name = None
                if entity_entry.device_id:
                    device = device_registry.async_get(entity_entry.device_id)
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
                    entity_registry = er.async_get(self.hass)
                    entity_entry = entity_registry.entities.get(entity_id)
                    if entity_entry and entity_entry.device_id:
                        device_registry = dr.async_get(self.hass)
                        device = device_registry.async_get(entity_entry.device_id)
                        if device:
                            device_name = device.name

                battery_entity = BatteryEntity(entity_id, new_state, device_name)
                self.entities[entity_id] = battery_entity
                _LOGGER.debug(f"Updated battery entity: {entity_id} -> {battery_entity.battery_level}%")
            except Exception as e:
                _LOGGER.warning(f"Failed to update battery entity {entity_id}: {e}")

    def _is_binary_sensor(self, entity_id: str) -> bool:
        """Check if entity is a binary_sensor domain.

        Sprint 3: Binary sensors are excluded because they report on/off state,
        not numeric battery_level values.
        """
        return entity_id.startswith("binary_sensor.")

    def _has_valid_battery_level(self, state: State) -> bool:
        """Check if state has valid numeric battery_level attribute.

        Sprint 3: Battery level must exist and be numeric (0-100).

        Args:
            state: HA State object

        Returns:
            True if battery_level is valid numeric (0-100), False otherwise
        """
        battery_level = state.attributes.get("battery_level")
        if battery_level is None:
            return False

        try:
            level = float(battery_level)
            return 0 <= level <= 100
        except (TypeError, ValueError):
            return False

    def _is_battery_entity(self, entity_id: str) -> bool:
        """Check if entity is a battery entity by checking registry.

        Sprint 3: Updated to exclude binary_sensors and validate battery_level.
        """
        try:
            # Fast path: already tracked
            if entity_id in self.entities:
                return True

            # Exclude binary_sensors
            if self._is_binary_sensor(entity_id):
                return False

            entity_registry = er.async_get(self.hass)
            entity_entry = entity_registry.entities.get(entity_id)
            if entity_entry:
                device_class = entity_entry.device_class or entity_entry.original_device_class
                if device_class != BATTERY_DEVICE_CLASS:
                    return False
            else:
                # Fallback: check state attributes
                state = self.hass.states.get(entity_id)
                if not state or state.attributes.get("device_class") != BATTERY_DEVICE_CLASS:
                    return False

            # Validate battery_level attribute exists
            state = self.hass.states.get(entity_id)
            return state and self._has_valid_battery_level(state)

        except Exception:
            return False

    def get_threshold_for_device(self, entity_id: str) -> int:
        """Get effective threshold for a device."""
        if entity_id in self.device_rules:
            return self.device_rules[entity_id]
        return self.global_threshold

    def get_status_for_device(self, device: BatteryEntity) -> str:
        """Get status classification for a device."""
        if not device.available:
            return STATUS_UNAVAILABLE

        threshold = self.get_threshold_for_device(device.entity_id)
        if device.battery_level <= threshold:
            return STATUS_CRITICAL
        elif device.battery_level <= (threshold + WARNING_BUFFER):
            return STATUS_WARNING
        else:
            return STATUS_HEALTHY

    def get_device_statuses(self) -> Dict[str, int]:
        """Get count of devices in each status group."""
        counts = {
            STATUS_CRITICAL: 0,
            STATUS_WARNING: 0,
            STATUS_HEALTHY: 0,
            STATUS_UNAVAILABLE: 0,
        }

        for device in self.entities.values():
            status = self.get_status_for_device(device)
            counts[status] += 1

        return counts

    def on_options_updated(self, new_options: Dict[str, Any]) -> None:
        """Called when user changes settings via config flow."""
        self.global_threshold = new_options.get("global_threshold", BATTERY_THRESHOLD_DEFAULT)
        self.device_rules = new_options.get("device_rules", {})
        _LOGGER.info(
            f"Threshold config updated: global={self.global_threshold}, "
            f"rules={len(self.device_rules)}"
        )

    def _get_entity_manufacturer(self, entity_id: str) -> Optional[str]:
        """Get manufacturer name for a battery entity via device_registry.

        Sprint 5: Used for server-side manufacturer filtering.

        Returns:
            Manufacturer string, or None if entity has no device or device has no manufacturer.
        """
        try:
            entity_registry = er.async_get(self.hass)
            entry = entity_registry.entities.get(entity_id)
            if not entry or not entry.device_id:
                return None
            device_registry = dr.async_get(self.hass)
            device = device_registry.async_get(entry.device_id)
            if device and device.manufacturer:
                return device.manufacturer
        except Exception:
            pass
        return None

    def _get_entity_area_name(self, entity_id: str) -> Optional[str]:
        """Get area name for a battery entity via area_registry.

        Sprint 5: Used for server-side area filtering.

        Lookup priority:
        1. Entity's own area_id (entity_registry.entities[entity_id].area_id)
        2. Entity's device area_id (device_registry.async_get(device_id).area_id)
        3. None (entity has no area assignment)

        Returns:
            Area name string, or None if no area assigned or area has no name.
        """
        try:
            entity_registry = er.async_get(self.hass)
            area_reg = ar.async_get(self.hass)
            entry = entity_registry.entities.get(entity_id)
            if not entry:
                return None

            area_id = entry.area_id
            if not area_id and entry.device_id:
                device_registry = dr.async_get(self.hass)
                device = device_registry.async_get(entry.device_id)
                if device:
                    area_id = device.area_id

            if area_id:
                area = area_reg.async_get_area(area_id)
                if area and area.name:
                    return area.name
        except Exception:
            pass
        return None

    def _apply_filters(
        self,
        devices: List[Tuple],
        filter_manufacturer: Optional[List[str]] = None,
        filter_device_class: Optional[List[str]] = None,
        filter_status: Optional[List[str]] = None,
        filter_area: Optional[List[str]] = None,
    ) -> List[Tuple]:
        """Apply server-side filters to device list.

        Sprint 5: Implements AND-across-categories, OR-within-category filter logic.
        Filter application order: filter → sort → paginate.

        Args:
            devices: List of (BatteryEntity, status_str) tuples (pre-sort, pre-paginate)
            filter_manufacturer: OR filter — include devices matching any value. None = no filter.
            filter_device_class: OR filter — include devices matching any value. None = no filter.
            filter_status: OR filter — include devices matching any status. None = no filter.
            filter_area: OR filter — include devices whose area name matches any value. None = no filter.

        Returns:
            Filtered list of (BatteryEntity, status_str) tuples.
        """
        # Fast path: no active filters
        if not any([filter_manufacturer, filter_device_class, filter_status, filter_area]):
            return devices

        result = []
        for entity, status in devices:
            # AND across categories: skip device if it fails ANY active filter category
            if filter_manufacturer:
                manufacturer = self._get_entity_manufacturer(entity.entity_id)
                if manufacturer not in filter_manufacturer:
                    continue

            if filter_device_class:
                device_class = entity.state.attributes.get("device_class", "")
                if device_class not in filter_device_class:
                    continue

            if filter_status:
                if status not in filter_status:
                    continue

            if filter_area:
                area_name = self._get_entity_area_name(entity.entity_id)
                if area_name not in filter_area:
                    continue

            result.append((entity, status))

        return result

    async def get_filter_options(self) -> Dict[str, Any]:
        """Return available filter values derived from tracked battery entities.

        Sprint 5: Called by get_filter_options WebSocket command handler.

        Reads device_registry, area_registry, and entity_registry.
        Only returns values that are actually present in tracked battery entities.

        Returns:
            Dict with manufacturers, device_classes, areas, statuses keys.
        """
        from .const import MAX_FILTER_OPTIONS, SUPPORTED_STATUSES

        try:
            entity_registry = er.async_get(self.hass)
            device_registry = dr.async_get(self.hass)
            area_reg = ar.async_get(self.hass)

            manufacturers: set = set()
            device_classes: set = set()
            area_ids_seen: Dict[str, str] = {}  # area_id → area_name

            for entity_id, battery_entity in self.entities.items():
                # Collect manufacturer
                entry = entity_registry.entities.get(entity_id)
                if entry and entry.device_id:
                    device = device_registry.async_get(entry.device_id)
                    if device and device.manufacturer:
                        manufacturers.add(device.manufacturer)

                # Collect device_class
                device_class = battery_entity.state.attributes.get("device_class")
                if device_class:
                    device_classes.add(device_class)

                # Collect area
                if entry:
                    area_id = entry.area_id
                    if not area_id and entry.device_id:
                        device = device_registry.async_get(entry.device_id)
                        if device:
                            area_id = device.area_id
                    if area_id and area_id not in area_ids_seen:
                        area = area_reg.async_get_area(area_id)
                        if area and area.name:
                            area_ids_seen[area_id] = area.name

            # Build sorted areas list
            areas = [
                {"id": area_id, "name": name}
                for area_id, name in area_ids_seen.items()
            ]
            areas.sort(key=lambda a: a["name"])

            return {
                "manufacturers": sorted(list(manufacturers))[:MAX_FILTER_OPTIONS],
                "device_classes": sorted(list(device_classes))[:MAX_FILTER_OPTIONS],
                "areas": areas[:MAX_FILTER_OPTIONS],
                "statuses": SUPPORTED_STATUSES,
            }

        except Exception as e:
            _LOGGER.error(f"Error building filter options: {e}")
            raise

    @staticmethod
    def encode_cursor(last_changed: str, entity_id: str) -> str:
        """Encode cursor to base64 string.

        Sprint 3: Cursor format is base64-encoded "{last_changed}|{entity_id}"

        Args:
            last_changed: ISO8601 timestamp of last_changed
            entity_id: Entity identifier

        Returns:
            Base64-encoded cursor string
        """
        data = f"{last_changed}|{entity_id}"
        return base64.b64encode(data.encode("utf-8")).decode("utf-8")

    @staticmethod
    def decode_cursor(cursor_str: str) -> Tuple[str, str]:
        """Decode cursor from base64 string.

        Sprint 3: Cursor format is base64-encoded "{last_changed}|{entity_id}"

        Args:
            cursor_str: Base64-encoded cursor string

        Returns:
            Tuple of (last_changed, entity_id)

        Raises:
            ValueError: If cursor is invalid or cannot be decoded
        """
        try:
            decoded = base64.b64decode(cursor_str).decode("utf-8")
            parts = decoded.split("|")
            if len(parts) != 2:
                raise ValueError("Invalid cursor format")
            return parts[0], parts[1]
        except Exception as e:
            raise ValueError(f"Invalid cursor: {e}")

    async def query_devices(
        self,
        limit: int = 20,
        offset: int = 0,
        cursor: Optional[str] = None,
        sort_key: str = SORT_KEY_PRIORITY,
        sort_order: str = SORT_ORDER_ASC,
        filter_manufacturer: Optional[List[str]] = None,
        filter_device_class: Optional[List[str]] = None,
        filter_status: Optional[List[str]] = None,
        filter_area: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Query and return paginated, sorted battery devices with status.

        Sprint 3: Supports both offset-based (legacy) and cursor-based pagination.
        Cursor-based pagination is recommended for stability with large result sets.

        Sprint 5: Added server-side filtering by manufacturer, device_class, status, and area.

        Args:
            limit: Number of items to return (1-100)
            offset: Offset for legacy pagination (deprecated, use cursor instead)
            cursor: Base64-encoded cursor for cursor-based pagination
            sort_key: Sort method (priority, alphabetical, level_asc, level_desc)
            sort_order: Sort direction (asc, desc)
            filter_manufacturer: Optional list of manufacturer names to filter by (OR logic)
            filter_device_class: Optional list of device classes to filter by (OR logic)
            filter_status: Optional list of statuses to filter by (OR logic)
            filter_area: Optional list of area names to filter by (OR logic)

        Returns:
            Dict with devices, total, has_more, next_cursor, device_statuses
        """
        # Validate parameters
        if limit < 1 or limit > 100:
            raise ValueError("Limit must be between 1 and 100")
        if sort_order not in [SORT_ORDER_ASC, SORT_ORDER_DESC]:
            raise ValueError("Sort order must be 'asc' or 'desc'")

        # Support legacy sort keys
        if sort_key in [SORT_KEY_BATTERY_LEVEL, SORT_KEY_AVAILABLE, SORT_KEY_DEVICE_NAME]:
            # Map legacy keys to new format
            if sort_key == SORT_KEY_BATTERY_LEVEL:
                sort_key = SORT_KEY_LEVEL_ASC
            elif sort_key == SORT_KEY_AVAILABLE:
                sort_key = SORT_KEY_PRIORITY
            elif sort_key == SORT_KEY_DEVICE_NAME:
                sort_key = SORT_KEY_ALPHABETICAL

        if sort_key not in [SORT_KEY_PRIORITY, SORT_KEY_ALPHABETICAL, SORT_KEY_LEVEL_ASC, SORT_KEY_LEVEL_DESC]:
            raise ValueError(f"Unknown sort key: {sort_key}")

        # Convert entities to list with status
        devices = [
            (entity, self.get_status_for_device(entity))
            for entity in self.entities.values()
        ]

        # Sprint 5: Apply server-side filters BEFORE sort and pagination
        devices = self._apply_filters(
            devices,
            filter_manufacturer=filter_manufacturer,
            filter_device_class=filter_device_class,
            filter_status=filter_status,
            filter_area=filter_area,
        )

        # Sort devices
        if sort_key == SORT_KEY_PRIORITY:
            # Priority sort: critical < warning < healthy, then by level
            def status_priority(status: str) -> int:
                priority_map = {
                    STATUS_CRITICAL: 0,
                    STATUS_WARNING: 1,
                    STATUS_HEALTHY: 2,
                    STATUS_UNAVAILABLE: 3,
                }
                return priority_map.get(status, 99)

            reverse = sort_order == SORT_ORDER_DESC
            devices.sort(
                key=lambda d: (
                    status_priority(d[1]),
                    d[0].battery_level,
                    d[0].device_name,
                ),
                reverse=reverse,
            )
        elif sort_key == SORT_KEY_LEVEL_ASC:
            reverse = sort_order == SORT_ORDER_DESC
            devices.sort(
                key=lambda d: (d[0].battery_level, d[0].device_name),
                reverse=reverse,
            )
        elif sort_key == SORT_KEY_LEVEL_DESC:
            reverse = sort_order == SORT_ORDER_ASC  # Invert because we want desc
            devices.sort(
                key=lambda d: (d[0].battery_level, d[0].device_name),
                reverse=reverse,
            )
        elif sort_key == SORT_KEY_ALPHABETICAL:
            reverse = sort_order == SORT_ORDER_DESC
            devices.sort(
                key=lambda d: (d[0].device_name, d[0].battery_level),
                reverse=reverse,
            )

        # Handle pagination: cursor-based (Sprint 3) or offset-based (legacy)
        total = len(devices)
        start_index = 0

        if cursor:
            # Cursor-based pagination
            try:
                cursor_last_changed, cursor_entity_id = self.decode_cursor(cursor)
                # Find cursor position in sorted list
                for i, (entity, _) in enumerate(devices):
                    last_changed_str = (
                        entity.state.last_changed.isoformat()
                        if entity.state.last_changed
                        else ""
                    )
                    if (
                        last_changed_str == cursor_last_changed
                        and entity.entity_id == cursor_entity_id
                    ):
                        start_index = i + 1
                        break
            except ValueError as e:
                _LOGGER.warning(f"Invalid cursor, resetting to beginning: {e}")
                start_index = 0
        else:
            # Legacy offset-based pagination (if offset provided)
            if offset < 0:
                raise ValueError("Offset must be >= 0")
            start_index = offset

        # Slice to limit
        end_index = start_index + limit
        paginated_devices = devices[start_index:end_index]

        # Generate next_cursor
        next_cursor = None
        if end_index < total and paginated_devices:
            last_item = paginated_devices[-1]
            entity = last_item[0]
            last_changed_str = (
                entity.state.last_changed.isoformat()
                if entity.state.last_changed
                else ""
            )
            next_cursor = self.encode_cursor(last_changed_str, entity.entity_id)

        return {
            "devices": [device[0].to_dict(status=device[1]) for device in paginated_devices],
            "total": total,
            "offset": start_index,  # Include offset for legacy clients
            "limit": limit,
            "has_more": end_index < total,
            "next_cursor": next_cursor,  # Sprint 3: Cursor for next page
            "device_statuses": self.get_device_statuses(),
        }
