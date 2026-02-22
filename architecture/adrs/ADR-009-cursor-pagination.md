# ADR-009: Cursor-Based Pagination for Infinite Scroll

**Date**: February 22, 2026
**Status**: Proposed
**Deciders**: FiremanDecko (Architect), ArsonWells (Lead Developer)
**Sprint**: Sprint 3

## Context

Sprint 2 used offset-based pagination (`offset=0, limit=50`) to fetch device lists. This works fine for small datasets (< 50 devices) but breaks down with large device libraries (150+).

**Problem with Offset-Based Pagination**:
1. **Data Shifting** — If new devices are added between page 1 and page 2, offsets shift (duplicates or skipped items)
2. **Inconsistent Results** — Real-time updates during pagination can cause items to appear twice or disappear
3. **Performance Degradation** — Each page fetch requires scanning and skipping N items (O(n) for each request)

**Example of the Problem**:
```
Page 1 (offset=0, limit=50): Items 0-49
  User scrolls, 2 new devices added (inserted at position 40)
Page 2 (offset=50, limit=50): Items 50-99
  But the offsets shifted! Item 50 is now at 52.
  Items 50-51 appear on both pages (duplicates).
```

For 150+ battery devices with real-time updates, this is unacceptable.

## Options Considered

### Option 1: Offset-Based Pagination (Current Sprint 2)

**Pros**:
- Simple to understand and implement
- Works fine for small datasets
- Supported by most databases/ORMs

**Cons**:
- Fails with real-time updates (duplicates/skipped items)
- Performance degrades with large datasets (O(n) per request)
- Requires server-side state tracking (which devices were on previous pages)

**Verdict**: ❌ Not acceptable for 150+ devices with real-time updates

---

### Option 2: Cursor-Based Pagination (CHOSEN)

**How It Works**:
1. Client requests: `{limit: 50, cursor: null}` (or `cursor: base64(...)}`)
2. Server finds cursor position in sorted list
3. Server returns items AFTER cursor + `next_cursor` for next page
4. Cursor format: Base64-encoded `{last_changed}|{entity_id}`
5. Cursor is immutable (points to specific item, not position)

**Example**:
```
Page 1 Request:
  {limit: 50, cursor: null}

Page 1 Response:
  {
    devices: [...items 0-49...],
    total: 200,
    has_more: true,
    next_cursor: "base64(2026-02-22T10:15:30Z|sensor.kitchen_motion_battery)"
  }

Page 2 Request:
  {limit: 50, cursor: "base64(2026-02-22T10:15:30Z|sensor.kitchen_motion_battery)"}

Page 2 Response:
  {
    devices: [...items 50-99...],
    total: 200,
    has_more: true,
    next_cursor: "base64(2026-02-22T10:30:45Z|sensor.garage_sensor_battery)"
  }

Even if new devices added between requests, cursor still points to correct position.
```

**Pros**:
- ✅ Stable ordering (cursor points to specific item, not position)
- ✅ Immune to real-time insertions/deletions
- ✅ Efficient (can use database indexes on last_changed + entity_id)
- ✅ Scalable to 1000+ items
- ✅ Industry standard (Google, Facebook, Stripe all use cursor pagination)

**Cons**:
- More complex than offset (needs cursor encoding/decoding)
- Requires stable sort order (last_changed + entity_id)
- Cursor format must be deterministic

**Verdict**: ✅ Best choice for real-time, large-scale device lists

---

### Option 3: Keyset Pagination (Alternative)

Similar to cursor-based, but cursor contains the last item's keys (`{last_changed, entity_id}`) instead of base64-encoded values.

**Pros**:
- Slightly simpler than base64 encoding
- Still immune to real-time changes

**Cons**:
- Requires JSON parsing instead of base64 decode
- Longer cursor strings (not opaque)

**Verdict**: ⚠️ Similar to Option 2, but base64 is more opaque and compact

---

## Decision

**Use cursor-based pagination (Option 2) for Sprint 3 infinite scroll.**

Cursor format: `base64("{last_changed}|{entity_id}")`

