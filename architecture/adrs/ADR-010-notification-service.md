# ADR-010: Home Assistant Notification Service Integration

**Date**: February 22, 2026
**Status**: Proposed
**Deciders**: FiremanDecko (Architect), ArsonWells (Lead Developer)
**Sprint**: Sprint 3

## Context

Sprint 3 introduces proactive notifications: when a battery drops below threshold, users should receive an alert in Home Assistant. This is the #1 feature request from users (15 upvoted issues).

**Challenge**: How to integrate with HA's notification system in a way that is:
1. User-friendly (notifications appear in HA sidebar)
2. Non-spammy (frequency caps, per-device control)
3. Persistent (users can review notification history)
4. Reliable (notifications don't get lost during disconnects)

## Options Considered

### Option 1: Use HA's `persistent_notification` Service (CHOSEN)

**How It Works**:
- Call HA service: `persistent_notification.create`
- HA stores notification in its database
- Notification appears in sidebar + notification center
- Users can dismiss or review history

**API Call**:
```python
await hass.services.async_call(
    'persistent_notification',
    'create',
    {
        'title': '🔋 Battery Low',
        'message': 'Front Door Lock battery critical (8%) — action needed soon',
        'notification_id': 'vulcan_brownout.front_door_lock.critical'
    }
)
```

**Pros**:
- ✅ Built-in to Home Assistant (no external dependency)
- ✅ Native HA notification UI (familiar to users)
- ✅ Persistent storage (survives restarts)
- ✅ Notification center integration (review history)
- ✅ Deduplication via `notification_id` (same ID = update, not duplicate)
- ✅ Works with HA's existing notification routing (web, mobile, email)

**Cons**:
- ⚠️ Requires HA service to be available (blocking call)
- ⚠️ No scheduling/quiet hours (would need custom logic)

**Verdict**: ✅ Best choice for native HA integration

---

### Option 2: Custom In-Memory Notification Queue

Store notifications in Vulcan Brownout's database/memory, serve via separate API endpoint.

**Pros**:
- Full control over notification behavior
- Can implement scheduling, quiet hours, etc.

**Cons**:
- ❌ Duplicates HA's notification system (why?)
- ❌ Users don't see notifications in HA sidebar
- ❌ Requires separate UI to view history
- ❌ More code to maintain

**Verdict**: ❌ Reinventing the wheel

---

### Option 3: Send Notifications via MQTT

Use HA's MQTT integration to trigger automations.

**Pros**:
- Decoupled from notification system

**Cons**:
- ❌ Overly complex for this use case
- ❌ Requires MQTT setup
- ❌ Less reliable than direct service call

**Verdict**: ❌ Overkill

---

## Decision

**Use HA's `persistent_notification` service for notification delivery (Option 1).**

### Implementation Strategy

1. **NotificationManager** class monitors battery levels in real-time
2. When battery drops below threshold:
   - Check notification preferences (enabled? frequency cap? severity filter?)
   - Call `hass.services.async_call('persistent_notification', 'create', ...)`
   - Track `last_notification_time` per device (for frequency cap)
3. Users can review notifications in HA notification center
4. Frequency caps prevent spam (configurable: 1h, 6h, 24h)

### Notification Payload

**Title**: `🔋 Battery Low` (always)

**Message Format**: `{Device} battery {status} ({level}%) — action needed soon`

Examples:
- `Front Door Lock battery critical (8%) — action needed soon`
- `Kitchen Sensor battery warning (18%) — action needed soon`

**notification_id**: `vulcan_brownout.{entity_id}.{status}`

Purpose: Deduplication. Same ID means update existing notification, not create duplicate.

## Frequency Cap Logic

To prevent notification spam, enforce per-device frequency caps:

```python
def should_send_notification(entity_id: str, preferences: dict) -> bool:
    """Check if notification should be sent based on frequency cap."""
    # Check 1: Global enabled?
    if not preferences['enabled']:
        return False

    # Check 2: Device enabled?
    device_pref = preferences['per_device'].get(entity_id, {})
    if not device_pref.get('enabled', True):
        return False

    # Check 3: Severity filter
    severity = preferences['severity_filter']
    if severity == 'critical_only' and status == 'warning':
        return False

    # Check 4: Within frequency cap window?
    frequency_cap_hours = device_pref.get('frequency_cap_hours', preferences['frequency_cap_hours'])
    last_notif_time = self.notification_history.get(entity_id)
    if last_notif_time:
        time_since = datetime.now() - last_notif_time
        if time_since < timedelta(hours=frequency_cap_hours):
            return False  # Too soon, within cap window

    return True  # ✅ Send notification
```

Example:
- Device: Front Door Lock
- Current status: CRITICAL (8%)
- Frequency cap: 6 hours
- Last notification: 2 hours ago
- Result: ❌ Don't send (within 6-hour cap)

---

## Notification History UI

Frontend displays last 5-10 notifications in Notification Preferences modal:

```
2026-02-22 10:15 — Front Door Lock (8% critical)
2026-02-22 09:30 — Solar Backup (5% critical)
2026-02-21 14:20 — Kitchen Sensor (18% warning)
```

Click "View All History" → Opens HA's notification center (built-in HA UI).

### Backend Storage

Track last notification time per device in NotificationManager:

```python
self.notification_history = {
    'sensor.front_door_lock_battery': '2026-02-22T10:15:00Z',  # ISO8601
    'sensor.solar_backup_battery': '2026-02-22T09:30:00Z',
    # ... more devices
}
```

Persist to HA config entry on save (so thresholds survive restart).

---

## Handling Edge Cases

### Edge Case 1: HA Notification Service Unavailable

If `persistent_notification.create` fails:
- Log error: `_LOGGER.error(f"Failed to send notification for {entity_id}: {error}")`
- Queue locally (keep in memory)
- Retry on next status update
- Don't lose notification (eventual delivery)

### Edge Case 2: Duplicate Notifications Due to Real-Time Updates

If battery level bounces: 95% → 8% → 10% → 8% (rapid changes):
- Frequency cap prevents duplicates (only 1 notification per 6h per device)
- `notification_id` ensures deduplication (same ID = update, not new notification)

### Edge Case 3: User Disables Notifications, Battery Still Critical

Backend respects user preferences:
- If notifications disabled for device X: never send notification, even if critical
- User must opt-in per device

### Edge Case 4: WebSocket Disconnect During Notification Queue

If client disconnects while notifications being checked:
- NotificationManager continues in background (decoupled from WebSocket)
- Notification still sent to HA
- On reconnect, client catches up via notification history

---

## Notification Preferences Storage

Store in HA config entry options:

```json
{
  "notification_preferences": {
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
    }
  }
}
```

Persists across HA restarts.

---

## Performance Considerations

- **Notification Service Call**: ~100-200ms (HA internal service call)
- **Frequency Check**: ~1ms (in-memory lookup)
- **Total Latency**: Battery change → Notification sent: < 2 seconds

---

## Testing Strategy

1. **Unit Tests**:
   - Frequency cap logic (mock time, test window expiration)
   - Preference validation (enable/disable per device)
   - Severity filter (critical vs warning)

2. **Integration Tests**:
   - Create real HA service call
   - Verify notification appears in HA notification center
   - Test with 5+ devices going critical simultaneously

3. **E2E Tests**:
   - Full workflow: device critical → notification sent → history updated
   - User disables device → no notification sent
   - Frequency cap window expires → next notification sent

---

## Consequences

### Positive
- ✅ Native HA integration (users see notifications in sidebar)
- ✅ Persistent notification history (can review past alerts)
- ✅ No external dependencies (uses HA's built-in service)
- ✅ Frequency caps prevent spam
- ✅ Per-device control (users decide which devices to alert on)

### Negative
- ⚠️ Requires HA notification service to be available
- ⚠️ No built-in quiet hours (would need custom logic)
- ⚠️ Notification persistence depends on HA database

### Mitigation
- Log errors if notification service fails (let user know)
- Queue notifications locally, retry on next opportunity
- Document that notifications depend on HA's availability

---

## Related Decisions

- ADR-011: Theme Detection & Dark Mode (notifications visible on dark background)
- ADR-012: Entity Filtering (only battery_level entities trigger notifications)

---

**Decision**: ✅ Use HA's `persistent_notification` service
**Implementation**: Sprint 3, Story 3
**Owner**: ArsonWells (Lead Developer)
**Reviewed by**: FiremanDecko (Architect)
