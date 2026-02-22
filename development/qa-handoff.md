# Sprint 5: Simple Filtering — QA Handoff

**To**: Loki (QA Lead)
**From**: ArsonWells (Lead Developer)
**Date**: 2026-02-22
**Status**: Ready for validation

---

## Overview

Sprint 5 implements server-side filtering by manufacturer, device class, status, and room/area. This document provides QA with test scenarios, focus areas, and acceptance criteria.

All code is complete and compiles successfully. No new dependencies.

---

## Files Changed

### Backend (Python)
- `development/src/custom_components/vulcan_brownout/const.py` — Filter constants, version bump
- `development/src/custom_components/vulcan_brownout/battery_monitor.py` — Filter methods, updated `query_devices`
- `development/src/custom_components/vulcan_brownout/websocket_api.py` — Filter handler, updated schema
- `development/src/custom_components/vulcan_brownout/manifest.json` — Version 5.0.0
- `.github/docker/mock_ha/server.py` — Filter support for E2E

### Frontend (JavaScript)
- `development/src/custom_components/vulcan_brownout/frontend/vulcan-brownout-panel.js` — Complete filter UI, storage, API integration

---

## Test Scenarios

### Component Tests (Python/pytest)

#### Scenario 1: Filter by Single Manufacturer
**Test**: `test_query_devices_filter_manufacturer`
- Precondition: 5 test entities, 2 Aqara, 2 Hue, 1 IKEA
- Action: Query with `filter_manufacturer=["Aqara"]`
- Expected: Only Aqara devices returned, total=2
- Check: `total` reflects filtered count

#### Scenario 2: Filter by Multiple Categories (AND Logic)
**Test**: `test_query_devices_filter_and_logic`
- Precondition: Devices with various manufacturers and statuses
- Action: Query with `filter_manufacturer=["Aqara"]` AND `filter_status=["critical"]`
- Expected: Only Aqara devices in critical status
- Check: AND logic enforced across categories

#### Scenario 3: Multiple Values in One Category (OR Logic)
**Test**: `test_query_devices_filter_or_logic`
- Precondition: Mixed manufacturers
- Action: Query with `filter_manufacturer=["Aqara", "Hue"]`
- Expected: Both Aqara AND Hue devices returned (not just one)
- Check: OR logic within category

#### Scenario 4: Empty Filter Array = No Filter
**Test**: `test_query_devices_filter_empty_array`
- Action: Query with `filter_manufacturer=[]`
- Expected: All devices returned (same as no filter)
- Check: Empty array normalized to None/no filter

#### Scenario 5: No Matching Devices
**Test**: `test_query_devices_filter_no_match`
- Action: Query with `filter_manufacturer=["NonExistent"]`
- Expected: Empty devices list, total=0, has_more=false
- Check: No error, just empty result

#### Scenario 6: get_filter_options Returns Correct Data
**Test**: `test_get_filter_options_manufacturers`
- Action: Call `get_filter_options()`
- Expected: manufacturers array contains only manufacturers from tracked entities
- Check: No null/empty values included

#### Scenario 7: get_filter_options Returns Only Areas with Battery Entities
**Test**: `test_get_filter_options_areas`
- Precondition: HA has 5 areas; only 3 have battery devices
- Action: Call `get_filter_options()`
- Expected: areas array has 3 entries only
- Check: Only areas with battery entities included

#### Scenario 8: Total Reflects Filtered Count (Not Entity Count)
**Test**: `test_query_devices_filter_total_is_filtered_count`
- Precondition: 100 total entities, 20 match filter
- Action: Query with filter, limit=10
- Expected: total=20, returned 10, has_more=true
- Check: total is filtered count, not entity count

#### Scenario 9: Backward Compatibility
**Test**: `test_query_devices_no_filters_unchanged`
- Action: Query without any filter params
- Expected: Full unfiltered result set (same as Sprint 4)
- Check: No breaking changes

---

