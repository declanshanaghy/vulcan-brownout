# ADR-007: Threshold Configuration Storage & UI Flow

**Status**: Proposed
**Sprint**: 2

## Decision

**Implement Option 1: HA ConfigEntry Options Flow**

Store thresholds in `hass.config_entries[entry_id].options` dictionary. Use HA's standard options flow (config flow UI). Thresholds persist across restarts and sync with HA backups.

## Rationale

- **HA native**: Follows established HA patterns; users familiar with HA understand it
- **Persistent**: Saved by HA framework, survives restarts and updates
- **Synced**: Works with HA backups and multi-instance setups
- **Versioned**: HA handles schema changes automatically
- **Validated**: voluptuous schema validates inputs before saving

## Implementation Details

**Config entry options schema**:
```python
{
    'global_threshold': 15,      # int: 5-100 (default 15)
    'device_rules': {
        'sensor.solar_backup_battery': 50,
        'sensor.front_door_lock_battery': 30,
        # ... up to 10 device-specific rules
    },
    'filter_state': 'all',       # For persistence
    'sort_method': 'priority'    # For persistence
}
```

**Backend changes** (`battery_monitor.py`):
- Load threshold options from config entry on startup
- Cache in memory for fast lookup: `get_threshold_for_device(entity_id)`
- Listen for options updates via `entry.add_update_listener()`
- On update: Re-calculate device statuses, broadcast threshold_updated event

**Frontend** (settings panel):
- Slider for global threshold (5-100%, default 15%)
- Device rules list (max 10 entries)
- "+ Add Device Rule" button
- Live preview: "X devices below this threshold"
- Save/Cancel buttons

**WebSocket command**: `vulcan-brownout/set_threshold`

Request:
```json
{
  "type": "vulcan-brownout/set_threshold",
  "id": "msg_001",
  "data": {
    "global_threshold": 20,
    "device_rules": {
      "sensor.solar_backup_battery": 50
    }
  }
}
```

Response broadcast to all clients:
```json
{
  "type": "vulcan-brownout/threshold_updated",
  "data": {
    "global_threshold": 20,
    "device_rules": {...}
  }
}
```

## Device status calculation

```python
def get_status_for_device(device):
    if not device.available: return 'unavailable'
    threshold = get_threshold_for_device(device.entity_id)
    if device.battery_level <= threshold: return 'critical'
    elif device.battery_level <= (threshold + 10): return 'warning'
    else: return 'healthy'
```

## Consequences

**Positive**:
- HA native patterns (easier for future developers)
- Persistent across HA restart/updates
- UI built-in (HA form framework)
- Validation prevents invalid inputs
- Scalable (extensible for future enhancements)
- Audit trail visible in HA's config entry history

**Negative**:
- More code (config flow boilerplate)
- Settings not user-facing by default (hidden in HA UI)

**Mitigation**:
- Custom UI in Vulcan Brownout sidebar panel (primary access point)
- Document settings in README
- Pre-populate defaults so users have working config immediately

## Migration from Sprint 1

- Existing users default to `global_threshold: 15` (same as Sprint 1)
- First settings save creates options entry automatically
- No breaking changes

## Future (Sprint 3+)

- Per-device-class thresholds (e.g., locks warn at 20%, sensors at 15%)
- Threshold schedules (stricter on weekdays)
- Threshold templates/presets
- Export/import threshold configs
- Threshold history/audit log
