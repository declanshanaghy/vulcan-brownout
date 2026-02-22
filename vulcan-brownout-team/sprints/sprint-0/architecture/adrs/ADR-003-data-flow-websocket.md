# ADR-003: Data Flow and WebSocket API

## Status: Accepted

## Context

Vulcan Brownout needs real-time communication between the Home Assistant backend and the sidebar panel frontend. The key decisions are:

1. **API Protocol:** WebSocket vs REST vs gRPC?
2. **Data Flow:** Push (server sends updates) vs Pull (client requests data) vs Hybrid?
3. **Caching Strategy:** In-memory cache on backend, browser cache, or both?
4. **State Change Detection:** How does the backend know when battery levels change?
5. **Error Handling:** What happens on disconnection, timeout, or invalid data?

Requirements:
- Real-time updates when battery levels change
- Support for pagination and sorting
- Handle unavailable entities
- Efficient (minimize re-renders and network traffic)
- Respect Home Assistant's performance constraints

## Options Considered

### Option A: REST API with Polling
Frontend polls `/api/vulcan-brownout/devices?page=0&limit=20&sort=battery_level` every 5 seconds.

**Pros:**
- Simple to implement
- Stateless backend
- Standard HTTP caching applies

**Cons:**
- Inefficient — many requests for no data change
- Latency — 5-second delay before UI updates
- Does not meet "real-time" requirement
- High CPU usage at scale (100+ devices)
- Not idiomatic for HA (which uses WebSocket for real-time)

### Option B: Pure Server-Push WebSocket
Backend maintains open WebSocket, sends full device list whenever any battery level changes.

**Pros:**
- True real-time (millisecond latency)
- Frontend just receives data

**Cons:**
- Large payloads if hundreds of devices change state
- Backend must maintain state for every connected client
- Tight coupling — backend tied to frontend's display needs
- Hard to scale (memory overhead per connection)
- No pagination — backend sends everything each time

### Option C: Request-Response WebSocket (Hybrid)
Frontend sends a WebSocket command (`vulcan-brownout/query_devices`), backend responds with paginated data. Backend also sends `device_changed` events for real-time updates to currently-displayed devices.

**Pros:**
- Explicit queries for pagination/sorting (backend controls the "what")
- Real-time updates only for data user is viewing
- Efficient — only send what's needed
- Frontend drives the conversation (request-response is familiar)
- Scales well

**Cons:**
- Slightly more latency than pure push (request → response)
- More complex than pure push

### Option D: GraphQL Subscription
Structured queries with mutations and subscriptions for real-time updates.

**Pros:**
- Powerful query language
- Standardized

**Cons:**
- Overkill for a simple battery monitoring API
- Extra dependencies
- Not idiomatic for HA
- Complexity not justified by feature scope

## Decision

**Choose Option C: Request-Response WebSocket with Event Notifications**

Data flow architecture:

1. **Frontend sends WebSocket request:**
   ```
   {
     "type": "vulcan-brownout/query_devices",
     "id": "msg_123",
     "data": {
       "limit": 20,
       "offset": 0,
       "sort_key": "battery_level",
       "sort_order": "asc",
       "threshold": 15
     }
   }
   ```

2. **Backend responds immediately:**
   ```
   {
     "type": "result",
     "id": "msg_123",
     "success": true,
     "data": {
       "devices": [
         {
           "entity_id": "sensor.phone_battery",
           "name": "Phone",
           "battery_level": 12,
           "state": "12",
           "unit_of_measurement": "%",
           "device_name": "iPhone",
           "last_changed": "2026-02-22T10:15:00Z",
           "available": true
         },
         // ... more devices
       ],
       "total": 127,
       "offset": 0,
       "limit": 20
     }
   }
   ```

3. **Backend sends event notifications when displayed devices change:**
   ```
   {
     "type": "vulcan-brownout/device_changed",
     "data": {
       "entity_id": "sensor.phone_battery",
       "battery_level": 8,
       "state": "8",
       "available": true,
       "last_changed": "2026-02-22T10:16:00Z"
     }
   }
   ```

4. **Backend sends connection status:**
   ```
   {
     "type": "vulcan-brownout/status",
     "data": {
       "status": "connected",
       "threshold": 15
     }
   }
   ```

### Data Flow Diagram

```
Frontend (Panel)                    Backend (Integration)
────────────────────────────────    ──────────────────────────────

User scrolls
   │
   ├─→ [IntersectionObserver fires]
   │
   ├─→ emit: query_devices {
   │     limit: 20,
   │     offset: 20,
   │     sort_key: "battery_level"
   │   }
   │
   │                                entity_registry.async_all()
   │                                   │
   │                                   ├─→ Filter: device_class=battery
   │                                   │
   │                                   ├─→ Filter: battery_level < threshold
   │                                   │
   │                                   ├─→ Sort by sort_key/sort_order
   │                                   │
   │                                   ├─→ Slice: offset:offset+limit
   │                                   │
   │                                   └─→ Build response payload
   │
   │   ←─ [WebSocket response] ────────
   │
   ├─→ Append items to battery_devices[]
   │
   └─→ Re-render DOM
```

