# ADR-010: Home Assistant Notification Service Integration

**Date**: February 22, 2026
**Status**: Proposed
**Sprint**: Sprint 3

## Decision

**Use HA's `persistent_notification` service for notification delivery**

When battery drops below threshold, call `persistent_notification.create` to send HA-native notifications. Notifications appear in HA sidebar and notification center.

## Rationale

- **Built-in to HA**: No external dependency
- **Native HA UI**: Notifications appear in sidebar (familiar to users)
- **Persistent**: Survives restarts, visible in notification center
- **Deduplication**: Same `notification_id` = update existing, not create duplicate
- **Routing**: Works with HA's notification system (web, mobile, email)

## Implementation Details

**Notification trigger**:
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

**NotificationManager class**:
- Monitor battery levels in real-time
- Check notification preferences (enabled? frequency cap? severity?)
- Call HA notification service
- Track `last_notification_time` per device (frequency cap)

**Frequency cap logic** (prevent spam):
```python
def should_send_notification(entity_id: str, preferences: dict) -> bool:
    # Check 1: Global enabled?
    if not preferences['enabled']: return False

    # Check 2: Device enabled?
    if not preferences['per_device'].get(entity_id, {}).get('enabled', True): return False

    # Check 3: Severity filter?
    if preferences['severity_filter'] == 'critical_only' and status == 'warning':
        return False

    # Check 4: Within frequency cap window?
    freq_hours = preferences['per_device'].get(entity_id, {}).get('frequency_cap_hours', 6)
    last_notif = self.notification_history.get(entity_id)
    if last_notif and (datetime.now() - last_notif) < timedelta(hours=freq_hours):
        return False  # Too soon

    return True  # Send notification
```

**Notification preferences** (stored in config entry options):
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
        "enabled": false
      }
    }
  }
}
```

## Message format

**Title**: `🔋 Battery Low` (always)

**Message**: `{Device} battery {status} ({level}%) — action needed soon`

Examples:
- `Front Door Lock battery critical (8%) — action needed soon`
- `Kitchen Sensor battery warning (18%) — action needed soon`

**notification_id**: `vulcan_brownout.{entity_id}.{status}` (enables deduplication)

## Edge cases

**HA notification service unavailable**:
- Log error
- Queue locally
- Retry on next status update
- Don't lose notification (eventual delivery)

**Duplicate notifications** (rapid battery changes):
- Frequency cap prevents duplicates
- Same `notification_id` ensures deduplication

**User disables notifications** for device:
- Never send notification, even if critical
- User must opt-in per device

**WebSocket disconnect**:
- NotificationManager runs in background (decoupled from WebSocket)
- Notification still sent to HA
- On reconnect, client catches up via notification history

## Consequences

**Positive**:
- Native HA integration (appears in sidebar)
- Persistent notification history
- No external dependencies
- Frequency caps prevent spam
- Per-device control

**Negative**:
- Depends on HA notification service availability
- No built-in quiet hours (custom logic needed)
- Notification persistence depends on HA database

## Testing

- Unit tests: Frequency cap logic, preference validation
- Integration tests: Real HA service calls, notification center
- E2E tests: Full workflow from critical device to notification history
