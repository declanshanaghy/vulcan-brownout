# System Design — Sprint 5

**Updated**: 2026-02-22 | **Status**: Sprint 5 architecture complete

## Architecture Overview

```
HA Core: State Machine + Event Bus + persistent_notification service + hass.themes API
    ↓ state_changed events
    ↓ hass_themes_updated event (SPRINT 4)
Vulcan Brownout Integration:
    __init__.py        → Setup, register panel/commands, create managers
    config_flow.py     → Settings UI, ConfigEntry.options storage
    BatteryMonitor     → Entity discovery, filtering, cursor pagination, SPRINT 5: server-side filter logic
    SubMgr             → WebSocket subscription broadcasting
    NotificationMgr    → Threshold monitoring, frequency caps, HA notification service
    websocket_api.py   → WS command handlers (query_devices w/ filters, subscribe, set_threshold,
                         get/set_notification_preferences, SPRINT 5: get_filter_options)
    ↓ WebSocket
Frontend (Lit Element):
    vulcan-brownout-panel.js → Main panel with infinite scroll, skeleton loaders, back-to-top,
                               hass_themes_updated listener (SPRINT 4),
                               SPRINT 5: filter bar, filter dropdowns, chip row, mobile bottom sheet,
                               get_filter_options call, localStorage filter persistence
    styles.css               → CSS custom properties for dark/light theme (hass.themes.darkMode-driven),
                               SPRINT 5: filter UI tokens (--vb-bg-secondary, --vb-filter-chip-*, etc.)
```

## Inherited Features (Sprint 1-4)

1. **Cursor pagination**: base64(last_changed|entity_id), 50 items/page, max 100
2. **Entity filtering**: Exclude binary_sensor domain + require numeric battery_level 0-100
3. **Notifications**: HA persistent_notification, frequency caps (1/2/6/12/24h), severity filter (all|critical_only|critical_and_warning), per-device enable
4. **Threshold config**: Global threshold + per-device device_rules, stored in ConfigEntry.options
5. **Real-time updates**: WebSocket device_changed, threshold_updated, notification_sent events
6. **Connection states**: DISCONNECTED → CONNECTING → CONNECTED → RECONNECTING → OFFLINE
7. **Deployment**: Idempotent bash+rsync, symlink releases, health check endpoint, .env validation
8. **Theme detection**: hass.themes.darkMode as primary, DOM data-theme + prefers-color-scheme fallback, hass_themes_updated event listener, 300ms CSS transition

## Sprint 5 New Features: Server-Side Filtering Architecture

### Filtering Problem Statement

With cursor-based pagination, the server returns one page (up to 100 items) of the full result set. Any filter applied client-side operates only on that one page. If 200 devices exist and filters match only 2, client-side filtering on page 1 (50 items) might find 1 match and hide the second match on page 2. This is a silent data integrity failure.

The only architecturally correct solution for paginated datasets is to filter server-side before pagination, so the paginated slice reflects the filtered total. See ADR-015 for full decision record.

### Sprint 5 Filtering Data Flow

```
User selects filter value (e.g., "Room: Living Room")
    ↓
Panel JS updates active_filters state
    ↓
Panel JS saves to localStorage (vulcan_brownout_filters)
    ↓
Panel JS resets current_cursor to null
    ↓
Panel JS calls query_devices({ filter_area: ["Living Room"], cursor: null })
    ↓ WebSocket
BatteryMonitor.query_devices() receives filter params
    ↓
BatteryMonitor._apply_filters(all_entities, filters)
    → filters by manufacturer (AND)
    → filters by device_class (AND)
    → filters by status (AND)
    → filters by area name (AND)
    [OR logic within each category]
    ↓
BatteryMonitor applies sort to filtered result
    ↓
BatteryMonitor applies cursor pagination to sorted+filtered result
    ↓
Returns { devices, total (filtered), has_more, next_cursor }
    ↓ WebSocket
Panel JS replaces device list, updates total count display, shows filter chips
```

