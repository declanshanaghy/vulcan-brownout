# Sprint 6: Tabbed UI — Implementation Plan

> **⚠️ NOTE: This document describes Sprint 6 work that has been implemented but is NOT YET MERGED into the v6.0.0 codebase described in CLAUDE.md.**
> The features described here (tabbed UI, `query_unavailable` command) are in-flight and pending final validation. Current v6.0.0 remains: fixed 15% threshold, two WebSocket commands (`query_entities`, `subscribe`), no tabs.

**Status**: Completed (pending merge)
**Date**: 2026-02-23
**Developer**: FiremanDecko (Principal Engineer)

---

## Executive Summary

Sprint 6 adds a two-tab UI to the Vulcan Brownout panel:
- **Low Battery** (existing) — shows battery entities below 15%, real-time updates
- **Unavailable Devices** (new) — shows battery entities in unavailable/unknown state, lazy-loaded point-in-time snapshot

New backend command `vulcan-brownout/query_unavailable` serves the unavailable tab.
Frontend uses `sessionStorage` to remember the last active tab across page reloads.

---

## Backend Implementation (Python)

### 1. `const.py` — New Command Constant

**Added**:
- `COMMAND_QUERY_UNAVAILABLE: str = "vulcan-brownout/query_unavailable"`

---

### 2. `battery_monitor.py` — `get_unavailable_entities()` Method

**Added**: `async get_unavailable_entities() -> Dict[str, Any]`

- Queries the HA entity registry directly (does NOT use `self.entities` — that dict
  contains only numeric/valid entities)
- Filters to `device_class=battery` entities only
- Skips `binary_sensor.*` entity IDs
- Returns entities where `state.state in ("unavailable", "unknown")`
- Resolves device name, manufacturer, model, area via `_resolve_device_info()`
- Sets `battery_level = None` (not a number)
- Sorts by `last_changed` descending (most recently changed first)
- Returns `{"entities": [...], "total": N}`

No new class created — method returns dicts directly.

---

### 3. `websocket_api.py` — New Handler

**Added**: `handle_query_unavailable` decorated handler

- Registered via `@websocket_api.websocket_command({vol.Required("type"): COMMAND_QUERY_UNAVAILABLE})`
- Pattern identical to `handle_query_entities` — retrieves `BatteryMonitor` from `hass.data`,
  calls `await battery_monitor.get_unavailable_entities()`, sends result
- `register_websocket_commands()` updated to register 3 commands (was 2)

---

### 4. `.github/docker/mock_ha/server.py` — Mock Handler

**Added**: `_handle_query_unavailable()` method

- Iterates `entity_data`
- Skips `binary_sensor.*` entities
- Skips entities without `device_class: battery` in attributes
- Includes entities where `available=False` OR `state in ("unavailable", "unknown")`
- Sets `battery_level = None`
- Sorts by `last_changed` descending

---

## Frontend Implementation (JavaScript)

### `vulcan-brownout-panel.js` — Complete Rewrite with Tab UI

**Version**: bumped to v6.1.0 in file comment

**Constants Added**:
- `QUERY_UNAVAILABLE_COMMAND = "vulcan-brownout/query_unavailable"`
- `SESSION_STORAGE_KEY = "vulcan_brownout_active_tab"`
- `TAB_LOW_BATTERY = "low-battery"`
- `TAB_UNAVAILABLE = "unavailable"`

**Reactive Properties Added** (5 new):
- `_activeTab` — String, default `"low-battery"` (lazy-load guard via `null` for tab data)
- `_unavailableEntities` — Array or `null` (null = not yet fetched — lazy-load guard)
- `_unavailableTotal` — Number, default `0`
- `_unavailableLoading` — Boolean
- `_unavailableError` — String or null

**Lifecycle**:
- `connectedCallback()` reads `sessionStorage.getItem(SESSION_STORAGE_KEY)` before `_load_devices()`
  and sets `_activeTab` if valid value found
