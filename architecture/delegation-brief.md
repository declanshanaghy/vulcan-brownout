# Sprint 5 Delegation Brief

**To**: ArsonWells (Lead Developer) | **From**: FiremanDecko (Architect) | **Date**: 2026-02-22

**Status**: Ready for implementation | **Priority**: P1 | **Timeline**: 2 weeks

---

## Executive Summary

Sprint 5 delivers **Simple Filtering** — server-side filtering of the battery device list by manufacturer, device class, status, and room/area. This is both a backend and frontend sprint.

**Backend**: `query_devices` gains four optional filter params; a new `get_filter_options` command returns dynamic filter values from HA registries.

**Frontend**: A filter bar replaces the existing sort/filter control bar; a chip row shows active filters; a mobile bottom sheet handles filter selection on small viewports; filter state persists to localStorage.

**No new Python dependencies.** All filter data comes from HA's existing device_registry, area_registry, and entity_registry — already imported in `battery_monitor.py`.

The core architectural decision is documented in ADR-015. Read it first.

---

## Architecture Documents to Follow

1. **ADR-015**: `architecture/adrs/ADR-015-server-side-filtering.md` — Decision record, rationale, filter logic spec
2. **System Design**: `architecture/system-design.md` — Sprint 5 section with data flows and method signatures
3. **API Contracts**: `architecture/api-contracts.md` v5.0.0 — Updated `query_devices` schema, new `get_filter_options` spec
4. **Sprint Plan**: `architecture/sprint-plan.md` — 4 stories with acceptance criteria and technical notes
5. **Wireframes**: `design/wireframes.md` — Wireframes 12-16 for all filter UI layouts
6. **Interactions**: `design/interactions.md` — Interactions 11-13 for filter behavior, chip management, dynamic population
7. **Design Brief**: `design/product-design-brief.md` — Sprint 5 section for product decisions and UX constraints

---

## File-by-File Code Changes

### 1. `development/src/custom_components/vulcan_brownout/const.py`

**Add the following constants**:

```python
# Sprint 5: Filter commands and keys
COMMAND_GET_FILTER_OPTIONS = "vulcan-brownout/get_filter_options"

FILTER_KEY_MANUFACTURER = "filter_manufacturer"
FILTER_KEY_DEVICE_CLASS = "filter_device_class"
FILTER_KEY_STATUS = "filter_status"
FILTER_KEY_AREA = "filter_area"

# Supported filter keys (for validation reference)
SUPPORTED_FILTER_KEYS = [
    FILTER_KEY_MANUFACTURER,
    FILTER_KEY_DEVICE_CLASS,
    FILTER_KEY_STATUS,
    FILTER_KEY_AREA,
]

# Maximum values per category returned by get_filter_options
MAX_FILTER_OPTIONS = 20

# Bump version
VERSION = "5.0.0"
```

Note: `SUPPORTED_STATUSES` is already defined in `const.py` as of Sprint 3. Do not duplicate it. Use it in the `filter_status` validation.

---

### 2. `development/src/custom_components/vulcan_brownout/battery_monitor.py`

#### Update imports

Add `area_registry` to the existing HA helper imports:
```python
from homeassistant.helpers import entity_registry as er, device_registry as dr, area_registry as ar
```

#### Add new private helper methods to `BatteryMonitor`

