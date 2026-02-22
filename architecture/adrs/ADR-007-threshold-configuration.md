# ADR-007: Threshold Configuration Storage & UI Flow

**Status**: Proposed
**Sprint**: 2
**Author**: FiremanDecko (Architect)
**Date**: February 2026

---

## Context

Sprint 1 used a hardcoded 15% threshold for all devices. Users requested the ability to set custom thresholds:
- Global threshold override (e.g., "warn when ANY battery drops below 25%")
- Per-device thresholds (e.g., "Solar Backup warns at 50%, sensors warn at 15%")

This requires a configuration system that stores thresholds persistently and applies them during filtering.

### Current State (Sprint 1)
- Hardcoded `BATTERY_THRESHOLD = 15` in `const.py`
- All devices use this threshold
- No UI for configuration

### Desired State (Sprint 2)
- User opens settings panel
- Sets global threshold (5-100%, default 15%)
- Optionally adds per-device rules (up to 10 visible in UI)
- Settings persist in HA's config entry
- Thresholds applied immediately to battery list colors
- Live preview: "X batteries will be CRITICAL with this threshold"

---

## Options Considered

### Option 1: Config Entry Options Flow (Recommended)
Store thresholds in HA's `ConfigEntry.options` dictionary. Use HA's standard options flow UI.

**Pros:**
- Native to Home Assistant patterns
- Persisted automatically by HA framework
- Settings survive HA restarts
- Can be changed without restarting
- YAML-compatible for advanced users

**Cons:**
- Options UI must be custom (no built-in threshold UI widget)
- Requires frontend component for settings panel
- More HA framework integration needed

**Implementation:**
```python
# In config_flow.py
class OptionsFlow(config_entries.OptionsFlow):
    async def async_step_init(self, user_input=None):
        """Settings panel step."""
        # Load current options
        global_threshold = self.config_entry.options.get('global_threshold', 15)
        device_rules = self.config_entry.options.get('device_rules', {})

        # If user submitted form:
        # Validate inputs
        # Update self.config_entry.options
        # Broadcast update to all clients
```

### Option 2: JSON File in Config Directory
Store thresholds in `config/custom_components/vulcan_brownout/thresholds.json`

**Pros:**
- Simple file-based storage
- Easy to backup/restore
- Human-readable format

**Cons:**
- Not discoverable by HA framework
- Harder to sync if HA has multiple instances
- Requires manual file management
- Won't survive HACS reinstalls

**Decision**: Rejected. Not HA-native.

### Option 3: Persistent Database (SQLite)
Create a SQLite database to store thresholds.

**Pros:**
- Scales well with many rules
- Supports queries/filtering

**Cons:**
- Overkill for MVP (Sprint 2)
- Adds complexity
- Licensing considerations
- Heavier footprint

**Decision**: Deferred to Sprint 3+. Too complex for initial release.

---

## Decision

**Implement Option 1: HA ConfigEntry Options Flow**

Thresholds will be stored in `hass.config_entries[config_entry_id].options` as:

```python
{
    'global_threshold': 15,  # int: 5-100
    'device_rules': {
        'sensor.solar_backup_battery': 50,
        'sensor.front_door_lock_battery': 30,
        # ...
    },
    'filter_state': 'all',  # For Sprint 2: filter state persistence
    'sort_method': 'priority',  # For Sprint 2: sort persistence
}
```

This is:
- **Persistent**: Saved by HA framework
- **Synced**: Works with HA backups
- **Accessible**: Available to other integrations via config entry
- **Versioned**: HA handles schema changes
- **User-Friendly**: HA UI components handle form presentation

---

## Consequences

### Positive
1. **HA Native**: Follows established patterns; users familiar with HA understand it
2. **Persistent**: Survives HA restart, updates, HACS reinstalls
3. **UI Built-In**: HA provides form framework; we just define schema
4. **Validation**: HA's voluptuous schema validates inputs
5. **Scalable**: Supports future enhancements (notifications, scheduling, etc.)
6. **Audit Trail**: Changes visible in HA's config entry history