### Filter Options Discovery Flow

```
Panel connectedCallback() fires
    ↓
Panel calls get_filter_options WebSocket command
    ↓ WebSocket
handle_get_filter_options():
    → Reads entity_registry: entity.area_id per battery entity
    → Reads device_registry: device.manufacturer per battery entity's device_id
    → Reads area_registry: area names for entity/device area_ids
    → Computes device_class list from entity attributes
    → statuses = fixed list ["critical","warning","healthy","unavailable"]
    ↓
Returns { manufacturers[], device_classes[], areas[{id,name}], statuses[] }
    ↓ WebSocket
Panel JS caches in this._filter_options (in-memory, session only)
Panel JS enables filter dropdowns and populates checkbox lists
Panel JS proceeds with first query_devices (with restored localStorage filters)
```

### BatteryMonitor Changes (Sprint 5)

#### New Constants Required
```python
# Filter keys
FILTER_KEY_MANUFACTURER = "filter_manufacturer"
FILTER_KEY_DEVICE_CLASS = "filter_device_class"
FILTER_KEY_STATUS = "filter_status"
FILTER_KEY_AREA = "filter_area"

# Commands
COMMAND_GET_FILTER_OPTIONS = "vulcan-brownout/get_filter_options"

# Limits
MAX_FILTER_OPTIONS = 20   # max values per filter category in get_filter_options response
```

#### New Methods on BatteryMonitor

**`_apply_filters(devices, filters) -> list`**
Applies AND-across-categories, OR-within-category filter logic. Input is a list of `(BatteryEntity, status_str)` tuples (post-status-calculation). Returns the same format, filtered.

```python
def _apply_filters(self, devices, filters):
    """Filter devices by manufacturer, device_class, status, area.

    AND logic across categories: all non-empty filter lists must match.
    OR logic within category: any value in the list matches.

    Args:
        devices: List of (BatteryEntity, status_str) tuples
        filters: Dict with optional keys:
            filter_manufacturer: list[str]
            filter_device_class: list[str]
            filter_status: list[str]
            filter_area: list[str]
    Returns:
        Filtered list of (BatteryEntity, status_str) tuples
    """
```

**`_get_entity_manufacturer(entity_id) -> Optional[str]`**
Looks up manufacturer from device_registry via entity's device_id. Returns None if entity has no device or device has no manufacturer.

**`_get_entity_area_name(entity_id) -> Optional[str]`**
Looks up area name from area_registry. Priority: entity's own area_id → device's area_id → None.

**`async get_filter_options() -> Dict`**
Iterates `self.entities`, reads device_registry and area_registry for each entity, builds deduplicated sorted lists. Returns the options response structure.

#### Updated query_devices Signature

```python
async def query_devices(
    self,
    limit: int = 20,
    offset: int = 0,
    cursor: Optional[str] = None,
    sort_key: str = SORT_KEY_PRIORITY,
    sort_order: str = SORT_ORDER_ASC,
    filter_manufacturer: Optional[List[str]] = None,
    filter_device_class: Optional[List[str]] = None,
    filter_status: Optional[List[str]] = None,
    filter_area: Optional[List[str]] = None,
) -> Dict[str, Any]:
```

**Filter application order**:
1. Convert entities to `(entity, status)` tuples
2. Apply `_apply_filters()` (filter first, reduces set size before sort/paginate)
3. Apply sort
4. Apply cursor pagination
5. Compute `total` from post-filter, pre-pagination length
6. Return response

### websocket_api.py Changes (Sprint 5)

#### Updated query_devices Schema