```python
def _get_entity_manufacturer(self, entity_id: str) -> Optional[str]:
    """Get manufacturer name for a battery entity via device_registry.

    Sprint 5: Used for server-side manufacturer filtering.

    Returns:
        Manufacturer string, or None if entity has no device or device has no manufacturer.
    """
    try:
        entity_registry = er.async_get(self.hass)
        entry = entity_registry.entities.get(entity_id)
        if not entry or not entry.device_id:
            return None
        device_registry = dr.async_get(self.hass)
        device = device_registry.async_get(entry.device_id)
        if device and device.manufacturer:
            return device.manufacturer
    except Exception:
        pass
    return None


def _get_entity_area_name(self, entity_id: str) -> Optional[str]:
    """Get area name for a battery entity via area_registry.

    Sprint 5: Used for server-side area filtering.

    Lookup priority:
    1. Entity's own area_id (entity_registry.entities[entity_id].area_id)
    2. Entity's device area_id (device_registry.async_get(device_id).area_id)
    3. None (entity has no area assignment)

    Returns:
        Area name string, or None if no area assigned or area has no name.
    """
    try:
        entity_registry = er.async_get(self.hass)
        area_reg = ar.async_get(self.hass)
        entry = entity_registry.entities.get(entity_id)
        if not entry:
            return None

        area_id = entry.area_id
        if not area_id and entry.device_id:
            device_registry = dr.async_get(self.hass)
            device = device_registry.async_get(entry.device_id)
            if device:
                area_id = device.area_id

        if area_id:
            area = area_reg.async_get_area(area_id)
            if area and area.name:
                return area.name
    except Exception:
        pass
    return None


def _apply_filters(
    self,
    devices: List[Tuple],
    filter_manufacturer: Optional[List[str]] = None,
    filter_device_class: Optional[List[str]] = None,
    filter_status: Optional[List[str]] = None,
    filter_area: Optional[List[str]] = None,
) -> List[Tuple]:
    """Apply server-side filters to device list.

    Sprint 5: Implements AND-across-categories, OR-within-category filter logic.
    Filter application order: filter → sort → paginate.

    Args:
        devices: List of (BatteryEntity, status_str) tuples (pre-sort, pre-paginate)
        filter_manufacturer: OR filter — include devices matching any value. None = no filter.
        filter_device_class: OR filter — include devices matching any value. None = no filter.
        filter_status: OR filter — include devices matching any status. None = no filter.
        filter_area: OR filter — include devices whose area name matches any value. None = no filter.

    Returns:
        Filtered list of (BatteryEntity, status_str) tuples.
    """
    # Fast path: no active filters
    if not any([filter_manufacturer, filter_device_class, filter_status, filter_area]):
        return devices

    result = []
    for entity, status in devices:
        # AND across categories: skip device if it fails ANY active filter category
        if filter_manufacturer:
            manufacturer = self._get_entity_manufacturer(entity.entity_id)
            if manufacturer not in filter_manufacturer:
                continue

        if filter_device_class:
            device_class = entity.state.attributes.get("device_class", "")
            if device_class not in filter_device_class:
                continue

        if filter_status:
            if status not in filter_status:
                continue

        if filter_area:
            area_name = self._get_entity_area_name(entity.entity_id)
            if area_name not in filter_area:
                continue

        result.append((entity, status))

    return result


async def get_filter_options(self) -> Dict[str, Any]:
    """Return available filter values derived from tracked battery entities.

    Sprint 5: Called by get_filter_options WebSocket command handler.

    Reads device_registry, area_registry, and entity_registry.
    Only returns values that are actually present in tracked battery entities.

    Returns:
        Dict with manufacturers, device_classes, areas, statuses keys.
    """
    from .const import MAX_FILTER_OPTIONS, SUPPORTED_STATUSES

    try:
        entity_registry = er.async_get(self.hass)
        device_registry = dr.async_get(self.hass)
        area_reg = ar.async_get(self.hass)

        manufacturers: set = set()
        device_classes: set = set()
        area_ids_seen: Dict[str, str] = {}  # area_id → area_name

        for entity_id, battery_entity in self.entities.items():
            # Collect manufacturer
            entry = entity_registry.entities.get(entity_id)
            if entry and entry.device_id:
                device = device_registry.async_get(entry.device_id)
                if device and device.manufacturer:
                    manufacturers.add(device.manufacturer)

            # Collect device_class
            device_class = battery_entity.state.attributes.get("device_class")
            if device_class:
                device_classes.add(device_class)

            # Collect area
            if entry:
                area_id = entry.area_id
                if not area_id and entry.device_id:
                    device = device_registry.async_get(entry.device_id)
                    if device:
                        area_id = device.area_id
                if area_id and area_id not in area_ids_seen:
                    area = area_reg.async_get_area(area_id)
                    if area and area.name:
                        area_ids_seen[area_id] = area.name

        # Build sorted areas list
        areas = [
            {"id": area_id, "name": name}
            for area_id, name in area_ids_seen.items()
        ]
        areas.sort(key=lambda a: a["name"])

        return {
            "manufacturers": sorted(list(manufacturers))[:MAX_FILTER_OPTIONS],
            "device_classes": sorted(list(device_classes))[:MAX_FILTER_OPTIONS],
            "areas": areas[:MAX_FILTER_OPTIONS],
            "statuses": SUPPORTED_STATUSES,
        }

    except Exception as e:
        _LOGGER.error(f"Error building filter options: {e}")
        raise
```

#### Update `query_devices` method signature

Add filter params to the existing signature:

```python
async def query_devices(
    self,
    limit: int = 20,
    offset: int = 0,
    cursor: Optional[str] = None,
    sort_key: str = SORT_KEY_PRIORITY,
    sort_order: str = SORT_ORDER_ASC,
    # Sprint 5: Server-side filter params (None = no filter on that category)
    filter_manufacturer: Optional[List[str]] = None,
    filter_device_class: Optional[List[str]] = None,
    filter_status: Optional[List[str]] = None,
    filter_area: Optional[List[str]] = None,
) -> Dict[str, Any]:
```

Inside `query_devices`, apply `_apply_filters` BEFORE sorting. Current code builds devices list then sorts. The new order is:

```python
# Convert entities to list with status
devices = [
    (entity, self.get_status_for_device(entity))
    for entity in self.entities.values()
]

# Sprint 5: Apply server-side filters BEFORE sort and pagination
devices = self._apply_filters(
    devices,
    filter_manufacturer=filter_manufacturer,
    filter_device_class=filter_device_class,
    filter_status=filter_status,
    filter_area=filter_area,
)

# Sort devices (existing code)
# ... existing sort code ...

# IMPORTANT: total is now the filtered count, not entity count
total = len(devices)
# ... existing pagination code ...
```

The `total` variable must be set from `len(devices)` AFTER filtering and AFTER sorting but BEFORE pagination slicing. Existing code sets `total = len(devices)` before sorting, which is fine since filtering doesn't add items — but move it to after the `_apply_filters` call explicitly for clarity.

---

### 3. `development/src/custom_components/vulcan_brownout/websocket_api.py`

#### Update imports

```python
from .const import (
    COMMAND_QUERY_DEVICES,
    COMMAND_SUBSCRIBE,
    COMMAND_SET_THRESHOLD,
    COMMAND_GET_NOTIFICATION_PREFERENCES,
    COMMAND_SET_NOTIFICATION_PREFERENCES,
    COMMAND_GET_FILTER_OPTIONS,    # Sprint 5: NEW
    DOMAIN,
    MAX_PAGE_SIZE,
    BATTERY_THRESHOLD_MIN,
    BATTERY_THRESHOLD_MAX,
    MAX_DEVICE_RULES,
    SORT_KEY_PRIORITY,
    SORT_ORDER_ASC,
    SUPPORTED_SORT_KEYS,
    SUPPORTED_SORT_ORDERS,
    SUPPORTED_STATUSES,            # Sprint 5: for filter_status validation
    NOTIFICATION_FREQUENCY_CAP_OPTIONS,
    NOTIFICATION_SEVERITY_FILTER_OPTIONS,
)
```

#### Update `register_websocket_commands`

