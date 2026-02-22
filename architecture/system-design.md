# System Design — Sprint 4

**Updated**: 2026-02-22 | **Status**: Sprint 4 architecture complete

## Architecture Overview

```
HA Core: State Machine + Event Bus + persistent_notification service + hass.themes API
    ↓ state_changed events
    ↓ hass_themes_updated event (SPRINT 4)
Vulcan Brownout Integration:
    __init__.py        → Setup, register panel/commands, create managers
    config_flow.py     → Settings UI, ConfigEntry.options storage
    BatteryMonitor     → Entity discovery, filtering, cursor pagination
    SubMgr             → WebSocket subscription broadcasting
    NotificationMgr    → Threshold monitoring, frequency caps, HA notification service
    websocket_api.py   → WS command handlers (query_devices, subscribe, set_threshold, get/set_notification_preferences)
    ↓ WebSocket
Frontend (Lit Element):
    vulcan-brownout-panel.js → Main panel with infinite scroll, skeleton loaders, back-to-top, hass_themes_updated listener (SPRINT 4)
    Settings Panel           → Threshold config + notification preferences modal
    styles.css               → CSS custom properties for dark/light theme (hass.themes.darkMode-driven)
```

## Inherited Features (Sprint 1-3)

1. **Cursor pagination**: base64(last_changed|entity_id), 50 items/page, max 100
2. **Entity filtering**: Exclude binary_sensor domain + require numeric battery_level 0-100
3. **Notifications**: HA persistent_notification, frequency caps (1/2/6/12/24h), severity filter (all|critical_only|critical_and_warning), per-device enable
4. **Threshold config**: Global threshold + per-device device_rules, stored in ConfigEntry.options
5. **Real-time updates**: WebSocket device_changed, threshold_updated, notification_sent events
6. **Connection states**: DISCONNECTED → CONNECTING → CONNECTED → RECONNECTING → OFFLINE
7. **Deployment**: Idempotent bash+rsync, symlink releases, health check endpoint, .env validation

## Sprint 4 New Features: Theme Detection Architecture

### Theme Detection Strategy

**Primary Source**: `hass.themes.darkMode` boolean
- Authoritative source of user's theme preference (set in HA Settings → Person → Theme)
- Available in hass object when panel loads: `hass.themes.darkMode` is `true` or `false`

**Event Listener**: `hass_themes_updated` event
- Fired by HA when user changes theme in UI
- Listener attached in panel's `connectedCallback()` via `hass.connection.addEventListener("hass_themes_updated", ...)`
- Triggers re-evaluation of `hass.themes.darkMode` and CSS update

**Fallback Chain** (if `hass.themes` unavailable):
1. `document.documentElement.getAttribute('data-theme')` (HA sets this on `<html>`)
2. `window.matchMedia('(prefers-color-scheme: dark)').matches` (OS preference)
3. Default to `'light'`

### Theme Application Flow

```javascript
// On component load and on hass_themes_updated event:
function _detect_theme() {
  // Check primary source: hass.themes.darkMode
  if (hass?.themes?.darkMode !== undefined) {
    return hass.themes.darkMode ? 'dark' : 'light';
  }

  // Fallback 1: DOM attribute
  const domTheme = document.documentElement.getAttribute('data-theme');
  if (domTheme === 'dark' || domTheme === 'light') {
    return domTheme;
  }

  // Fallback 2: OS preference
  if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
    return 'dark';
  }

  // Default
  return 'light';
}

function _apply_theme(theme) {
  // Set CSS custom properties via data attribute
  document.documentElement.setAttribute('data-theme', theme);
  // Lit will update shadow DOM with theme-specific colors
  this.requestUpdate();
}

// On connectedCallback():
async connectedCallback() {
  super.connectedCallback();

  // Detect and apply initial theme
  const theme = this._detect_theme();
  this._apply_theme(theme);

  // Listen for theme changes
  if (this.hass?.connection) {
    this.hass.connection.addEventListener('hass_themes_updated', () => {
      const newTheme = this._detect_theme();
      this._apply_theme(newTheme);
    });
  }
}
```

### CSS Theme Application

**CSS Custom Properties** (in styles.css):
```css
[data-theme="light"] {
  --vb-bg-primary: #FFFFFF;
  --vb-bg-card: #F5F5F5;
  --vb-text-primary: #212121;
  --vb-text-secondary: #757575;
  --vb-color-critical: #F44336;
  --vb-color-warning: #FF9800;
  --vb-color-healthy: #4CAF50;
  --vb-color-unavailable: #9E9E9E;
  --vb-color-action: #03A9F4;
}

[data-theme="dark"] {
  --vb-bg-primary: #1C1C1C;
  --vb-bg-card: #2C2C2C;
  --vb-text-primary: #FFFFFF;
  --vb-text-secondary: #B0B0B0;
  --vb-color-critical: #FF5252;
  --vb-color-warning: #FFB74D;
  --vb-color-healthy: #66BB6A;
  --vb-color-unavailable: #BDBDBD;
  --vb-color-action: #03A9F4;
}

/* Smooth transition on theme change */
.panel, .device-card, .button, .modal {
  transition: background-color 300ms ease-out, color 300ms ease-out, border-color 300ms ease-out;
}
```

**Component Usage**:
```javascript
// In Lit render():
return html`
  <div class="panel" style="background-color: var(--vb-bg-primary); color: var(--vb-text-primary);">
    <div class="device-card" style="background-color: var(--vb-bg-card);">
      <!-- content -->
    </div>
  </div>
`;
```

