# Vulcan Brownout: Sprint 3 System Design

**Author**: FiremanDecko (Architect)
**Date**: February 22, 2026
**Status**: Proposed
**Previous**: [Sprint 2 System Design](./system-design.md)

---

## Overview

Sprint 3 transforms Vulcan Brownout into a truly proactive monitoring system by adding five major capabilities:

1. **Infinite Scroll with Server-Side Pagination** — Support 150+ battery entities without UI lag
2. **Binary Sensor Filtering** — Remove non-battery entities from results
3. **Notification System** — Send HA notifications when batteries drop below threshold
4. **Dark Mode / Theme Support** — Automatic detection and application of HA's theme
5. **Deployment & Infrastructure** — Idempotent deployment with enhanced health checks

The system evolves from:
- **Client-side limitations** (Sprint 2) → **Server-side pagination** (Sprint 3)
- **Silent monitoring** (Sprint 1-2) → **Proactive alerts** (Sprint 3)
- **Light mode only** (Sprint 1-2) → **Native dark mode** (Sprint 3)
- **All entities** → **Filtered to battery_level entities only** (Sprint 3)

---

## Component Architecture

### Updated Component Diagram

```mermaid
graph TB
    subgraph "Home Assistant Core"
        HA["Home Assistant<br/>State Machine & Entity Registry"]
        Events["HA Event Bus<br/>(state_changed)"]
        PersistNotif["persistent_notification<br/>Service"]
    end

    subgraph "Vulcan Brownout Integration"
        Init["__init__.py<br/>Setup & Registration"]
        Config["config_flow.py<br/>Settings UI"]
        Monitor["BatteryMonitor<br/>Service"]
        SubMgr["WebSocketSubscriptionManager"]
        NotifMgr["NotificationManager<br/>(NEW Sprint 3)"]
        WSApi["websocket_api.py<br/>WebSocket Handler"]
    end

    subgraph "Frontend"
        Panel["vulcan-brownout-panel.js<br/>Lit Component"]
        SettingsUI["Settings Panel"]
        NotifPrefs["Notification Preferences<br/>(NEW Sprint 3)"]
        SortFilterUI["Sort/Filter Bar"]
        BackToTop["Back to Top Button<br/>(NEW Sprint 3)"]
        Styles["styles.css<br/>Theme & Dark Mode (NEW)"]
    end

    subgraph "Storage"
        ConfigEntry["HA ConfigEntry<br/>(thresholds)"]
        NotifDB["Notifications State<br/>(HA Storage)"]
    end

    subgraph "User"
        Browser["Browser<br/>HA Sidebar Panel"]
    end

    HA -->|state_changed events| Events
    Events -->|battery entity changes| Monitor
    Monitor -->|device changes| SubMgr
    SubMgr -->|broadcast| WSApi
    Monitor -->|threshold check| NotifMgr
    NotifMgr -->|POST to service| PersistNotif

    Init -->|register panel| HA
    Init -->|register commands| HA
    Init -->|create managers| Monitor
    Init -->|create subscription mgr| SubMgr
    Init -->|create notification mgr| NotifMgr

    Config -->|store options| ConfigEntry
    ConfigEntry -->|load thresholds| Monitor
    ConfigEntry -->|load notif prefs| NotifMgr

    Panel -->|WebSocket connect| WSApi
    Panel -->|query_devices (pagination)| WSApi
    Panel -->|set_notification_preferences| WSApi
    SettingsUI -->|manage rules| Panel
    NotifPrefs -->|configure alerts| Panel
    SortFilterUI -->|sort/filter| Panel
    BackToTop -->|smooth scroll| Panel
    Panel -->|render| Browser

    WSApi -->|query response (paginated)| Panel
    WSApi -->|device_changed events| Panel
    WSApi -->|notification_sent events| Panel
    WSApi -->|status events (with theme)| Panel

    Styles -->|CSS custom properties| Panel
    Styles -->|dark mode colors| Panel

    classDef primary fill:#03A9F4,stroke:#0288D1,color:#fff
    classDef critical fill:#F44336,stroke:#D32F2F,color:#fff
    classDef success fill:#4CAF50,stroke:#388E3C,color:#fff
    classDef warning fill:#FF9800,stroke:#F57C00,color:#fff
    classDef neutral fill:#F5F5F5,stroke:#E0E0E0,color:#212121

    class Panel primary
    class NotifMgr critical
    class Monitor success
    class SettingsUI warning
```

