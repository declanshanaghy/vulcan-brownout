# ADR-006: WebSocket Subscription Architecture for Real-Time Updates

**Status**: Proposed
**Sprint**: 2

## Decision

**Implement Option 1: WebSocket Push Events**

Backend maintains subscription list for connected clients. When battery entity state changes in HA, backend broadcasts `device_changed` event to all subscribers. Frontend listens for events and updates UI in real-time.

## Rationale

- **Real-time requirement**: Push model < 100ms latency vs polling 30-60 second latency
- **Server efficiency**: No polling overhead; uses HA's native event system
- **User experience**: Updates appear instantly when battery levels change
- **Scalable**: Broadcast model handles 50+ concurrent subscriptions

## Implementation Details

**Backend**:
- Maintain list of active client subscriptions
- Listen to HA's `state_changed` events
- For each battery entity change: filter, then broadcast `device_changed` to subscribers
- Handle client disconnections gracefully (remove from list)

**Frontend**:
- Establish WebSocket connection on sidebar load
- Keep connection alive with periodic ping
- Listen for `device_changed` events
- Update local state and re-render
- Show connection status badge (connected/reconnecting/offline)
- Implement exponential backoff reconnection (1s, 2s, 4s, 8s, 16s, 30s)

**WebSocket message format**:

Subscribe request:
```json
{
  "type": "vulcan-brownout/subscribe",
  "id": "msg_001",
  "data": {}
}
```

Device changed event (broadcast):
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

## Consequences

**Positive**:
- Real-time updates (< 100ms latency)
- Low latency, no polling overhead
- Scalable (broadcast handles many clients)
- User confidence (visible connection indicator)
- Battery efficient (no constant polling)

**Negative**:
- More complex state tracking (subscriptions per client)
- Memory footprint (~500 bytes per client)
- Debugging harder (distributed state)
- Depends on HA reliability

## Connection lifecycle

**Normal**: Panel opens → WebSocket connects → Subscribe succeeds → Receives updates in real-time

**Disconnect**: Network drops → Frontend detects → Shows reconnecting badge → Exponential backoff → Reconnects → Syncs latest state

**HA restart**: HA restarts → WebSocket connections drop → Frontend reconnects → Backend recreates subscriptions → Updates resume

## Testing Strategy

- Unit tests: Subscription manager, event filtering, message formats
- Integration tests: Real HA, multiple clients, battery changes, reconnection
- E2E tests: Panel loading, real-time updates, connection badge changes
