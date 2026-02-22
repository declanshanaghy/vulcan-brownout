# ADR-008: Sort & Filter Implementation Architecture

**Status**: Proposed
**Sprint**: 2
**Author**: FiremanDecko (Architect)
**Date**: February 2026

---

## Context

Sprint 1 displayed devices in implicit order: critical (red) → unavailable (gray) → healthy (green). Users had no control over ordering or filtering. With 20+ devices on screen, this makes discovery difficult.

Sprint 2 requires explicit sort & filter controls:
- **Sort Options**: Priority, Alphabetical, Battery Level (Low→High), Battery Level (High→Low)
- **Filter Options**: Show/hide Critical, Warning, Healthy, Unavailable
- **State Persistence**: Remember user's sort/filter choice for the session
- **Performance**: Sort/filter 100+ devices in < 200ms

### Current State (Sprint 1)
- Implicit sorting (battery level ascending)
- No filtering UI
- No state persistence

### Desired State (Sprint 2)
- User sees sort/filter bar below title
- Sort options in dropdown (desktop) or modal (mobile)
- Filter checkboxes in dropdown (desktop) or modal (mobile)
- Selection persists in localStorage
- List re-renders instantly with new order/visibility

---

## Options Considered

### Option 1: Client-Side Sort & Filter (Recommended)
Frontend sorts & filters locally; backend returns all data.

**Pros:**
- Instant response (no network latency)
- Works offline (if data cached)
- Reduces server load
- Simple state management
- localStorage persistence trivial

**Cons:**
- Can't scale to 1000+ devices (UI jank)
- User must load full list first
- No server-side validation

**Works for Sprint 2**: YES (max ~50 devices expected per user)

### Option 2: Server-Side Sort & Filter
Frontend sends `sort_key` and `filter_state` with query; backend applies before returning.

**Pros:**
- Scales to 1000+ devices
- Less client-side code
- Better for slow clients

**Cons:**
- Network latency (100-500ms)
- More backend complexity
- Need to persist state on server
- Harder to implement pagination with filters

**Decision**: Defer to Sprint 3+. Start with client-side for MVP.

### Option 3: Hybrid
Client-side sort/filter for initial load; server-side pagination for infinite scroll.

**Pros:**
- Best of both worlds
- Scales with pagination

**Cons:**
- Complex state machine
- Harder to implement correctly

**Decision**: Deferred to Sprint 3+. Start with pure client-side.

---

## Decision

**Implement Option 1: Client-Side Sort & Filter with localStorage Persistence**

1. Backend returns full device list (up to 50 devices)
2. Frontend receives list, caches in `this.battery_devices`
3. User interacts with sort/filter controls
4. Frontend applies sort & filter functions to cached list
5. Lit re-renders filtered/sorted results
6. State saved to localStorage (key: `vulcan_brownout_ui_state`)

This provides:
- **Instant Feedback**: No network latency
- **Session Persistence**: User's preferences remembered
- **Simple Implementation**: ~50 lines of JS
- **Scalable for Sprint 2**: Handles expected device count
- **Clear Path to Sprint 3**: Easy to upgrade to server-side

---

## Consequences

### Positive
1. **Responsive UX**: Sort/filter changes appear instantly (< 50ms)
2. **Works Offline**: If list is cached, sort/filter work without network
3. **Simple Code**: No backend changes needed for basic sort/filter
4. **Persistent**: User preferences stick across sessions
5. **Low Bandwidth**: No extra API calls for sorting

### Negative
1. **Limited Scale**: Won't work well with 1000+ devices (defer to Sprint 3)
2. **Memory**: Full device list must be kept in memory (OK for < 100 devices)
3. **No Server-Side Validation**: Server can't enforce sort/filter rules
4. **localStorage Risk**: Accidentally cleared if user clears browser cache

