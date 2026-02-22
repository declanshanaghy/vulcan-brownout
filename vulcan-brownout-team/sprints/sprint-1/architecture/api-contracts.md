# Vulcan Brownout: API Contracts

## Overview

All communication between the Vulcan Brownout panel (frontend) and backend uses Home Assistant's WebSocket protocol. This document specifies all message schemas, commands, events, and error handling.

---

## WebSocket Connection Lifecycle

### Connection Establishment

The frontend connects to HA's WebSocket endpoint (same as HA's main UI):

```
WebSocket URL: ws://{ha_url}/api/websocket
Authentication: HA session token (already in `hass` object)
```

### Initial Handshake

After authentication, the backend immediately sends a `vulcan-brownout/status` event:

```json
{
  "type": "vulcan-brownout/status",
  "data": {
    "status": "connected",
    "version": "1.0.0",
    "threshold": 15,
    "supported_sort_keys": ["battery_level", "available", "device_name"]
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | "connected" when ready; "disconnected" on logout |
| `version` | string | API version (used for compatibility checks) |
| `threshold` | int | Current battery threshold (0-100, hardcoded 15% for Sprint 1) |
| `supported_sort_keys` | string[] | List of valid sort keys |

**Timing:** Sent immediately after HA authentication succeeds (within 50ms).

---

## Commands (Frontend → Backend)

### Command 1: Query Devices

**Type:** `vulcan-brownout/query_devices`

**Purpose:** Fetch a paginated, sorted list of battery devices below threshold.

**Request Schema:**

```json
{
  "type": "vulcan-brownout/query_devices",
  "id": "msg_abc123",
  "data": {
    "limit": 20,
    "offset": 0,
    "sort_key": "battery_level",
    "sort_order": "asc"
  }
}
```

| Field | Type | Required | Default | Constraints |
|-------|------|----------|---------|-------------|
| `limit` | int | No | 20 | 1-100 |
| `offset` | int | No | 0 | ≥ 0 |
| `sort_key` | string | No | "battery_level" | One of: `battery_level`, `available`, `device_name` |
| `sort_order` | string | No | "asc" | "asc" or "desc" |

**Validation:**
- If `limit < 1` or `limit > 100` → Return error `invalid_limit`
- If `offset < 0` → Return error `invalid_offset`
- If `sort_key` not in `supported_sort_keys` → Return error `invalid_sort_key`
- If `sort_order` not in ["asc", "desc"] → Return error `invalid_sort_order`

---

### Response: Success (Query Devices)

```json
{
  "type": "result",
  "id": "msg_abc123",
  "success": true,
  "data": {
    "devices": [
      {
        "entity_id": "sensor.kitchen_motion_battery",
        "state": "5",
        "attributes": {
          "unit_of_measurement": "%",
          "friendly_name": "Kitchen Motion Sensor Battery",
          "device_class": "battery"
        },
        "last_changed": "2026-02-22T10:15:30Z",
        "last_updated": "2026-02-22T10:15:30Z",
        "device_id": "device_abc123",
        "device_name": "Kitchen Motion Sensor",
        "battery_level": 5,
        "available": true
      },
      {
        "entity_id": "sensor.living_room_motion_battery",
        "state": "12",
        "attributes": {
          "unit_of_measurement": "%",
          "friendly_name": "Living Room Motion Sensor Battery",
          "device_class": "battery"
        },
        "last_changed": "2026-02-22T09:45:20Z",
        "last_updated": "2026-02-22T09:45:20Z",
        "device_id": "device_def456",
        "device_name": "Living Room Motion Sensor",
        "battery_level": 12,
        "available": true
      },
      {
        "entity_id": "sensor.phone_battery",
        "state": "unavailable",
        "attributes": {
          "unit_of_measurement": "%",
          "friendly_name": "Phone Battery",
          "device_class": "battery"
        },
        "last_changed": "2026-02-22T11:00:00Z",
        "last_updated": "2026-02-22T11:00:00Z",
        "device_id": "device_ghi789",
        "device_name": "iPhone 14",
        "battery_level": 0,
        "available": false
      }
    ],
    "total": 47,
    "offset": 0,
    "limit": 20,
    "has_more": true
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `devices` | object[] | Array of battery device objects |
| `devices[].entity_id` | string | Unique HA entity ID (e.g., "sensor.phone_battery") |
| `devices[].state` | string | Raw state value from HA (e.g., "5" for 5%) |
| `devices[].attributes` | object | Entity attributes (unit_of_measurement, friendly_name, device_class) |
| `devices[].last_changed` | string | ISO8601 timestamp of last state change |
| `devices[].last_updated` | string | ISO8601 timestamp of last attribute update |
| `devices[].device_id` | string | Associated HA device ID (nullable if not linked to device) |
| `devices[].device_name` | string | Device name from HA device registry |
| `devices[].battery_level` | number | Parsed battery percentage (float, 0-100) |
| `devices[].available` | bool | Whether device is available (false if state is "unavailable") |
| `total` | int | Total count of devices matching filter (for pagination logic) |
| `offset` | int | Request offset (echoed back) |
| `limit` | int | Request limit (echoed back) |
| `has_more` | bool | True if `offset + limit < total` (indicates more pages available) |

**Response Time:** 20-50ms (local, no network latency)

**Sorting:**
All results are sorted by the specified `sort_key`:
- `battery_level` (ascending) = lowest first (most critical)
- `available` (descending) = available devices first
- `device_name` (ascending) = A-Z

---

### Response: Error (Query Devices)

```json
{
  "type": "result",
  "id": "msg_abc123",
  "success": false,
  "error": {
    "code": "invalid_limit",
    "message": "Limit must be between 1 and 100"
  }
}
```

| Error Code | HTTP Equiv | Message | Recovery |
|------------|-----------|---------|----------|
| `invalid_limit` | 400 | Limit must be between 1 and 100 | Retry with `limit` ≤ 100 |
| `invalid_offset` | 400 | Offset must be >= 0 | Retry with `offset` ≥ 0 |
| `invalid_sort_key` | 400 | Unknown sort key: `{key}` | Use supported_sort_keys from status event |
| `invalid_sort_order` | 400 | Sort order must be 'asc' or 'desc' | Retry with valid `sort_order` |
| `internal_error` | 500 | Failed to query devices: `{reason}` | Retry after exponential backoff |

---

## Events (Backend → Frontend)

### Event 1: Device Changed

**Type:** `vulcan-brownout/device_changed`

**Purpose:** Real-time notification when a visible device's battery level or availability changes.

**Event Schema:**

```json
{
  "type": "vulcan-brownout/device_changed",
  "data": {
    "entity_id": "sensor.phone_battery",
    "state": "8",
    "battery_level": 8,
    "available": true,
    "last_changed": "2026-02-22T10:30:45Z",
    "last_updated": "2026-02-22T10:30:45Z",
    "attributes": {
      "unit_of_measurement": "%",
      "friendly_name": "Phone Battery",
      "device_class": "battery"
    }
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `entity_id` | string | Entity that changed |
| `state` | string | New raw state (e.g., "8" or "unavailable") |
| `battery_level` | number | Parsed battery percentage (0-100) |
| `available` | bool | Whether entity is available |
| `last_changed` | string | ISO8601 timestamp of state change |
| `last_updated` | string | ISO8601 timestamp of attribute update |
| `attributes` | object | Updated entity attributes |

**Trigger Conditions:**
- Device's battery level changed AND entity is in currently-visible list
- Device's availability changed (available → unavailable or vice versa)
- Entity moved between status groups (critical → healthy, etc.)

**Timing:** Sent within 50ms of HA state change.

**Frontend Action:**
- Find device in `this.battery_devices[]` by matching `entity_id`
- Update device object with new `battery_level` and `available`
- Lit auto-re-renders (property change detected)
- Progress bar animates to new level (300ms)

---

### Event 2: Device Removed

**Type:** `vulcan-brownout/device_removed`

**Purpose:** Notification when a device no longer matches filter criteria.

**Event Schema:**

```json
{
  "type": "vulcan-brownout/device_removed",
  "data": {
    "entity_id": "sensor.tablet_battery",
    "reason": "battery_level_above_threshold"
  }
}
```

| Field | Type | Possible Values | Description |
|-------|------|-----------------|-------------|
| `entity_id` | string | — | Entity ID that was removed |
| `reason` | string | "battery_level_above_threshold", "entity_deleted", "device_class_changed" | Why removed |

**Trigger Conditions:**
- Battery level rose above threshold (e.g., 15% → 20%)
- Entity was deleted from HA
- Device class changed (no longer battery)

**Timing:** Sent immediately when condition met.

**Frontend Action:**
- Find device in `this.battery_devices[]`
- Remove device (fade out animation, 150ms)
- Decrement `this.total` by 1
- Re-calculate `this.hasMore`

---

### Event 3: Status Update

**Type:** `vulcan-brownout/status`

**Purpose:** Configuration changes or connection status updates.

**Event Schema:**

```json
{
  "type": "vulcan-brownout/status",
  "data": {
    "status": "connected",
    "threshold": 15,
    "message": "Configuration updated"
  }
}
```

| Field | Type | Possible Values | Description |
|-------|------|-----------------|-------------|
| `status` | string | "connected", "disconnected", "error" | Connection or service status |
| `threshold` | int | 0-100 | Current threshold (if changed) |
| `message` | string | — | Optional human-readable message |

**Trigger Conditions:**
- User changes configuration (Sprint 2)
- Backend service restarts or encounters error
- Connection state changes

---

## Error Handling

### WebSocket Connection Errors

If the WebSocket connection drops:

1. **Frontend detects disconnect** (no data for >10s)
2. **Show "Offline" message** to user
3. **Implement exponential backoff** reconnection:
   ```
   Attempt 1: wait 1s, reconnect
   Attempt 2: wait 2s, reconnect
   Attempt 3: wait 4s, reconnect
   Attempt 4: wait 8s, reconnect
   Attempt 5: wait 16s, reconnect
   Max wait: 30s
   ```
4. **On successful reconnect:**
   - HA sends `vulcan-brownout/status`
   - Frontend re-sends last `query_devices` request
   - UI updates with fresh data
   - "Offline" message clears

### Command Timeout

If a command doesn't receive a response within 10 seconds:

1. **Frontend logs error:** "vulcan-brownout/query_devices timed out after 10s"
2. **Show toast to user:** "Failed to load devices (timeout)"
3. **Trigger reconnection logic** (see above)

### Invalid Response

If backend sends malformed JSON or missing required fields:

1. **Frontend logs error** with full message body
2. **Show toast to user:** "Received invalid data from server"
3. **Do NOT attempt to parse** partial response

### Rate Limiting

No explicit rate limiting, but frontend should:
- Debounce sort/filter changes (100ms)
- Not send more than 1 query per 500ms
- Backend silently drops duplicate message IDs

---

## Message ID Tracking

Every command sent from frontend includes a unique `id` field:

```javascript
const messageId = 'msg_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
const request = {
  type: 'vulcan-brownout/query_devices',
  id: messageId,
  data: { ... }
};
```

The response echoes back the same `id`, allowing frontend to correlate responses to requests (important for async pagination).

---

## Versioning

The API includes a `version` field in the initial `vulcan-brownout/status` event.

**Current Version:** `1.0.0`

**Format:** Semantic Versioning (MAJOR.MINOR.PATCH)

**Compatibility Rules:**
- **Major version change** (1.x → 2.x): Breaking change → Frontend shows "Integration update required"
- **Minor version change** (1.0 → 1.1): Backward compatible → New optional fields, new events
- **Patch version change** (1.0.0 → 1.0.1): Bug fixes → No API changes

**Frontend Behavior:**
1. Read `version` from initial `vulcan-brownout/status`
2. Parse major.minor.patch
3. If major version differs from expected (1), show warning to user
4. Gracefully handle unknown events (ignore, log warning)

---

## Example Conversation

### Scenario: User opens panel, scrolls to bottom, battery changes

```
STEP 1: Panel mounts
→ Frontend connects to WebSocket

STEP 2: Backend sends initial status
← {type: 'vulcan-brownout/status', status: 'connected', version: '1.0.0', threshold: 15, ...}

STEP 3: Frontend loads initial data
→ {type: 'vulcan-brownout/query_devices', id: 'msg_001', data: {limit: 20, offset: 0, ...}}

STEP 4: Backend responds with 20 devices
← {type: 'result', id: 'msg_001', success: true, data: {devices: [...20...], total: 47, has_more: true}}

STEP 5: Frontend renders first 20 devices

STEP 6: User scrolls to bottom → IntersectionObserver fires
→ {type: 'vulcan-brownout/query_devices', id: 'msg_002', data: {limit: 20, offset: 20, ...}}

STEP 7: Backend responds with next 20 devices
← {type: 'result', id: 'msg_002', success: true, data: {devices: [...20...], offset: 20, has_more: true}}

STEP 8: Frontend appends 20 more devices

STEP 9: Battery level changes on first device
← {type: 'vulcan-brownout/device_changed', data: {entity_id: 'sensor.kitchen_motion_battery', battery_level: 5, ...}}

STEP 10: Frontend finds device, updates battery_level, Lit re-renders

STEP 11: Another device's battery rises above 15% threshold
← {type: 'vulcan-brownout/device_removed', data: {entity_id: 'sensor.tablet_battery', reason: 'battery_level_above_threshold'}}

STEP 12: Frontend removes device from list, re-renders
```

---

## Testing Mock Data

### Mock Query Response (5 Devices, Sprint 1 Scope)

```json
{
  "type": "result",
  "id": "test_001",
  "success": true,
  "data": {
    "devices": [
      {
        "entity_id": "sensor.kitchen_motion_battery",
        "state": "5",
        "attributes": {
          "unit_of_measurement": "%",
          "friendly_name": "Kitchen Motion Sensor Battery",
          "device_class": "battery"
        },
        "last_changed": "2026-02-22T10:00:00Z",
        "last_updated": "2026-02-22T10:00:00Z",
        "device_id": "dev_001",
        "device_name": "Kitchen Motion Sensor",
        "battery_level": 5,
        "available": true
      },
      {
        "entity_id": "sensor.bedroom_motion_battery",
        "state": "12",
        "attributes": {
          "unit_of_measurement": "%",
          "friendly_name": "Bedroom Motion Sensor Battery",
          "device_class": "battery"
        },
        "last_changed": "2026-02-22T09:45:00Z",
        "last_updated": "2026-02-22T09:45:00Z",
        "device_id": "dev_002",
        "device_name": "Bedroom Motion Sensor",
        "battery_level": 12,
        "available": true
      },
      {
        "entity_id": "sensor.living_room_motion_battery",
        "state": "15",
        "attributes": {
          "unit_of_measurement": "%",
          "friendly_name": "Living Room Motion Sensor Battery",
          "device_class": "battery"
        },
        "last_changed": "2026-02-22T08:30:00Z",
        "last_updated": "2026-02-22T08:30:00Z",
        "device_id": "dev_003",
        "device_name": "Living Room Motion Sensor",
        "battery_level": 15,
        "available": true
      },
      {
        "entity_id": "sensor.phone_battery",
        "state": "unavailable",
        "attributes": {
          "unit_of_measurement": "%",
          "friendly_name": "Phone Battery",
          "device_class": "battery"
        },
        "last_changed": "2026-02-22T11:00:00Z",
        "last_updated": "2026-02-22T11:00:00Z",
        "device_id": "dev_004",
        "device_name": "iPhone 14",
        "battery_level": 0,
        "available": false
      },
      {
        "entity_id": "sensor.front_door_lock_battery",
        "state": "8",
        "attributes": {
          "unit_of_measurement": "%",
          "friendly_name": "Front Door Lock Battery",
          "device_class": "battery"
        },
        "last_changed": "2026-02-21T16:20:00Z",
        "last_updated": "2026-02-21T16:20:00Z",
        "device_id": "dev_005",
        "device_name": "Front Door Smart Lock",
        "battery_level": 8,
        "available": true
      }
    ],
    "total": 5,
    "offset": 0,
    "limit": 20,
    "has_more": false
  }
}
```

This represents 5 devices:
- 2 critical (5%, 8%)
- 1 at threshold (15%)
- 1 unavailable
- Total = 5, no more pages

Use this for frontend unit tests and mock WebSocket responses.

---

## Next Steps

- Lead Developer implements backend WebSocket handlers
- Lead Developer implements frontend WebSocket communication
- QA tests all message types end-to-end
- Code review verifies error handling
