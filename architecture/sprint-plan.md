# Sprint 5 Plan

**Status**: Ready for implementation | **Duration**: 2 weeks | **Capacity**: 5 stories

---

## Story 5.1: Server-Side Filtering Backend

- **As a**: HA user with 50+ battery devices across multiple manufacturers and rooms
- **I want**: The `query_devices` WebSocket command to accept filter parameters for manufacturer, device class, status, and area
- **So that**: The panel only returns devices matching my filters, including across all pagination pages — not just the devices loaded on the current page

**Acceptance Criteria**:
- `query_devices` accepts optional `filter_manufacturer`, `filter_device_class`, `filter_status`, `filter_area` params (all are `string[]`)
- Empty array for any filter param is treated identically to omitting that param (no filter on that category)
- AND logic applied across categories: device must match all non-empty filter categories
- OR logic applied within each category: device matches if it matches any value in the category's filter list
- Filter applied before sort and before pagination; `total` in response reflects filtered count
- `filter_status` values are validated against `["critical","warning","healthy","unavailable"]`; invalid values return `invalid_filter_status` error
- Existing `query_devices` calls without filter params continue to work unchanged (backward compatible)
- `get_filter_options` command returns manufacturers from device_registry, areas from area_registry (filtered to areas with battery entities), device_classes from entity attributes, and fixed status list
- `get_filter_options` excludes manufacturers and areas with null/empty names
- Maximum 20 values per filter category in `get_filter_options` response (truncate if more exist)

**Technical Notes**:
- Add `COMMAND_GET_FILTER_OPTIONS`, `FILTER_KEY_*` constants, `MAX_FILTER_OPTIONS = 20` to `const.py`
- Add `SUPPORTED_STATUSES` to `const.py` if not already present (it exists as of Sprint 3)
- Add `_apply_filters(devices, filters)`, `_get_entity_manufacturer(entity_id)`, `_get_entity_area_name(entity_id)`, `async get_filter_options()` methods to `BatteryMonitor` in `battery_monitor.py`
- Update `query_devices()` signature in `battery_monitor.py` to accept `filter_manufacturer`, `filter_device_class`, `filter_status`, `filter_area` (all `Optional[List[str]]`, default `None`)
- Update `handle_query_devices` voluptuous schema in `websocket_api.py` to accept optional filter list params; normalize empty lists to None before passing to battery_monitor
- Register `handle_get_filter_options` in `register_websocket_commands()` in `websocket_api.py`
- Update mock server `server.py`: add `_handle_get_filter_options()` handler, add filter logic to `_handle_query_devices()`, extend entity data schema to support `manufacturer` and `area` fields
- Reference: `system-design.md` "Sprint 5 New Features" section, `api-contracts.md`, ADR-015

**Estimated Complexity**: M

**UX Reference**: Product Design Brief Sprint 5 — "Server-side filtering is mandatory" (Handoff Notes)

---

## Story 5.2: Filter Options Discovery Command

- **As a**: HA user opening the Vulcan Brownout panel
- **I want**: The filter dropdowns to show only manufacturers, rooms, and device classes that actually exist in my Home Assistant installation
- **So that**: I never see irrelevant filter options (e.g., a "Philips Hue" option when I own no Hue devices)

**Acceptance Criteria**:
- `vulcan-brownout/get_filter_options` WebSocket command is available and responds within 300ms
- `manufacturers` in response contains only manufacturers of devices that have at least one tracked battery entity; null/empty manufacturers excluded
- `areas` in response contains only areas that have at least one tracked battery entity; area lookup tries entity's own area_id first, then device's area_id
- `areas` returns `{ id, name }` objects, sorted alphabetically by name; areas without a name excluded
- `device_classes` contains the deduplicated device_class attribute values of tracked battery entities
- `statuses` is always `["critical","warning","healthy","unavailable"]` regardless of current device states
- Maximum 20 values per category; additional values beyond 20 are truncated without error
- Command accessible to authenticated HA WebSocket clients (same auth as query_devices)
- Integration-not-loaded error returned if BatteryMonitor is not initialized

