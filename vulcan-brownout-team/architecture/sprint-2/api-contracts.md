# Vulcan Brownout: Sprint 2 API Contracts

**Author**: FiremanDecko (Architect)
**Date**: February 2026
**Status**: Proposed
**Version**: 2.0.0

---

## Overview

This document defines all WebSocket messages, commands, and events for Sprint 2. It extends the Sprint 1 API with three new capabilities:

1. **WebSocket Subscriptions** — Real-time push updates
2. **Threshold Configuration** — Setting global and per-device thresholds
3. **Sort/Filter Metadata** — Filter counts and sort hints

All messages use the same WebSocket protocol established in Sprint 1.

---

## Connection Lifecycle

### Initial Handshake (Updated from Sprint 1)

After successful WebSocket authentication, the backend immediately sends a status event:

```json
{
  "type": "vulcan-brownout/status",
  "data": {
    "status": "connected",
    "version": "2.0.0",
    "threshold": 15,
    "threshold_rules": {},
    "device_statuses": {
      "critical": 2,
      "warning": 3,
      "healthy": 8,
      "unavailable": 1
    }
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | "connected" when ready; "disconnected" on logout |
| `version` | string | API version (2.0.0 for Sprint 2) |
| `threshold` | int | Current global battery threshold (5-100) |
| `threshold_rules` | object | Current device-specific rules (entity_id → threshold) |
| `device_statuses` | object | Count of devices in each status group |

**Timing**: Sent within 100ms of successful authentication.

---

## Commands (Frontend → Backend)

### Command 1: Query Devices (UPDATED)

**Type**: `vulcan-brownout/query_devices`

**Purpose**: Fetch paginated, sorted list of battery devices (same as Sprint 1, but response includes filter metadata).

**Request** (UNCHANGED from Sprint 1):

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

**Response** (UPDATED with filter counts):

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
        "attributes": { "unit_of_measurement": "%", ... },
        "last_changed": "2026-02-22T10:15:30Z",
        "last_updated": "2026-02-22T10:15:30Z",
        "device_id": "device_abc123",
        "device_name": "Kitchen Motion Sensor",
        "battery_level": 5,
        "available": true,
        "status": "critical"
      },
      // ... more devices
    ],
    "total": 47,
    "offset": 0,
    "limit": 20,
    "has_more": true,
    "device_statuses": {
      "critical": 2,
      "warning": 3,
      "healthy": 8,
      "unavailable": 1
    }
  }
}
```

**New Fields**:
- `devices[].status` — Pre-calculated status for each device (based on thresholds)
- `device_statuses` — Counts for filter UI (how many devices in each group)

---

### Command 2: Subscribe to Updates (NEW)

**Type**: `vulcan-brownout/subscribe`

**Purpose**: Request real-time push updates for battery changes.

**Request**:

```json
{
  "type": "vulcan-brownout/subscribe",
  "id": "msg_001",
  "data": {}
}
```

**Response** (Success):

```json
{
  "type": "result",
  "id": "msg_001",
  "success": true,
  "data": {
    "subscription_id": "sub_abc123",
    "status": "subscribed"
  }
}
```

**Response** (Error):

```json
{
  "type": "result",
  "id": "msg_001",
  "success": false,
  "error": {
    "code": "subscription_limit_exceeded",
    "message": "Maximum subscriptions reached (100)"
  }
}
```

| Error Code | Meaning | Recovery |
|------------|---------|----------|
| `integration_not_loaded` | Integration failed to initialize | Refresh page |
| `subscription_limit_exceeded` | Too many subscriptions on server | Close other panels |
| `auth_failed` | Authentication token expired | Refresh page |

**Timing**: Sent immediately; subscription active within 50ms.

**Lifecycle**:
- Frontend calls this on sidebar load (once per panel instance)
- Backend adds client to subscriber list
- Client receives `device_changed` events until disconnect
- On disconnect, subscription automatically removed

---

### Command 3: Set Threshold (NEW)

**Type**: `vulcan-brownout/set_threshold`

**Purpose**: Update global and/or device-specific thresholds.

**Request**:

```json
{
  "type": "vulcan-brownout/set_threshold",
  "id": "msg_002",
  "data": {
    "global_threshold": 20,
    "device_rules": {
      "sensor.solar_backup_battery": 50,
      "sensor.front_door_lock_battery": 30
    }
  }
}
```

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `global_threshold` | int | No | 5-100 |
| `device_rules` | object | No | Each rule 5-100 |

**Response** (Success):

```json
{
  "type": "result",
  "id": "msg_002",
  "success": true,
  "data": {
    "message": "Thresholds updated",
    "global_threshold": 20,
    "device_rules": {
      "sensor.solar_backup_battery": 50,
      "sensor.front_door_lock_battery": 30
    }
  }
}
```

**Response** (Error):

```json
{
  "type": "result",
  "id": "msg_002",
  "success": false,
  "error": {
    "code": "invalid_threshold",
    "message": "Global threshold must be between 5 and 100"
  }
}
```

