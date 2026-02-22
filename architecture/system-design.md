# System Design — Sprint 3

## Architecture

```
HA Core: State Machine + Event Bus + persistent_notification service
    ↓ state_changed events
Vulcan Brownout Integration:
    __init__.py        → Setup, register panel/commands, create managers
    config_flow.py     → Settings UI, ConfigEntry.options storage
    BatteryMonitor     → Entity discovery, filtering, cursor pagination
    SubMgr             → WebSocket subscription broadcasting
    NotificationMgr    → Threshold monitoring, frequency caps, HA notification service
    websocket_api.py   → WS command handlers (query_devices, subscribe, set_threshold, get/set_notification_preferences)
    ↓ WebSocket
Frontend (Lit Element):
    vulcan-brownout-panel.js → Main panel with infinite scroll, skeleton loaders, back-to-top
    Settings Panel           → Threshold config + notification preferences modal
    styles.css               → CSS custom properties for dark/light theme
```

## Sprint 3 Features
1. **Cursor pagination**: base64(last_changed|entity_id), 50 items/page, max 100
2. **Entity filtering**: Exclude binary_sensor domain + require numeric battery_level 0-100
3. **Notifications**: HA persistent_notification, frequency caps (1/6/24h), severity filter (critical_only|critical_and_warning), per-device enable
4. **Dark mode**: CSS custom properties, 3-level detection (data-theme → matchMedia → localStorage), MutationObserver for live switching
5. **Deployment**: Idempotent bash+rsync, symlink releases, health check endpoint, .env validation

## Key Algorithms

### Entity Filter
```python
def is_battery_entity(entity_id, entity_data):
    if entity_id.split('.')[0] == 'binary_sensor': return False
    if entity_data.attributes.get('device_class') != 'battery': return False
    level = entity_data.attributes.get('battery_level')
    if level is None: return False
    try: return 0 <= float(level) <= 100
    except: return False
```

### Notification Check
```python
# Checks in order: global enabled → device enabled → severity filter → frequency cap
# Frequency cap: track last_notification_time per device, skip if within cap window
# Sends via hass.services.async_call('persistent_notification', 'create', ...)
```

### Theme Detection
```javascript
// 1. document.documentElement.getAttribute('data-theme') === 'dark'
// 2. window.matchMedia('(prefers-color-scheme: dark)').matches
// 3. localStorage.getItem('ha_theme')
// MutationObserver watches data-theme attribute changes on <html>
```

## Color Tokens

| Element | Light | Dark |
|---------|-------|------|
| Background | #FFFFFF | #1C1C1C |
| Card | #F5F5F5 | #2C2C2C |
| Text Primary | #212121 | #FFFFFF |
| Text Secondary | #757575 | #B0B0B0 |
| Critical | #F44336 | #FF5252 |
| Warning | #FF9800 | #FFB74D |
| Healthy | #4CAF50 | #66BB6A |
| Unavailable | #9E9E9E | #BDBDBD |
| Action Blue | #03A9F4 | #03A9F4 |

All dark mode colors pass WCAG AA (4.5:1 minimum contrast on #1C1C1C).

## Connection States
DISCONNECTED → CONNECTING → CONNECTED (green) → RECONNECTING (blue, exp backoff 1-30s) → OFFLINE (red, manual retry)

## Performance Targets
Initial load <1s, scroll fetch <500ms, notification <2s, theme detection <50ms, theme transition 300ms CSS.

## Security
- HA WebSocket session auth, HA device registry controls visibility
- No telemetry, no external API calls
- HTTPS/WSS (HA handles), notifications in HA secure storage