**Technical Notes**:
- Implemented in `handle_get_filter_options()` in `websocket_api.py`
- Uses `er.async_get(hass)`, `dr.async_get(hass)`, `area_registry.async_get(hass)` — all synchronous HA helper getups
- Iterates only `battery_monitor.entities` (already-filtered set) to avoid returning options for non-battery devices
- Area lookup order: `entity_entry.area_id` → `device.area_id` (entity-level area takes precedence over device-level)
- No caching server-side; options computed fresh on each request (client caches for session)
- Mock server must implement this handler for E2E tests to pass
- Reference: `system-design.md` "Filter Options Discovery Flow", `api-contracts.md` get_filter_options section, ADR-015 "get_filter_options Data Collection"

**Estimated Complexity**: S

**UX Reference**: Product Design Brief Sprint 5 Q7 (Dynamic Filter Population), Interaction 13 (Dynamic Filter Population), Wireframe 13 (Filter Dropdown loading/error states)

---

## Story 5.3: Frontend Filter Bar UI

- **As a**: HA user managing battery devices across multiple rooms and manufacturers
- **I want**: A filter bar below the panel header with manufacturer, device class, status, and room dropdowns on desktop, and a "Filter" button opening a bottom sheet on mobile
- **So that**: I can narrow the device list to the specific subset I care about, with my filter selections persisted between panel sessions

**Acceptance Criteria**:

**Filter Bar (Desktop — >= 768px)**:
- Filter bar row (48px, `--vb-bg-secondary` background, 1px bottom border) renders below header on desktop
- Four filter trigger buttons: Manufacturer, Device Class, Status, Room — each 44px height minimum
- Each dropdown trigger shows active selection count in label when selections exist (e.g., "Room (2)")
- Active trigger buttons display `--vb-filter-active-bg` fill and `--vb-filter-active-text` text
- Each dropdown opens a positioned custom `<div>` panel (not a native `<select>`) below its trigger on click
- Dropdown contains a scrollable checkbox list (max-height 300px) with multi-select support
- Dropdown values populated from `get_filter_options` response cached in `this._filter_options`
- Dropdown shows loading state while `get_filter_options` is pending
- Dropdown shows error state with [Retry] button if `get_filter_options` failed
- Dropdown shows "No options available" and disables trigger if category has zero options
- Dropdown closes on outside click or Escape key; focus returns to trigger button on close
- Filter changes apply immediately on dropdown close (no "Apply" button on desktop)
- Cursor resets to null before every filter-triggered `query_devices` call
- Filter bar is hidden when no battery devices exist at all (Wireframe 6 empty state)

**Filter Bar (Mobile — < 768px)**:
- Mobile filter bar shows sort dropdown + single "Filter" button (no individual category dropdowns)
- "Filter" button shows badge count of total active filter values (e.g., "Filter (3)")
- "Filter" button has `--vb-filter-active-bg` styling when any filter is active
- Tapping "Filter" opens a bottom sheet (slides up from bottom, 300ms ease-out)
- Bottom sheet: sticky header with "Filters" title, "[Clear All]" link, "[X]" close button
- Bottom sheet body: four accordion sections (Manufacturer, Device Class, Status, Room), each with checkbox list (44px per row)
- Bottom sheet sticky footer: "[Apply Filters]" primary button (48px height, full width)
- Changes inside bottom sheet are staged in `staged_filters`, not applied until "Apply Filters" is tapped
- "[X]" button or outside-tap dismisses sheet, discards staged changes, no API call
- "Clear All" in sheet header clears staged selections only (not yet committed to active filters)
- Active filter count badge on "Filter" button reflects committed (applied) filters, not staged
- Bottom sheet `role="dialog"`, `aria-modal="true"`, `aria-label="Filter options"`

