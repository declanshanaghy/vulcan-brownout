# ADR-006: WebSocket Subscription Architecture for Real-Time Updates

**Status**: Proposed
**Sprint**: 2
**Author**: FiremanDecko (Architect)
**Date**: February 2026

---

## Context

Sprint 1 delivered a basic battery monitoring panel with manual refresh. Users can see battery levels, but must click refresh to check for updates. This is a poor user experience for a "monitoring" tool.

Sprint 2 requires real-time updates: when a device's battery level changes in Home Assistant, the panel should reflect that change within 2-5 seconds, without user interaction. This requires a persistent WebSocket subscription that the backend maintains for each connected client.

### Current State (Sprint 1)
- Frontend fetches device list via `query_devices` command (request-response)
- No persistent subscription
- Manual refresh only

### Desired State (Sprint 2)
- Backend automatically sends updates when battery levels change
- Frontend receives updates without polling
- Connection status visible to user
- Graceful reconnection if connection drops

---

## Options Considered

### Option 1: Push Events via WebSocket (Recommended)
Backend maintains a subscription to HA's `state_changed` events and broadcasts filtered updates to all connected clients.

**Pros:**
- Real-time feedback (< 100ms latency)
- No polling overhead
- Works with HA's native event system
- Minimal client code
- Scales well (broadcast is efficient)

**Cons:**
- Must handle concurrent subscribers
- Reconnection logic needed (if client loses connection)
- Bandwidth increases slightly with many updates

**Implementation:**
```
Client connects → Backend registers subscriber in list
→ Backend listens to HA state_changed events
→ For each battery entity change, send device_changed event to all subscribers
→ On client reconnect, resend last known state
```

### Option 2: Client-Side Polling via WebSocket
Client periodically sends `query_devices` requests, backend responds.

**Pros:**
- Simple client logic
- No persistent state tracking on backend

**Cons:**
- High latency (30-60s typical polling interval)
- Wasted bandwidth (polling empty results)
- Not truly real-time
- Scales poorly with many clients

**Decision**: Rejected. Violates "real-time" requirement.

### Option 3: Hybrid: Push + Fallback Polling
Backend sends push updates if possible; client falls back to polling if subscription fails.

**Pros:**
- Best of both worlds
- Resilient to edge cases

**Cons:**
- Complex state machine
- Harder to debug

**Decision**: Deferred to Sprint 3. Start with pure push for MVP.

---

## Decision

**Implement Option 1: WebSocket Push Events**

Backend will:
1. Maintain a list of active client subscriptions
2. Listen to HA's `state_changed` events for all battery entities
3. For each event, filter changes (only send if relevant to current display)
4. Broadcast `device_changed` event to all subscribed clients
5. Handle client disconnections gracefully

Frontend will:
1. Establish WebSocket connection on sidebar load
2. Keep connection alive with periodic ping
3. Listen for `device_changed` events
4. Update local state and re-render
5. Show connection status badge
6. Implement exponential backoff reconnection

---

## Consequences

### Positive
1. **Real-Time Experience**: Users see updates within 100ms of HA state change
2. **Low Latency**: No polling overhead; uses HA's native event system
3. **Scalable**: Broadcast model handles many clients efficiently
4. **User Confidence**: Visible connection indicator shows monitoring is active
5. **Battery Efficient**: No constant polling drains device batteries

### Negative
1. **State Complexity**: Backend must track all active subscriptions
2. **Memory Footprint**: Each client connection takes ~500 bytes for subscription tracking
3. **Debugging Harder**: Distributed state harder to troubleshoot
4. **HA Dependency**: Relies on HA's reliability; if HA drops events, users miss updates