### New Components in Sprint 3

**Backend**:
- `NotificationManager` — Handles threshold monitoring, notification frequency caps, per-device preferences
- Enhanced `websocket_api.py` — New commands: `set_notification_preferences`, `get_notification_preferences`
- Enhanced `battery_monitor.py` — Entity filtering (battery_level attribute only)

**Frontend**:
- `Notification Preferences Modal` — Configure per-device alerts, frequency caps, severity filters
- `Back to Top Button` — Sticky button for infinite scroll lists
- `Theme Detection & CSS Variables` — Automatic dark mode support
- Enhanced `vulcan-brownout-panel.js` — Cursor-based pagination, skeleton loaders

---

## Data Flow: Infinite Scroll with Pagination

### Scenario: User Scrolls to Bottom, Next Batch Fetches

```
T=0s:
  User has scrolled to item 50 (of 200 total)
  Currently showing items 0-49
  WebSocket subscription active
  Last item visible: offset=49, battery_level=25%, last_changed="2026-02-22T10:00:00Z"

T=50ms:
  User scrolls down, approaches item 50
  Event: ScrollNearBottom (within 100px of bottom)

T=100ms:
  Frontend calculates cursor:
    last_changed=2026-02-22T10:00:00Z
    entity_id=sensor.kitchen_motion_battery
    Cursor = base64("2026-02-22T10:00:00Z|sensor.kitchen_motion_battery")

T=150ms:
  Frontend sends: vulcan-brownout/query_devices
    {
      limit: 50,
      cursor: "base64(...)",  ← NEW: cursor-based pagination
      sort_key: "priority",
      sort_order: "asc"
    }

T=200-300ms:
  Backend processes query:
    - Finds cursor position in entity registry
    - Returns next 50 items after cursor
    - Orders by: status (critical < warning < healthy), then battery_level asc
    - Filters: device_class=battery AND battery_level IS NOT NULL

T=300ms:
  Response arrives:
    {
      devices: [...50 items...],
      total: 200,
      has_more: true,
      next_cursor: "base64(...)"  ← Cursor for next fetch
    }

T=300-350ms:
  Skeleton loaders appear (5 placeholder cards)
  Animation: opacity 0 → 1 (300ms)

T=350-600ms:
  Real devices arrive and fade in
  Skeleton loaders fade out simultaneously

T=600ms:
  New items appended to list
  User can continue scrolling
  If scroll continues to bottom, process repeats
```

---

## Data Flow: Notification System

### Scenario 1: Battery Drops Below Threshold

```
T=0s:
  Device "Front Door Lock" battery at 20%
  Threshold: 15%
  Status: CRITICAL (will trigger notification)
  Notification preferences: enabled, frequency cap = 6 hours

T=5s:
  Battery level changes: 20% → 8%
  HA fires: state_changed event

T=5-50ms:
  BatteryMonitor.on_state_changed()
  NotificationManager.check_and_queue_notification()
  Checks:
    1. Notifications enabled globally? YES
    2. Notifications enabled for this device? YES
    3. Frequency cap: Has notification been sent in last 6h? NO
    4. All checks pass → Queue notification

T=100ms:
  POST /api/services/persistent_notification/create
  Payload:
    {
      "title": "🔋 Battery Low",
      "message": "Front Door Lock battery critical (8%)",
      "notification_id": "vulcan_brownout.front_door_lock.critical"
    }

T=200ms:
  HA notification service responds 200 OK
  Notification appears in HA sidebar
  Timestamp of notification saved to NotificationManager

T=300ms:
  NotificationManager broadcasts: notification_sent event to all WebSocket clients
  Frontend updates notification history

T=300ms+:
  User sees:
    1. HA notification in sidebar
    2. Notification history in panel
    3. Device status unchanged (already CRITICAL)
    4. Frequency cap prevents spam: next notification after 6h
```

