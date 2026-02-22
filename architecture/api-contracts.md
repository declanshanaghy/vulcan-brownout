# API Contracts — Sprint 5 (v5.0.0)

**Updated**: 2026-02-22 | **Status**: Sprint 5 — filtering commands added

**Breaking changes from v4.0.0**: None. All Sprint 5 additions are backward compatible.
- `query_devices` accepts new optional filter params; existing calls without them continue to work unchanged
- `get_filter_options` is a new command; old clients simply do not call it

## Commands (Frontend → Backend)

### query_devices
```json
→ {
    "type": "vulcan-brownout/query_devices",
    "limit": 50,
    "cursor": null,
    "sort_key": "priority|alphabetical|level_asc|level_desc",
    "sort_order": "asc|desc",
    "filter_manufacturer": ["Aqara", "Hue"],
    "filter_device_class": ["battery"],
    "filter_status": ["critical", "warning"],
    "filter_area": ["Living Room", "Kitchen"]
  }

← {
    "devices": [...],
    "total": N,
    "has_more": bool,
    "next_cursor": "base64"|null,
    "device_statuses": { "critical": N, "warning": N, "healthy": N, "unavailable": N }
  }
```

**Filter parameters** (all optional; added in Sprint 5):
- `filter_manufacturer`: `string[]` — OR logic within category. Matches entities whose device's `manufacturer` field equals any value in the list. Empty array or omitted = no manufacturer filter.
- `filter_device_class`: `string[]` — OR logic within category. Matches entities where `device_class` attribute equals any value in the list. Empty array or omitted = no device_class filter.
- `filter_status`: `string[]` — OR logic within category. Values must be from `["critical", "warning", "healthy", "unavailable"]`. Status is computed server-side using threshold logic. Empty array or omitted = no status filter.
- `filter_area`: `string[]` — OR logic within category. Matches entities whose area name (from area_registry) equals any value in the list. Use area names (strings), not area IDs. Empty array or omitted = no area filter.

**AND logic across categories**: A device matches only if it satisfies ALL active filter categories simultaneously.

**Filter application order**: filter → sort → paginate. The `total` in the response reflects the filtered count (number of devices matching all active filters), not the unfiltered count.

**Cursor reset requirement**: Clients MUST reset cursor to null when any filter param changes. Sending a cursor from a pre-filter query with different filter params produces undefined behavior (the cursor position refers to an item in a different result set).

**Cursor format**: `base64("{last_changed}|{entity_id}")`. Auto-filters to device_class=battery + battery_level IS NOT NULL. Binary sensors excluded. All these base filters apply before any user-specified filter params.

**Backward compatibility**: Existing clients that do not send filter params receive the full unfiltered result set as before.

---

### get_filter_options (NEW — Sprint 5)
```json
→ { "type": "vulcan-brownout/get_filter_options" }

← {
    "manufacturers": ["Aqara", "Hue", "IKEA", "Sonoff"],
    "device_classes": ["battery"],
    "areas": [
      { "id": "living_room_area_id", "name": "Living Room" },
      { "id": "kitchen_area_id", "name": "Kitchen" },
      { "id": "bedroom_area_id", "name": "Bedroom" }
    ],
    "statuses": ["critical", "warning", "healthy", "unavailable"]
  }
```

**Purpose**: Returns available values for each filter category, derived from the actual battery entities in the user's HA installation. Clients use this response to populate filter dropdown checkbox lists.

**Data sources**:
- `manufacturers`: Derived from `device_registry.devices[].manufacturer` for devices that have at least one tracked battery entity. Deduplicated, sorted alphabetically, null/empty values excluded. Maximum 20 values (truncated if more exist).
- `device_classes`: Derived from battery entity `device_class` attributes. Deduplicated, sorted. Typically `["battery"]` only. Maximum 20 values.
- `areas`: Derived from `area_registry.areas` filtered to only areas containing at least one tracked battery entity. Area lookup priority: entity's own `area_id` → entity's device's `area_id`. Sorted alphabetically by name. Areas without a name are excluded. Returns `{ id, name }` objects. Maximum 20 values.
- `statuses`: Fixed list `["critical", "warning", "healthy", "unavailable"]` — all four statuses are always possible and always returned. Not dynamically derived.

**Freshness policy**: Options reflect HA state at the time of the request. The response is not pushed in real-time — if a user adds a new device or room, filter options remain stale until the client re-fetches (typically on panel reload). Clients may cache the response for the duration of the session.

**Caching recommendation**: Call once on panel load, cache in memory (`this._filter_options`). Do not cache in localStorage (options reflect current HA state, which may change between sessions). Provide a [Retry] mechanism in the UI for when the fetch fails.

**Empty categories**: If no battery entities have a known manufacturer, `manufacturers: []`. Clients should show "No options available" in the dropdown and disable the filter trigger for that category.

**Error handling**: If the command fails, clients should show an error state in filter dropdowns (not a page-level error) with a [Retry] button.

---

### subscribe (unchanged from S2)
```json
→ { "type": "vulcan-brownout/subscribe" }
← { "subscription_id": "sub_abc", "status": "subscribed" }
```

---

### set_threshold (unchanged from S2)
```json
→ {
    "type": "vulcan-brownout/set_threshold",
    "data": {
      "global_threshold": 20,
      "device_rules": { "entity_id": threshold }
    }
  }
```

---