```python
@websocket_api.websocket_command({
    vol.Required("type"): COMMAND_QUERY_DEVICES,
    vol.Optional("limit", default=50): vol.All(vol.Coerce(int), vol.Range(min=1, max=100)),
    vol.Optional("offset", default=0): vol.All(vol.Coerce(int), vol.Range(min=0)),
    vol.Optional("cursor"): vol.Any(str, None),
    vol.Optional("sort_key", default=SORT_KEY_PRIORITY): vol.In(SUPPORTED_SORT_KEYS),
    vol.Optional("sort_order", default=SORT_ORDER_ASC): vol.In(SUPPORTED_SORT_ORDERS),
    # Sprint 5: Filter params (all optional, empty list = no filter)
    vol.Optional("filter_manufacturer", default=[]): [str],
    vol.Optional("filter_device_class", default=[]): [str],
    vol.Optional("filter_status", default=[]): vol.All([str], vol.Length(max=4)),
    vol.Optional("filter_area", default=[]): [str],
})
```

Filter params are normalized before passing to `battery_monitor.query_devices()`: empty lists are converted to None so `_apply_filters` can correctly skip inactive filter categories.

#### New get_filter_options Handler

```python
@websocket_api.websocket_command({
    vol.Required("type"): COMMAND_GET_FILTER_OPTIONS,
})
@websocket_api.async_response
async def handle_get_filter_options(hass, connection, msg):
    """Handle vulcan-brownout/get_filter_options WebSocket command.

    Sprint 5: Returns available filter values from HA device/area registries.
    Values are derived from the actual battery entities tracked by BatteryMonitor,
    not from all HA devices (avoids showing irrelevant filter options).
    """
```

### Frontend Changes (Sprint 5)

#### New State Properties on VulcanBrownoutPanel

```javascript
// Filter state
active_filters: { state: true },        // { manufacturer: [], device_class: [], status: [], area: [] }
staged_filters: { state: true },        // Mobile bottom sheet staging (uncommitted changes)
filter_options: { state: true },        // Cached get_filter_options response
filter_options_loading: { state: true }, // true while get_filter_options in flight
filter_options_error: { state: true },  // Error message if get_filter_options failed
show_filter_dropdown: { state: true },  // Which dropdown is open: null | "manufacturer" | "device_class" | "status" | "area"
show_mobile_filter_sheet: { state: true }, // true when mobile bottom sheet is open
is_mobile: { state: true },             // true when window.innerWidth < 768
```

#### Filter Bar Component Architecture

The filter bar is a separate rendering section (not a separate Lit component) within the main panel template. It consists of two separate DOM rows:

**Row 1: Filter Bar Row** (always visible when devices exist or filters active)
- Desktop: Sort dropdown + four filter trigger buttons (Manufacturer, Device Class, Status, Room)
- Mobile: Sort dropdown + single "Filter" button with active count badge
- Height: 48px, background: `--vb-bg-secondary`, 1px bottom border

**Row 2: Chip Row** (conditionally rendered — not hidden, removed from DOM)
- Appears when `active_filters` has at least one non-empty array
- Contains one chip per active filter value, plus "Clear all" text link
- Height: 40px, overflow-x: auto, slide-in/out animation 200ms

#### Filter Dropdown Architecture

Custom `<div>` panels, not native `<select>` elements. Positioned absolutely below their trigger button. Key behaviors:
- Opens on trigger button click
- Closes on outside click (document-level click listener, removed on close)
- Closes on Escape key
- Max-height: 300px with overflow-y: auto
- Loading state while `get_filter_options` pending
- Error state with Retry button if `get_filter_options` failed
- Checks apply immediately to trigger button label and chip row (desktop, no staging)

#### Mobile Bottom Sheet Architecture

Triggered by the single "Filter" button on mobile (< 768px). Staged apply pattern:
- Opens: copy `active_filters` → `staged_filters`; sheet slides up 300ms
- User changes checkboxes: update `staged_filters` only (no API call)
- "Apply Filters": commit `staged_filters` → `active_filters`; close sheet; reset cursor; call `query_devices`
- "[X]" or outside tap: discard `staged_filters`; close sheet; no changes

