# Vulcan Brownout: Sprint 3 API Contracts

**Author**: FiremanDecko (Architect)
**Date**: February 22, 2026
**Status**: Proposed
**Version**: 3.0.0

---

## Overview

This document defines all WebSocket messages, commands, and events for Sprint 3. It extends the Sprint 2 API with four major additions:

1. **Cursor-Based Pagination** — Replace offset-based with stable cursor pagination
2. **Notification Preferences** — Configure per-device alerts and frequency caps
3. **Theme Information** — Status events include theme detection
4. **Binary Sensor Filtering** — API filters battery_level entities automatically

All messages use the same WebSocket protocol established in Sprint 1.

---

## Connection Lifecycle

### Initial Handshake (Updated from Sprint 2)

After successful WebSocket authentication, the backend immediately sends a status event:

```json
{
  "type": "vulcan-brownout/status",
  "data": {
    "status": "connected",
    "version": "3.0.0",
    "threshold": 15,
    "threshold_rules": {},
    "device_statuses": {
      "critical": 2,
      "warning": 3,
      "healthy": 37,
      "unavailable": 0
    },
    "theme": "dark",
    "notifications_enabled": true,
    "notification_preferences": {
      "enabled": true,
      "frequency_cap_hours": 6,
      "severity_filter": "critical_only",
      "per_device": {}
    }
  }
}
```

| Field | Type | NEW? | Description |
|-------|------|------|-------------|
| `status` | string | — | "connected" when ready |
| `version` | string | — | API version (3.0.0 for Sprint 3) |
| `threshold` | int | — | Current global battery threshold (5-100) |
| `threshold_rules` | object | — | Current device-specific rules |
| `device_statuses` | object | — | Count of devices in each status group |
| `theme` | string | ✓ NEW | "dark" or "light" (detected from HA) |
| `notifications_enabled` | bool | ✓ NEW | Whether notification system is active |
| `notification_preferences` | object | ✓ NEW | Current notification configuration |

**Timing**: Sent within 100ms of successful authentication.

---

## Commands (Frontend → Backend)

### Command 1: Query Devices (UPDATED - Cursor-Based)

**Type**: `vulcan-brownout/query_devices`

**Purpose**: Fetch paginated, sorted list of battery devices with cursor-based pagination.

**Request** (UPDATED from Sprint 2):

```json
{
  "type": "vulcan-brownout/query_devices",
  "id": "msg_abc123",
  "data": {
    "limit": 50,
    "cursor": null,
    "sort_key": "priority",
    "sort_order": "asc"
  }
}
```

| Field | Type | Required | Constraints | Notes |
|-------|------|----------|-------------|-------|
| `limit` | int | Yes | 1-100 | Default 50; max 100 for performance |
| `cursor` | string | No | base64 | Null for first page; use `next_cursor` from previous response |
| `sort_key` | string | Yes | "priority" \| "alphabetical" \| "level_asc" \| "level_desc" | Sorting method |
| `sort_order` | string | Yes | "asc" \| "desc" | Direction (typically "asc") |

**Response** (UPDATED with cursor):

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
      // ... more devices (up to limit)
    ],
    "total": 200,
    "has_more": true,
    "next_cursor": "eyIyMDI2LTAyLTIyVDEwOjE1OjMwWiIsInNlbnNvci5raXRjaGVuX21vdGlvbl9iYXR0ZXJ5In0=",
    "device_statuses": {
      "critical": 2,
      "warning": 3,
      "healthy": 195,
      "unavailable": 0
    }
  }
}
```

| Field | Type | NEW? | Description |
|-------|------|------|-------------|
| `devices` | array | — | Array of device objects (up to limit) |
| `total` | int | — | Total devices available |
| `has_more` | bool | — | Whether more devices exist after this page |
| `next_cursor` | string | ✓ NEW | Cursor for next page (null if at end) |
| `device_statuses` | object | — | Counts for filter UI |

**Cursor Format**: `base64("{last_changed}|{entity_id}")`

Example decode:
```
eyIyMDI2LTAyLTIyVDEwOjE1OjMwWiIsInNlbnNvci5raXRjaGVuX21vdGlvbl9iYXR0ZXJ5In0=
  → 2026-02-22T10:15:30Z|sensor.kitchen_motion_battery