### Negative
1. **More Code**: Config flow boilerplate required
2. **Requires Restart? (No, Options)**: Options can be changed without restart ✓
3. **Not User-Facing by Default**: Settings hidden in HA UI; our custom panel is primary access point

### Mitigations
- Provide clear UI in Vulcan Brownout sidebar panel
- Document settings in README
- Pre-populate defaults so users have working config immediately
- Validate thresholds client-side with live preview

---

## Storage Schema

### Config Entry Options (HA Native)

**Location**: `hass.config_entries[entry_id].options`

**Schema** (validated with voluptuous):
```python
THRESHOLD_CONFIG_SCHEMA = vol.Schema({
    vol.Optional('global_threshold', default=15): vol.All(
        vol.Coerce(int),
        vol.Range(min=5, max=100)
    ),
    vol.Optional('device_rules', default={}): vol.Schema({
        str: vol.All(vol.Coerce(int), vol.Range(min=5, max=100))
    }),
    vol.Optional('filter_state', default='all'): str,
    vol.Optional('sort_method', default='priority'): str,
})
```

**Example Contents**:
```json
{
  "global_threshold": 20,
  "device_rules": {
    "sensor.solar_backup_battery": 50,
    "sensor.front_door_lock_battery": 30,
    "sensor.bedroom_sensor_battery": 15
  },
  "filter_state": "all",
  "sort_method": "priority"
}
```

### Runtime Cache (BatteryMonitor)

When backend loads config entry, it caches thresholds in memory for fast lookup:

```python
class BatteryMonitor:
    def __init__(self, hass, config_entry):
        self.global_threshold = config_entry.options.get('global_threshold', 15)
        self.device_rules = config_entry.options.get('device_rules', {})

    def get_threshold_for_device(self, entity_id):
        """Get effective threshold for a device."""
        # Check device-specific rule first
        if entity_id in self.device_rules:
            return self.device_rules[entity_id]
        # Fall back to global threshold
        return self.global_threshold

    def on_options_updated(self, new_options):
        """Called when user changes settings."""
        self.global_threshold = new_options.get('global_threshold', 15)
        self.device_rules = new_options.get('device_rules', {})
        # Notify all connected clients of change
        self._broadcast_threshold_update()
```

---

## Implementation Details

### Backend (Python)

**File: `config_flow.py` (NEW)**

```python
import voluptuous as vol
from homeassistant.config_entries import OptionsFlow

class VulcanBrownoutOptionsFlow(OptionsFlow):
    """Options flow for Vulcan Brownout settings."""

    async def async_step_init(self, user_input=None):
        """Initial step: gather threshold settings."""
        if user_input is not None:
            return self.async_create_entry(
                title="Vulcan Brownout Settings",
                data=user_input
            )

        # Get current settings
        current = self.config_entry.options
        global_threshold = current.get('global_threshold', 15)
        device_rules = current.get('device_rules', {})

        # TODO: Render form with:
        # - Global threshold slider (5-100, default 15)
        # - Device rules list (show up to 5)
        # - "+ Add Device Rule" button
        # - "Save" and "Cancel" buttons

        return self.async_show_form(...)
```

**File: `__init__.py` (UPDATED)**

```python
async def async_setup_entry(hass, entry):
    """Set up integration from config entry."""
    # ... existing code ...

    # Load threshold configuration
    options = entry.options
    global_threshold = options.get('global_threshold', 15)
    device_rules = options.get('device_rules', {})

    # Pass to BatteryMonitor
    battery_monitor = BatteryMonitor(hass, threshold=global_threshold, device_rules=device_rules)

    # Listen for options updates
    entry.add_update_listener(update_listener)

async def update_listener(hass, config_entry):
    """Called when user changes settings."""
    battery_monitor = hass.data[DOMAIN]
    battery_monitor.on_options_updated(config_entry.options)
    # Re-filter battery list with new thresholds
    # Broadcast update to all WebSocket clients
```

**File: `battery_monitor.py` (UPDATED)**