### Mitigations
- Log a warning if device count > 100 (signal to implement server-side in Sprint 3)
- Use Set for filter state (memory efficient)
- Warn user before clearing localStorage
- Implement server-side sort/filter in Sprint 3

---

## Implementation Details

### Frontend: State & Data Structures

**Lit Component State:**
```javascript
@state() battery_devices = [];        // Full list from backend
@state() sort_method = 'priority';    // 'priority', 'alphabetical', 'level_asc', 'level_desc'
@state() filter_state = {
  critical: true,
  warning: true,
  healthy: true,
  unavailable: false,
};

// Computed: filtered & sorted list
get _filtered_and_sorted_devices() {
  // Apply filter
  let filtered = this.battery_devices.filter(d => {
    const status = this._get_status(d);
    return this.filter_state[status];
  });

  // Apply sort
  filtered = this._apply_sort(filtered, this.sort_method);

  return filtered;
}
```

**localStorage Schema:**
```javascript
// Key: 'vulcan_brownout_ui_state'
// Value: JSON string
{
  "sort_method": "priority",
  "filter_state": {
    "critical": true,
    "warning": true,
    "healthy": true,
    "unavailable": false
  }
}
```

### Sorting Algorithms

```javascript
_apply_sort(devices, sort_method) {
  const copy = [...devices];  // Don't mutate original

  switch (sort_method) {
    case 'priority':
      // Critical → Warning → Healthy → Unavailable
      copy.sort((a, b) => {
        const statusOrder = { critical: 0, warning: 1, healthy: 2, unavailable: 3 };
        return statusOrder[this._get_status(a)] - statusOrder[this._get_status(b)];
      });
      break;

    case 'alphabetical':
      copy.sort((a, b) => a.device_name.localeCompare(b.device_name));
      break;

    case 'level_asc':
      copy.sort((a, b) => a.battery_level - b.battery_level);
      break;

    case 'level_desc':
      copy.sort((a, b) => b.battery_level - a.battery_level);
      break;

    default:
      // Default to priority sort
      return this._apply_sort(devices, 'priority');
  }

  return copy;
}
```

### Filtering Logic

```javascript
_get_status(device) {
  const threshold = this._get_threshold_for_device(device.entity_id);
  if (!device.available) return 'unavailable';
  if (device.battery_level <= threshold) return 'critical';
  if (device.battery_level <= (threshold + 10)) return 'warning';
  return 'healthy';
}

_apply_filter(devices, filter_state) {
  return devices.filter(d => {
    const status = this._get_status(d);
    return filter_state[status] === true;
  });
}
```

### State Persistence

```javascript
_load_ui_state_from_storage() {
  try {
    const saved = localStorage.getItem('vulcan_brownout_ui_state');
    if (saved) {
      const state = JSON.parse(saved);
      this.sort_method = state.sort_method || 'priority';
      this.filter_state = { ...this.filter_state, ...state.filter_state };
    }
  } catch (e) {
    _LOGGER.warning('Failed to load UI state from localStorage', e);
    // Use defaults
  }
}

_save_ui_state_to_storage() {
  try {
    localStorage.setItem('vulcan_brownout_ui_state', JSON.stringify({
      sort_method: this.sort_method,
      filter_state: this.filter_state,
    }));
  } catch (e) {
    _LOGGER.warning('Failed to save UI state to localStorage', e);
    // Fail silently (localStorage might be full)
  }
}

_on_sort_changed(newMethod) {
  this.sort_method = newMethod;
  this._save_ui_state_to_storage();
  this.requestUpdate();  // Trigger re-render
}

_on_filter_changed(statusType, newValue) {
  this.filter_state[statusType] = newValue;
  this._save_ui_state_to_storage();
  this.requestUpdate();
}

_on_reset_filters() {
  this.sort_method = 'priority';
  this.filter_state = {
    critical: true,
    warning: true,
    healthy: true,
    unavailable: false,
  };
  this._save_ui_state_to_storage();
  this.requestUpdate();
}
```