### In-Memory State on Backend

The `BatteryMonitor` service (in `battery_monitor.py`) maintains:

```python
class BatteryMonitor:
    def __init__(self, hass, config_entry):
        self.hass = hass
        self.threshold = config_entry.data['threshold']  # User-configurable
        self.cached_devices = []  # Refreshed on state change
        self.last_update = None

    async def query_devices(self, limit=20, offset=0, sort_key='battery_level', sort_order='asc'):
        """Fetch filtered, sorted, paginated battery devices."""
        # 1. Get all entities from HA's entity registry
        # 2. Filter: device_class=battery AND battery_level < threshold
        # 3. Sort by sort_key (battery_level, name, last_changed, etc.)
        # 4. Slice for pagination
        # 5. Return paginated results + total count
        pass

    async def handle_state_change(self, entity_id, new_state):
        """Called when any entity changes state."""
        # 1. Check if entity is in our filtered set
        # 2. If yes, and it's currently visible to any client, send device_changed event
        # 3. Update cached_devices
        pass
```

## Consequences

### Positive

1. **Efficient:** Only send data user is viewing; event updates for changes to visible devices.
2. **Scalable:** No large payloads; pagination ensures constant bandwidth.
3. **Real-Time:** Event notifications ensure sub-second updates.
4. **Idiomatic for HA:** Uses HA's WebSocket API pattern (request/response with events).
5. **Clear Contract:** Well-defined message schema (see api-contracts.md).
6. **Testable:** Decoupled frontend and backend — easy to mock WebSocket for testing.
7. **Graceful Degradation:** If connection drops, frontend shows "offline" state; reconnect re-queries.

### Negative

1. **Slight Latency:** Request-response adds ~50ms vs pure push.
   - *Mitigation:* Negligible for user experience; still feels real-time.

2. **Pagination State:** Frontend must track offset/limit. If user sorts, must reset to offset=0.
   - *Mitigation:* Clear semantic — offset resets on sort change.

3. **Cache Invalidation:** Backend must track which devices are visible to which clients.
   - *Mitigation:* Simple in-memory map; cleared on disconnect.

## Event Subscription Model

The backend tracks **currently-visible devices** for each WebSocket connection:

```python
# In websocket_api.py
client_subscriptions = {
    connection_id: {
        'entities': set(['sensor.phone_battery', 'sensor.tablet_battery', ...]),
        'timestamp': time.time()
    }
}

async def vulcan-brownout_query_devices(hass, connection, msg):
    entities = get_visible_entities(msg['data'])
    client_subscriptions[connection.id]['entities'] = set(entities)
    # ... send response

async def on_entity_state_change(hass, entity_id, new_state):
    # For each WebSocket connection:
    #   If entity_id in connection's visible set:
    #     Send device_changed event
    for connection_id, sub in client_subscriptions.items():
        if entity_id in sub['entities']:
            await connection.send_message({
                'type': 'vulcan-brownout/device_changed',
                'data': { ... }
            })
```

## Connection Lifecycle

1. **Panel loads** → Frontend connects to WebSocket (already open for HA's frontend)
2. **Connection ready** → Backend sends `vulcan-brownout/status` event
3. **User views panel** → Frontend sends `query_devices` request
4. **Backend responds** → Frontend renders first page
5. **User scrolls** → Frontend sends next `query_devices` request
6. **Entity state changes** → Backend sends `device_changed` event (if entity in visible set)
7. **User closes panel** → Frontend disconnects (or unsubscribes)
8. **Connection drops** → Frontend shows "offline" state; auto-reconnect with exponential backoff
9. **Reconnect succeeds** → Frontend re-queries to sync state

## Data Consistency Guarantees

- **Eventual Consistency:** Backend state eventually matches HA's entity state (within 1-2 seconds).
- **No Lost Updates:** Event updates are fired for every state change; not batched.
- **Idempotent Queries:** Calling `query_devices` twice returns same data (unless state changed).
- **Total Count Accurate:** `total` field reflects count at query time; may be stale if items added while paginating.
  - *Mitigation:* Frontend shows "refresh" button if user notices inconsistency.

## Security & Authentication

- All WebSocket commands use HA's built-in authentication (session token).
- No additional API keys needed.
- Authorization: Only show devices the user has access to (inherited from HA's entity access control).
- No sensitive data in responses (no passwords, tokens, etc.).