### E2E Tests (Playwright)

#### Scenario A: Filter Bar Renders
**File**: `quality/e2e/filter-bar.spec.ts`
- Desktop: Four filter buttons visible (Manufacturer, Device Class, Status, Room)
- Mobile: Single "Filter" button visible

#### Scenario B: Dropdown Populates from API
**File**: `quality/e2e/filter-options.spec.ts`
- Click filter button
- Dropdown opens
- Options populated from mock `get_filter_options` response
- No hardcoded values

#### Scenario C: Single Filter Selection
**File**: `quality/e2e/filter-select.spec.ts`
- Select manufacturer filter
- Device list updates (via `query_devices` with filter param)
- Chip appears in chip row
- Chip shows correct value and category

#### Scenario D: AND Logic (Two Categories)
**File**: `quality/e2e/filter-and-logic.spec.ts`
- Select manufacturer filter (Aqara)
- Select status filter (critical)
- Device list shows only Aqara devices in critical status
- No Hue devices shown even if critical
- No Aqara devices in healthy status shown

#### Scenario E: OR Logic (Two Values in One Category)
**File**: `quality/e2e/filter-or-logic.spec.ts`
- Select manufacturer: Aqara
- Select manufacturer: Hue (without deselecting Aqara)
- Device list shows both Aqara AND Hue devices
- No IKEA devices shown

#### Scenario F: Remove Single Filter Chip
**File**: `quality/e2e/filter-chip-remove.spec.ts`
- Apply manufacturer filter
- Chip appears with [x] button
- Click [x]
- Chip removed, device list updates
- Other filters remain active

#### Scenario G: Clear All Filters
**File**: `quality/e2e/filter-clear-all.spec.ts`
- Apply multiple filters
- Click "Clear all" link
- All chips removed
- Device list updates to show all devices

#### Scenario H: Filter Persistence (localStorage)
**File**: `quality/e2e/filter-persistence.spec.ts`
- Select filters: Manufacturer=Aqara, Status=critical
- Reload page (F5)
- Filters restored automatically
- Chip row shows same filters
- Device list still filtered

#### Scenario I: Mobile Bottom Sheet Open/Apply
**File**: `quality/e2e/filter-mobile-sheet.spec.ts`
- Viewport width < 768px
- Click "Filter" button
- Bottom sheet slides up
- Check categories and options present
- Select filters: Manufacturer=Aqara, Area=Kitchen
- Click "Apply Filters"
- Sheet closes, chips appear, device list updates

#### Scenario J: Mobile Bottom Sheet Cancel
**File**: `quality/e2e/filter-mobile-discard.spec.ts`
- Open bottom sheet
- Select filters (staged)
- Click [X] or "Cancel"
- Sheet closes without applying
- Active filters unchanged
- Device list unchanged

#### Scenario K: Filtered Empty State
**File**: `quality/e2e/filter-empty-state.spec.ts`
- Apply filter with zero matches
- Empty state renders:
  - Icon: 🔍 (magnifying glass, not battery)
  - Text: "No devices match your filters"
  - CTA: "Clear Filters" button
  - NOT the "No battery entities found" message from Wireframe 6

#### Scenario L: Filter Options Load in Parallel
**File**: `quality/e2e/filter-loading-state.spec.ts`
- Device list loads
- Filter options load in parallel (not blocking device list)
- Both complete successfully

#### Scenario M: No Cache Staleness with Device Changes
**File**: `quality/e2e/filter-cache.spec.ts`
- Load panel, get filter options (cached)
- Add new device to HA (via mock control endpoint)
- New device not in filter dropdown (expected cache behavior)
- Reload panel
- New device appears in dropdown

---

## Acceptance Criteria

### Functionality
- [ ] All filter categories functional (manufacturer, device_class, status, area)
- [ ] AND-across-categories logic working
- [ ] OR-within-category logic working
- [ ] Filter changes reset cursor (pagination restart)
- [ ] `total` reflects filtered count
- [ ] Empty list handled gracefully
- [ ] `get_filter_options` returns correct data
- [ ] Backward compatibility maintained (no params works)