### Mitigations
- Subscribe with exponential backoff (don't hammer HA on reconnect)
- Log all subscription events for debugging
- Implement health check endpoint to verify connectivity
- Graceful degradation: if subscription fails, fall back to cached data + timestamp
- Limit concurrent subscriptions per client (1 subscription per connection)

---

## Implementation Notes

### Backend (Python)

**New class: `WebSocketSubscriptionManager`**
```python
class WebSocketSubscriptionManager:
    def __init__(self, hass, battery_monitor):
        self.hass = hass
        self.battery_monitor = battery_monitor
        self.subscribers = {}  # {connection_id: ClientSubscription}

    async def subscribe(self, connection, client_id):
        """Register a new client subscription."""
        # Create subscription object
        # Add to subscribers list
        # Return acknowledgment

    async def unsubscribe(self, client_id):
        """Unregister client on disconnect."""
        # Remove from subscribers
        # Cleanup

    async def on_state_changed(self, entity_id, new_state):
        """Broadcast update to all subscribers."""
        # Filter: is this entity in any subscriber's visible list?
        # For each affected subscriber, send device_changed event
        # Handle errors gracefully

    async def broadcast_device_changed(self, entity_id, device_data):
        """Send update to all connected clients."""
        # For each subscriber connection:
        #   Send JSON message: {type: 'vulcan-brownout/device_changed', data: {...}}
        #   Handle connection errors (remove dead connections)
```

**Modified: `websocket_api.py`**
- Add `handle_subscribe` command handler
- Add `on_state_changed` event listener that calls subscription manager
- Maintain subscription state across requests

**Modified: `battery_monitor.py`**
- Track which entities have active subscriptions
- Optimize state change handler to only broadcast relevant updates
- Add subscription lifecycle hooks

### Frontend (JavaScript)

**New state:**
```javascript
@state() connectionStatus = 'disconnected';  // 'connected' | 'reconnecting' | 'offline'
@state() lastUpdateTime = null;
@state() subscriptionId = null;
```

**New methods:**
```javascript
async _subscribe_to_updates() {
  // Send subscribe command to backend
  // Store subscription ID
  // Set up listeners for device_changed events
}

async _on_device_changed(event) {
  // Find device by entity_id
  // Update battery_level, available, timestamp
  // Trigger re-render (Lit handles this)
  // Animate progress bar
}

_on_connection_status_changed(status) {
  // Update badge: 🟢 (connected) | 🔵 (reconnecting) | 🔴 (offline)
  // Show/hide timestamp
}

async _handle_reconnection() {
  // Wait with exponential backoff: 1s, 2s, 4s, 8s, 16s, 30s
  // Attempt re-subscribe
  // On success, refresh full device list (to catch missed updates)
}
```

### Connection Lifecycle (Detailed)

**Scenario 1: Normal Operation**
```
T=0ms:   User opens sidebar
         → Panel mounts
         → Calls _subscribe_to_updates()

T=50ms:  WebSocket connect, auth succeeds
         → Backend creates subscription object
         → Stores in subscriber list

T=100ms: Backend sends initial status
         → vulcan-brownout/status { status: 'connected' }

T=100ms: Frontend shows 🟢 (connected)
         → Battery list still shows from initial query

T=200ms+: Device changes battery level in HA
         → HA fires state_changed event
         → Backend receives event
         → Checks if any subscribers have this entity
         → Sends device_changed event to all subscribers

T=250ms: Frontend receives device_changed
         → Updates device in list
         → Triggers re-render
         → Progress bar animates
         → User sees update in real-time
```

**Scenario 2: Connection Drops**
```
T=0s:    Connection active, real-time updates flowing

T=30s:   Network disconnects (user loses WiFi)
         → WebSocket closes
         → Backend detects closed connection
         → Removes subscription from list
         → Frontend detects close (no data for >5s)

T=30s:   Frontend shows 🔵 (reconnecting)
         → Battery list becomes slightly grayed out
         → Timestamp stops updating

T=31s:   Frontend attempts reconnect
         → WebSocket connect fails
         → Waits 1s, retries

T=32s:   Reconnect attempt again (backoff: 2s)

T=34s:   Auth succeeds
         → Backend creates new subscription
         → Frontend shows 🟢 (connected)
         → Toast notification: "✓ Connection updated"

T=35s:   Frontend sends fresh query_devices to catch up
         → Gets latest state + any missed updates
         → Battery list refreshes
         → Timestamp updates again
```

**Scenario 3: HA Restarts**
```
T=0s:    Normal operation

T=60s:   HA restarts (maintenance, update, etc.)
         → WebSocket connections drop
         → Backend subscription manager cleared
         → Frontend detects disconnect

T=60s-65s: Frontend attempts reconnection (backoff)

T=65s:   HA comes back online
         → Frontend reconnects successfully
         → Backend initializes new subscription manager
         → Frontend updates, shows fresh data

T=70s+:  Real-time updates resume
```

---

## WebSocket Message Format (Updated)

### New Command: Subscribe

**Request:**
```json
{
  "type": "vulcan-brownout/subscribe",
  "id": "msg_001",
  "data": {}
}
```

**Response:**
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

### New Event: Device Changed

**Broadcast from Backend:**
```json
{
  "type": "vulcan-brownout/device_changed",
  "data": {
    "entity_id": "sensor.phone_battery",
    "battery_level": 8,
    "available": true,
    "last_changed": "2026-02-22T10:30:45Z"
  }
}
```

### New Event: Status

**Sent on Connection Established:**
```json
{
  "type": "vulcan-brownout/status",
  "data": {
    "status": "connected",
    "version": "2.0.0",
    "threshold": 15,
    "device_rules": {}
  }
}
```

---

## Testing Strategy

### Unit Tests
- `test_subscription_manager.py`: Subscribe, unsubscribe, broadcast
- `test_websocket_events.py`: Event filtering, message format
- `test_connection_state.js`: Frontend connection state machine

### Integration Tests
- Spin up HA with 10 mock battery entities
- Connect 5 concurrent clients
- Simulate battery level changes
- Verify all clients receive updates within 100ms
- Simulate client disconnect/reconnect
- Verify reconnection logic and state sync

### E2E Tests
- Open panel, watch real-time updates as battery levels change
- Simulate network drop (dev tools), verify reconnection UI
- Verify timestamp updates and connection badge changes
- Load test: 50 concurrent clients, 100 battery changes/min

---

## Open Questions

1. **Update Frequency**: Should we throttle updates if a device changes rapidly? (e.g., sending 10 updates/second might overload the UI)
   - **Proposal**: Debounce on frontend; max 1 update per 100ms per device

2. **Bandwidth Constraints**: For Home Automation users on slow connections, should we compress payloads?
   - **Proposal**: Start without compression; add if users report issues

3. **Battery Drain (Mobile)**: WebSocket keeps connection alive; drains battery on mobile HA Companion app. Acceptable?
   - **Proposal**: Add option to disable real-time in settings (Sprint 3)

4. **Subscription Limits**: Should we limit subscriptions per user (e.g., prevent opening panel multiple times)?
   - **Proposal**: One subscription per user session; multiple panel opens share same subscription

---

## Success Criteria

1. Battery levels update within 2-5 seconds of HA state change
2. Connection badge accurately reflects connection state
3. Reconnection happens automatically with exponential backoff
4. No lost updates (if client misses one, next update catches up)
5. < 500ms UI latency between state change and visual update
6. Supports 50+ concurrent subscriptions without degradation

---

## Related Documents

- `system-design.md` — Updated component diagram
- `api-contracts.md` — WebSocket message schemas
- `ADR-007` — Threshold configuration (depends on this)
- `interactions.md` — Real-time update UX flows

---

**Approved by**: [Architect]
**Implementation Lead**: [Lead Developer]
**Code Review**: [Code Review Lead]
