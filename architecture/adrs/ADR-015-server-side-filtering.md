# ADR-015: Server-Side Filtering Architecture

**Date**: 2026-02-22
**Status**: Accepted
**Sprint**: Sprint 5
**Author**: FiremanDecko (Architect)

---

## Problem

**Sprint 2-4 Implementation (Current)**: The panel uses client-side status filtering (critical/warning/healthy/unavailable toggle chips) applied to the already-fetched page of results. The `query_devices` WebSocket command accepts no filter parameters beyond sort options.

**Why This Is Architecturally Insufficient at Scale**:

With cursor-based pagination (ADR-009), the server returns one page (up to 100 items) of the full result set. Any filter logic applied on the client only operates on that one page. If a user has 200 battery devices and selects "show only Aqara devices in the Kitchen" when only 2 of those 200 devices match, the client-side filter would:

1. Receive the first 50 devices (page 1 of 4)
2. Apply the filter to those 50, potentially finding 0 or 1 matching device
3. Display an incomplete result — the remaining matching device(s) on pages 2-4 are silently hidden
4. The user cannot discover the hidden devices without clearing the filter

This is a silent data integrity failure, not a UX limitation. It misleads users about which devices exist in their installation.

**New Filter Categories Requested (Sprint 5)**:
- Manufacturer (from device_registry: Aqara, Hue, IKEA, Sonoff, etc.)
- Device class (from entity attributes: typically just "battery")
- Status (critical, warning, healthy, unavailable — replaces client-side toggles)
- Room/Area (from area_registry: Living Room, Kitchen, Bedroom, etc.)

These four categories require different data sources (device registry, area registry, computed status) that are only available server-side.

---

## Options Considered

### Option 1: Client-Side Filtering Only (Current Approach, Extended)

**Approach**: Fetch all devices (no limit) and filter in the browser.

**Pros**:
- No backend changes required
- Instant filtering response (no network round-trip)
- Works offline

**Cons**:
- Requires loading all devices before filtering is possible (could be 500+ items)
- Memory and render overhead for large device sets
- Manufacturer and area data not available in current API response (would require additional API calls)
- Fundamentally broken with cursor pagination (ADR-009 established pagination for a reason)
- No path to scale — gets worse as device count grows
- Fetching all devices defeats the purpose of pagination

**Verdict**: Rejected. Architecturally incompatible with cursor-based pagination at scale.

---

### Option 2: Server-Side Filtering via Updated query_devices (CHOSEN)

**Approach**: Add optional filter parameters to `query_devices`. Backend applies filters before pagination, ensuring the paginated result set reflects only matching devices.

**Filter params added to query_devices**:
```
filter_manufacturer: string[]   (OR within category)
filter_device_class: string[]   (OR within category)
filter_status: string[]         (OR within category)
filter_area: string[]           (area name strings, OR within category)
```

**AND logic across categories**:
```
WHERE (manufacturer IN filter_manufacturer OR filter_manufacturer empty)
  AND (device_class IN filter_device_class OR filter_device_class empty)
  AND (status IN filter_status OR filter_status empty)
  AND (area IN filter_area OR filter_area empty)
```

**New command `get_filter_options`**:
A separate command returns the available values for each filter category, derived from the actual HA device_registry and area_registry. This ensures dropdowns show only manufacturers/areas that actually exist in the user's installation.

**Pros**:
- Correct result set regardless of pagination (filter applied before slicing)
- Total count in response reflects filtered total (accurate "showing N of M" display)
- Backward compatible (all filter params are optional; omitting = no filter)
- No new Python dependencies
- Manufacturer and area data already available in HA's device_registry/area_registry
- Cursor reset on filter change is well-defined and safe (return to page 1)
- Scales correctly with growing device count

**Cons**:
- Filter change requires a server round-trip (vs instant client-side)
- Backend complexity increases (new filter logic in battery_monitor.py)
- Cursor must be reset on every filter change (pagination restarts)
- Need to implement `get_filter_options` command (one-time, cached client-side)

**Verdict**: Chosen. Only architecturally correct solution for paginated datasets.

---

### Option 3: Hybrid (Client-Side for Status, Server-Side for Others)

**Approach**: Keep status as client-side toggles, add manufacturer/area/device_class server-side.

**Pros**:
- Status filter remains instant (no round-trip)
- Smaller backend change

**Cons**:
- Still architecturally broken for status: if page 1 has 50 devices but only 10 match status filter, 40 devices of the 50 are hidden and 40 from subsequent pages that match are never shown
- Two different filter paradigms (some client-side, some server-side) creates confusion for both users and developers
- Status is a computed property (server computes it via threshold logic), so the server already has it — no reason to duplicate on client
- Sprint 5 acceptance criteria explicitly requires server-side status filtering