**Filter Chip Row**:
- Chip row is a separate conditionally-rendered DOM row (not hidden, removed from DOM when empty)
- Chip row renders below filter bar row when at least one filter value is active
- Chip row slides in (200ms ease-out, max-height animation) when first filter applied
- Chip row slides out (200ms ease-in) when last filter cleared
- Each active filter value rendered as a chip: `[Category: Value  x]` (32px height, pill shape)
- Chip category prefix shows category name: "Manufacturer: Aqara", "Room: Kitchen", etc.
- Chip [x] button removes that specific filter value; updates active_filters, resets cursor, calls query_devices
- "[Clear all]" text link at end of chip row removes all filters simultaneously
- Chip row scrolls horizontally (overflow-x: auto) when chips overflow viewport; no wrapping
- Chip [x] `aria-label`: `"Remove [Category]: [Value] filter"` (not just "x")
- Chip row container: `aria-label="Active filters"`, `role="group"`

**Filter Persistence**:
- Filter state saved to localStorage key `vulcan_brownout_filters` on every filter change
- Filter state restored from localStorage in `connectedCallback()` before first `query_devices` call
- No unfiltered flash: restored filters included in very first `query_devices` call
- Persisted filter values that no longer appear in `get_filter_options` response are silently dropped

**Empty State (Filtered)**:
- When `query_devices` returns `total: 0` AND at least one filter is active: show filtered empty state (Wireframe 16)
- Filtered empty state: filter/funnel icon (48px, `--vb-text-secondary`), title "No devices match your filters.", subtitle with suggestion, single "[Clear Filters]" CTA button
- "[Clear Filters]" button clears all filters (identical to chip row "Clear all")
- Filtered empty state is visually and contextually distinct from no-devices empty state (Wireframe 6)
- Filter bar and chip row remain visible in filtered empty state (so user can see what filters are active)

**New CSS custom properties** (in both `[data-theme="light"]` and `[data-theme="dark"]`):
- `--vb-bg-secondary`, `--vb-filter-chip-bg`, `--vb-filter-chip-text`, `--vb-filter-chip-border`
- `--vb-filter-active-bg`, `--vb-filter-active-text`, `--vb-overlay-bg`

**Technical Notes**:
- Add `GET_FILTER_OPTIONS_COMMAND = "vulcan-brownout/get_filter_options"` constant to frontend JS
- Add reactive properties: `active_filters`, `staged_filters`, `filter_options`, `filter_options_loading`, `filter_options_error`, `show_filter_dropdown`, `show_mobile_filter_sheet`, `is_mobile`
- Call `_load_filter_options()` in `connectedCallback()` in parallel with first `query_devices`
- Use `_filter_options_fetch_promise` guard to prevent duplicate in-flight calls
- Restore `active_filters` from localStorage in `connectedCallback()` before first `query_devices`
- Debounce desktop filter-triggered `query_devices` calls by 300ms (avoid redundant calls from rapid dropdown open/close)
- Dropdown z-index: 100 (above device list, below modal overlays at 200+)
- Bottom sheet z-index: 201, overlay z-index: 200
- Chip ordering: Manufacturer → Device Class → Status → Room, within-category in selection order
- Reference: `system-design.md` "Frontend Changes (Sprint 5)", Wireframes 12-16, Interactions 11-13

**Estimated Complexity**: M

**UX Reference**: Wireframes 12-16 (filter bar, dropdown, chips, mobile sheet, filtered empty state), Interactions 11-13 (filter selection, chip management, dynamic population), Product Design Brief Sprint 5 Q1-Q7

---

## Story 5.4: Sprint 5 Deployment

- **As a**: The QA team and deployment manager
- **I want**: A safe, idempotent deployment of Sprint 5 to the test HA server with manifest version 5.0.0
- **So that**: All previous work (Sprint 1-4) remains stable while the new filtering feature is added and verified

**Acceptance Criteria**:
- `manifest.json` version bumped to 5.0.0 before deployment
- Deployment script deploys all changed files: `const.py`, `battery_monitor.py`, `websocket_api.py`, `vulcan-brownout-panel.js`, `manifest.json`
- Mock server (`server.py`) updated with Sprint 5 filter support and deployed to test environment
- HA service restarted after deployment
- Health check endpoint `/api/vulcan_brownout/health` returns 200 with `"version": "5.0.0"`
- Smoke test: Panel loads, filter dropdowns populate from `get_filter_options`, selecting a filter triggers a filtered `query_devices` call and updates device list
- All Sprint 4 tests continue to pass (no regressions)
- Rollback capability: Previous version (4.0.0) can be restored via symlink strategy if issues detected

