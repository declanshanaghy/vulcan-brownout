# Vulcan Brownout: API Contracts

## Overview

All communication between the Vulcan Brownout panel frontend and backend uses Home Assistant's WebSocket protocol. This document defines all message schemas, command types, event types, and error handling.

---

## WebSocket Connection Lifecycle

### 1. Connection Establishment

The frontend connects to HA's existing WebSocket endpoint (same as HA's UI):

```
WebSocket URL: ws://{ha_url}/api/websocket
```

Authentication uses HA's session token (already available in `hass` object).

### 2. Initial Handshake

After connection, the backend sends a `vulcan-brownout/status` event:

**Message Type:** `vulcan-brownout/status` (unsolicited event)

```json
{
  "type": "vulcan-brownout/status",
  "data": {
    "status": "connected",
    "version": "1.0.0",
    "threshold": 15,
    "supported_sort_keys": ["battery_level", "name", "device_name", "last_changed", "available"]
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | "connected" when ready to accept queries |
| `version` | string | API version for compatibility checking |
| `threshold` | int | Current battery threshold (0-100) |
| `supported_sort_keys` | string[] | List of valid sort keys |

**Timing:** Sent immediately after HA authentication succeeds.

---

## Commands (Frontend → Backend)

### Command 1: Query Devices

**Type:** `vulcan-brownout/query_devices`

**Purpose:** Fetch a paginated, sorted list of battery devices below threshold.

**Request Schema:**

```json
{
  "type": "vulcan-brownout/query_devices",
  "id": "msg_12345",
  "data": {
    "limit": 20,
    "offset": 0,
    "sort_key": "battery_level",
    "sort_order": "asc",
    "filter": {
      "available_only": false
    }
  }
}
```

| Field | Type | Required | Default | Constraints |
|-------|------|----------|---------|-------------|
| `limit` | int | No | 20 | 1-100 |
| `offset` | int | No | 0 | ≥ 0 |
| `sort_key` | string | No | "battery_level" | One of: battery_level, name, device_name, last_changed, available |
| `sort_order` | string | No | "asc" | "asc" or "desc" |
| `filter.available_only` | bool | No | false | If true, exclude unavailable devices |

**Response Schema (Success):**

```json
{
  "type": "result",
  "id": "msg_12345",
  "success": true,
  "data": {
    "devices": [
      {
        "entity_id": "sensor.living_room_motion_battery",
        "state": "12",
        "attributes": {
          "unit_of_measurement": "%",
          "friendly_name": "Living Room Motion Sensor Battery",
          "device_class": "battery"
        },
        "last_changed": "2026-02-22T10:15:30Z",
        "last_updated": "2026-02-22T10:15:30Z",
        "context": {
          "id": "ctx_123456"
        },
        "device_id": "device_abc123",
        "device_name": "Living Room Motion Sensor",
        "battery_level": 12,
        "available": true
      },
      {
        "entity_id": "sensor.kitchen_motion_battery",
        "state": "5",
        "attributes": {
          "unit_of_measurement": "%",
          "friendly_name": "Kitchen Motion Sensor Battery",
          "device_class": "battery"
        },
        "last_changed": "2026-02-22T09:45:20Z",
        "last_updated": "2026-02-22T09:45:20Z",
        "context": {
          "id": "ctx_789012"
        },
        "device_id": "device_def456",
        "device_name": "Kitchen Motion Sensor",
        "battery_level": 5,
        "available": true
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
| `devices` | object[] | Array of battery devices |
| `devices[].entity_id` | string | Unique entity identifier (e.g., sensor.phone_battery) |
| `devices[].state` | string | Raw state value from HA (e.g., "12" for 12%) |
| `devices[].attributes` | object | Entity attributes (unit_of_measurement, friendly_name, etc.) |
| `devices[].last_changed` | string | ISO8601 timestamp of last state change |
| `devices[].last_updated` | string | ISO8601 timestamp of last attribute update |
| `devices[].context` | object | HA context metadata (optional) |
| `devices[].device_id` | string | Associated device ID (nullable if entity not linked to device) |
| `devices[].device_name` | string | Device name (from device registry) |
| `devices[].battery_level` | number | Parsed battery percentage (float) |
| `devices[].available` | bool | Whether device is available (true if state != "unavailable") |
| `total` | int | Total count of devices matching filter (for pagination logic) |
| `offset` | int | Request offset (echoed back) |
| `limit` | int | Request limit (echoed back) |
| `has_more` | bool | True if `offset + limit < total` |

**Response Schema (Error):**

```json
{
  "type": "result",
  "id": "msg_12345",
  "success": false,
  "error": {
    "code": "invalid_limit",
    "message": "Limit must be between 1 and 100"
  }
}
```

| Error Code | HTTP Equiv | Message | Recovery |
|------------|-----------|---------|----------|
| `invalid_limit` | 400 | Limit must be between 1 and 100 | Retry with limit ≤ 100 |
| `invalid_offset` | 400 | Offset must be >= 0 | Retry with offset ≥ 0 |
| `invalid_sort_key` | 400 | Unknown sort key: {key} | Use supported_sort_keys from status event |
| `invalid_sort_order` | 400 | Sort order must be 'asc' or 'desc' | Retry with valid order |
| `internal_error` | 500 | Failed to query devices | Retry after backoff |

**Timing:**
- Request → Response: ~50-150ms (local, no network latency)
- All results sorted by `sort_key`/`sort_order` on backend
- Unavailable devices included unless `filter.available_only=true`

---

## Events (Backend → Frontend)

### Event 1: Device Changed

**Type:** `vulcan-brownout/device_changed`

**Purpose:** Real-time notification when a currently-visible device's battery level or availability changes.

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
      "friendly_name": "Phone Battery"
    }
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `entity_id` | string | Entity that changed |
| `state` | string | New raw state |
| `battery_level` | number | Parsed battery percentage |
| `available` | bool | Whether entity is available |
| `last_changed` | string | ISO8601 timestamp of change |
| `last_updated` | string | ISO8601 timestamp of attribute update |
| `attributes` | object | Updated attributes |

**Trigger Conditions:**
- Device's battery level changed AND entity is in user's currently-viewed list
- Device's availability changed (e.g., went from available → unavailable)
- Entity was added to the filtered set (moved from above threshold to below)
- Entity was removed from the filtered set (moved from below to above threshold)

**Timing:** Sent within 100ms of state change.

**Note:** Frontend should update the device in `battery_devices[]` by matching `entity_id`, or remove/add to list if it crossed the threshold.

---

### Event 2: Device Removed

**Type:** `vulcan-brownout/device_removed`

**Purpose:** Notification when a device no longer matches the filter criteria (e.g., battery level rose above threshold, or device was deleted).

**Event Schema:**

```json
{
  "type": "vulcan-brownout/device_removed",
  "data": {
    "entity_id": "sensor.phone_battery",
    "reason": "battery_level_above_threshold"
  }
}
```

| Field | Type | Possible Values | Description |
|-------|------|-----------------|-------------|
| `entity_id` | string | — | Entity that was removed from results |
| `reason` | string | "battery_level_above_threshold", "entity_deleted", "device_class_changed" | Why it was removed |

**Timing:** Sent immediately when condition is met.

**Note:** Frontend should remove the device from `battery_devices[]` and decrement `totalItems` by 1.

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
| `status` | string | "connected", "disconnected", "error" | Connection status |
| `threshold` | int | — | Current threshold (if changed) |
| `message` | string | — | Optional human-readable message (optional) |

**Trigger Conditions:**
- User changes configuration in HA (threshold, device classes)
- Backend service restarts
- Connection is lost/restored

---

## Error Handling

### WebSocket Connection Errors

If the WebSocket connection drops:

1. **Frontend detects disconnect** (no data received for >10s)
2. **Show "Offline" message** to user
3. **Implement exponential backoff reconnection:**
   ```
   Attempt 1: wait 1s
   Attempt 2: wait 2s
   Attempt 3: wait 4s
   Attempt 4: wait 8s
   Attempt 5: wait 16s
   ... max 30s
   ```
4. **On successful reconnect:**
   - Re-send last `query_devices` request
   - Update UI with fresh data

### Command Timeout

If a command doesn't receive a response within 10 seconds:

1. **Log error:** "vulcan-brownout/query_devices timed out after 10s"
2. **Show toast to user:** "Failed to load devices (timeout)"
3. **Trigger reconnection logic**

### Invalid Response

If backend sends malformed JSON or missing required fields:

1. **Log error with full message body**
2. **Show toast to user:** "Received invalid data from server"
3. **Do NOT attempt to parse partial response**

### Rate Limiting

No explicit rate limiting, but:
- Frontend should debounce sort/filter changes (100ms)
- Frontend should not send more than 1 query per 500ms
- Backend will silently drop duplicate requests (same message ID)

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

The response includes the same `id`, allowing frontend to correlate responses to requests (important for async pagination requests).

---

## Versioning

The API includes a `version` field in the `vulcan-brownout/status` event. This allows for future evolution:

**Current Version:** `1.0.0`

**Compatibility Rules:**
- **Major version change** (1.x → 2.x): Breaking change; frontend should show "Integration update required" message
- **Minor version change** (1.0 → 1.1): Backward compatible; new fields in events, new optional fields in requests
- **Patch version change** (1.0.0 → 1.0.1): Bug fixes; no API changes

Frontend should:
1. Read `version` from initial `vulcan-brownout/status` event
2. Parse major.minor.patch
3. If major version differs from what's supported, show warning to user

---

## Example Conversation

### Scenario: User opens panel and scrolls to bottom

```
STEP 1: Panel mounts
→ Frontend connects to WebSocket

STEP 2: Backend sends status
← {type: 'vulcan-brownout/status', status: 'connected', version: '1.0.0', threshold: 15, ...}

STEP 3: Frontend loads initial data
→ {type: 'vulcan-brownout/query_devices', id: 'msg_001', data: {limit: 20, offset: 0, sort_key: 'battery_level', sort_order: 'asc'}}

STEP 4: Backend responds with 20 devices
← {type: 'result', id: 'msg_001', success: true, data: {devices: [...], total: 127, offset: 0, limit: 20, has_more: true}}

STEP 5: Frontend renders first 20 devices

STEP 6: User scrolls to bottom → IntersectionObserver fires
→ {type: 'vulcan-brownout/query_devices', id: 'msg_002', data: {limit: 20, offset: 20, sort_key: 'battery_level', sort_order: 'asc'}}

STEP 7: Backend responds with next 20 devices
← {type: 'result', id: 'msg_002', success: true, data: {devices: [...], total: 127, offset: 20, limit: 20, has_more: true}}

STEP 8: Frontend appends 20 more devices to the list

STEP 9: Device battery level changes
← {type: 'vulcan-brownout/device_changed', data: {entity_id: 'sensor.phone_battery', battery_level: 5, ...}}

STEP 10: Frontend finds device in list by entity_id, updates battery_level, re-renders

STEP 11: Another device's battery level rises above threshold
← {type: 'vulcan-brownout/device_removed', data: {entity_id: 'sensor.tablet_battery', reason: 'battery_level_above_threshold'}}

STEP 12: Frontend removes device from list, decrements total
```

---

## Testing Mock Data

### Mock `query_devices` Response (5 devices):

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
        "state": "8",
        "attributes": {
          "unit_of_measurement": "%",
          "friendly_name": "Bedroom Motion Sensor Battery",
          "device_class": "battery"
        },
        "last_changed": "2026-02-22T09:45:00Z",
        "last_updated": "2026-02-22T09:45:00Z",
        "device_id": "dev_002",
        "device_name": "Bedroom Motion Sensor",
        "battery_level": 8,
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
        "last_changed": "2026-02-22T08:30:00Z",
        "last_updated": "2026-02-22T08:30:00Z",
        "device_id": "dev_003",
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
        "device_id": "dev_004",
        "device_name": "iPhone 14",
        "battery_level": 0,
        "available": false
      },
      {
        "entity_id": "sensor.front_door_lock_battery",
        "state": "15",
        "attributes": {
          "unit_of_measurement": "%",
          "friendly_name": "Front Door Lock Battery",
          "device_class": "battery"
        },
        "last_changed": "2026-02-21T16:20:00Z",
        "last_updated": "2026-02-21T16:20:00Z",
        "device_id": "dev_005",
        "device_name": "Front Door Smart Lock",
        "battery_level": 15,
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

This represents 5 devices below the 15% threshold, with one unavailable.