Example implementation:
```python
def get_devices_paginated(cursor: str | None, limit: int, sort_key: str) -> dict:
    """Fetch paginated device list with cursor-based pagination."""
    # Step 1: Decode cursor to find starting position
    all_devices = get_all_battery_devices()
    all_devices = apply_sort(all_devices, sort_key)

    start_index = 0
    if cursor:
        last_changed, entity_id = base64_decode(cursor)
        for i, device in enumerate(all_devices):
            if device.last_changed.isoformat() == last_changed and device.entity_id == entity_id:
                start_index = i + 1  # Start AFTER cursor
                break

    # Step 2: Slice to limit
    page = all_devices[start_index:start_index + limit]

    # Step 3: Generate next cursor
    next_cursor = None
    if start_index + limit < len(all_devices):
        last_device = page[-1]
        next_cursor = base64_encode(f"{last_device.last_changed.isoformat()}|{last_device.entity_id}")

    return {
        'devices': page,
        'total': len(all_devices),
        'has_more': start_index + limit < len(all_devices),
        'next_cursor': next_cursor
    }
```

## Consequences

### Positive
- ✅ Supports 150+ device lists without UI lag
- ✅ Real-time updates don't break pagination (no duplicates/skipped items)
- ✅ Infinite scroll feels smooth (items load in background)
- ✅ Scales to 1000+ devices (if needed in future)
- ✅ Cursor is opaque (client can't guess next cursor)

### Negative
- ❌ Slightly more complex than offset (cursor encoding/decoding)
- ❌ Requires stable sort order (last_changed + entity_id)
- ❌ Cursor breaks if sort order changes mid-pagination (user scrolls with sort=priority, then changes sort to alphabetical — cursor becomes invalid)
- ⚠️ If device is deleted, cursor might point to wrong position (edge case)

### Mitigation for Negatives
1. **Cursor complexity**: Document encoding format, provide helper functions
2. **Sort order stability**: Lock sort order during pagination; if user changes sort, reset pagination to first page
3. **Device deletion**: If cursor not found, restart from beginning (log warning)

## Implementation Notes

### Cursor Encoding
```python
import base64

def encode_cursor(last_changed: str, entity_id: str) -> str:
    data = f"{last_changed}|{entity_id}"
    return base64.b64encode(data.encode('utf-8')).decode('utf-8')

def decode_cursor(cursor: str) -> tuple[str, str]:
    decoded = base64.b64decode(cursor).decode('utf-8')
    parts = decoded.split('|', 1)  # Split on first | only
    return parts[0], parts[1]
```

### Cursor Format
- Do NOT use `datetime` objects in cursor (not serializable)
- Use ISO8601 strings: `"2026-02-22T10:15:30Z"`
- Include timezone (Z for UTC)
- Example cursor: `eyIyMDI2LTAyLTIyVDEwOjE1OjMwWiIsInNlbnNvci5raXRjaGVuX21vdGlvbl9iYXR0ZXJ5In0=`

### API Versioning
- Change API version from 2.0.0 to 3.0.0 (breaking change)
- Old clients expecting `offset` will break with new API
- Document in CHANGELOG: "Sprint 3: Changed pagination from offset-based to cursor-based (breaking change)"

## Alternative: Bring Back Offset with Real-Time Fixes

If cursor-based is too complex, could use offset WITH mechanisms to fix real-time collisions:
1. Include `snapshot_id` in each response (frozen point-in-time)
2. Client keeps snapshot_id; server validates snapshot still exists before fetching next page
3. If snapshot expired, return error; client re-fetches from page 1

This adds complexity without the elegance of cursor pagination. **Not recommended.**

## References

- [REST API Pagination Best Practices](https://slack.engineering/pagination-you-re-probably-doing-it-wrong/)
- [Cursor-Based Pagination](https://medium.com/@_icyrgon/cursor-based-pagination-21ac6701da4f)
- [Google Cloud Cursor Pagination](https://cloud.google.com/apis/docs/pagination)
- [GraphQL Relay Cursor Connections](https://relay.dev/graphql-cursor-connections/)

---

**Decision**: ✅ Cursor-based pagination (Option 2)
**Implementation**: Sprint 3, Story 2
**Owner**: ArsonWells (Lead Developer)
**Reviewed by**: FiremanDecko (Architect)