**Technical Notes**:
- Bump `VERSION = "5.0.0"` in `const.py`
- Update `manifest.json` version field to "5.0.0"
- Update deployment script to include `server.py` if not already included
- Run full E2E test suite post-deployment: `npx playwright test`
- Smoke test steps:
  1. Navigate to Battery Monitoring panel in HA
  2. Verify filter bar renders with four filter buttons (desktop)
  3. Click "Manufacturer" filter button, verify dropdown opens with options
  4. Select a manufacturer, verify chip appears and device list filters
  5. Click [x] on chip, verify filter cleared and full list restored
  6. On mobile viewport: tap "Filter" button, verify bottom sheet opens
  7. Select options in sheet, tap "Apply Filters", verify device list filters
  8. Reload panel, verify filter state restored from localStorage
- Reference: ADR-003 (deployment architecture), `architecture/sprint-plan.md` Story 4.5 (deployment pattern)

**Estimated Complexity**: S

**UX Reference**: N/A (infrastructure story)

---

## Dependencies & Recommended Order

1. **Story 5.1** (Server-Side Filtering Backend) — Core backend feature. Must be complete before frontend can be tested end-to-end. Start first.
2. **Story 5.2** (Filter Options Discovery) — Can be built in parallel with 5.1 (same backend sprint). Small story; deliver alongside 5.1.
3. **Story 5.3** (Frontend Filter Bar UI) — Can begin once 5.1 schema is stable (even if 5.1 not yet fully deployed, frontend can be built against the mock server). Start in parallel, blocks on 5.1+5.2 for integration testing.
4. **Story 5.4** (Deployment) — Final integration and deployment. Run after 5.1-5.3 complete and QA verified.

---

## Definition of Done (Per Story)

- [ ] Code changes implemented per specification in `system-design.md` and `api-contracts.md`
- [ ] Voluptuous schema updated and validated (backend stories)
- [ ] New constants added to `const.py` (backend stories)
- [ ] Backend unit tests pass (filter logic: AND/OR, empty array, no match cases)
- [ ] Playwright E2E tests pass (frontend stories: filter bar, chip row, mobile sheet, localStorage persistence)
- [ ] No console errors or warnings in browser DevTools
- [ ] Accessibility verified: all filter UI elements keyboard accessible, ARIA attributes correct, 44px touch targets
- [ ] WCAG AA contrast verified for filter chip text, dropdown labels, trigger button text in both light and dark themes
- [ ] Code reviewed by Architect (FiremanDecko)
- [ ] QA acceptance confirmed (Loki)

---

## Success Criteria for Sprint 5

- [ ] 4/4 stories implemented and QA-passed
- [ ] All Sprint 4 tests continue to pass (no regressions)
- [ ] Server-side filtering returns correct results (AND across categories, OR within category)
- [ ] Total count in response reflects filtered count (not unfiltered count)
- [ ] Filter options populated dynamically from HA device/area registries (no hardcoded lists)
- [ ] Filter state persisted to localStorage and restored on panel reload without unfiltered flash
- [ ] Cursor resets to null on every filter change before re-querying
- [ ] Mobile bottom sheet stages changes (no immediate API calls while selecting options)
- [ ] Filtered empty state is distinct from no-devices empty state
- [ ] Manifest version 5.0.0 deployed to test HA server
- [ ] No regressions from Sprint 1-4 features (theme detection, notifications, infinite scroll, back-to-top)

---

## Future Backlog (Sprint 6+)

- Filter presets: save named filter combinations ("Critical + Living Room", "IKEA devices")
- Battery degradation trend graphs (historical level tracking)
- Notification scheduling with quiet hours
- Bulk device operations (enable/disable notifications for all filtered devices)
- Multi-language internationalization
- CSV/JSON export of filtered device data
- Advanced sort within filtered results (sort by last_changed, manufacturer name)
- Device group view: collapsed/expanded sections per manufacturer or room