```javascript
_open_mobile_filter_sheet() {
  this.staged_filters = JSON.parse(JSON.stringify(this.active_filters)); // deep copy
  this.show_mobile_filter_sheet = true;
}

_apply_mobile_filters() {
  this.active_filters = this.staged_filters;
  this.show_mobile_filter_sheet = false;
  this._save_filters_to_localstorage();
  this._current_cursor = null;
  this._load_devices();
}

_cancel_mobile_filters() {
  this.staged_filters = null;
  this.show_mobile_filter_sheet = false;
  // No changes to active_filters, no API call
}
```

#### Filter Persistence via localStorage

Key: `vulcan_brownout_filters`
Schema: `{ manufacturer: string[], device_class: string[], status: string[], area: string[] }`

Read timing: in `connectedCallback()`, before the first `query_devices` call. If localStorage key is absent, default to `{ manufacturer: [], device_class: [], status: [], area: [] }`.

Validation on restore: after `get_filter_options` response, remove any persisted filter values that no longer exist in the options. For example, if a room was deleted from HA, its name is silently dropped from the restored area filter.

Write timing: on every filter change (chip add, chip remove, clear all, mobile apply).

#### get_filter_options Client-Side Caching

```javascript
async _load_filter_options() {
  // Guard against duplicate in-flight calls
  if (this._filter_options_fetch_promise) {
    return this._filter_options_fetch_promise;
  }

  this.filter_options_loading = true;
  this._filter_options_fetch_promise = this._call_websocket(
    GET_FILTER_OPTIONS_COMMAND, {}
  ).then(result => {
    this.filter_options = result;
    this.filter_options_loading = false;
    this._filter_options_fetch_promise = null;
  }).catch(err => {
    this.filter_options_error = err.message;
    this.filter_options_loading = false;
    this._filter_options_fetch_promise = null;
  });

  return this._filter_options_fetch_promise;
}
```

Called once in `connectedCallback()`. Result cached in `this.filter_options` for the session. Retry available via [Retry] button inside failed dropdown.

#### Filtered Empty State

When `query_devices` returns `total: 0` AND `active_filters` has at least one non-empty array, show the filtered empty state (Wireframe 16) instead of the no-devices empty state (Wireframe 6):

- Icon: Filter/funnel SVG (48px, `--vb-text-secondary` color)
- Title: "No devices match your filters."
- Subtitle: "Try removing one or more filters, or clear all filters to see the full device list."
- CTA: Single "[Clear Filters]" button → calls `_clear_all_filters()`

### Mock HA Server Changes (Sprint 5)

`server.py` must be updated to support:

1. **`get_filter_options` command handler**: Returns filter options derived from `self.entity_data`. For E2E tests, entities loaded via `/mock/control` should include `manufacturer` and `area` fields so the mock can return meaningful filter options.

2. **Filter params in `_handle_query_devices`**: Parse `filter_manufacturer`, `filter_device_class`, `filter_status`, `filter_area` from the incoming command. Apply AND/OR filter logic before pagination. Return filtered `total`.

3. **Entity data schema extension**: Entities loaded via `/mock/control` should support `manufacturer` and `area` fields:
   ```json
   {
     "entity_id": "sensor.aqara_door_battery",
     "state": "45",
     "manufacturer": "Aqara",
     "area": "Living Room",
     "friendly_name": "Front Door Battery"
   }
   ```

This allows E2E tests to verify that filtering by manufacturer and area returns the correct subset.

## Key Algorithms

### Entity Filter (Unchanged from Sprint 3)
```python
def is_battery_entity(entity_id, entity_data):
    if entity_id.split('.')[0] == 'binary_sensor': return False
    if entity_data.attributes.get('device_class') != 'battery': return False
    level = entity_data.attributes.get('battery_level')
    if level is None: return False
    try: return 0 <= float(level) <= 100
    except: return False
```

### Server-Side Filter Application (Sprint 5 NEW)
```python
# Filter application order: filter → sort → paginate
# Filter logic: AND across categories, OR within category
# Empty category filter = no filter on that category
# total = len(filtered_devices) before pagination
```

