# Sprint 6: Tabbed UI — QA Handoff

**To**: Loki (QA Lead)
**From**: FiremanDecko (Principal Engineer)
**Date**: 2026-02-23
**Status**: Ready for validation

---

## Overview

Sprint 6 adds a tabbed UI to the Vulcan Brownout panel. The existing Low Battery view
becomes one tab; a new Unavailable Devices tab shows battery entities whose state is
`"unavailable"` or `"unknown"`. The unavailable tab is lazy-loaded (not fetched at
startup) and is a point-in-time snapshot (not updated by real-time events).

All code is complete and all 15 component tests pass. No new dependencies.

---

## Files Changed

### Backend (Python)
- `development/src/custom_components/vulcan_brownout/const.py`
  - Added `COMMAND_QUERY_UNAVAILABLE = "vulcan-brownout/query_unavailable"`
- `development/src/custom_components/vulcan_brownout/battery_monitor.py`
  - Added `get_unavailable_entities()` method — queries entity registry directly,
    returns `device_class=battery` entities in unavailable/unknown state,
    sorted by `last_changed` descending
- `development/src/custom_components/vulcan_brownout/websocket_api.py`
  - Added `handle_query_unavailable` handler
  - `register_websocket_commands()` now registers 3 commands (was 2)
- `.github/docker/mock_ha/server.py`
  - Added `_handle_query_unavailable()` mock handler

### Frontend (JavaScript)
- `development/src/custom_components/vulcan_brownout/frontend/vulcan-brownout-panel.js`
  - New reactive properties: `_activeTab`, `_unavailableEntities`, `_unavailableTotal`,
    `_unavailableLoading`, `_unavailableError`
  - Tab bar rendered below header with `role="tablist"` ARIA
  - `_switchTab()` persists active tab to `sessionStorage`
  - `_load_unavailable()` lazy-fetches unavailable entities on first tab visit
  - `_renderLowBatteryPanel()` and `_renderUnavailablePanel()` replace monolithic `render()`
  - Keyboard navigation: ArrowLeft/ArrowRight between tabs
  - Added CSS for `.tab-bar`, `.tab`, `.tab.active`, `.status-badge`

### Test Suite
- `quality/scripts/test_component_integration.py`
  - Added `TestQueryUnavailable` class with 6 new tests

### Architecture / Docs
- `architecture/api-contracts.md` — added `query_unavailable` spec (Sprint 6 section)
- `development/qa-handoff.md` — this document
- `development/implementation-plan.md` — Sprint 6 section

---

## Test Scenarios

### Component Tests (Python/pytest)

#### Scenario 1: query_unavailable returns success
**Test**: `test_query_unavailable_basic`
- Action: Send `vulcan-brownout/query_unavailable`
- Expected: `type=result`, `success=true`, response has `entities` (list) and `total` (int)

#### Scenario 2: entity structure is correct
**Test**: `test_query_unavailable_entity_structure`
- Expected: Each entity has `entity_id`, `state`, `device_name`, `last_changed`,
  `last_updated`, and `battery_level == null`

#### Scenario 3: returns only unavailable/unknown entities
**Test**: `test_query_unavailable_returns_unavailable_entities`
- Precondition: 10-entity fixture with 2 unavailable entities
- Expected: All returned entities have `state` in `("unavailable", "unknown")`

#### Scenario 4: excludes binary sensors
**Test**: `test_query_unavailable_excludes_binary_sensors`
- Expected: No `entity_id` starts with `"binary_sensor."`

#### Scenario 5: battery_level is null (not numeric)
**Test**: `test_query_unavailable_no_numeric_entities`
- Expected: `battery_level` is `null` for every returned entity

#### Scenario 6: empty result when all entities are available
**Test**: `test_query_unavailable_empty_when_all_available`
- Precondition: Single entity with `available=True` and numeric state
- Expected: `total=0`, `entities=[]`

---

### E2E / Manual Tests (browser)

#### Scenario A: Tab bar renders
- Open panel
- Two tabs visible: "Low Battery" (active by default) and "Unavailable Devices"
- Tab bar is below the header, flush left, with a bottom border

#### Scenario B: Low Battery tab unchanged
- Low Battery tab shows existing table with columns: Last Seen, Entity Name, Area,
  Manufacturer & Model, % Remaining
- Empty state shows battery icon and "All batteries above 15%"
- Real-time updates continue to work

#### Scenario C: Unavailable Devices tab loads lazily
- On initial panel load: `query_unavailable` is NOT called
- Click "Unavailable Devices" tab — `query_unavailable` IS called once
- Click back to "Low Battery", then back to "Unavailable Devices" — NOT called again
  (cached result shown)

