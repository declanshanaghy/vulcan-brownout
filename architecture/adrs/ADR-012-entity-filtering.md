# ADR-012: Binary Sensor Entity Filtering Strategy

**Date**: February 22, 2026
**Status**: Proposed
**Deciders**: FiremanDecko (Architect), ArsonWells (Lead Developer)
**Sprint**: Sprint 3

## Context

QA discovered 45 devices in the test HA instance with `device_class="battery"` but `battery_level` NOT available. These are binary sensors (report on/off state, not percentage).

**Problem**: Binary sensors appear in battery list with unavailable status, causing:
1. Confusion (why is this device "unavailable"?)
2. Data quality issues (list shows devices that don't have battery percentages)
3. Notification spam (notifications triggered for unavailable entities)

**Example**:
```
sensor.front_door_lock_battery: battery_level=8% ✅ (valid)
binary_sensor.door_open: device_class=battery, no battery_level ❌ (invalid)
```

Only the first should appear in the battery list.

## Options Considered

### Option 1: Filter at Query Time (Server-Side) (CHOSEN)

When fetching battery devices, filter on backend:
```python
def is_battery_entity(entity_id: str) -> bool:
    domain = entity_id.split('.')[0]
    if domain == 'binary_sensor':
        return False  # Binary sensors excluded

    battery_level = entity.attributes.get('battery_level')
    if battery_level is None:
        return False  # No battery_level attribute

    try:
        level = float(battery_level)
        if not (0 <= level <= 100):
            return False  # Invalid range
    except (TypeError, ValueError):
        return False  # Non-numeric

    return True  # ✅ Valid battery entity
```

**Pros**:
- ✅ Filters at source (no bad data sent to frontend)
- ✅ Cleaner API responses (only valid entities)
- ✅ Reduces frontend complexity
- ✅ Prevents notifications for non-battery entities
- ✅ Easier to extend (add new criteria later)

**Cons**:
- Requires backend change
- Must be done in every query

**Verdict**: ✅ Best choice

---

### Option 2: Filter at Display Time (Client-Side)

Send all battery entities to frontend, filter in JavaScript before rendering.

**Pros**:
- No backend change needed

**Cons**:
- ❌ Bad data still sent over network
- ❌ Frontend must implement filtering logic
- ❌ Harder to maintain (filtering logic in two places)
- ❌ Notifications can still be triggered for invalid entities
- ❌ Confusing UX (temporarily show invalid entity, then filter)

**Verdict**: ❌ Not acceptable

---

### Option 3: Hybrid Approach

Backend sends all entities, frontend filters AND caches filtered list.

**Pros**:
- Flexibility

**Cons**:
- ❌ Duplicate filtering logic
- ❌ More complex than necessary
- ❌ Still sends bad data over network

**Verdict**: ❌ Over-engineered

---

## Decision

**Filter entities at query time on backend (Option 1).**

### Filtering Criteria

An entity is a valid battery device if:
1. Domain is NOT 'binary_sensor' (binary_sensors excluded)
2. Attribute `device_class` is exactly 'battery'
3. Attribute `battery_level` exists and is available (not "unknown" or "unavailable")
4. Attribute `battery_level` is numeric (string representation of number)
5. Attribute `battery_level` is in range 0-100 (valid battery percentage)

All criteria must be met.

### Implementation

```python
def is_battery_entity(entity_id: str, hass) -> bool:
    """
    Check if entity should appear in battery list.

    Criteria:
    1. NOT a binary_sensor
    2. device_class == 'battery'
    3. battery_level attribute exists
    4. battery_level is numeric (0-100)
    """
    # Criterion 1: Exclude binary_sensors
    domain = entity_id.split('.')[0]
    if domain == 'binary_sensor':
        return False

    # Get entity state
    entity = hass.states.get(entity_id)
    if not entity:
        return False

    # Criterion 2: Check device_class
    if entity.attributes.get('device_class') != 'battery':
        return False

    # Criterion 3 & 4: Check battery_level attribute
    battery_level = entity.attributes.get('battery_level')
    if battery_level is None:
        return False  # Missing attribute

    # Handle string representation
    if battery_level == 'unknown' or battery_level == 'unavailable':
        return False  # Invalid state

    # Criterion 5: Validate numeric range
    try:
        level = float(battery_level)
        if not (0 <= level <= 100):
            return False  # Out of range
    except (TypeError, ValueError):
        return False  # Not numeric

    return True  # ✅ Valid battery entity
```

### Apply Filtering Everywhere

Modify these functions in `battery_monitor.py`:
1. `get_battery_entities()` — Entity discovery (startup)
2. `query_devices()` — Query handler (pagination)
3. `on_state_changed()` — Real-time updates (only process valid entities)

### Example Impact

**Before Filtering**:
```
Total entities: 47
  - Valid battery sensors: 42
  - Invalid (binary sensors, no battery_level): 5
Query result: 47 devices
```

**After Filtering**:
```
Total entities: 47
  - Valid battery sensors: 42
  - Filtered out: 5
Query result: 42 devices (clean)
```

### Empty State Handling

If no battery entities found after filtering:
- Show friendly empty state message
- "No battery devices found. Check your Home Assistant configuration."
- Include link to documentation
- Provide "Refresh" button to retry query

---

## Backward Compatibility

### User Migration

Existing users (Sprint 1-2) will see:
1. On first page load after upgrade: some devices disappear (the invalid ones)
2. Device list becomes smaller (only valid battery devices)
3. No data loss (settings/thresholds for valid devices preserved)

**Mitigation**:
- Add release notes: "Sprint 3: Improved data quality — binary sensors and devices without battery_level are now excluded"
- Provide migration guide (optional per-device threshold rules unaffected)

### Threshold Rules

If user had a threshold rule for a removed entity:
- Rule still exists in config entry (no error)
- Rule is ignored (entity no longer exists)
- No action needed

---

## Real-Time Updates

When entity state changes:
1. Check: Is this entity valid (per criteria above)?
2. If YES: Process update (send to subscribers, check notifications)
3. If NO: Ignore update (skip)

This prevents invalid entities from triggering notifications or UI updates.

---

## Testing Strategy

1. **Unit Tests**:
   - Test `is_battery_entity()` with:
     - Valid sensor (domain=sensor, device_class=battery, battery_level=50)
     - Binary sensor (domain=binary_sensor, should return False)
     - Sensor missing battery_level (should return False)
     - Sensor with invalid battery_level ("unknown", negative, > 100)
     - Sensor with non-numeric battery_level ("low", "critical")

2. **Integration Tests**:
   - Query HA instance with mixed entities
   - Verify count = valid battery sensors only
   - Verify invalid entities not in response

3. **QA Tests**:
   - Verify 45 binary sensors removed from test HA instance
   - Verify thresholds for remaining devices still work
   - Verify empty state shown if no batteries (after filter)

4. **Regression Tests**:
   - Sprint 2 features still work (real-time, thresholds, sort/filter)
   - No valid batteries accidentally filtered

---

## Consequences

### Positive
- ✅ Cleaner device list (only valid battery entities)
- ✅ Better data quality
- ✅ Prevents notifications for non-battery entities
- ✅ Simpler frontend (no filtering logic needed)
- ✅ Easier to extend criteria in future

### Negative
- ⚠️ Users may wonder why some entities disappeared
- ⚠️ Requires backend change + rollout
- ⚠️ Threshold rules for removed entities become orphaned (harmless but messy)

### Mitigation
- Release notes explaining change
- Migration guide for users who had thresholds on invalid entities
- Validation in config flow to prevent new invalid rules

---

## Criteria Evolution (Future Sprints)

Could expand filtering criteria later:
- Exclude by device_type (only battery sensors, not generic sensors)
- Exclude by manufacturer
- Exclude unavailable entities temporarily (vs. permanently)
- Custom filtering rules per user

Current implementation is simple and extensible.

---

## Related Decisions

- ADR-010: Notification Service (won't trigger for invalid entities)
- ADR-009: Cursor-Based Pagination (works only with filtered valid entities)

---

**Decision**: ✅ Server-side filtering at query time
**Implementation**: Sprint 3, Story 1 (Quick Win)
**Owner**: ArsonWells (Lead Developer)
**Reviewed by**: FiremanDecko (Architect)