**Verdict**: Rejected. Inconsistency without benefit; status filter has the same correctness problem as the other categories.

---

## Decision

**Implement Option 2: Server-side filtering via updated `query_devices` plus new `get_filter_options` command.**

All four filter categories (manufacturer, device_class, status, area) are applied server-side in `battery_monitor.py` before pagination. Filter parameters are optional and backward compatible. A new `get_filter_options` command provides dynamic filter population from HA registries.

---

## Filter Parameter Schema

### Updated query_devices

```json
{
  "type": "vulcan-brownout/query_devices",
  "limit": 50,
  "cursor": null,
  "sort_key": "priority",
  "sort_order": "asc",
  "filter_manufacturer": ["Aqara", "Hue"],
  "filter_device_class": ["battery"],
  "filter_status": ["critical", "warning"],
  "filter_area": ["Living Room", "Kitchen"]
}
```

**Rules**:
- All filter params are optional (omit = no filter on that category)
- Empty array `[]` is treated identically to omitting the param (no filter)
- AND logic across categories; OR logic within each category
- Filter application order: filter first, then sort, then paginate
- `total` in response reflects filtered count, not unfiltered count

### New get_filter_options

```json
→ { "type": "vulcan-brownout/get_filter_options" }

← {
    "manufacturers": ["Aqara", "Hue", "IKEA", "Sonoff"],
    "device_classes": ["battery"],
    "areas": [
      { "id": "area_001", "name": "Living Room" },
      { "id": "area_002", "name": "Kitchen" }
    ],
    "statuses": ["critical", "warning", "healthy", "unavailable"]
  }
```

**Data sources**:
- `manufacturers`: `device_registry.async_get(hass).devices` → `device.manufacturer` field, deduplicated, sorted, nulls excluded
- `device_classes`: entity attributes `device_class`, deduplicated, sorted (typically just `["battery"]`)
- `areas`: `area_registry.async_get(hass).areas` filtered to only areas containing at least one battery entity, sorted by name, includes `{ id, name }` pairs
- `statuses`: Fixed list `["critical", "warning", "healthy", "unavailable"]` (all statuses always possible)

**Maximum values per category**: 20 (truncated; frontend shows "and N more" if exceeded).

---

## Consequences

### Positive
- **Correctness**: Filtered result set is always complete, regardless of pagination depth
- **Backward compatible**: Old clients without filter params continue to work unchanged
- **Dynamic population**: Filter dropdowns reflect actual HA installation (no hardcoded lists)
- **Accurate counts**: `total` in response reflects filtered total, enabling correct "N devices found" UI
- **Single source of truth**: Status is computed once on server (threshold logic), not duplicated on client
- **Scalable**: Correct for 50 or 5,000 devices

### Negative
- **Network round-trip on filter change**: Each filter change triggers a new `query_devices` call. Mitigated by 300ms debounce on desktop and mobile bottom-sheet staging.
- **Cursor invalidation**: Cursor must reset to null on every filter change. This is safe and expected — it's the same cursor behavior required when sort order changes (ADR-009).
- **Backend complexity**: `battery_monitor.py` grows with new filter methods. Contained in a dedicated `_apply_filters()` method to keep `query_devices` readable.
- **Mock server update required**: `server.py` must implement filter support for E2E tests. This is a testing infrastructure cost, not a production cost.

### Cursor Reset Behavior

Every filter change resets the pagination cursor to null before issuing a new `query_devices` call. Rationale: a cursor points to a specific position within a specific (pre-filter) ordered result set. After filters change, the result set is different; the cursor position is meaningless and potentially points to an item not in the new result set.

**This is identical to the behavior required when sort order changes (documented in ADR-009).**

Frontend implementation: `this._current_cursor = null` immediately before any `query_devices` call triggered by a filter change.

### localStorage Persistence

Filter state (all four categories) is persisted to `localStorage` under key `vulcan_brownout_filters`:
```json
{ "manufacturer": [], "device_class": [], "status": [], "area": [] }
```

Restored before the first `query_devices` call on panel load. This avoids an unfiltered flash: the first query includes restored filters, not an unfiltered request followed by a filtered re-request.

---

## Implementation Notes

### Filter Application Order in battery_monitor.py

```
1. Start with all tracked battery entities (self.entities.values())
2. Apply _apply_filters(entities, filters) → filtered list
3. Apply _apply_sort(filtered, sort_key, sort_order) → sorted list
4. Apply _apply_pagination(sorted, cursor, limit) → paginated slice
5. Return { devices, total (of filtered), has_more, next_cursor }
```

`total` is computed from the filtered (pre-pagination) list length, not from `self.entities`.

### get_filter_options Data Collection

The `get_filter_options` handler reads from HA registries at request time (not cached server-side):