- `disconnectedCallback()` unchanged (reconnect timer and theme listener cleanup)

**Tab Management** (2 new methods):
- `_switchTab(tab)` — sets `_activeTab`, persists to sessionStorage, triggers lazy-load
  if switching to Unavailable tab and `_unavailableEntities === null`
- `_onTabKeydown(event)` — handles ArrowLeft/ArrowRight, Enter, Space keyboard events

**Data Methods** (1 new):
- `_load_unavailable()` — async, calls `query_unavailable`, populates `_unavailableEntities`;
  on error keeps `_unavailableEntities = null` so next visit retries

**Render Methods** (2 new):
- `_renderLowBatteryPanel()` — extracts existing Low Battery table; same empty state icon
  changed to battery icon for clarity
- `_renderUnavailablePanel()` — loading state, error state, empty state (checkmark + message),
  or table with Status column (grey pill badge) replacing % Remaining

**CSS Added** (~50 lines):
- `.tab-bar` — flex row, 40px height, border-bottom
- `.tab` — base tab button style (transparent border, secondary color)
- `.tab.active` — primary color + 2px solid border-bottom + bold
- `.tab:hover:not(.active)` — primary text color on hover
- `.tab:focus-visible` — 2px outline for keyboard navigation
- `.status-badge` — grey pill badge (rounded-12, grey border, secondary text)

---

## Test Suite

### `quality/scripts/test_component_integration.py`

**Added**: `TestQueryUnavailable` class with 6 tests:

1. `test_query_unavailable_basic` — verifies response shape
2. `test_query_unavailable_entity_structure` — verifies fields present and `battery_level=null`
3. `test_query_unavailable_returns_unavailable_entities` — verifies state values
4. `test_query_unavailable_excludes_binary_sensors` — verifies no `binary_sensor.*` ids
5. `test_query_unavailable_no_numeric_entities` — verifies `battery_level=null`
6. `test_query_unavailable_empty_when_all_available` — verifies empty list when no unavailable entities

**Total tests**: 15 (9 original + 6 new) — all passing.

---

## Files Modified

### Backend
- `const.py` — +1 line
- `battery_monitor.py` — +69 lines (`get_unavailable_entities` method)
- `websocket_api.py` — +48 lines (new handler + registration)

### Mock Server
- `.github/docker/mock_ha/server.py` — +47 lines (new mock handler + routing)

### Test Suite
- `quality/scripts/test_component_integration.py` — +82 lines (TestQueryUnavailable)

### Frontend
- `vulcan-brownout-panel.js` — full rewrite (484 → ~560 lines effective;
  same table logic, refactored into render methods + tab infrastructure)

### Docs
- `architecture/api-contracts.md` — added `query_unavailable` spec
- `development/qa-handoff.md` — Sprint 6 QA handoff
- `development/implementation-plan.md` — this document

---

## Design Decisions

- **Null vs empty array for lazy-load guard**: `_unavailableEntities = null` used as
  the sentinel value (not `[]`). An empty array means "loaded and empty"; null means
  "not yet fetched". This prevents re-fetching when the tab is empty.

- **No new dataclass for unavailable entities**: `get_unavailable_entities()` returns
  dicts directly. The unavailable entity shape is similar to `BatteryEntity.to_dict()`
  but with `battery_level=None` and no `status` field.

- **Point-in-time snapshot**: Real-time `entity_changed` events only re-fetch Low
  Battery data. Unavailable tab is not updated by events because unavailability is
  typically a network/device issue, not a rapid state-changing event.

- **sessionStorage (not localStorage)**: Tab preference is session-scoped. On fresh
  browser open, the panel defaults to Low Battery (most actionable view).

---

## Validation

All code passes:
- `flake8` (max-line-length=127, max-complexity=10) — clean
- `mypy` — no issues in 4 source files
- 15 component tests — all passing

---

**End of Implementation Plan**