```python
def register_websocket_commands(hass: HomeAssistant) -> None:
    """Register WebSocket command handlers."""
    websocket_api.async_register_command(hass, handle_query_devices)
    websocket_api.async_register_command(hass, handle_subscribe)
    websocket_api.async_register_command(hass, handle_set_threshold)
    websocket_api.async_register_command(hass, handle_get_notification_preferences)
    websocket_api.async_register_command(hass, handle_set_notification_preferences)
    websocket_api.async_register_command(hass, handle_get_filter_options)  # Sprint 5: NEW
```

#### Update `handle_query_devices` schema

Replace the existing `@websocket_api.websocket_command` decorator:

```python
@websocket_api.websocket_command(
    {
        vol.Required("type"): COMMAND_QUERY_DEVICES,
        vol.Optional("limit", default=50): vol.All(vol.Coerce(int), vol.Range(min=1, max=100)),
        vol.Optional("offset", default=0): vol.All(vol.Coerce(int), vol.Range(min=0)),
        vol.Optional("cursor"): vol.Any(str, None),
        vol.Optional("sort_key", default=SORT_KEY_PRIORITY): vol.In(SUPPORTED_SORT_KEYS),
        vol.Optional("sort_order", default=SORT_ORDER_ASC): vol.In(SUPPORTED_SORT_ORDERS),
        # Sprint 5: Optional filter params (empty list = no filter on that category)
        vol.Optional("filter_manufacturer", default=[]): [str],
        vol.Optional("filter_device_class", default=[]): [str],
        vol.Optional("filter_status", default=[]): vol.All(
            [vol.In(SUPPORTED_STATUSES)],
        ),
        vol.Optional("filter_area", default=[]): [str],
    }
)
```

Inside `handle_query_devices`, extract filter params and normalize empty lists to None:

```python
# Sprint 5: Extract filter params; normalize empty list to None (= no filter)
def _normalize_filter(value):
    """Convert empty list to None; non-empty list passes through."""
    return value if value else None

filter_manufacturer = _normalize_filter(msg.get("filter_manufacturer", []))
filter_device_class = _normalize_filter(msg.get("filter_device_class", []))
filter_status = _normalize_filter(msg.get("filter_status", []))
filter_area = _normalize_filter(msg.get("filter_area", []))

# Query devices (now includes filter params)
result = await battery_monitor.query_devices(
    limit=limit,
    offset=offset,
    cursor=cursor,
    sort_key=sort_key,
    sort_order=sort_order,
    filter_manufacturer=filter_manufacturer,
    filter_device_class=filter_device_class,
    filter_status=filter_status,
    filter_area=filter_area,
)
```

#### Add new `handle_get_filter_options` handler

```python
@websocket_api.websocket_command(
    {
        vol.Required("type"): COMMAND_GET_FILTER_OPTIONS,
    }
)
@websocket_api.async_response
async def handle_get_filter_options(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: Dict[str, Any]
) -> None:
    """Handle vulcan-brownout/get_filter_options WebSocket command.

    Sprint 5: Returns available filter values (manufacturers, device_classes, areas, statuses)
    derived from the actual battery entities in the user's HA installation.
    """
    try:
        battery_monitor: BatteryMonitor = hass.data.get(DOMAIN)
        if battery_monitor is None:
            connection.send_error(
                msg["id"],
                "integration_not_loaded",
                "Vulcan Brownout integration not loaded",
            )
            return

        result = await battery_monitor.get_filter_options()
        connection.send_result(msg["id"], result)

    except Exception as e:
        _LOGGER.error(f"Error handling get_filter_options command: {e}")
        connection.send_error(
            msg["id"],
            "internal_error",
            "Failed to get filter options",
        )
```

---

### 4. `development/src/custom_components/vulcan_brownout/frontend/vulcan-brownout-panel.js`

This is the largest change in Sprint 5. Work through it section by section.

#### Step 1: Add new constants

```javascript
const GET_FILTER_OPTIONS_COMMAND = "vulcan-brownout/get_filter_options";

const FILTER_STORAGE_KEY = "vulcan_brownout_filters";
const DEFAULT_FILTERS = { manufacturer: [], device_class: [], status: [], area: [] };

// Filter category display names (for chip labels and dropdown headers)
const FILTER_CATEGORY_LABELS = {
  manufacturer: "Manufacturer",
  device_class: "Device Class",
  status: "Status",
  area: "Room",
};

// Breakpoint for mobile vs desktop filter UI
const MOBILE_BREAKPOINT_PX = 768;
```

#### Step 2: Add new reactive properties

Add to the existing `static properties = { ... }` block:

```javascript
// Sprint 5: Filter state
active_filters: { state: true },          // { manufacturer: [], device_class: [], status: [], area: [] }
staged_filters: { state: true },          // Mobile bottom sheet staging copy
filter_options: { state: true },          // Cached get_filter_options response
filter_options_loading: { state: true },  // true while fetching
filter_options_error: { state: true },    // error message if fetch failed
show_filter_dropdown: { state: true },    // null or "manufacturer"|"device_class"|"status"|"area"
show_mobile_filter_sheet: { state: true }, // true when bottom sheet open
is_mobile: { state: true },              // true when window.innerWidth < MOBILE_BREAKPOINT_PX
_filter_options_fetch_promise: {},       // not state; used as instance property guard
```

#### Step 3: Initialize new state in the constructor

```javascript
constructor() {
  super();
  // ... existing init ...

  // Sprint 5: Filter initialization
  this.active_filters = this._load_filters_from_localstorage();
  this.staged_filters = null;
  this.filter_options = null;
  this.filter_options_loading = false;
  this.filter_options_error = null;
  this.show_filter_dropdown = null;
  this.show_mobile_filter_sheet = false;
  this.is_mobile = window.innerWidth < MOBILE_BREAKPOINT_PX;
  this._filter_options_fetch_promise = null;
}
```

#### Step 4: Update `connectedCallback()`

After `super.connectedCallback()`, add:

```javascript
// Sprint 5: Start filter options fetch in parallel with device load
this._load_filter_options();  // non-blocking, result cached in this.filter_options

// Sprint 5: Set mobile breakpoint listener
this._resizeListener = () => {
  this.is_mobile = window.innerWidth < MOBILE_BREAKPOINT_PX;
};
window.addEventListener('resize', this._resizeListener);

// Sprint 5: Attach outside-click listener for dropdowns
this._outsideClickListener = (e) => {
  if (this.show_filter_dropdown && !this.shadowRoot.contains(e.target)) {
    this._close_filter_dropdown(true); // true = apply filter changes
  }
};
document.addEventListener('click', this._outsideClickListener);
```

Note: `_load_devices()` already reads `this.active_filters` (after Step 6 below), so the restored filter state is included in the first `query_devices` call automatically.

#### Step 5: Update `disconnectedCallback()`

```javascript
// Sprint 5: Clean up listeners
if (this._resizeListener) {
  window.removeEventListener('resize', this._resizeListener);
}
if (this._outsideClickListener) {
  document.removeEventListener('click', this._outsideClickListener);
}
```

#### Step 6: Update `_load_devices()` to pass filter params

When building the WebSocket message for `query_devices`, include active filters:

```javascript
const msg = {
  type: QUERY_DEVICES_COMMAND,
  limit: DEFAULT_PAGE_SIZE,
  cursor: this.current_cursor,
  sort_key: this.sort_method,
  // Sprint 5: Include active filters
  filter_manufacturer: this.active_filters.manufacturer || [],
  filter_device_class: this.active_filters.device_class || [],
  filter_status: this.active_filters.status || [],
  filter_area: this.active_filters.area || [],
};
```

#### Step 7: Add filter management methods

```javascript
// Load filter state from localStorage on panel init
_load_filters_from_localstorage() {
  try {
    const saved = localStorage.getItem(FILTER_STORAGE_KEY);
    if (saved) {
      const parsed = JSON.parse(saved);
      // Ensure all four categories present (handle partial/old data)
      return {
        manufacturer: parsed.manufacturer || [],
        device_class: parsed.device_class || [],
        status: parsed.status || [],
        area: parsed.area || [],
      };
    }
  } catch (e) {
    // Silently ignore localStorage errors
  }
  return { ...DEFAULT_FILTERS };
}

// Save filter state to localStorage
_save_filters_to_localstorage() {
  try {
    localStorage.setItem(FILTER_STORAGE_KEY, JSON.stringify(this.active_filters));
  } catch (e) {
    // Silently ignore (quota exceeded, etc.)
  }
}

// Called when filters change — centralized entry point
_on_filter_changed() {
  this._save_filters_to_localstorage();
  this.current_cursor = null;   // Reset pagination
  this._load_devices();         // Re-fetch with new filters
}

// Remove a single filter value
_remove_filter_chip(category, value) {
  const updated = { ...this.active_filters };
  updated[category] = updated[category].filter(v => v !== value);
  this.active_filters = updated;
  this._on_filter_changed();
}

// Clear all active filters
_clear_all_filters() {
  this.active_filters = { ...DEFAULT_FILTERS };
  this._on_filter_changed();
}

// Toggle a filter value in a category (desktop dropdown)
_toggle_filter_value(category, value) {
  const updated = { ...this.active_filters };
  const list = updated[category] || [];
  if (list.includes(value)) {
    updated[category] = list.filter(v => v !== value);
  } else {
    updated[category] = [...list, value];
  }
  this.active_filters = updated;
  // Note: For desktop, filter is applied on dropdown CLOSE, not on each toggle
  // The trigger label and chip row update reactively via render()
  this._save_filters_to_localstorage();
  // Debounced query — use a timer to avoid calling on every checkbox toggle
  clearTimeout(this._filter_debounce_timer);
  this._filter_debounce_timer = setTimeout(() => {
    this.current_cursor = null;
    this._load_devices();
  }, 300);
}

// Dropdown open/close
_open_filter_dropdown(category) {
  this.show_filter_dropdown = category;
}

_close_filter_dropdown(apply) {
  this.show_filter_dropdown = null;
  // No separate apply step needed — _toggle_filter_value already handles debounced query
}

// Mobile bottom sheet methods
_open_mobile_filter_sheet() {
  // Deep copy active_filters into staged_filters
  this.staged_filters = JSON.parse(JSON.stringify(this.active_filters));
  this.show_mobile_filter_sheet = true;
}

_apply_mobile_filters() {
  this.active_filters = this.staged_filters;
  this.staged_filters = null;
  this.show_mobile_filter_sheet = false;
  this._on_filter_changed();
}

_cancel_mobile_filters() {
  this.staged_filters = null;
  this.show_mobile_filter_sheet = false;
  // No change to active_filters, no API call
}

_toggle_staged_filter_value(category, value) {
  const updated = { ...this.staged_filters };
  const list = updated[category] || [];
  if (list.includes(value)) {
    updated[category] = list.filter(v => v !== value);
  } else {
    updated[category] = [...list, value];
  }
  this.staged_filters = updated;
}

_clear_staged_filters() {
  this.staged_filters = { ...DEFAULT_FILTERS };
}

// Load filter options from backend (called once on connectedCallback)
async _load_filter_options() {
  if (this._filter_options_fetch_promise) {
    return this._filter_options_fetch_promise;
  }
  this.filter_options_loading = true;
  this.filter_options_error = null;

  this._filter_options_fetch_promise = this.hass.connection.sendMessagePromise({
    type: GET_FILTER_OPTIONS_COMMAND,
  }).then(result => {
    this.filter_options = result;
    this.filter_options_loading = false;
    this._filter_options_fetch_promise = null;
  }).catch(err => {
    this.filter_options_error = err.message || "Failed to load filter options";
    this.filter_options_loading = false;
    this._filter_options_fetch_promise = null;
  });

  return this._filter_options_fetch_promise;
}

// Retry loading filter options (called from [Retry] button in dropdown error state)
_retry_filter_options() {
  this.filter_options_error = null;
  this._load_filter_options();
}

// Check if any filter category has active selections
_has_active_filters() {
  const f = this.active_filters;
  return (f.manufacturer.length + f.device_class.length + f.status.length + f.area.length) > 0;
}

// Count total active filter values across all categories
_active_filter_count() {
  const f = this.active_filters;
  return f.manufacturer.length + f.device_class.length + f.status.length + f.area.length;
}

// Check if current empty state is due to filters (not "no devices at all")
_is_filtered_empty_state() {
  return this.battery_devices.length === 0
    && !this.isLoading
    && this._has_active_filters();
}
```