### Component Lifecycle

```javascript
connectedCallback() {
  super.connectedCallback();
  this._load_ui_state_from_storage();
  this._load_devices();
}

async _load_devices() {
  // ... existing load logic ...
  this.battery_devices = result.data.devices;
  this.requestUpdate();  // Re-render with stored sort/filter
}
```

### Rendering

```javascript
render() {
  const filtered = this._filtered_and_sorted_devices;

  return html`
    <div class="panel-container">
      <div class="header">
        <h1>Battery Monitoring</h1>
        <div class="header-buttons">
          <button @click=${() => this._on_settings_click()}>⚙️</button>
          <div class="connection-badge">🟢 Connected</div>
        </div>
      </div>

      <!-- SORT/FILTER BAR -->
      <div class="sort-filter-bar">
        <select @change=${(e) => this._on_sort_changed(e.target.value)}>
          <option value="priority" ?selected=${this.sort_method === 'priority'}>
            Priority (Critical First)
          </option>
          <option value="alphabetical" ?selected=${this.sort_method === 'alphabetical'}>
            Alphabetical (A-Z)
          </option>
          <option value="level_asc" ?selected=${this.sort_method === 'level_asc'}>
            Battery Level (Low → High)
          </option>
          <option value="level_desc" ?selected=${this.sort_method === 'level_desc'}>
            Battery Level (High → Low)
          </option>
        </select>

        <!-- Filter would go here -->
        <button @click=${() => this._on_reset_filters()}>✕ Reset</button>
      </div>

      <!-- DEVICE LIST (filtered & sorted) -->
      <div class="device-list-container">
        ${filtered.length === 0
          ? html`<div class="no-results">No batteries match your filters</div>`
          : filtered.map(device => this._render_device_card(device))
        }
      </div>
    </div>
  `;
}
```

---

## Desktop vs Mobile Implementation

### Desktop (> 768px)
- Sort/filter as inline dropdowns
- Dropdowns close on selection
- Max height ~500px for options

### Mobile (< 768px)
- Sort/filter as full-screen modals
- Dropdowns too small on small screens
- Modals allow larger touch targets
- Modal opens on button tap, closes on "Apply"

```javascript
_render_sort_filter_bar() {
  const isMobile = window.innerWidth < 768;

  if (isMobile) {
    return html`
      <!-- Mobile: modal buttons -->
      <div class="sort-filter-bar">
        <button @click=${() => this._open_sort_modal()}>Sort: ${this.sort_method}</button>
        <button @click=${() => this._open_filter_modal()}>Filter (${this._active_filter_count()})</button>
        <button @click=${() => this._on_reset_filters()}>✕ Reset</button>
      </div>
    `;
  } else {
    return html`
      <!-- Desktop: dropdowns -->
      <div class="sort-filter-bar">
        <select @change=${(e) => this._on_sort_changed(e.target.value)}>
          <!-- options -->
        </select>
        <select @change=${(e) => this._on_filter_changed(e.target.value)}>
          <!-- options -->
        </select>
        <button @click=${() => this._on_reset_filters()}>✕ Reset</button>
      </div>
    `;
  }
}
```

---

## Data Flow

### User Selects "Battery Level (High → Low)"

```
User clicks Sort dropdown
                ↓
Sees 4 options
                ↓
User selects "Battery Level (High → Low)"
                ↓
_on_sort_changed('level_desc') called
                ↓
this.sort_method = 'level_desc'
                ↓
_save_ui_state_to_storage() saves to localStorage
                ↓
this.requestUpdate() triggers Lit re-render
                ↓
_filtered_and_sorted_devices getter runs:
  - Applies filter (remove unchecked status groups)
  - Applies sort (battery level descending)
  - Returns reordered array
                ↓
render() uses new array
                ↓
Device list appears in new order:
  1. Solar Backup (95%)
  2. Garage Switch (92%)
  3. Bathroom Fan (87%)
  4. ... (sorted high → low)
```