```python
class BatteryMonitor:
    def __init__(self, hass, config_entry):
        self.hass = hass
        self.config_entry = config_entry
        self.global_threshold = config_entry.options.get('global_threshold', 15)
        self.device_rules = config_entry.options.get('device_rules', {})
        self.entities = {}

    def get_threshold_for_device(self, entity_id: str) -> int:
        """Get effective threshold for a device."""
        if entity_id in self.device_rules:
            return self.device_rules[entity_id]
        return self.global_threshold

    def get_status_for_device(self, device):
        """Determine status (critical, warning, healthy) for a device."""
        if not device.available:
            return 'unavailable'

        threshold = self.get_threshold_for_device(device.entity_id)
        if device.battery_level <= threshold:
            return 'critical'
        elif device.battery_level <= (threshold + 10):  # Warning range
            return 'warning'
        else:
            return 'healthy'

    def on_options_updated(self, new_options):
        """Called when user changes thresholds in settings."""
        self.global_threshold = new_options.get('global_threshold', 15)
        self.device_rules = new_options.get('device_rules', {})
        _LOGGER.info(f"Threshold config updated: global={self.global_threshold}, rules={len(self.device_rules)}")
```

**File: `websocket_api.py` (UPDATED)**

```python
async def handle_set_threshold(hass, connection, msg):
    """Handle vulcan-brownout/set_threshold WebSocket command."""
    try:
        data = msg.get('data', {})
        global_threshold = data.get('global_threshold')
        device_rules = data.get('device_rules', {})

        # Validate
        if global_threshold is not None:
            if not (5 <= global_threshold <= 100):
                raise ValueError("Global threshold must be 5-100")

        # Update config entry
        config_entry = hass.config_entries.async_entries(DOMAIN)[0]
        hass.config_entries.async_update_entry(
            config_entry,
            options={
                'global_threshold': global_threshold or 15,
                'device_rules': device_rules,
                # Preserve other options
                **config_entry.options,
            }
        )

        # Respond
        connection.send_json_message({
            'type': 'result',
            'id': msg['id'],
            'success': True,
            'data': {'message': 'Thresholds updated'}
        })

    except Exception as e:
        _LOGGER.error(f"Error setting threshold: {e}")
        connection.send_error(msg['id'], 'invalid_request', str(e))
```

### Frontend (JavaScript)

**New Component: `VulcanBrownoutSettings` (part of panel)**

```javascript
class SettingsPanel extends LitElement {
  @state() globalThreshold = 15;
  @state() deviceRules = {};
  @state() isLoading = false;
  @state() error = null;

  async _on_save() {
    this.isLoading = true;
    try {
      const result = await this._call_websocket({
        type: 'vulcan-brownout/set_threshold',
        data: {
          global_threshold: this.globalThreshold,
          device_rules: this.deviceRules,
        }
      });

      if (!result.success) throw new Error(result.error?.message);

      // Notify parent to update device list with new colors
      this.dispatchEvent(new CustomEvent('settings-updated'));

      // Close panel
      this.dispatchEvent(new CustomEvent('close'));
    } catch (e) {
      this.error = e.message;
    } finally {
      this.isLoading = false;
    }
  }

  _get_affected_device_count(threshold) {
    // Live preview: count how many devices would be CRITICAL at this threshold
    return this.parent.battery_devices.filter(
      d => d.battery_level <= threshold
    ).length;
  }

  render() {
    return html`
      <div class="settings-panel">
        <h2>Battery Monitoring Settings</h2>

        <h3>Global Threshold</h3>
        <div class="threshold-control">
          <input
            type="range"
            min="5"
            max="100"
            .value=${this.globalThreshold}
            @change=${(e) => this.globalThreshold = parseInt(e.target.value)}
          />
          <input
            type="number"
            min="5"
            max="100"
            .value=${this.globalThreshold}
            @change=${(e) => this.globalThreshold = parseInt(e.target.value)}
          />
          <p>${this._get_affected_device_count(this.globalThreshold)} devices below threshold</p>
        </div>

        <h3>Device-Specific Rules</h3>
        <button @click=${() => this._add_device_rule()}>+ Add Device Rule</button>

        <!-- Device rules list -->
        ${Object.entries(this.deviceRules).map(([entityId, threshold]) => html`
          <div class="device-rule">
            <span>${this._get_device_name(entityId)}</span>
            <input type="number" min="5" max="100" .value=${threshold} />
            <button @click=${() => this._remove_device_rule(entityId)}>✕</button>
          </div>
        `)}

        <div class="buttons">
          <button @click=${() => this._on_save()}>Save</button>
          <button @click=${() => this._on_cancel()}>Cancel</button>
        </div>
      </div>
    `;
  }
}
```