### Frontend UI/UX
- [ ] Desktop filter bar with category buttons
- [ ] Dropdown appears on button click
- [ ] Dropdown has loading/error/ready states
- [ ] Checkboxes toggle filter values
- [ ] Chip row appears when filters active
- [ ] Chip has [x] remove button (min 44px touch target)
- [ ] "Clear all" link appears in chip row
- [ ] Filtered empty state distinct from no-devices state
- [ ] Mobile breakpoint (768px) changes UI appropriately
- [ ] Mobile bottom sheet slides up from bottom
- [ ] Mobile sheet has Apply/Cancel buttons
- [ ] Filters persist across page reload

### Performance
- [ ] No noticeable lag on filter selection
- [ ] Desktop: 300ms debounce prevents excessive API calls
- [ ] Mobile: Changes staged (not instant API call per toggle)
- [ ] `get_filter_options` cached client-side (not refetched every load)

### Accessibility
- [ ] 44px minimum touch target on all buttons
- [ ] Keyboard navigation: Tab through buttons, Enter to toggle dropdown
- [ ] ARIA labels on buttons: "Filter options, N active"
- [ ] Dropdown: `role="listbox"`, options `role="option"`
- [ ] Chip row: `aria-label="Active filters"`
- [ ] Remove button: descriptive label (not just "x")
- [ ] Mobile sheet: `role="dialog"`, `aria-modal="true"`
- [ ] WCAG AA contrast in both light and dark themes

### Theming
- [ ] Dark mode colors applied correctly
- [ ] Light mode colors applied correctly
- [ ] All filter UI elements follow theme
- [ ] Transitions smooth (300ms)

---

## Known Limitations (Expected Behavior)

1. **Stale Filter Options**: Options cached for session. If user adds device/area to HA, dropdown won't show it until panel reload. Acceptable per architecture decision.

2. **Persisted Invalid Filters**: If a persisted filter value (e.g., deleted area) is no longer valid, it's silently removed when options load. No user-visible error. Acceptable per risk mitigation in brief.

3. **Cursor Reset on Filter Change**: Pagination always restarts (cursor = null) when filters change. This is correct behavior, not a bug. Same as when sort order changes.

---

## Focus Areas

1. **Filter Logic Correctness**: Highest priority. Verify AND/OR logic works as specified. Test edge cases (no matches, single value, many values).

2. **Filtering Performance**: Verify no lag or excessive API calls. Check debounce works on desktop (300ms).

3. **UI Responsiveness**: Check filter bar switches layout at 768px. Check touch targets are 44x44px minimum.

4. **localStorage Persistence**: Critical path. Filters must survive reload without losing data.

5. **Accessibility**: Keyboard navigation and screen reader support for all new UI.

6. **Backward Compatibility**: Verify old clients (without filter params) still work.

---

## How to Run Tests

### Component Tests
```bash
docker compose -f .github/docker-compose.yml up --build --abort-on-container-exit component_tests
```

### E2E Tests
```bash
cd quality/e2e
npm install && npx playwright install chromium
npx playwright test                  # all tests
npx playwright test filter*.spec.ts  # filter tests only
npx playwright test --headed         # with browser visible
npx playwright show-report           # view HTML report
```

### Linting
```bash
flake8 development/src/custom_components/vulcan_brownout/ --max-line-length=127
mypy development/src/custom_components/vulcan_brownout/ --ignore-missing-imports
```

---

## Sign-Off

QA lead will validate and sign off on:
- All test scenarios pass
- No regressions to Sprint 4 features
- Accessibility meets WCAG AA standard
- Performance acceptable
- Backward compatibility confirmed

Then proceed to **Stage 4: VALIDATE** in team workflow.

---

**Ready for QA validation. All code complete and tested locally.**