```

**Filtering (NEW Sprint 3)**: Only entities with `device_class="battery"` AND `battery_level` attribute are included. Binary sensors excluded automatically.

---

### Command 2: Subscribe to Updates (UNCHANGED)

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

---

### Command 3: Set Threshold (UNCHANGED)

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

---

### Command 4: Get Notification Preferences (NEW)

**Type**: `vulcan-brownout/get_notification_preferences`

**Purpose**: Retrieve current notification configuration.

**Request**:

```json
{
  "type": "vulcan-brownout/get_notification_preferences",
  "id": "msg_003",
  "data": {}
}
```

**Response** (Success):

```json
{
  "type": "result",
  "id": "msg_003",
  "success": true,
  "data": {
    "enabled": true,
    "frequency_cap_hours": 6,
    "severity_filter": "critical_only",
    "per_device": {
      "sensor.front_door_lock_battery": {
        "enabled": true,
        "frequency_cap_hours": 6
      },
      "sensor.kitchen_sensor_battery": {
        "enabled": false,
        "frequency_cap_hours": 6
      },
      "sensor.solar_backup_battery": {
        "enabled": true,
        "frequency_cap_hours": 24
      }
    },
    "notification_history": [
      {
        "timestamp": "2026-02-22T10:15:00Z",
        "entity_id": "sensor.front_door_lock_battery",
        "device_name": "Front Door Lock",
        "battery_level": 8,
        "status": "critical",
        "message": "Front Door Lock battery critical (8%)"
      },
      {
        "timestamp": "2026-02-22T09:30:00Z",
        "entity_id": "sensor.solar_backup_battery",
        "device_name": "Solar Backup",
        "battery_level": 5,
        "status": "critical",
        "message": "Solar Backup battery critical (5%)"
      }
    ]
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `enabled` | bool | Global notifications on/off |
| `frequency_cap_hours` | int | 1, 6, or 24 hours |
| `severity_filter` | string | "critical_only" or "critical_and_warning" |
| `per_device` | object | Device-specific settings (entity_id → {enabled, frequency_cap_hours}) |
| `notification_history` | array | Last 10-20 notifications sent |

---

### Command 5: Set Notification Preferences (NEW)

**Type**: `vulcan-brownout/set_notification_preferences`

**Purpose**: Update notification configuration.

**Request**:

```json
{
  "type": "vulcan-brownout/set_notification_preferences",
  "id": "msg_004",
  "data": {
    "enabled": true,
    "frequency_cap_hours": 6,
    "severity_filter": "critical_and_warning",
    "per_device": {
      "sensor.front_door_lock_battery": {
        "enabled": true,
        "frequency_cap_hours": 6
      },
      "sensor.kitchen_sensor_battery": {
        "enabled": false,
        "frequency_cap_hours": 6
      },
      "sensor.solar_backup_battery": {
        "enabled": true,
        "frequency_cap_hours": 24
      }
    }
  }
}
```

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `enabled` | bool | Yes | — |
| `frequency_cap_hours` | int | Yes | 1, 6, or 24 |
| `severity_filter` | string | Yes | "critical_only" or "critical_and_warning" |
| `per_device` | object | No | Optional; null to clear |

**Response** (Success):

```json
{
  "type": "result",
  "id": "msg_004",
  "success": true,
  "data": {
    "message": "Notification preferences updated",
    "enabled": true,
    "frequency_cap_hours": 6,
    "severity_filter": "critical_and_warning"
  }
}
```

**Response** (Error):

```json
{
  "type": "result",
  "id": "msg_004",
  "success": false,
  "error": {
    "code": "invalid_notification_preferences",
    "message": "Invalid frequency_cap_hours: must be 1, 6, or 24"
  }
}
```

| Error Code | Meaning | Recovery |
|------------|---------|----------|
| `invalid_notification_preferences` | Invalid settings | Check constraints (1/6/24 hours) |
| `invalid_device_entity` | Device entity doesn't exist | Remove from per_device config |
| `permission_denied` | User can't edit config | Contact admin |
| `internal_error` | Server-side error | Retry |

---

## Events (Backend → Frontend)

### Event 1: Device Changed (UNCHANGED)

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

---

### Event 2: Threshold Updated (UNCHANGED)

**Type**: `vulcan-brownout/threshold_updated`

**Purpose**: Notify all connected clients when thresholds change.

**Event**:

```json
{
  "type": "vulcan-brownout/threshold_updated",
  "data": {
    "global_threshold": 20,
    "device_rules": {
      "sensor.solar_backup_battery": 50
    },
    "affected_devices": [
      { "entity_id": "sensor.kitchen_motion_battery", "old_status": "healthy", "new_status": "warning" }
    ]
  }
}
```

---

### Event 3: Notification Sent (NEW)

**Type**: `vulcan-brownout/notification_sent`

**Purpose**: Notify frontend when a notification is sent (for history UI).

**Event**:

```json
{
  "type": "vulcan-brownout/notification_sent",
  "data": {
    "timestamp": "2026-02-22T10:15:00Z",
    "entity_id": "sensor.front_door_lock_battery",
    "device_name": "Front Door Lock",
    "battery_level": 8,
    "status": "critical",
    "message": "Front Door Lock battery critical (8%)",
    "notification_id": "vulcan_brownout.front_door_lock.critical"
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | string | ISO8601 when notification was sent |
| `entity_id` | string | Battery entity that triggered notification |
| `device_name` | string | Friendly device name |
| `battery_level` | int | Battery % at time of notification |
| `status` | string | "critical" or "warning" |
| `message` | string | Full notification message |
| `notification_id` | string | HA persistent_notification ID |

**Timing**: Sent within 100ms of HA notification service call.

**Frontend Action**:
1. Add notification to history list
2. Update notification preferences modal (if open)
3. Show toast notification (optional)

---

### Event 4: Status Update (UPDATED)

**Type**: `vulcan-brownout/status`

**Purpose**: Configuration changes or connection status updates.

**Event** (UPDATED from Sprint 2):

```json
{
  "type": "vulcan-brownout/status",
  "data": {
    "status": "connected",
    "threshold": 20,
    "threshold_rules": {
      "sensor.solar_backup_battery": 50
    },
    "theme": "dark",
    "notifications_enabled": true,
    "message": "Configuration updated"
  }
}
```

| Field | Type | NEW? | Description |
|-------|------|------|-------------|
| `status` | string | — | "connected", "disconnected", "error" |
| `threshold` | int | — | Current global threshold (optional) |
| `threshold_rules` | object | — | Current device rules (optional) |
| `theme` | string | ✓ NEW | "dark" or "light" |
| `notifications_enabled` | bool | ✓ NEW | Whether notifications are active |
| `message` | string | — | Human-readable message (optional) |

**Trigger Conditions**:
- Connection established (sent immediately)
- Configuration changes propagated
- Theme change detected
- Connection errors occur

---

## Message Flow Examples

### Scenario 1: Infinite Scroll with Cursor Pagination

```
T=0ms: Frontend connects to WebSocket

T=50ms: Backend sends vulcan-brownout/status
        ← { status: 'connected', version: '3.0.0', theme: 'dark', ... }

T=100ms: Frontend sends vulcan-brownout/query_devices
         → { limit: 50, cursor: null, sort_key: 'priority' }

T=150ms: Frontend sends vulcan-brownout/subscribe
         → { type: '...', data: {} }

T=200ms: Backend responds to query_devices
         ← { devices: [...50...], total: 200, has_more: true, next_cursor: "base64(...)" }

T=250ms: Backend responds to subscribe
         ← { subscription_id: 'sub_xyz', status: 'subscribed' }

T=300ms: Frontend renders battery list with 50 items
         ← User sees list + "Back to Top" appears after scroll

T=500ms: User scrolls to bottom

T=550ms: Frontend sends vulcan-brownout/query_devices (next page)
         → { limit: 50, cursor: "base64(...)", sort_key: 'priority' }

T=750ms: Backend responds with next 50 items
         ← { devices: [...50...], total: 200, has_more: true, next_cursor: "base64(...)" }

T=800ms: Skeleton loaders fade out, new items fade in
         ← User sees 100 items total
```

---

### Scenario 2: Notification Triggered by Battery Drop

```
T=0ms: Device battery drops from 20% to 8%
       HA fires state_changed event

T=50ms: Backend NotificationManager checks:
        - Notifications enabled? YES
        - Device enabled? YES
        - Frequency cap: within 6h? NO
        - Severity: critical? YES (below threshold)
        ✓ Send notification

T=100ms: Backend POST /api/services/persistent_notification/create
         Payload:
           {
             "title": "🔋 Battery Low",
             "message": "Front Door Lock battery critical (8%)",
             "notification_id": "vulcan_brownout.front_door_lock.critical"
           }

T=200ms: HA notification service responds 200 OK
         Notification appears in HA sidebar

T=250ms: Backend broadcasts vulcan-brownout/notification_sent
         ← { entity_id: "...", device_name: "...", status: "critical", ... }

T=300ms: Frontend updates notification history
         Toast: "🔔 Notification sent: Front Door Lock"

T=400ms: Backend broadcasts vulcan-brownout/device_changed
         ← { entity_id: "...", battery_level: 8, status: "critical", ... }

T=450ms: Frontend updates device in list
         Progress bar animates to 8%
```

---

### Scenario 3: User Changes Notification Preferences

```
T=0ms: User opens notification preferences modal

T=100ms: Frontend sends vulcan-brownout/get_notification_preferences
         → { type: '...', data: {} }

T=200ms: Backend responds
         ← { enabled: true, frequency_cap_hours: 6, per_device: {...}, notification_history: [...] }

T=300ms: Modal renders with current preferences

T=500ms: User toggles "Kitchen Sensor" from ON to OFF

T=600ms: User clicks "SAVE PREFERENCES"

T=700ms: Frontend sends vulcan-brownout/set_notification_preferences
         → { enabled: true, per_device: { ..., "sensor.kitchen_sensor_battery": { enabled: false } } }

T=800ms: Backend validates and updates config entry

T=850ms: Backend broadcasts vulcan-brownout/status
         ← { status: 'connected', notifications_enabled: true }

T=900ms: Frontend closes modal
         Toast: "✓ Notification preferences saved"

T=1000ms+: Kitchen Sensor no longer triggers notifications (even if battery drops)
```

---

### Scenario 4: Dark Mode Detection

```
T=0ms: User has HA configured with dark theme
       User clicks sidebar, opens Vulcan Brownout panel

T=50ms: WebSocket connects successfully

T=100ms: Backend sends vulcan-brownout/status
         ← { status: 'connected', theme: 'dark', version: '3.0.0', ... }

T=150ms: Frontend detectTheme() runs
         - Checks: document.documentElement.getAttribute('data-theme')
         - Result: 'dark' detected

T=200ms: CSS custom properties applied:
         --vb-bg-primary: #1C1C1C
         --vb-color-critical: #FF5252 (brightened red)
         etc.

T=250ms: Panel renders with dark mode colors
         User sees battery list in dark background

T=250ms+: MutationObserver listens for theme changes
          If user toggles HA theme while panel is open:
          - Detects data-theme attribute change
          - Calls applyTheme() → updates CSS variables
          - Smooth transition (300ms CSS)
          - No page reload
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

Standard error codes:

| Code | Meaning |
|------|---------|
| `invalid_request` | Request malformed or missing fields |
| `invalid_limit` | Limit out of range (1-100) |
| `invalid_cursor` | Cursor invalid or expired |
| `invalid_sort_key` | Sort key not supported |
| `invalid_threshold` | Threshold out of range (5-100) |
| `invalid_notification_preferences` | Invalid notification settings |
| `invalid_device_entity` | Device entity doesn't exist |
| `too_many_rules` | > 10 device-specific rules |
| `permission_denied` | User lacks permission |
| `integration_not_loaded` | Integration initialization failed |
| `subscription_limit_exceeded` | Max subscriptions reached |
| `internal_error` | Server-side error |

---

## Versioning & Backward Compatibility

**Current Version**: `3.0.0` (Semantic Versioning)

**Breaking Changes from Sprint 2 → Sprint 3**:
- `query_devices` response now uses `next_cursor` instead of `offset` (offset removed)
- `status` event now includes `theme` field (optional, non-breaking)
- New command `set_notification_preferences` (clients can ignore if not used)

**Backward Compatibility**:
- Frontend written for version 2.0.0 can still connect to 3.0.0 backend
- Cursor-based pagination is a breaking change for offset-based clients
- Clients expecting `offset` in response will fail to paginate

**Version Checking**:
```javascript
const statusEvent = await this.hass.callWS({type: 'vulcan-brownout/status'});
const version = statusEvent.data.version;  // "3.0.0"
const majorVersion = parseInt(version.split('.')[0]);

if (majorVersion < 3) {
  console.warn(`Version mismatch: expected 3.x, got ${version}`);
  // Show user warning, suggest update
}
```

---

## API Rate Limiting

**Recommended Limits** (per WebSocket connection):

| Command | Max Requests/Min | Rationale |
|---------|------------------|-----------|
| `query_devices` | 10 | Pagination fetch (user scrolling) |
| `set_threshold` | 2 | Settings changes (user interaction) |
| `set_notification_preferences` | 5 | Preference changes (modal interaction) |
| `subscribe` | 1 | Once per session |
| `get_notification_preferences` | 5 | Modal open/refresh |

**Enforcement**: Backend should log but not reject excess requests in Sprint 3 (log for Sprint 4 rate limiting feature).

---

## WebSocket Message Timing

**Maximum Message Latencies**:

| Message Type | Max Latency | Typical | Retry |
|--------------|-------------|---------|-------|
| `query_devices` | 2s | 200-500ms | 3x with backoff |
| `set_threshold` | 2s | 300-600ms | 1x |
| `set_notification_preferences` | 2s | 300-600ms | 1x |
| `device_changed` (event) | 500ms | 50-100ms | — |
| `notification_sent` (event) | 2s | 100-200ms | — |
| `status` (event) | 1s | 50-100ms | — |

---

## Related Documents

- [System Design](./system-design.md)
- [Sprint Plan](./sprint-plan.md)
- [ADR-009: Cursor-Based Pagination](./adrs/ADR-009-cursor-pagination.md)
- [ADR-010: Notification Service](./adrs/ADR-010-notification-service.md)
- [ADR-011: Dark Mode](./adrs/ADR-011-dark-mode-support.md)
- [ADR-012: Entity Filtering](./adrs/ADR-012-entity-filtering.md)

---

**Approved by**: [Architect]
**Implementation**: [Lead Developer]
**Code Review**: [Code Review Lead]