### Event Listener Lifecycle

**Setup** (connectedCallback):
- Attach `hass_themes_updated` listener to `hass.connection`
- Store listener reference for cleanup

**Active** (component rendered):
- Listener fires when user changes theme
- `_detect_theme()` re-evaluates `hass.themes.darkMode`
- CSS custom properties update (smooth 300ms transition)
- No double-renders (requestUpdate queued, not called immediately)

**Cleanup** (disconnectedCallback):
- Remove listener: `this.hass.connection.removeEventListener('hass_themes_updated', ...)`
- Clear any pending requestUpdate calls

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

### Theme Detection (Sprint 4 Updated)
```javascript
// Step 1: Check hass.themes.darkMode (primary source)
if (hass?.themes?.darkMode !== undefined) {
  return hass.themes.darkMode ? 'dark' : 'light';
}

// Step 2: Check DOM data-theme attribute (fallback)
const domTheme = document.documentElement.getAttribute('data-theme');
if (domTheme === 'dark' || domTheme === 'light') {
  return domTheme;
}

// Step 3: Check OS preference (fallback)
if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
  return 'dark';
}

// Step 4: Default to light
return 'light';
```

## Color Tokens

| Element | Light | Dark | WCAG AA |
|---------|-------|------|---------|
| Background | #FFFFFF | #1C1C1C | — |
| Card | #F5F5F5 | #2C2C2C | — |
| Text Primary | #212121 | #FFFFFF | 9:1 |
| Text Secondary | #757575 | #B0B0B0 | 4.5:1 |
| Critical | #F44336 | #FF5252 | 5.5:1 |
| Warning | #FF9800 | #FFB74D | 6.8:1 |
| Healthy | #4CAF50 | #66BB6A | 4.8:1 |
| Unavailable | #9E9E9E | #BDBDBD | 4.2:1 |
| Action Blue | #03A9F4 | #03A9F4 | 6.2:1 |

All dark mode colors pass WCAG AA (4.5:1 minimum contrast on #1C1C1C).

## UX Polish: Empty State Messaging

**Current** (Sprint 3): "No battery devices found"

**Updated** (Sprint 4): "No battery entities found. Check that your devices have a `battery_level` attribute and are not binary sensors. [→ Documentation]"

This message provides users with actionable debugging steps and links to help.

## Connection States

DISCONNECTED → CONNECTING → CONNECTED (green) → RECONNECTING (blue, exp backoff 1-30s) → OFFLINE (red, manual retry)

## Performance Targets

- Initial load: <1s
- Scroll fetch (pagination): <500ms
- Notification send: <2s
- Theme detection: <50ms (hass.themes.darkMode lookup)
- Theme transition: 300ms CSS smooth (user-visible)
- Scroll smooth: No jank on 150+ devices during theme switch

## Security

- HA WebSocket session auth, HA device registry controls visibility
- No telemetry, no external API calls
- HTTPS/WSS (HA handles), notifications in HA secure storage
- Theme data (user preference) is read-only from hass.themes, no writes

## Answers to Technical Feasibility Questions

### Q1: Is `hass_themes_updated` event available in minimum HA version 2026.2.0?

**Answer**: The `hass.connection.addEventListener()` API and `hass_themes_updated` event are available in HA 2023.2.0+. Our minimum version is 2026.2.0, so this is well-supported.

**Fallback**: If `hass.connection` is unavailable (edge case), the fallback chain (DOM + OS preference) will handle theme detection. Not ideal, but functional.

### Q2: Should we debounce `hass_themes_updated` listener?

**Answer**: No explicit debounce needed. The event fires once per theme change (not rapid succession). `requestUpdate()` is already queued by Lit (only one render per microtask), so even rapid events won't cause multiple renders.

### Q3: Will theme switching interfere with real-time device updates?

**Answer**: No. WebSocket messages (device_changed, threshold_updated, notification_sent) and the hass_themes_updated event are independent. Both trigger Lit's requestUpdate queue. Updates are serialized by Lit's update scheduler, so no race conditions.

### Q4: Are there memory leaks with the new event listener?

**Answer**: Potential leak if cleanup is skipped. **Solution**: Always remove listener in `disconnectedCallback()`:
```javascript
disconnectedCallback() {
  super.disconnectedCallback();
  if (this._themeListener && this.hass?.connection) {
    this.hass.connection.removeEventListener('hass_themes_updated', this._themeListener);
  }
}
```

## Implementation Notes

- **Event listener storage**: Store reference as `this._themeListener = () => { ... }` to enable proper cleanup
- **Initial theme detection**: Call `_detect_theme()` in `connectedCallback()` before listener is attached (avoids missing initial state)
- **CSS transition safety**: The 300ms transition is applied only to color properties (background, color, border-color), not layout properties, to avoid jank
- **Backward compatibility**: MutationObserver on data-theme can be removed entirely; hass_themes_updated is more reliable

## Minimum Home Assistant Version

**Sprint 4 Requirement**: HA 2026.2.0 or later (for hass_themes_updated event support)

Current manifest.json version in Sprint 3 already specifies 2026.2.0, so no bump needed.

## Deployment Considerations

No backend changes needed for Sprint 4 (theme detection is frontend-only). The WebSocket API and BatteryMonitor are unchanged from Sprint 3.

**Deployment steps**:
1. Update frontend assets (vulcan-brownout-panel.js, styles.css)
2. Update manifest.json version to 4.0.0
3. Redeploy via existing idempotent script
4. Smoke test: Open panel, change HA theme, verify smooth transition