#### Step 8: Validate persisted filter values after filter options load

After `get_filter_options` resolves successfully, validate that restored localStorage filter values still exist in the options. Drop values that no longer exist:

```javascript
// In the .then() block of _load_filter_options:
if (this.active_filters && this.filter_options) {
  const cleaned = { ...this.active_filters };
  const options = this.filter_options;

  if (options.manufacturers && cleaned.manufacturer.length > 0) {
    cleaned.manufacturer = cleaned.manufacturer.filter(v => options.manufacturers.includes(v));
  }
  if (options.device_classes && cleaned.device_class.length > 0) {
    cleaned.device_class = cleaned.device_class.filter(v => options.device_classes.includes(v));
  }
  if (options.statuses && cleaned.status.length > 0) {
    cleaned.status = cleaned.status.filter(v => options.statuses.includes(v));
  }
  if (options.areas && cleaned.area.length > 0) {
    const areaNames = options.areas.map(a => a.name);
    cleaned.area = cleaned.area.filter(v => areaNames.includes(v));
  }

  if (JSON.stringify(cleaned) !== JSON.stringify(this.active_filters)) {
    this.active_filters = cleaned;
    this._save_filters_to_localstorage();
  }
}
```

#### Step 9: Update `render()` — filter bar and chip row

In the existing `render()` method, replace the `SORT/FILTER BAR` section with:

**Desktop filter bar** (show when `!this.is_mobile`):
```javascript
html`
<div class="filter-bar" role="toolbar" aria-label="Filter and sort controls">
  ${this._render_sort_control()}
  ${this._render_desktop_filter_buttons()}
</div>
${this._has_active_filters() ? this._render_chip_row() : ''}
`
```

**Mobile filter bar** (show when `this.is_mobile`):
```javascript
html`
<div class="filter-bar" role="toolbar" aria-label="Filter and sort controls">
  ${this._render_sort_control()}
  <button
    class="filter-trigger ${this._active_filter_count() > 0 ? 'active' : ''}"
    @click="${this._open_mobile_filter_sheet}"
    aria-label="Filter options, ${this._active_filter_count()} active"
    aria-haspopup="dialog">
    Filter${this._active_filter_count() > 0 ? ` (${this._active_filter_count()})` : ''}
  </button>
</div>
${this._has_active_filters() ? this._render_chip_row() : ''}
${this.show_mobile_filter_sheet ? this._render_mobile_filter_sheet() : ''}
`
```

Implement `_render_desktop_filter_buttons()`, `_render_chip_row()`, `_render_mobile_filter_sheet()`, and `_render_filter_dropdown(category)` as separate render helper methods returning Lit `html` templates.

#### Step 10: Update empty state render logic

In the existing empty state rendering, differentiate between filtered and unfiltered empty states:

```javascript
// In render() where empty state is shown:
if (this._is_filtered_empty_state()) {
  return this._render_filtered_empty_state();
} else if (this.battery_devices.length === 0 && !this.isLoading) {
  return this._render_no_devices_empty_state();  // existing Wireframe 6 empty state
}
```

#### Step 11: Add new CSS for filter UI

Add to the component's static CSS (inside `static styles = css\`...\``):

```css
/* Filter Bar Row */
.filter-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 16px;
  height: 48px;
  background-color: var(--vb-bg-secondary);
  border-bottom: 1px solid var(--vb-border-color);
  flex-shrink: 0;
}

/* Filter Trigger Buttons */
.filter-btn {
  height: 44px;
  padding: 0 12px;
  border-radius: 4px;
  border: 1px solid var(--vb-border-color);
  background: var(--vb-bg-primary);
  color: var(--vb-text-primary);
  cursor: pointer;
  font-size: 14px;
  white-space: nowrap;
}

.filter-btn.active {
  background-color: var(--vb-filter-active-bg);
  color: var(--vb-filter-active-text);
  border-color: var(--vb-filter-active-bg);
}

/* Filter Dropdown Panel */
.filter-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  min-width: 220px;
  max-height: 300px;
  background: var(--vb-bg-primary);
  border: 1px solid var(--vb-border-color);
  border-radius: 4px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
  overflow-y: auto;
  z-index: 100;
}

/* Chip Row */
.chip-row {
  display: flex;
  flex-wrap: nowrap;
  overflow-x: auto;
  padding: 6px 16px;
  gap: 8px;
  align-items: center;
  background: var(--vb-bg-primary);
  border-bottom: 1px solid var(--vb-border-color);
  scrollbar-width: thin;
}

/* Individual Filter Chip */
.filter-chip {
  display: inline-flex;
  align-items: center;
  height: 32px;
  padding: 0 8px;
  border-radius: 16px;
  background: var(--vb-filter-chip-bg);
  border: 1px solid var(--vb-filter-chip-border);
  color: var(--vb-filter-chip-text);
  font-size: 12px;
  white-space: nowrap;
  flex-shrink: 0;
}

.filter-chip button {
  background: none;
  border: none;
  cursor: pointer;
  padding: 4px;
  color: var(--vb-filter-chip-text);
  font-size: 14px;
  line-height: 1;
  margin-left: 4px;
}

/* Clear All Link */
.chip-clear-all {
  background: none;
  border: none;
  cursor: pointer;
  color: var(--vb-color-action);
  font-size: 13px;
  padding: 8px 4px;
  margin-left: auto;
  white-space: nowrap;
  flex-shrink: 0;
}

/* Mobile Bottom Sheet */
.sheet-overlay {
  position: fixed;
  inset: 0;
  background: var(--vb-overlay-bg);
  z-index: 200;
}

.bottom-sheet {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  max-height: 85vh;
  overflow-y: auto;
  background: var(--vb-bg-primary);
  border-radius: 16px 16px 0 0;
  box-shadow: 0 -4px 20px rgba(0,0,0,0.2);
  z-index: 201;
  animation: slideUp 300ms ease-out;
}

@keyframes slideUp {
  from { transform: translateY(100%); }
  to { transform: translateY(0); }
}

/* Chip row animation */
.chip-row {
  animation: chipRowIn 200ms ease-out;
}

@keyframes chipRowIn {
  from { max-height: 0; opacity: 0; }
  to { max-height: 48px; opacity: 1; }
}

/* New CSS custom properties for filter UI tokens */
/* These tokens must be defined in the [data-theme] CSS blocks in styles.css */
/* See system-design.md "Sprint 5 New Filter UI Tokens" table */
```