---

## WebSocket Messages

### New Command: Set Threshold

**Request:**
```json
{
  "type": "vulcan-brownout/set_threshold",
  "id": "msg_001",
  "data": {
    "global_threshold": 20,
    "device_rules": {
      "sensor.solar_backup_battery": 50,
      "sensor.front_door_lock_battery": 30
    }
  }
}
```

**Response:**
```json
{
  "type": "result",
  "id": "msg_001",
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

### Broadcast Event: Threshold Updated

**Sent to All Connected Clients:**
```json
{
  "type": "vulcan-brownout/threshold_updated",
  "data": {
    "global_threshold": 20,
    "device_rules": {
      "sensor.solar_backup_battery": 50,
      "sensor.front_door_lock_battery": 30
    }
  }
}
```

---

## Data Flow

### User Changes Threshold

```
User opens settings → Sees global threshold slider (15%)
                   ↓
User moves slider to 25%
                   ↓
Frontend shows live preview: "8 devices below this threshold"
                   ↓
User clicks "Save"
                   ↓
Frontend sends: vulcan-brownout/set_threshold { global_threshold: 25, ... }
                   ↓
Backend validates input
                   ↓
Backend updates config_entry.options
                   ↓
update_listener() fires
                   ↓
Backend calls battery_monitor.on_options_updated()
                   ↓
BatteryMonitor broadcasts vulcan-brownout/threshold_updated to all clients
                   ↓
Frontend receives broadcast
                   ↓
Frontend re-calculates status for all devices
                   ↓
Frontend re-renders list with new colors
                   ↓
(8 devices that were HEALTHY now show as CRITICAL)
```

---

## Testing Strategy

### Unit Tests
- `test_threshold_validation.py`: Valid/invalid thresholds
- `test_device_status.py`: Status calculation with thresholds
- `test_options_flow.py`: Form submission, validation
- `test_websocket_threshold.js`: Frontend threshold updates

### Integration Tests
- Change global threshold, verify all devices re-color
- Add device-specific rule, verify override works
- Remove device rule, verify fallback to global
- Persist and reload settings across HA restart

### E2E Tests
- Open settings panel, adjust threshold
- Verify preview count updates in real-time
- Save and verify battery list re-colors
- Reload page, verify settings persist

---

## Migration from Sprint 1

For existing users:
- If no options set, default to `global_threshold: 15` (same as Sprint 1)
- First settings save creates options entry automatically
- No breaking changes

---

## Future Enhancements (Sprint 3+)

1. Per-device-class thresholds (e.g., "locks warn at 20%, sensors at 15%")
2. Threshold schedules (e.g., "stricter thresholds on weekdays")
3. Threshold templates (e.g., "Smart Lock Standard", "Sensor Standard")
4. Export/import threshold configs
5. Threshold history/audit log

---

## Success Criteria

1. Users can set global threshold (5-100%)
2. Users can add up to 10 device-specific rules
3. Settings persist across HA restart
4. Live preview shows affected device count
5. Threshold changes apply immediately (within 100ms)
6. Settings UI is accessible and intuitive
7. Validation prevents invalid inputs

---

## Related Documents

- `system-design.md` — Updated component diagram
- `api-contracts.md` — New WebSocket messages
- `ADR-006` — WebSocket subscriptions (depends on this)
- `interactions.md` — Settings UI flows

---

**Approved by**: [Architect]
**Implementation Lead**: [Lead Developer]
**Code Review**: [Code Review Lead]