| Error Code | Meaning | Recovery |
|------------|---------|----------|
| `invalid_threshold` | Threshold out of range | Use 5-100 |
| `invalid_device_rule` | Device entity doesn't exist | Check entity_id |
| `too_many_rules` | > 10 device rules | Remove some rules |
| `permission_denied` | User can't edit config | Contact admin |

**Timing**: Backend responds within 200ms; broadcasts update to all clients within 300ms.

**Persistence**: Changes saved in HA's `ConfigEntry.options`; survive HA restart.

---

## Events (Backend → Frontend)

### Event 1: Device Changed (ENHANCED)

**Type**: `vulcan-brownout/device_changed`

**Purpose**: Notify of battery level or availability change for a monitored device.

**Event**:

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
    "status": "critical",
    "attributes": {
      "unit_of_measurement": "%",
      "friendly_name": "Phone Battery",
      "device_class": "battery"
    }
  }
}
```

| Field | Type | NEW? | Description |
|-------|------|------|-------------|
| `entity_id` | string | — | Entity that changed |
| `state` | string | — | Raw state (e.g., "8" or "unavailable") |
| `battery_level` | number | — | Parsed battery % (0-100) |
| `available` | bool | — | Whether device is available |
| `last_changed` | string | — | ISO8601 timestamp of state change |
| `last_updated` | string | — | ISO8601 timestamp of last update |
| `status` | string | ✓ NEW | "critical" \| "warning" \| "healthy" \| "unavailable" |
| `attributes` | object | — | Entity attributes |

**New Field Rationale**:
- `status` — Eliminates need for frontend to re-calculate status from battery_level + threshold
- Thresholds may have changed since last update; backend has authoritative value

**Trigger Conditions**:
- Device's battery level changed AND entity is in active subscription list
- Device's availability changed (available ↔ unavailable)
- Threshold rule changed affecting this device's status

**Timing**: Sent within 100ms of HA state change.

**Frontend Action**:
1. Find device in `this.battery_devices[]` by matching `entity_id`
2. Update device object: `battery_level`, `available`, `status`, `last_changed`
3. Trigger Lit re-render
4. Progress bar animates to new level (300ms CSS transition)
5. Update timestamp

---

### Event 2: Threshold Updated (NEW)

**Type**: `vulcan-brownout/threshold_updated`

**Purpose**: Notify all connected clients when thresholds change (e.g., user modified settings).

**Event**:

```json
{
  "type": "vulcan-brownout/threshold_updated",
  "data": {
    "global_threshold": 20,
    "device_rules": {
      "sensor.solar_backup_battery": 50,
      "sensor.front_door_lock_battery": 30
    },
    "affected_devices": [
      { "entity_id": "sensor.kitchen_motion_battery", "old_status": "healthy", "new_status": "warning" },
      { "entity_id": "sensor.garage_sensor_battery", "old_status": "healthy", "new_status": "critical" }
    ]
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `global_threshold` | int | New global threshold value |
| `device_rules` | object | New device-specific rules |
| `affected_devices` | array | Devices whose status changed (for optimized re-render) |

**Trigger Conditions**:
- Any client sends `vulcan-brownout/set_threshold` command
- Threshold changes processed by backend
- Broadcast to ALL connected clients (not just the requester)

**Timing**: Sent within 300ms of threshold change request.

**Frontend Action**:
1. Update local threshold cache
2. Re-calculate status for affected devices only (optimization)
3. Full re-render (color coding may have changed)
4. Device list may re-sort (if sorting by priority)

---

### Event 3: Status Update (UNCHANGED)

**Type**: `vulcan-brownout/status`

**Purpose**: Configuration changes or connection status updates.

**Event**:

```json
{
  "type": "vulcan-brownout/status",
  "data": {
    "status": "connected",
    "threshold": 20,
    "threshold_rules": {
      "sensor.solar_backup_battery": 50
    },
    "message": "Configuration updated"
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | "connected", "disconnected", "error" |
| `threshold` | int | Current global threshold (optional) |
| `threshold_rules` | object | Current device rules (optional) |
| `message` | string | Human-readable message (optional) |

**Trigger Conditions**:
- Connection established (sent immediately)
- Configuration changes propagated
- Connection errors occur

---

## Message Flow Examples

### Scenario 1: Initial Load with Real-Time Subscription

```
T=0ms: Frontend connects to WebSocket

T=50ms: Backend sends vulcan-brownout/status
        ← { status: 'connected', version: '2.0.0', threshold: 15, ... }

T=100ms: Frontend sends vulcan-brownout/query_devices
         → { type: '...', data: { limit: 20, offset: 0 } }

T=150ms: Frontend sends vulcan-brownout/subscribe
         → { type: '...', data: {} }

T=200ms: Backend responds to query_devices
         ← { type: 'result', data: { devices: [...20...], device_statuses: {...} } }

T=250ms: Backend responds to subscribe
         ← { type: 'result', data: { subscription_id: 'sub_xyz', status: 'subscribed' } }

T=300ms: Frontend renders battery list
         ← User sees 20 devices

T=300ms+: Real-time updates start flowing
         ← device_changed events as batteries change
```

### Scenario 2: User Changes Threshold

```
T=0ms: Frontend sends vulcan-brownout/set_threshold
       → { global_threshold: 25, device_rules: {} }

T=100ms: Backend processes request
         - Validates: 25 is 5-100 ✓
         - Updates config entry
         - Updates BatteryMonitor cache

T=150ms: Backend broadcasts to ALL clients
         ← vulcan-brownout/threshold_updated
           { global_threshold: 25, affected_devices: [... devices whose status changed ...] }

T=200ms: Backend sends response to requester
         ← { type: 'result', success: true }

T=250ms: All connected clients re-render
         - Status colors updated
         - Sort order may change (if priority sort)
         - Timestamps updated
```

### Scenario 3: Network Disconnect & Reconnect

```
T=0-30s: Normal operation
         ← device_changed events flowing

T=30s: Network drops
       - WebSocket closes
       - Backend removes subscription
       - Frontend detects close

T=30-35s: Frontend shows connection badge: 🔵 (reconnecting)
          Attempts reconnect with backoff (1s, 2s, 4s, 8s, ...)

T=35s: Reconnect succeeds
       - WebSocket handshake completes
       - Backend creates new subscription
       - Frontend re-sends query_devices to sync missed updates

T=36s: Backend broadcasts vulcan-brownout/status
       ← { status: 'connected' }

T=37s: Frontend shows connection badge: 🟢 (connected)
       Toast notification: "✓ Connection updated"
       Device list updates with any missed changes
```

---

## Error Response Format

All errors follow this format:

```json
{
  "type": "result",
  "id": "msg_xyz",
  "success": false,
  "error": {
    "code": "error_code_here",
    "message": "Human-readable error message"
  }
}
```

Standard HTTP-like error codes (mapped to string codes):

| Code | Meaning |
|------|---------|
| `invalid_request` | Request malformed or missing fields |
| `invalid_limit` | Limit out of range |
| `invalid_offset` | Offset out of range |
| `invalid_sort_key` | Sort key not supported |
| `invalid_sort_order` | Sort order not "asc" or "desc" |
| `invalid_threshold` | Threshold out of range (5-100) |
| `invalid_device_rule` | Device entity doesn't exist |
| `too_many_rules` | > 10 device-specific rules |
| `permission_denied` | User lacks permission |
| `integration_not_loaded` | Integration initialization failed |
| `subscription_limit_exceeded` | Max subscriptions reached |
| `internal_error` | Server-side error |

---

## Versioning & Backward Compatibility

**Current Version**: `2.0.0` (Semantic Versioning)

**Breaking Changes from Sprint 1 → Sprint 2**:
- Response to `query_devices` now includes `device_statuses` object (optional field, not breaking)
- New optional fields in device objects: `status`
- New event types: `threshold_updated` (clients can ignore unknown events)

**Backward Compatibility**:
- Frontend written for version 1.0.0 can connect to 2.0.0 backend
- New fields are optional; requests without them use defaults
- Unknown events are logged and ignored (graceful degradation)

**Version Checking**:
```javascript
// Frontend should check version on connect
const statusEvent = await this.hass.callWS({type: 'vulcan-brownout/status'});
const version = statusEvent.data.version;  // "2.0.0"
const majorVersion = parseInt(version.split('.')[0]);

if (majorVersion !== 2) {
  console.warn(`Version mismatch: expected 2.x, got ${version}`);
  // Show user warning, suggest update
}
```

---

## Testing Mock Data

### Mock Query Response (Sprint 2)

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
        "battery_level": 5,
        "available": true,
        "status": "critical",
        "device_name": "Kitchen Motion Sensor",
        "device_id": "dev_001",
        "last_changed": "2026-02-22T10:00:00Z",
        "last_updated": "2026-02-22T10:00:00Z",
        "attributes": {
          "unit_of_measurement": "%",
          "friendly_name": "Kitchen Motion Sensor Battery",
          "device_class": "battery"
        }
      },
      {
        "entity_id": "sensor.solar_backup_battery",
        "state": "95",
        "battery_level": 95,
        "available": true,
        "status": "healthy",
        "device_name": "Solar Backup",
        "device_id": "dev_002",
        "last_changed": "2026-02-22T09:30:00Z",
        "last_updated": "2026-02-22T09:30:00Z",
        "attributes": {
          "unit_of_measurement": "%",
          "friendly_name": "Solar Backup Battery",
          "device_class": "battery"
        }
      }
    ],
    "total": 13,
    "offset": 0,
    "limit": 50,
    "has_more": false,
    "device_statuses": {
      "critical": 2,
      "warning": 3,
      "healthy": 8,
      "unavailable": 0
    }
  }
}
```

---

## Related Documents

- [System Design](./system-design.md) — Architecture overview
- [ADR-006](./ADR-006-websocket-subscriptions.md) — Subscription design
- [ADR-007](./ADR-007-threshold-configuration.md) — Threshold storage
- [ADR-008](./ADR-008-sort-filter-implementation.md) — Sort/filter logic

---

**Approved by**: [Architect]
**Implementation**: [Lead Developer]
**Code Review**: [Code Review Lead]
