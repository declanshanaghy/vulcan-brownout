# Sprint 5: Simple Filtering — Implementation Plan

**Status**: Completed
**Date**: 2026-02-22
**Developer**: ArsonWells (Lead)

---

## Executive Summary

Sprint 5 implements server-side filtering of battery devices by manufacturer, device class, status, and room/area. This document summarizes what was implemented, file-by-file.

The implementation follows ADR-015 (Server-Side Filtering Architecture) and the delegation brief provided by FiremanDecko (Architect).

---

## Backend Implementation (Python)

### 1. `const.py` — New Filter Constants

**Added**:
- `COMMAND_GET_FILTER_OPTIONS = "vulcan-brownout/get_filter_options"` — New WebSocket command
- Filter key constants: `FILTER_KEY_MANUFACTURER`, `FILTER_KEY_DEVICE_CLASS`, `FILTER_KEY_STATUS`, `FILTER_KEY_AREA`
- `SUPPORTED_FILTER_KEYS` list
- `MAX_FILTER_OPTIONS = 20` — Maximum values per category
- `VERSION = "5.0.0"` — Bumped from 3.0.0

---

### 2. `battery_monitor.py` — Filter Methods

**Imports Added**: `area_registry as ar`

**New Private Methods**:
1. `_get_entity_manufacturer(entity_id)` — Lookup manufacturer from device_registry
2. `_get_entity_area_name(entity_id)` — Lookup area with priority: entity area_id → device area_id
3. `_apply_filters(devices, filter_manufacturer, filter_device_class, filter_status, filter_area)` — AND-across-categories, OR-within-category logic
4. `async get_filter_options()` — Return available filter values from tracked entities

**Updated Methods**:
- `query_devices()` signature expanded with filter params
- Filters applied BEFORE sort and pagination
- `total` reflects filtered count

---

### 3. `websocket_api.py` — Filter Support

**Imports Updated**: Added `COMMAND_GET_FILTER_OPTIONS`, `SUPPORTED_STATUSES`

**`handle_query_devices` Updates**:
- Schema accepts optional filter params
- `filter_status` validated against SUPPORTED_STATUSES
- Params normalized (empty [] → None)
- Passed to `battery_monitor.query_devices()`

**New Handler**: `handle_get_filter_options()`
- Returns result from `battery_monitor.get_filter_options()`
- No parameters required

---

### 4. `manifest.json`
- Version bumped to `5.0.0`

---

### 5. `.github/docker/mock_ha/server.py` — Filter Support

**Mock Entity Data**: Added `manufacturer` and `area` fields

**Updates**:
- Added `get_filter_options` command handler
- `_handle_query_devices()` applies filters before pagination
- `_mock_control` accepts manufacturer/area in entity data

---

## Frontend Implementation (JavaScript)

### `vulcan-brownout-panel.js` — Complete Filter UI

**Constants Added**:
- Filter category labels and storage key
- Mobile breakpoint threshold

**Reactive Properties Added** (7 new):
- `active_filters` — Current applied filters
- `staged_filters` — Mobile sheet staging copy
- `filter_options` — Cached response
- `filter_options_loading`, `filter_options_error`
- `show_filter_dropdown`, `show_mobile_filter_sheet`

**Filter Management** (10 new methods):
- localStorage persistence: `_load_filters_from_localstorage()`, `_save_filters_to_localstorage()`
- Filter changes: `_on_filter_changed()`, `_remove_filter_chip()`, `_clear_all_filters()`
- Desktop: `_toggle_filter_value()`, `_open/close_filter_dropdown()`
- Mobile: `_open_mobile_filter_sheet()`, `_apply/cancel_mobile_filters()`, `_toggle_staged_filter_value()`
- Data fetch: `_load_filter_options()`, `_retry_filter_options()`
- Helpers: `_has_active_filters()`, `_active_filter_count()`, `_is_filtered_empty_state()`

**Render Helpers** (5 new methods):
1. `_render_filter_bar()` — Desktop buttons or mobile single button
2. `_render_filter_dropdown(category)` — Checkbox list
3. `_render_chip_row()` — Active filter chips with remove buttons
4. `_render_mobile_filter_sheet()` — Bottom sheet UI
5. `_render_filtered_empty_state()` — No-results empty state

**CSS Added** (~150 lines):
- Filter bar, buttons, dropdowns
- Chip row and chips
- Mobile bottom sheet
- Animations (slideUp, chipRowIn)

**Lifecycle Updates**:
- Constructor loads filters from localStorage
- `connectedCallback()` fetches filter options and sets up listeners
- `disconnectedCallback()` cleans up listeners

**Device Query Updates**:
- `_load_devices()` and `_load_next_page()` include filter params

---

## Backward Compatibility

✓ Fully backward compatible
- All filter params optional
- Existing calls work unchanged
- Old clients don't call `get_filter_options`

---

## Files Modified

### Backend
- `const.py` — +19 lines
- `battery_monitor.py` — +217 lines
- `websocket_api.py` — +38 lines
- `manifest.json` — 1 line
- `.github/docker/mock_ha/server.py` — +72 lines

### Frontend
- `vulcan-brownout-panel.js` — +500+ lines

---

## Validation

All code compiles successfully:
- Python: `py_compile` check passed
- JavaScript: `node -c` syntax check passed
- No new dependencies

---

**End of Implementation Plan**