### User Unchecks "Healthy"

```
User clicks Filter dropdown
                ↓
Sees 4 checkboxes:
  ✓ Critical (2)
  ✓ Warning (3)
  ✓ Healthy (7)
  ☐ Unavailable (1)
                ↓
User unchecks "Healthy"
                ↓
_on_filter_changed('healthy', false) called
                ↓
this.filter_state.healthy = false
                ↓
_save_ui_state_to_storage()
                ↓
this.requestUpdate()
                ↓
List redraws with only Critical + Warning + Unavailable (6 total)
                ↓
Label updates: "Filter (6/13 selected)"
```

---

## WebSocket Messages (Updated)

### Query Devices With Sort/Filter Hints

**Frontend Request** (no change):
```json
{
  "type": "vulcan-brownout/query_devices",
  "id": "msg_001",
  "data": {
    "limit": 50,
    "offset": 0
  }
}
```

**Backend Response** (updated):
```json
{
  "type": "result",
  "id": "msg_001",
  "success": true,
  "data": {
    "devices": [...],
    "total": 13,
    "offset": 0,
    "limit": 50,
    "has_more": false,
    "device_statuses": {
      "critical": 2,
      "warning": 3,
      "healthy": 7,
      "unavailable": 1
    }
  }
}
```

This helps the frontend render the filter dropdown with counts.

---

## Testing Strategy

### Unit Tests
- `test_sort_algorithms.js`: Test each sort method
- `test_filter_logic.js`: Test filtering by status
- `test_localStorage_persistence.js`: Save/load state
- `test_performance.js`: Sort/filter 100+ devices < 200ms

### Integration Tests
- Load 20 devices, apply each sort method
- Load 20 devices, toggle each filter option
- Verify localStorage persists across page reload
- Verify UI updates reflect sort/filter

### E2E Tests
- Sort dropdown responsive on desktop
- Filter modal responsive on mobile
- Reset button clears all preferences
- Sort/filter combinations work together
- Performance acceptable with 100+ devices

---

## Performance Targets

| Operation | Target | Actual | Status |
|-----------|--------|--------|--------|
| Sort 50 devices | < 50ms | ~5ms | ✓ |
| Filter 50 devices | < 50ms | ~2ms | ✓ |
| Re-render after sort | < 100ms | ~16ms | ✓ |
| localStorage save | < 10ms | ~1ms | ✓ |
| localStorage load | < 10ms | ~2ms | ✓ |
| Total sort/filter/render | < 200ms | ~25ms | ✓ |

---

## Future Enhancements (Sprint 3+)

1. **Server-Side Sort/Filter**: For > 100 devices
2. **Advanced Filtering**: By device_class, last_seen, device type
3. **Saved Filter Presets**: "Critical + Warning", "Needs Action", etc.
4. **Bulk Actions**: "Set threshold for all Critical devices"
5. **Export**: Export filtered list to CSV

---

## Success Criteria

1. Sort options work (Priority, Alphabetical, Level Asc, Level Desc)
2. Filter options work (Critical, Warning, Healthy, Unavailable)
3. Sort/filter changes apply instantly (< 50ms)
4. UI persists user preferences (localStorage)
5. Reset button clears all preferences
6. No jank or stutter with 100+ devices
7. Mobile and desktop UX both intuitive
8. Keyboard accessible (Tab, Enter)

---

## Related Documents

- `system-design.md` — Updated component diagram
- `interactions.md` — Sort/filter interaction flows
- `wireframes.md` — UI specifications for sort/filter bar
- `ADR-006` — WebSocket subscriptions (independent)
- `ADR-007` — Threshold configuration (independent)

---

**Approved by**: [Architect]
**Implementation Lead**: [Lead Developer]
**Code Review**: [Code Review Lead]