### Scenario 2: Threshold Changes, Device Status Updates

```
T=0s:
  Device: "Kitchen Sensor" at 18%
  Global threshold: 15%
  Status: WARNING (18% is between 15% and 25%)
  Notification: Enabled for this device

T=100ms:
  User opens settings, changes global threshold: 15% → 30%
  User saves

T=150ms:
  Frontend sends: vulcan-brownout/set_notification_preferences
    {
      enabled: true,
      global_threshold: 30,  ← Changed
      per_device: {...}
    }

T=200ms:
  Backend processes:
    - Validates new threshold (30 is 5-100) ✓
    - Updates config entry
    - Recalculates status for all devices
    - NotificationManager rechecks all devices against new threshold

T=250ms:
  Kitchen Sensor status changes: WARNING (18%) → CRITICAL (now ≤ 30%)
  NotificationManager checks frequency cap: last notification? 2 days ago
  Frequency cap has reset → Send notification

T=300ms:
  POST /api/services/persistent_notification/create
    Message: "Kitchen Sensor battery critical (18%)"

T=350ms:
  Backend broadcasts: threshold_updated + notification_sent events

T=400ms:
  All clients re-render:
    - Kitchen Sensor color: orange (WARNING) → red (CRITICAL)
    - Notification history updated
    - Threshold in status bar updated
```

---

## Data Flow: Theme Detection & Application

### Scenario: User Opens Panel in Dark Mode

```
T=0ms:
  User opens HA with dark theme
  HA sets: document.documentElement.setAttribute('data-theme', 'dark')
  User clicks sidebar, opens Vulcan Brownout panel

T=50ms:
  Frontend JavaScript executes on component load
  detectTheme() function runs:
    - Check: document.documentElement.getAttribute('data-theme') === 'dark'
    - Result: YES, dark mode detected

T=100ms:
  CSS variables applied:
    --vb-bg-primary: #1C1C1C (dark)
    --vb-bg-card: #2C2C2C (dark card)
    --vb-text-primary: #FFFFFF (white text)
    --vb-color-critical: #FF5252 (brightened red)
    --vb-color-warning: #FFB74D (lightened amber)
    --vb-color-healthy: #66BB6A (lightened green)

T=150ms:
  Panel renders with dark mode colors
  User sees battery list in dark theme
  Status colors adjusted for dark background contrast

T=150ms+:
  MutationObserver listens for theme changes
  If user toggles HA theme while panel is open:
    - Detects data-theme attribute change
    - Calls applyTheme() to update CSS variables
    - Smooth transition (300ms CSS) to new theme
    - No page reload needed
    - Real-time updates continue uninterrupted
```

---

## Data Flow: Binary Sensor Filtering

### Scenario: Query Devices, Binary Sensors Excluded

```
T=0ms:
  Test HA instance has 47 total entities:
    - 42 sensors with device_class=battery + battery_level attribute
    - 5 binary_sensors with device_class=battery but NO battery_level
    (binary sensors report on/off state, not %)

T=50ms:
  Frontend sends: vulcan-brownout/query_devices
    {
      limit: 50,
      offset: 0,
      sort_key: "priority"
    }

T=100-200ms:
  Backend query_devices handler:
    - Query HA entity registry
    - Filter: WHERE device_class='battery' AND battery_level IS NOT NULL
    - Binary sensors excluded (they lack battery_level attribute)
    - Result: 42 devices (5 binary_sensors filtered out)

T=200ms:
  Response:
    {
      devices: [...42 battery devices...],
      total: 42,
      device_statuses: {
        critical: 2,
        warning: 3,
        healthy: 37,
        unavailable: 0
      }
    }

T=250ms:
  Frontend renders battery list with 42 devices
  Empty state NOT shown (devices found)
  User sees accurate battery data, no confusing "unavailable" binary_sensors
```