---

### 5. `development/src/custom_components/vulcan_brownout/manifest.json`

```json
{
  "domain": "vulcan_brownout",
  "name": "Vulcan Brownout",
  "version": "5.0.0",
  ...
}
```

Bump `version` field from `4.0.0` to `5.0.0`.

---

### 6. `.github/docker/mock_ha/server.py`

Add Sprint 5 support to the mock server. This is required for E2E tests to pass.

#### Extend entity data schema

The `/mock/control` endpoint must accept `manufacturer` and `area` fields per entity:

```python
# In _mock_control, entity loading block:
self.entity_data[entity_id] = {
    "state": entity.get("state", "unknown"),
    "friendly_name": entity.get("friendly_name", entity_id),
    "attributes": entity.get("attributes", {}),
    "available": entity.get("available", True),
    "manufacturer": entity.get("manufacturer"),   # Sprint 5: NEW
    "area": entity.get("area"),                   # Sprint 5: NEW (area name string)
    "last_changed": datetime.utcnow().isoformat() + "Z",
    "last_updated": datetime.utcnow().isoformat() + "Z",
}
```

#### Add `get_filter_options` handler

```python
elif command_type == "vulcan-brownout/get_filter_options":
    await self._handle_get_filter_options(ws, command)
```

```python
async def _handle_get_filter_options(self, ws, command):
    """Handle vulcan-brownout/get_filter_options command."""
    msg_id = command.get("id")

    manufacturers = sorted(list({
        e["manufacturer"]
        for e in self.entity_data.values()
        if e.get("manufacturer")
    }))

    areas_set = sorted(list({
        e["area"]
        for e in self.entity_data.values()
        if e.get("area")
    }))
    areas = [{"id": name.lower().replace(" ", "_"), "name": name} for name in areas_set]

    await ws.send_json({
        "type": "result",
        "id": msg_id,
        "success": True,
        "data": {
            "manufacturers": manufacturers[:20],
            "device_classes": ["battery"],
            "areas": areas[:20],
            "statuses": ["critical", "warning", "healthy", "unavailable"],
        },
    })
```

#### Add filter logic to `_handle_query_devices`

```python
async def _handle_query_devices(self, ws, command):
    msg_id = command.get("id")
    limit = min(command.get("limit", 50), 100)
    offset = command.get("offset", 0)

    # Sprint 5: Extract filter params
    filter_manufacturer = command.get("filter_manufacturer") or []
    filter_device_class = command.get("filter_device_class") or []
    filter_status = command.get("filter_status") or []
    filter_area = command.get("filter_area") or []

    # ... existing malformed_response check ...

    # Build device list
    devices = []
    for entity_id, entity in sorted(self.entity_data.items()):
        try:
            battery_level = float(entity.get("state", 0))
            available = entity.get("available", True)

            threshold = 15
            if battery_level < threshold:
                status = "critical"
            elif battery_level < (threshold + 10):
                status = "warning"
            else:
                status = "healthy"
            if not available:
                status = "unavailable"

            devices.append({
                "entity_id": entity_id,
                "state": str(battery_level),
                "battery_level": battery_level,
                "device_name": entity.get("friendly_name", entity_id),
                "available": available,
                "status": status,
                "manufacturer": entity.get("manufacturer"),   # Sprint 5
                "area": entity.get("area"),                   # Sprint 5
                "attributes": entity.get("attributes", {}),
                "last_changed": entity.get("last_changed"),
                "last_updated": entity.get("last_updated"),
            })
        except (ValueError, TypeError):
            continue

    # Sprint 5: Apply server-side filters (AND across categories, OR within)
    if filter_manufacturer:
        devices = [d for d in devices if d.get("manufacturer") in filter_manufacturer]
    if filter_device_class:
        devices = [d for d in devices
                   if d.get("attributes", {}).get("device_class") in filter_device_class]
    if filter_status:
        devices = [d for d in devices if d.get("status") in filter_status]
    if filter_area:
        devices = [d for d in devices if d.get("area") in filter_area]

    # Apply pagination
    total = len(devices)
    paginated = devices[offset: offset + limit]

    await ws.send_json({
        "type": "result",
        "id": msg_id,
        "success": True,
        "data": {
            "devices": paginated,
            "total": total,
            "offset": offset,
            "limit": limit,
            "has_more": (offset + limit) < total,
            "next_cursor": None,
            "device_statuses": self._calculate_statuses(devices),
        },
    })
```

---

## Implementation Order

### Phase 1: Backend (Story 5.1 + 5.2) — Days 1-4