#### Scenario D: Unavailable tab content
- Table columns: Last Seen, Entity Name, Area, Manufacturer & Model, Status
- "Status" column shows grey pill badge (`unavailable` or `unknown`)
- No "% Remaining" column on this tab

#### Scenario E: Unavailable empty state
- When no entities are unavailable:
  - Icon: checkmark (✅)
  - Text: "No unavailable devices. All monitored devices are responding."
  - No "Refresh" button (snapshot tab)

#### Scenario F: Session storage persistence
- Open panel — Low Battery tab active
- Switch to Unavailable Devices tab
- Close and reopen panel (same session / same tab / F5)
- Panel opens to Unavailable Devices tab (restored from sessionStorage)

#### Scenario G: Tab keyboard navigation
- Focus a tab with keyboard
- ArrowRight moves focus and activates the next tab
- ArrowLeft moves focus and activates the previous tab

#### Scenario H: ARIA semantics
- Tab bar has `role="tablist"`
- Each tab has `role="tab"`, `aria-selected="true/false"`, `aria-controls="panel-{tab}"`,
  `id="tab-{tab}"`
- Each panel has `role="tabpanel"`, `aria-labelledby="tab-{tab}"`, `id="panel-{tab}"`

---

## Acceptance Criteria

### Functionality
- [ ] `query_unavailable` WebSocket command registered and responding
- [ ] `battery_level` is `null` in unavailable response
- [ ] State values are `"unavailable"` or `"unknown"` only
- [ ] Binary sensors excluded from unavailable results
- [ ] Sorted by `last_changed` descending
- [ ] Lazy-load: unavailable tab not fetched at startup
- [ ] Result cached: unavailable not re-fetched within session
- [ ] Low Battery tab unaffected — all existing behavior preserved
- [ ] Real-time `entity_changed` events update Low Battery tab only

### Frontend UI/UX
- [ ] Tab bar renders below header
- [ ] Active tab has blue bottom border and bold text
- [ ] Inactive tab text is secondary color, no underline border
- [ ] Hover on inactive tab changes to primary text color
- [ ] Tab switch is instant (no animation)
- [ ] Unavailable tab shows "Status" column in 5th position
- [ ] Status values shown as grey pill badge
- [ ] Low Battery empty state: battery icon + "All batteries above 15%"
- [ ] Unavailable empty state: checkmark icon + "No unavailable devices..." message

### Accessibility
- [ ] `role="tablist"` on tab bar
- [ ] `role="tab"`, `aria-selected`, `aria-controls` on each tab button
- [ ] `role="tabpanel"`, `aria-labelledby` on each panel
- [ ] Keyboard: ArrowLeft/ArrowRight navigates between tabs
- [ ] Enter/Space on focused tab activates it
- [ ] `focus-visible` outline on tabs when keyboard-focused

### Session Persistence
- [ ] Active tab saved to `sessionStorage.getItem("vulcan_brownout_active_tab")`
- [ ] Tab restored from sessionStorage in `connectedCallback()`
- [ ] Only valid tab values (`"low-battery"`, `"unavailable"`) are restored

---

## Known Limitations (Expected Behavior)

1. **Point-in-time snapshot**: Unavailable tab data is fetched once per session visit.
   If a device comes back online or goes unavailable after loading, the tab does not
   update until the user navigates away and returns.

2. **No retry button on unavailable tab**: If `query_unavailable` fails, the error
   message is shown. The user must switch away and back to retry (which re-triggers
   fetch since `_unavailableEntities` stays `null` on error).

3. **Binary sensors excluded by design**: Devices with `binary_sensor.*` entity IDs are
   never shown, even if their state is unavailable. This matches the Low Battery tab
   behavior.

---

## How to Run Tests

### Component Tests (Docker)
```bash
./quality/scripts/run-all-tests.sh --component
```

### Lint
```bash
./quality/scripts/run-all-tests.sh --lint
```

### All Stages
```bash
./quality/scripts/run-all-tests.sh
```

---

## Sign-Off

QA lead will validate and sign off on:
- All 15 component tests pass
- All E2E/manual scenarios above verified
- No regressions to Low Battery tab or subscription behavior
- ARIA semantics verified with browser devtools or screen reader
- Session storage persistence confirmed across page reload

Then proceed to **Stage 4: VALIDATE** in team workflow.

---

**Ready for QA validation. All 15 component tests pass (9 original + 6 new).**