---

## Entity Filtering Pipeline

### Schema for Battery Entity Detection

```python
def is_battery_entity(entity_id: str, entity_data: dict) -> bool:
    """
    Determine if entity should appear in battery list.

    Criteria:
    1. Entity is a sensor or compatible domain
    2. device_class is "battery"
    3. battery_level attribute exists and is numeric (0-100)
    4. Entity is NOT a binary_sensor (excluded)

    Returns: bool
    """
    # Step 1: Check entity type (exclude binary_sensors)
    domain = entity_id.split('.')[0]
    if domain == 'binary_sensor':
        return False  # Binary sensors report on/off, not %

    # Step 2: Check device_class
    device_class = entity_data.attributes.get('device_class')
    if device_class != 'battery':
        return False

    # Step 3: Check battery_level attribute
    battery_level = entity_data.attributes.get('battery_level')
    if battery_level is None:
        return False

    # Step 4: Validate numeric range
    try:
        level = float(battery_level)
        if not (0 <= level <= 100):
            return False
    except (TypeError, ValueError):
        return False

    return True  # ✓ Valid battery entity
```

---

## Cursor-Based Pagination Algorithm

### Why Cursor-Based Instead of Offset?

**Offset-based pagination** (Sprint 2):
- Simple: `offset=50, limit=50` gets items 50-99
- Problem: If new items inserted at position 40, offsets shift (duplicates or skipped items)
- Problem: Last 50 items by offset, but new items added meanwhile (missed items)

**Cursor-based pagination** (Sprint 3):
- Stable: Cursor points to specific item (by timestamp + entity_id)
- Advantage: New items don't affect cursor position
- Advantage: Works with real-time additions/deletions
- Implementation: `cursor = base64("{last_changed}|{entity_id}")`

### Algorithm

```python
def query_devices_paginated(
    limit: int = 50,
    cursor: str | None = None,
    sort_key: str = "priority"
) -> dict:
    """
    Query battery entities with cursor-based pagination.

    Args:
        limit: Number of items to return (max 100)
        cursor: Base64-encoded position marker from previous response
        sort_key: Sort method (priority, alphabetical, level_asc, level_desc)

    Returns:
        {
            devices: [...items...],
            total: 200,  # Total items available
            has_more: bool,
            next_cursor: "base64(...)" or None if at end
        }
    """

    # Step 1: Get all battery entities
    all_entities = [e for e in HA.entities if is_battery_entity(e)]

    # Step 2: Apply sort
    all_entities = apply_sort(all_entities, sort_key)

    # Step 3: Find cursor position
    start_index = 0
    if cursor:
        last_changed, entity_id = base64_decode(cursor)
        for i, entity in enumerate(all_entities):
            if (
                entity.last_changed.isoformat() == last_changed and
                entity.entity_id == entity_id
            ):
                start_index = i + 1  # Start AFTER cursor
                break

    # Step 4: Slice to limit
    end_index = start_index + limit
    page_items = all_entities[start_index:end_index]

    # Step 5: Build response
    has_more = end_index < len(all_entities)
    next_cursor = None
    if has_more and page_items:
        last_item = page_items[-1]
        next_cursor = base64_encode(
            f"{last_item.last_changed.isoformat()}|{last_item.entity_id}"
        )

    return {
        "devices": [serialize_device(e) for e in page_items],
        "total": len(all_entities),
        "has_more": has_more,
        "next_cursor": next_cursor
    }
```

---

## Notification Manager Architecture