### get_notification_preferences (unchanged from S3)
```json
→ { "type": "vulcan-brownout/get_notification_preferences" }
← {
    "enabled": bool,
    "frequency_cap_hours": 1|6|24,
    "severity_filter": "critical_only|critical_and_warning",
    "per_device": { "entity_id": { "enabled": bool, "frequency_cap_hours": N } },
    "notification_history": [...last 10-20...]
  }
```

---

### set_notification_preferences (unchanged from S3)
```json
→ {
    "type": "vulcan-brownout/set_notification_preferences",
    "data": {
      "enabled": bool,
      "frequency_cap_hours": 1|6|24,
      "severity_filter": "critical_only|critical_and_warning",
      "per_device": { "entity_id": { "enabled": bool, "frequency_cap_hours": N } }
    }
  }
```

---

## Events (Backend → Frontend)

### status (on connect + config changes)
```json
← {
    "type": "vulcan-brownout/status",
    "data": {
      "status": "connected",
      "version": "5.0.0",
      "threshold": N,
      "theme": "dark|light",
      "notifications_enabled": bool,
      "notification_preferences": {...},
      "device_statuses": {...}
    }
  }
```

---

### device_changed
```json
← {
    "type": "vulcan-brownout/device_changed",
    "data": {
      "entity_id": "...",
      "battery_level": N,
      "status": "critical|warning|healthy",
      "available": bool,
      ...
    }
  }
```

---

### threshold_updated
```json
← {
    "type": "vulcan-brownout/threshold_updated",
    "data": {
      "global_threshold": N,
      "device_rules": {...},
      "affected_devices": [...]
    }
  }
```

---

### notification_sent (unchanged from S3)
```json
← {
    "type": "vulcan-brownout/notification_sent",
    "data": {
      "entity_id": "...",
      "device_name": "...",
      "battery_level": N,
      "status": "critical|warning",
      "message": "...",
      "notification_id": "..."
    }
  }
```

---

## Error Codes

| Code | Description |
|------|-------------|
| `invalid_request` | Malformed request (missing required field, wrong type) |
| `invalid_limit` | `limit` is not 1-100 |
| `invalid_cursor` | Cursor cannot be decoded or is malformed |
| `invalid_sort_key` | `sort_key` is not a supported value |
| `invalid_filter_status` | `filter_status` contains a value not in `["critical","warning","healthy","unavailable"]` |
| `invalid_threshold` | Threshold is not 5-100 |
| `invalid_notification_preferences` | Notification preference fields fail validation |
| `invalid_device_entity` | Referenced entity_id not found in battery entities |
| `too_many_rules` | More than 10 device_rules provided |
| `permission_denied` | HA auth check failed |
| `integration_not_loaded` | Vulcan Brownout integration data not found in hass.data |
| `subscription_limit_exceeded` | Maximum concurrent subscriptions reached |
| `internal_error` | Unexpected server-side error |

**New in Sprint 5**: `invalid_filter_status` — returned when `filter_status` contains a value other than the four supported statuses. Other filter params (manufacturer, device_class, area) accept arbitrary strings without a closed validation list.

---

## Filter Behavior Reference

### AND Logic Across Categories

The following example request returns ONLY devices that are:
- Manufactured by Aqara OR Hue (OR within manufacturer)
- AND located in Living Room OR Kitchen (OR within area)
- AND in critical OR warning status (OR within status)

```json
{
  "type": "vulcan-brownout/query_devices",
  "filter_manufacturer": ["Aqara", "Hue"],
  "filter_area": ["Living Room", "Kitchen"],
  "filter_status": ["critical", "warning"],
  "cursor": null
}
```

A device manufactured by IKEA in the Living Room would NOT match (fails manufacturer filter).
An Aqara device in the Bedroom would NOT match (fails area filter).
An Aqara device in the Living Room that is "healthy" would NOT match (fails status filter).

### Empty Filter = No Filter

These three requests are equivalent (all return unfiltered results):

```json
{ "type": "vulcan-brownout/query_devices" }
{ "type": "vulcan-brownout/query_devices", "filter_manufacturer": [] }
{ "type": "vulcan-brownout/query_devices", "filter_manufacturer": [], "filter_area": [], "filter_status": [], "filter_device_class": [] }
```

### Cursor Reset on Filter Change

When filter params change, clients must reset cursor to null:

```
Step 1: query_devices(filter_area=["Kitchen"], cursor=null) → next_cursor="abc123"
Step 2: User adds manufacturer filter
Step 3: query_devices(filter_area=["Kitchen"], filter_manufacturer=["Aqara"], cursor=null)  ← cursor RESET
Step 4: If more results: query_devices(...same filters..., cursor=response.next_cursor)      ← continue with new cursor
```

### Total Reflects Filtered Count

`total` in the response always reflects the count of devices matching ALL active filters. This is the correct value for UI display (e.g., "Showing 12 devices matching your filters"). It is NOT the total number of battery devices in HA.

---

## Breaking Changes History

| Version | Change |
|---------|--------|
| v2.0.0 | Initial cursor pagination (Sprint 2) |
| v3.0.0 | query_devices uses cursor instead of offset (Sprint 3) |
| v4.0.0 | No API changes (Sprint 4 — frontend theme detection only) |
| v5.0.0 | Added optional filter params to query_devices; added get_filter_options command (Sprint 5, backward compatible) |