1. Add constants to `const.py` (VERSION, COMMAND_GET_FILTER_OPTIONS, FILTER_KEY_*, MAX_FILTER_OPTIONS)
2. Add `area_registry` import to `battery_monitor.py`
3. Implement `_get_entity_manufacturer()` and `_get_entity_area_name()` helper methods
4. Implement `_apply_filters()` method
5. Update `query_devices()` signature and add `_apply_filters` call at correct position (before sort)
6. Implement `get_filter_options()` method
7. Update `websocket_api.py` imports and `register_websocket_commands()`
8. Update `handle_query_devices` voluptuous schema with filter params
9. Update `handle_query_devices` handler body to extract and pass filter params
10. Implement `handle_get_filter_options` handler
11. Update mock server: entity schema, `get_filter_options` handler, filter logic in `_handle_query_devices`
12. Run backend unit tests: filter logic (AND/OR, empty array, no-match cases)

### Phase 2: Frontend — Core (Story 5.3, Part A) — Days 3-7

13. Add new JS constants (`GET_FILTER_OPTIONS_COMMAND`, `FILTER_STORAGE_KEY`, etc.)
14. Add new reactive properties to `static properties`
15. Initialize new state in constructor
16. Implement localStorage read/write methods
17. Implement `_load_filter_options()` with fetch guard
18. Implement filter management methods (`_toggle_filter_value`, `_remove_filter_chip`, etc.)
19. Update `_load_devices()` to include filter params in query
20. Update `connectedCallback()` to call `_load_filter_options()` and add listeners
21. Update `disconnectedCallback()` to clean up listeners

### Phase 3: Frontend — UI Components (Story 5.3, Part B) — Days 5-9

22. Implement `_render_chip_row()` method
23. Implement `_render_desktop_filter_buttons()` method
24. Implement `_render_filter_dropdown(category)` method (loading/error/ready states)
25. Implement mobile "Filter" button rendering
26. Implement `_render_mobile_filter_sheet()` method with accordion sections
27. Implement `_render_filtered_empty_state()` method (Wireframe 16)
28. Update `render()` to include filter bar and conditional chip row
29. Update empty state condition in `render()` to distinguish filtered vs. unfiltered
30. Add all new CSS to `static styles`
31. Add new CSS custom properties to `[data-theme="light"]` and `[data-theme="dark"]` in styles.css

### Phase 4: Integration Testing (Story 5.3, Part C) — Days 8-10

32. E2E test: Filter bar renders on desktop with four buttons
33. E2E test: Clicking filter button opens dropdown with correct options from `get_filter_options`
34. E2E test: Selecting manufacturer filter updates device list via `query_devices`
35. E2E test: AND logic (manufacturer + area combined filter)
36. E2E test: Chip [x] removes specific filter value
37. E2E test: "Clear all" removes all filters
38. E2E test: localStorage persistence (save, reload, verify restored)
39. E2E test: Mobile bottom sheet opens, changes are staged, Apply commits them
40. E2E test: Mobile bottom sheet [X] discards staged changes
41. E2E test: Filtered empty state shows correct copy and CTA when zero results

### Phase 5: Deployment (Story 5.4) — Days 11-14

42. Bump `manifest.json` version to 5.0.0
43. Bump `VERSION` in `const.py` to "5.0.0"
44. Run full E2E test suite: `npx playwright test`
45. Deploy to test HA server
46. Run health check
47. Smoke test (filter bar populates, filter selection works, chip removal works)
48. Re-run Sprint 4 regression tests

---

## Code Review Criteria

Before submitting for review, verify:

**Backend**:
- [ ] `_apply_filters` correctly implements AND-across-categories, OR-within-category
- [ ] Empty list for any filter param is treated as "no filter" (None normalization)
- [ ] `total` in `query_devices` response reflects filtered count (not entity count)
- [ ] `get_filter_options` excludes null/empty manufacturers and area names
- [ ] `get_filter_options` respects area lookup priority (entity area_id → device area_id)
- [ ] `filter_status` values are validated against SUPPORTED_STATUSES (invalid value returns error)
- [ ] Existing `query_devices` calls without filter params still work (backward compat)
- [ ] Mock server `_handle_get_filter_options` returns correct data from entity store
- [ ] Mock server `_handle_query_devices` applies filter params before pagination

**Frontend**:
- [ ] `_load_filter_options()` called once on `connectedCallback()`, result cached in `this.filter_options`
- [ ] `_filter_options_fetch_promise` guard prevents duplicate in-flight requests
- [ ] `active_filters` restored from localStorage before first `query_devices` call (no unfiltered flash)
- [ ] Cursor reset to null before every filter-triggered `query_devices` call
- [ ] Desktop filter: changes applied immediately on dropdown close (with 300ms debounce)
- [ ] Mobile bottom sheet: changes staged in `staged_filters`, not applied until "Apply Filters"
- [ ] Chip row conditionally rendered (not hidden) — removed from DOM when no active filters
- [ ] Chip row slides in/out (200ms animation) correctly
- [ ] Bottom sheet slides up/down (300ms animation) correctly
- [ ] Filtered empty state uses filter icon, correct copy, and "[Clear Filters]" CTA — distinct from Wireframe 6 state
- [ ] All filter UI elements meet 44px touch target minimum
- [ ] WCAG AA contrast on chips, dropdown items, trigger buttons in both light and dark themes
- [ ] Keyboard accessibility: Tab through filter triggers, Enter/Space opens dropdown, Escape closes, arrow keys navigate options
- [ ] ARIA attributes: dropdown trigger has `aria-expanded`, `aria-haspopup`; chip row has `aria-label="Active filters"`; bottom sheet has `role="dialog"`, `aria-modal="true"`
- [ ] Chip [x] buttons have descriptive `aria-label` (not just "x")
- [ ] No console errors or warnings

---

## Known Risks and Mitigations