### Notification Check (Unchanged)
```python
# Checks in order: global enabled → device enabled → severity filter → frequency cap
# Frequency cap: track last_notification_time per device, skip if within cap window
# Sends via hass.services.async_call('persistent_notification', 'create', ...)
```

### Theme Detection (Sprint 4, Unchanged in Sprint 5)
```javascript
// Step 1: Check hass.themes.darkMode (primary source)
if (hass?.themes?.darkMode !== undefined) {
  return hass.themes.darkMode ? 'dark' : 'light';
}
// Step 2: Check DOM data-theme attribute (fallback)
// Step 3: Check OS preference (fallback)
// Step 4: Default to light
```

## Color Tokens

### Sprint 1-4 Tokens (Unchanged)

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

### Sprint 5 New Filter UI Tokens

| Token | Light | Dark | Usage |
|-------|-------|------|-------|
| `--vb-bg-secondary` | #F0F0F0 | #252525 | Filter bar background |
| `--vb-filter-chip-bg` | #E3F2FD | #1A3A5C | Filter chip background |
| `--vb-filter-chip-text` | #0D47A1 | #90CAF9 | Filter chip text |
| `--vb-filter-chip-border` | #90CAF9 | #1E5080 | Filter chip border |
| `--vb-filter-active-bg` | #03A9F4 | #0288D1 | Active filter trigger button bg |
| `--vb-filter-active-text` | #FFFFFF | #FFFFFF | Active filter trigger button text |
| `--vb-overlay-bg` | rgba(0,0,0,0.5) | rgba(0,0,0,0.5) | Bottom sheet overlay |

All filter UI tokens must be defined in both `[data-theme="light"]` and `[data-theme="dark"]` CSS blocks.

## Connection States

DISCONNECTED → CONNECTING → CONNECTED (green) → RECONNECTING (blue, exp backoff 1-30s) → OFFLINE (red, manual retry)

## Performance Targets

- Initial load: <1s (including get_filter_options call in parallel)
- Filter change round-trip (filter applied + new page loaded): <800ms
- Scroll fetch (pagination of filtered result): <500ms
- get_filter_options: <300ms (reads HA registry, no expensive computation)
- Theme detection: <50ms (hass.themes.darkMode lookup)
- Theme transition: 300ms CSS smooth
- Mobile bottom sheet open/close: 300ms animation
- Filter chip row slide-in/out: 200ms animation

## Security

- HA WebSocket session auth, HA device registry controls visibility
- Filter params are validated server-side (voluptuous schema, empty/null handling)
- No new external API calls (filter options come from HA's own registries)
- filter_status values validated against SUPPORTED_STATUSES constant
- localStorage filter state is client-controlled; backend validates all filter values independently

## Minimum Home Assistant Version

**Sprint 5**: 2026.2.0 (unchanged from Sprint 4). No new HA API usage beyond what Sprint 4 established.

## Deployment Considerations

Sprint 5 requires both backend and frontend changes:

1. **Backend changes**: `const.py`, `battery_monitor.py`, `websocket_api.py` — new filter logic and command handler
2. **Frontend changes**: `vulcan-brownout-panel.js` — filter bar, dropdowns, chip row, mobile bottom sheet, localStorage persistence, `get_filter_options` call
3. **Manifest version**: Bump to 5.0.0
4. **Mock server**: `server.py` — add `get_filter_options` handler, add filter logic to `_handle_query_devices`

**Deployment steps**:
1. Deploy updated Python files to HA custom_components directory
2. Deploy updated frontend JS file
3. Update manifest.json to version 5.0.0
4. Deploy updated mock server for testing
5. Restart HA service
6. Health check: `/api/vulcan_brownout/health` returns 200
7. Smoke test: Open panel, open filter dropdown, verify options populated, select filter, verify device list updates

**Rollback**: Previous version symlink strategy (ADR-003) allows instant rollback if issues detected post-deployment.