```python
async def handle_get_filter_options(hass, connection, msg):
    entity_reg = er.async_get(hass)
    device_reg = dr.async_get(hass)
    area_reg = area_registry.async_get(hass)
    battery_monitor = hass.data.get(DOMAIN)

    # Manufacturers: from device registry, for devices with battery entities
    manufacturers = set()
    for entity_id in battery_monitor.entities:
        entry = entity_reg.entities.get(entity_id)
        if entry and entry.device_id:
            device = device_reg.async_get(entry.device_id)
            if device and device.manufacturer:
                manufacturers.add(device.manufacturer)

    # Areas: from area registry, for areas with battery entities
    area_ids_with_batteries = set()
    for entity_id in battery_monitor.entities:
        entry = entity_reg.entities.get(entity_id)
        if entry and entry.area_id:
            area_ids_with_batteries.add(entry.area_id)
        elif entry and entry.device_id:
            device = device_reg.async_get(entry.device_id)
            if device and device.area_id:
                area_ids_with_batteries.add(device.area_id)

    areas = []
    for area_id in area_ids_with_batteries:
        area = area_reg.async_get_area(area_id)
        if area and area.name:
            areas.append({"id": area_id, "name": area.name})

    return {
        "manufacturers": sorted(list(manufacturers))[:MAX_FILTER_OPTIONS],
        "device_classes": ["battery"],
        "areas": sorted(areas, key=lambda a: a["name"])[:MAX_FILTER_OPTIONS],
        "statuses": SUPPORTED_STATUSES,
    }
```

### Area Lookup Priority

For area assignment on a battery entity, the lookup order is:
1. Entity's own `area_id` from entity_registry (direct entity-level area assignment)
2. Device's `area_id` from device_registry (device-level area, inherited by entity)
3. No area (entity excluded from area filter options)

This matches HA's own area assignment semantics.

### Filter Logic in query_devices

```python
def _apply_filters(self, devices, filters):
    """Apply AND-across-categories, OR-within-category filter logic."""
    if not filters:
        return devices

    result = []
    for entity, status in devices:
        # AND across categories: all active filters must match
        if filters.get("filter_manufacturer"):
            manufacturer = self._get_entity_manufacturer(entity.entity_id)
            if manufacturer not in filters["filter_manufacturer"]:
                continue

        if filters.get("filter_device_class"):
            device_class = entity.state.attributes.get("device_class", "")
            if device_class not in filters["filter_device_class"]:
                continue

        if filters.get("filter_status"):
            if status not in filters["filter_status"]:
                continue

        if filters.get("filter_area"):
            area_name = self._get_entity_area_name(entity.entity_id)
            if area_name not in filters["filter_area"]:
                continue

        result.append((entity, status))

    return result
```

Empty filter arrays are pre-normalized to None/omitted before calling `_apply_filters`, so the `if filters.get(...)` guard correctly skips empty filter categories.

---

## Migration Path

**From Sprint 4 to Sprint 5**:
1. All existing `query_devices` calls without filter params continue to work unchanged
2. New filter params are additive (optional fields in voluptuous schema)
3. Frontend reads `vulcan_brownout_filters` from localStorage on load; if absent, defaults to empty arrays (no filters active)
4. Status filter chips in Sprint 4 (client-side toggles) are replaced by the server-side status filter in Sprint 5. The old client-side filter_state property is superseded by the new active_filters structure.

**API Version**: Bumped to 5.0.0 (new command added, query_devices schema extended).

---

## Testing Strategy

### Backend Unit Tests
- `_apply_filters()` with single category: manufacturer filter returns only matching entities
- `_apply_filters()` with multiple categories: AND logic (manufacturer AND area)
- `_apply_filters()` within a category: OR logic (manufacturer=[Aqara, Hue])
- `_apply_filters()` with empty array: treated same as no filter
- `_apply_filters()` with no matching entities: returns empty list (not error)
- `get_filter_options()`: returns correct manufacturers from device registry
- `get_filter_options()`: returns only areas with battery entities
- `query_devices()` with filters: total reflects filtered count, not entity count

### Integration Tests
- Filter by manufacturer, verify only matching devices returned
- Filter by manufacturer AND area, verify AND logic
- Filter by two manufacturers, verify OR logic within category
- Filter returns empty list, verify has_more=false, next_cursor=null
- Cursor pagination on filtered result set: page 1 cursor leads to correct page 2

### Mock Server Tests
- Mock server `_handle_query_devices` applies filter params correctly
- Mock server `_handle_get_filter_options` returns options derived from mock entities
- E2E tests: filter bar populates from `get_filter_options` response

---

## Revision History

| Date | Status | Author | Notes |
|------|--------|--------|-------|
| 2026-02-22 | Accepted | FiremanDecko | Initial ADR for Sprint 5 |
