# ADR-009: Cursor-Based Pagination for Infinite Scroll

**Date**: February 22, 2026
**Status**: Proposed
**Sprint**: Sprint 3

## Problem

Offset-based pagination breaks with real-time updates. If new devices inserted during pagination, offsets shift, causing duplicates or skipped items.

**Example**:
```
Page 1 (offset=0, limit=50): Items 0-49
  2 new devices added (inserted at position 40)
Page 2 (offset=50, limit=50): Items 50-99
  → Items 50-51 now at 52+, duplicates appear
```

For 150+ battery devices with real-time updates, this is unacceptable.

## Decision

**Use cursor-based pagination (Option 2)**

Cursor format: `base64("{last_changed}|{entity_id}")`

**How it works**:
1. Client requests: `{limit: 50, cursor: null}` (first page)
2. Server returns items + `next_cursor` for following request
3. Cursor points to specific item (immutable), not position
4. New items inserted don't break pagination

## Implementation

**Cursor encoding**:
```python
import base64

def encode_cursor(last_changed: str, entity_id: str) -> str:
    data = f"{last_changed}|{entity_id}"
    return base64.b64encode(data.encode()).decode()

def decode_cursor(cursor: str) -> tuple[str, str]:
    decoded = base64.b64decode(cursor).decode()
    last_changed, entity_id = decoded.split('|', 1)
    return last_changed, entity_id
```

**Backend**:
```python
def get_devices_paginated(cursor: str | None, limit: int) -> dict:
    all_devices = get_all_battery_devices()
    all_devices = apply_sort(all_devices, 'last_changed')

    start_index = 0
    if cursor:
        last_changed, entity_id = decode_cursor(cursor)
        for i, device in enumerate(all_devices):
            if device.last_changed == last_changed and device.entity_id == entity_id:
                start_index = i + 1
                break

    page = all_devices[start_index:start_index + limit]
    next_cursor = None
    if start_index + limit < len(all_devices):
        last = page[-1]
        next_cursor = encode_cursor(last.last_changed, last.entity_id)

    return {
        'devices': page,
        'total': len(all_devices),
        'has_more': start_index + limit < len(all_devices),
        'next_cursor': next_cursor
    }
```

**API response**:
```json
{
  "devices": [...20 devices...],
  "total": 150,
  "has_more": true,
  "next_cursor": "base64(2026-02-22T10:30:45Z|sensor.garage_sensor_battery)"
}
```

## Consequences

**Positive**:
- Stable ordering (cursor points to specific item)
- Immune to real-time insertions/deletions
- Efficient (can use database indexes)
- Scales to 1000+ devices
- Industry standard (Google, Facebook, Stripe use it)

**Negative**:
- More complex than offset
- Requires stable sort order (last_changed + entity_id)
- Cursor invalid if sort order changes mid-pagination
- Edge case: if device deleted, cursor might miss

**Mitigation**:
- Lock sort order during pagination
- If user changes sort, reset to first page
- If cursor not found, restart from beginning (log warning)

## Breaking change

- API version changes from 2.0.0 to 3.0.0
- Document: "Sprint 3: Pagination changed from offset to cursor"
- Old clients expecting `offset` field will break