### Notification Preferences Structure

```python
notification_preferences = {
    "enabled": True,  # Global on/off
    "frequency_cap_hours": 6,  # 1, 6, or 24
    "severity_filter": "critical_only",  # critical_only or critical_and_warning
    "per_device": {
        "sensor.front_door_lock_battery": {
            "enabled": True,
            "last_notification_time": "2026-02-22T10:15:00Z",  # ISO8601
            "frequency_cap_hours": 6  # Can override global
        },
        "sensor.kitchen_sensor_battery": {
            "enabled": False,  # Don't notify for this device
            "last_notification_time": None,
            "frequency_cap_hours": 6
        },
        # ... more devices
    }
}
```

### Notification Frequency Cap Logic

```python
def should_send_notification(
    entity_id: str,
    current_status: str,  # critical or warning
    preferences: dict
) -> bool:
    """
    Check if notification should be sent based on frequency cap.

    Rules:
    1. Global notifications disabled? Return False
    2. Device notifications disabled? Return False
    3. Status not in severity filter? Return False
    4. Within frequency cap window? Return False (already notified recently)
    5. Otherwise? Return True (send notification)
    """

    # Step 1: Check global setting
    if not preferences['enabled']:
        return False

    # Step 2: Check per-device setting
    device_pref = preferences['per_device'].get(entity_id, {})
    if not device_pref.get('enabled', True):  # Default to enabled
        return False

    # Step 3: Check severity filter
    severity_filter = preferences['severity_filter']
    if severity_filter == 'critical_only' and current_status == 'warning':
        return False
    # (critical_and_warning accepts both)

    # Step 4: Check frequency cap
    last_notif_time = device_pref.get('last_notification_time')
    if last_notif_time:
        frequency_cap_hours = device_pref.get(
            'frequency_cap_hours',
            preferences['frequency_cap_hours']
        )
        time_since_last = datetime.now() - parse(last_notif_time)
        if time_since_last < timedelta(hours=frequency_cap_hours):
            return False  # Too soon, within cap window

    # Step 5: All checks passed
    return True
```

---

## Theme Detection & CSS Variables

### Supported Theme Detection Methods

```javascript
function detectTheme() {
  // Method 1: HA's data-theme attribute (most reliable)
  const haTheme = document.documentElement.getAttribute('data-theme');
  if (haTheme === 'dark') return 'dark';
  if (haTheme === 'light') return 'light';

  // Method 2: CSS Media Query (OS preference)
  if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
    return 'dark';
  }

  // Method 3: HA localStorage (fallback)
  const stored = localStorage.getItem('ha_theme');
  if (stored) return stored;

  // Default: light
  return 'light';
}
```

### CSS Custom Properties (Dark & Light)

