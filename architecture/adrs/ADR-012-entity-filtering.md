# ADR-012: Binary Sensor Entity Filtering Strategy

**Date**: February 22, 2026
**Status**: Proposed
**Sprint**: Sprint 3

## Problem

QA discovered 45 devices with `device_class=battery` but NO `battery_level` attribute (binary sensors report on/off, not percentage). These appear as "unavailable" in battery list, causing confusion and data quality issues.

**Example**:
```
sensor.front_door_lock_battery: battery_level=8% ✅ (valid)
binary_sensor.door_open: device_class=battery, no battery_level ❌ (invalid)
```

Only the first should appear in the battery list.

## Decision

**Filter entities at query time on backend (Option 1)**

Entity is valid battery device if:
1. Domain is NOT 'binary_sensor'
2. Attribute `device_class` is exactly 'battery'
3. Attribute `battery_level` exists and is available
4. Attribute `battery_level` is numeric (0-100)

## Implementation

**Filtering function**:
```python
def is_battery_entity(entity_id: str, hass) -> bool:
    # Exclude binary_sensors
    domain = entity_id.split('.')[0]
    if domain == 'binary_sensor': return False

    entity = hass.states.get(entity_id)
    if not entity: return False

    # Check device_class
    if entity.attributes.get('device_class') != 'battery': return False

    # Check battery_level attribute
    battery_level = entity.attributes.get('battery_level')
    if battery_level is None or battery_level in ('unknown', 'unavailable'): return False

    # Validate numeric range
    try:
        level = float(battery_level)
        if not (0 <= level <= 100): return False
    except (TypeError, ValueError):
        return False

    return True
```

**Apply filtering in**:
- `get_battery_entities()` — Entity discovery (startup)
- `query_devices()` — Query handler (pagination)
- `on_state_changed()` — Real-time updates (only process valid entities)

**Impact**:
- Before: 47 devices (42 valid + 5 invalid)
- After: 42 devices (clean, valid battery sensors only)

## Consequences

**Positive**:
- Cleaner device list (only valid battery entities)
- Better data quality
- Prevents notifications for non-battery entities
- Simpler frontend (no filtering logic needed)
- Extensible (easy to add new criteria later)

**Negative**:
- Users may wonder why some entities disappeared
- Requires backend change
- Threshold rules for removed entities become orphaned (harmless but messy)

**Mitigation**:
- Release notes: "Sprint 3: Improved data quality — binary sensors and devices without battery_level are now excluded"
- Migration guide for users with threshold rules on removed entities
- Validation in config flow to prevent new invalid rules

## Empty state handling

If no battery entities found after filtering:
- Show friendly message: "No battery devices found. Check your Home Assistant configuration."
- Include documentation link
- "Refresh" button to retry

## Real-time updates

When entity state changes:
1. Check: Is this entity valid (per criteria)?
2. If YES: Process update (send to subscribers, check notifications)
3. If NO: Ignore update (skip)

Prevents invalid entities from triggering notifications or UI updates.

## Testing

- Unit tests: Valid/invalid entity detection
- Integration tests: Query HA with mixed entities
- QA tests: Verify 45 binary sensors removed
- Regression tests: Sprint 2 features still work

## Future (Sprint 3+)

Could expand criteria:
- Exclude by device_type
- Exclude by manufacturer
- Exclude unavailable entities temporarily
- Custom filtering rules per user