### Risk 1: Area Lookup Performance
**Issue**: `_get_entity_area_name()` and `_get_entity_manufacturer()` call HA registries for each entity during `_apply_filters`. With 200 entities and an active area filter, this is 200 registry lookups per `query_devices` call.

**Mitigation**: HA's `entity_registry`, `device_registry`, and `area_registry` helpers use in-memory dictionaries with O(1) lookup by ID. 200 lookups is negligible (<1ms). No caching needed at this stage. If profiling shows this as a bottleneck in Sprint 6+ (500+ devices), we can cache manufacturer/area info in BatteryEntity at discovery time.

### Risk 2: Stale Filter Options
**Issue**: `get_filter_options` is cached client-side for the session. If a user adds a new device or area to HA during the session, the filter dropdown won't show it.

**Mitigation**: Accepted trade-off (documented in ADR-015 and interactions.md). Panel reload fetches fresh options. Panel does not auto-refresh filter options because real-time registry monitoring is out of scope for Sprint 5.

### Risk 3: localStorage Filter Values No Longer Valid
**Issue**: A persisted filter value (e.g., a room that was deleted from HA) may be restored from localStorage and no longer appear in `get_filter_options` response.

**Mitigation**: After `get_filter_options` response is received, validate `active_filters` against the response and silently drop invalid values (Step 8 above). The cleanup is silent (no user-visible error).

### Risk 4: Cursor from Pre-Filter Pagination Used After Filter Change
**Issue**: If the frontend fails to reset cursor to null before a filter-triggered `query_devices`, the response may contain items from the wrong page of a different result set.

**Mitigation**: `_on_filter_changed()` always sets `this.current_cursor = null` before calling `_load_devices()`. This is centralized in a single method, not scattered across chip removal, clear all, and apply functions. Review all paths to confirm all filter changes go through `_on_filter_changed()`.

### Risk 5: Mobile Bottom Sheet Overlay Blocking Accessibility
**Issue**: The semi-transparent overlay blocks keyboard and screen reader users from reaching content behind the sheet.

**Mitigation**: `role="dialog"` and `aria-modal="true"` on the sheet element instructs assistive technology to confine Tab navigation to the sheet content. Focus must be moved to the sheet's first interactive element on open, and returned to the "Filter" button on close.

### Risk 6: Filter Dropdown Positioning Overflow
**Issue**: If a filter trigger button is near the right or bottom edge of the viewport, the dropdown may render off-screen.

**Mitigation**: Implement viewport overflow detection in the dropdown render method (see Wireframe 13 Dropdown Positioning Rules). If right edge of dropdown exceeds viewport width, align dropdown to right edge of trigger (right-anchored). If bottom edge exceeds viewport height, open upward. Use `getBoundingClientRect()` after dropdown renders to detect and reposition.

---

## Testing Expectations

### Backend Unit Tests

Write/update tests in `quality/scripts/test_component_integration.py`:

- `test_query_devices_filter_manufacturer`: Filter by single manufacturer, verify only matching devices returned
- `test_query_devices_filter_manufacturer_multi`: Filter by two manufacturers (OR logic), verify both included
- `test_query_devices_filter_and_logic`: Filter by manufacturer AND status, verify AND behavior
- `test_query_devices_filter_empty_array`: Empty array is same as no filter (all returned)
- `test_query_devices_filter_no_match`: Filter that matches nothing returns empty list, total=0, has_more=false
- `test_query_devices_filter_total_is_filtered_count`: total reflects filtered count, not entity count
- `test_get_filter_options_manufacturers`: Returns manufacturers from battery entity devices
- `test_get_filter_options_areas`: Returns only areas with battery entities
- `test_get_filter_options_null_excluded`: Null/empty manufacturer names excluded from response
- `test_get_filter_options_max_20`: More than 20 values are truncated to 20

### E2E Tests (Playwright)

Write in `quality/e2e/`:

- `filter-bar.spec.ts`: Filter bar renders, four buttons visible on desktop, single button on mobile
- `filter-options.spec.ts`: Options populated from mock `get_filter_options` response
- `filter-select.spec.ts`: Select filter, verify device list updates, chip appears
- `filter-and-logic.spec.ts`: Two categories active, verify AND logic
- `filter-or-logic.spec.ts`: Two values in one category, verify OR logic
- `filter-chip-remove.spec.ts`: Chip [x] removes specific value, list updates
- `filter-clear-all.spec.ts`: "Clear all" removes all filters, list updates
- `filter-persistence.spec.ts`: Select filter, reload panel, verify restored from localStorage
- `filter-mobile-sheet.spec.ts`: Mobile viewport, open sheet, apply filters, verify list updates
- `filter-mobile-discard.spec.ts`: Mobile sheet [X], verify no changes applied
- `filter-empty-state.spec.ts`: Filter that matches nothing shows Wireframe 16 empty state (not Wireframe 6)

---

## References

- **ADR-015**: `architecture/adrs/ADR-015-server-side-filtering.md` — Core decision record
- **System Design**: `architecture/system-design.md` Sprint 5 section — data flows, method signatures, mock server changes
- **API Contracts**: `architecture/api-contracts.md` v5.0.0 — full schema, filter behavior reference
- **Sprint Plan**: `architecture/sprint-plan.md` — 4 stories with acceptance criteria
- **Design Brief**: `design/product-design-brief.md` Sprint 5 section — product decisions, UX constraints
- **Wireframes**: `design/wireframes.md` Wireframes 12-16 — filter bar, dropdown, chips, mobile sheet, filtered empty state
- **Interactions**: `design/interactions.md` Interactions 11-13 — filter selection, chip management, dynamic population

---

**Good luck. The filtering architecture is solid — server-side with AND/OR semantics, backward-compatible schema, localStorage persistence, and properly staged mobile UX. Ship it clean. — FiremanDecko**