```css
/* Light Mode (Default) */
:root,
[data-theme="light"] {
  --vb-bg-primary: #FFFFFF;
  --vb-bg-card: #F5F5F5;
  --vb-bg-divider: #E0E0E0;
  --vb-text-primary: #212121;
  --vb-text-secondary: #757575;
  --vb-text-disabled: #BDBDBD;
  --vb-color-critical: #F44336;
  --vb-color-warning: #FF9800;
  --vb-color-healthy: #4CAF50;
  --vb-color-unavailable: #9E9E9E;
  --vb-color-primary-action: #03A9F4;
  --vb-color-success: #4CAF50;
  --vb-color-error: #F44336;
  --vb-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  --vb-skeleton-bg: #E0E0E0;
  --vb-skeleton-shimmer: #F5F5F5;
}

/* Dark Mode */
[data-theme="dark"],
[data-theme="dark-theme"] {
  --vb-bg-primary: #1C1C1C;
  --vb-bg-card: #2C2C2C;
  --vb-bg-divider: #444444;
  --vb-text-primary: #FFFFFF;
  --vb-text-secondary: #B0B0B0;
  --vb-text-disabled: #666666;
  --vb-color-critical: #FF5252;       /* Brightened red */
  --vb-color-warning: #FFB74D;        /* Lightened amber */
  --vb-color-healthy: #66BB6A;        /* Lightened green */
  --vb-color-unavailable: #BDBDBD;    /* Unchanged gray */
  --vb-color-primary-action: #03A9F4; /* HA blue (unchanged) */
  --vb-color-success: #66BB6A;        /* Lightened green */
  --vb-color-error: #FF5252;          /* Brightened red */
  --vb-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
  --vb-skeleton-bg: #444444;
  --vb-skeleton-shimmer: #555555;
}

/* Apply to all components */
.battery-panel {
  background-color: var(--vb-bg-primary);
  color: var(--vb-text-primary);
  border-color: var(--vb-bg-divider);
}

.battery-card {
  background-color: var(--vb-bg-card);
  color: var(--vb-text-primary);
  box-shadow: var(--vb-shadow);
}

.battery-critical {
  color: var(--vb-color-critical);
  background-color: rgba(255, 82, 82, 0.1); /* Subtle background */
}

.battery-warning {
  color: var(--vb-color-warning);
}

.battery-healthy {
  color: var(--vb-color-healthy);
}

.battery-unavailable {
  color: var(--vb-color-unavailable);
  opacity: 0.6;
}
```

---

## Skeleton Loader Animation (Dark Mode)

```css
@keyframes shimmer {
  0% {
    background-position: -1000px 0;
  }
  100% {
    background-position: 1000px 0;
  }
}

.skeleton-loader {
  background: linear-gradient(
    90deg,
    var(--vb-skeleton-bg) 25%,
    var(--vb-skeleton-shimmer) 50%,
    var(--vb-skeleton-bg) 75%
  );
  background-size: 1000px 100%;
  animation: shimmer 2s infinite;
  border-radius: 4px;
  height: 16px;
  margin-bottom: 8px;
}

.skeleton-loader.short {
  width: 60%;
}

.skeleton-loader.long {
  width: 100%;
}
```

---

## Connection State Machine (Sprint 3 Updates)

```
[DISCONNECTED]
    ↓ (User opens sidebar)

[CONNECTING]
    ├─ WebSocket handshake
    ├─ HA authentication
    └─ (50-200ms)

[CONNECTED] ← Status badge: 🟢 GREEN
    ├─ Events can be received
    ├─ Real-time updates flowing
    ├─ Timestamp actively updating
    ├─ Notifications can be triggered
    └─ (Normal operation)

[CONNECTED] ──→ [RECONNECTING] ← Status badge: 🔵 BLUE (spinning)
    │ (Network drops)
    │ (No data > 5s)
    ├─ Exponential backoff: wait 1s, 2s, 4s, 8s, 16s, 30s
    ├─ Retry WebSocket connect
    └─ (Device shows grayed out)

[RECONNECTING] ──→ [CONNECTED] ← Automatic recovery
    ├─ Auth succeeds
    ├─ Re-subscribe to updates
    ├─ Notification frequency caps preserved
    ├─ Toast: "✓ Connection updated"
    └─ Fresh data loaded

[RECONNECTING] ──→ [OFFLINE] ← Status badge: 🔴 RED
    │ (Max retries exceeded ~1 min)
    ├─ User sees offline message
    ├─ Can manually click "Retry"
    └─ (Device shows grayed out)

[OFFLINE] ──→ [CONNECTING] ← (User clicks "Retry" or page reloads)
    └─ Attempt to re-establish connection

[OFFLINE] ──→ [DISCONNECTED] ← (User closes sidebar)
    └─ Release subscription resources
```

---

## Performance Targets

| Operation | Target | Reasoning |
|-----------|--------|-----------|
| Initial load (50 items) | < 1s | User sees list quickly |
| Infinite scroll fetch | < 500ms | Smooth append to list |
| Skeleton loader display | 300ms | Smooth transition |
| Notification delivery | < 2s | HA notification service + broadcast |
| Theme detection | < 50ms | No flashing |
| Theme transition | 300ms | Smooth CSS animation |
| Query 200+ devices | < 500ms | Backend filtering + pagination |
| Binary sensor filtering | < 100ms | Built into query |
| Sort 200 devices | < 50ms | Client-side, in-memory |
| Filter 200 devices | < 50ms | Client-side array filter |
| Dark mode rendering | < 100ms | CSS custom properties |

---

## Error Handling

### Backend Errors (Sprint 3)

| Scenario | Handling | User Sees |
|----------|----------|-----------|
| Invalid cursor | Reset to offset=0 | Pagination restarts (no error) |
| Notification service unavailable | Queue locally, retry on reconnect | Silent, no notification sent |
| Notification preferences invalid | Validate on save, show error | Error message in modal |
| Theme detection fails | Default to light mode | Light mode displayed |
| Entity attribute missing | Filter out (exclude from list) | Entity not shown (no error) |

### Frontend Errors (Sprint 3)

| Scenario | Handling | User Sees |
|----------|----------|-----------|
| Infinite scroll API fails | Retry with backoff | Error "Failed to load more devices" |
| Notification modal save fails | Show error, form preserved | Error message + retry button |
| Dark mode CSS variables unavailable | Fall back to hardcoded colors | Colors may not match theme |
| localStorage full | Fail silently (no persistence) | No skeleton loaders on reload |
| Theme detection unavailable | Default to light | Light mode displayed |

---

## Scalability

### Supported Scales (Sprint 3)

| Metric | Limit | Notes |
|--------|-------|-------|
| Devices per user | 200+ | Cursor-based pagination, server-side filtering |
| Concurrent users | 20+ | Per HA instance, WebSocket subscriptions |
| Notifications per minute | 50+ | Frequency caps prevent spam |
| Notification history items | 100+ | Stored in HA state |
| Devices with custom notif prefs | 50+ | Per-device configuration |
| Real-time events/second | 100+ | Debounced on frontend |

### Future Upgrade Path (Sprint 4+)

- Server-side sort/filter for advanced queries (device_class, type, manufacturer)
- Notification aggregation (batch multiple alerts into one)
- Notification scheduling (quiet hours, do-not-disturb)
- Battery degradation graphs and historical trends
- Bulk operations (apply threshold to multiple devices)
- Multi-language support (i18n framework ready)

---

## Security & Privacy

**Authentication**: Uses HA's WebSocket session (same as Sprint 1-2)

**Authorization**: HA's core device registry controls visibility; only user's devices shown

**Notifications**: Stored in HA's persistent_notification service (secure)

**Notification Preferences**: Stored in HA's config entry (encrypted with HA's key)

**Data**: No telemetry, no external API calls (only HA internal)

**Encryption**: HTTPS/WSS (HA handles)

**Theme Data**: No personal data; theme preference is read-only from HA

**Binary Sensor Filtering**: No user data exposure; filtering is deterministic

---

## Related Documentation

- [ADR-009: Cursor-Based Pagination](./adrs/ADR-009-cursor-pagination.md)
- [ADR-010: Notification Service Integration](./adrs/ADR-010-notification-service.md)
- [ADR-011: Theme Detection & Dark Mode](./adrs/ADR-011-dark-mode-support.md)
- [ADR-012: Binary Sensor Entity Filtering](./adrs/ADR-012-entity-filtering.md)
- [API Contracts](./api-contracts.md)
- [Sprint Plan](./sprint-plan.md)
- [Delegation Brief](./delegation-brief.md)
- [Product Design Brief](../design/product-design-brief.md)
- [Wireframes](../design/wireframes.md)
- [Interactions](../design/interactions.md)

---

**Approved by**: [Architect]
**Implementation**: [Lead Developer]
**Code Review**: [Code Review Lead]
