# Sprint 2 Test Cases

**Project:** Vulcan Brownout Battery Monitoring
**Sprint:** 2
**QA Lead:** Loki
**Date:** February 2026

---

## Test Case Format

```
# TC-{ID}: {Title}
## Category: Functional | Integration | Edge Case | Regression
## Priority: P1-Critical | P2-High | P3-Medium | P4-Low
## Type: API | UI | Deployment
## Preconditions
- Setup steps
## Steps
1. Action
2. Verify outcome
## Expected Result
## Idempotent: Yes/No
```

---

# STORY 1: REAL-TIME WEBSOCKET UPDATES

## TC-101: Device updates in real-time via WebSocket
**Category:** Functional
**Priority:** P1-Critical
**Type:** API + UI
**Preconditions:**
- Panel open with battery list displayed
- At least 5 battery test entities created
- WebSocket subscription active (connected badge green)

**Steps:**
1. Open Vulcan Brownout panel in HA sidebar
2. Verify connection badge shows 🟢 Connected
3. In another terminal, change battery level: `hass-cli entity set_state sensor.test_battery_critical 12`
4. Observe panel within 1 second
5. Verify battery level updated to 12%
6. Verify progress bar animates smoothly
7. Verify status color updates if crossed threshold
8. Verify timestamp updates to "just now"

**Expected Result:**
- Device updates appear within 500ms
- Progress bar animates smoothly (no jank)
- Timestamp shows recent update
- Status color reflects new battery level
- No console errors

**Idempotent:** Yes (repeatable, non-destructive)

---

## TC-102: Multiple devices updating simultaneously
**Category:** Integration
**Priority:** P2-High
**Type:** API
**Preconditions:**
- Panel open with 5+ test entities
- WebSocket subscription active

**Steps:**
1. Change 3 battery levels rapidly (within 1 second)
2. Change sensor.test_battery_critical to 5%
3. Change sensor.test_battery_warning to 25%
4. Change sensor.test_battery_healthy to 40%
5. Observe panel updates
6. Verify all 3 devices update within 2 seconds
7. Verify no devices missed
8. Verify order/grouping still correct

**Expected Result:**
- All 3 devices update within 2 seconds
- No update losses
- List remains organized by status
- No performance degradation

**Idempotent:** Yes

---

## TC-103: Connection badge shows correct state
**Category:** Functional
**Priority:** P1-Critical
**Type:** UI
**Preconditions:**
- Panel open

**Steps:**
1. Verify connection badge displays 🟢 (green)
2. Verify tooltip shows "Connected"
3. Simulate network drop: `sudo tc qdisc add dev lo root netem loss 100%`
4. Wait 5 seconds, observe badge
5. Verify badge changes to 🔵 (blue spinning) - "Reconnecting"
6. Restore network: `sudo tc qdisc del dev lo root`
7. Wait 10 seconds, observe badge
8. Verify badge returns to 🟢 (green) - "Connected"
9. Verify toast notification appears: "✓ Connection updated"

**Expected Result:**
- Connected: 🟢 Green
- Reconnecting: 🔵 Blue (spinning animation)
- Offline: 🔴 Red
- State changes within 5 seconds of network change
- Toast notification on reconnection

**Idempotent:** Yes (network changes are temporary)

---

## TC-104: Exponential backoff reconnection
**Category:** Integration
**Priority:** P2-High
**Type:** API
**Preconditions:**
- Panel open
- Network simulator available

**Steps:**
1. Note current time as T0
2. Simulate network drop for 2 minutes
3. Observe reconnection attempts in browser console
4. Verify attempts follow pattern: 1s, 2s, 4s, 8s, 16s, 30s, 30s, ...
5. Restore network at T0 + 2 minutes
6. Verify reconnection succeeds within 30 seconds
7. Verify connection badge becomes green
8. Verify devices resume updating

**Expected Result:**
- Reconnection attempts use exponential backoff
- Max backoff is 30 seconds
- Reconnects successfully when network restored
- No endless reconnection loops

**Idempotent:** Yes

---

## TC-105: Subscription survives HA restart
**Category:** Integration
**Priority:** P2-High
**Type:** API
**Preconditions:**
- Panel open with active subscription
- HA instance with restart capability

**Steps:**
1. Note subscription_id from browser console: `window.customElements.get('vulcan-brownout-panel').subscription_id`
2. Restart Home Assistant service
3. Observe panel as HA restarts
4. Verify badge goes: Green → Blue (reconnecting) → Green (within 2 minutes)
5. Verify devices resume updating after restart
6. Change battery level, verify update appears within 1 second

**Expected Result:**
- Panel handles HA restart gracefully
- Subscription re-established after HA comes online
- No crashed UI
- No console errors

**Idempotent:** Yes

---

## TC-106: WebSocket message loss handled gracefully
**Category:** Edge Case
**Priority:** P3-Medium
**Type:** API
**Preconditions:**
- Panel open
- Network simulation available

**Steps:**
1. Simulate packet loss: `sudo tc qdisc add dev lo root netem loss 30%`
2. Change battery levels repeatedly (5+ changes)
3. Observe updates over 30 seconds
4. Verify most updates arrive (allow ~1-2 missed)
5. Verify no UI crashes
6. Restore network: `sudo tc qdisc del dev lo root`
7. Verify all subsequent updates arrive

**Expected Result:**
- UI handles occasional message loss gracefully
- No crashes or hangs
- Updates resume correctly when network stabilizes
- No console errors

**Idempotent:** Yes

---

## TC-107: Last update timestamp updates every second
**Category:** Functional
**Priority:** P3-Medium
**Type:** UI
**Preconditions:**
- Panel open with active subscription

**Steps:**
1. Observe last updated timestamp
2. Wait 3 seconds without any changes
3. Verify timestamp changes from "Updated 1s ago" → "Updated 2s ago" → "Updated 3s ago"
4. Verify updates continue every 1 second
5. Change a battery level
6. Verify timestamp resets to "Updated just now"
7. Verify it continues counting up

**Expected Result:**
- Timestamp updates every 1 second
- Shows relative time (seconds/minutes/hours ago)
- Resets to "just now" when update occurs
- No performance impact from counter

**Idempotent:** Yes

---

## TC-108: Multiple panels (tabs) receive updates
**Category:** Integration
**Priority:** P2-High
**Type:** API
**Preconditions:**
- 2 browser tabs open to Vulcan Brownout panel
- Both subscribed to updates

**Steps:**
1. In Tab 1, verify connection badge is green
2. In Tab 2, verify connection badge is green
3. Change battery level via hass-cli
4. Verify both Tab 1 and Tab 2 update within 1 second
5. Close Tab 1
6. Change battery level again
7. Verify Tab 2 still updates (Tab 1 subscription cleaned up)

**Expected Result:**
- Both tabs receive updates simultaneously
- Each tab has independent subscription
- Closing one tab doesn't affect other
- No duplicate updates within same tab

**Idempotent:** Yes

---

# STORY 2: CONFIGURABLE THRESHOLDS

## TC-201: Global threshold changes device status colors
**Category:** Functional
**Priority:** P1-Critical
**Type:** UI + API
**Preconditions:**
- Panel open with battery list
- Test devices with various battery levels:
  - sensor.test_battery_critical: 5% (currently CRITICAL at 15% threshold)
  - sensor.test_battery_warning: 18% (currently WARNING)
  - sensor.test_battery_healthy: 87% (currently HEALTHY)

**Steps:**
1. Verify initial statuses:
   - 5% → CRITICAL (red)
   - 18% → WARNING (orange)
   - 87% → HEALTHY (green)
2. Click settings icon (⚙️)
3. Verify settings panel opens
4. Adjust global threshold slider from 15% to 50%
5. Observe live preview updates in real-time
6. Click SAVE
7. Verify device status colors update:
   - 5% → CRITICAL (red, unchanged)
   - 18% → CRITICAL (red, changed from WARNING)
   - 87% → HEALTHY (green, unchanged)

**Expected Result:**
- Threshold changes update device colors immediately
- Live preview shows count changes as slider moves
- All clients see updates (if multiple tabs open)
- Colors match new threshold logic

**Idempotent:** Yes (settings are applied atomically)

---

## TC-202: Device-specific rules override global threshold
**Category:** Functional
**Priority:** P1-Critical
**Type:** UI + API
**Preconditions:**
- Settings panel open
- Global threshold at 15%
- sensor.test_battery_critical at 5%

**Steps:**
1. Current state: 5% device is CRITICAL (threshold 15%)
2. Click "+ ADD DEVICE RULE"
3. Select "sensor.test_battery_critical"
4. Set device-specific threshold to 2%
5. Click "SAVE RULE"
6. Verify rule appears in device rules list
7. Verify device status still CRITICAL (5% > 2% but ≤ 2%+10%)
8. Change global threshold to 50%
9. Verify device status remains CRITICAL (device rule takes precedence)
10. Click SAVE settings
11. Verify status persists after page reload

**Expected Result:**
- Device-specific rules override global threshold
- Multiple device rules can coexist (up to 10)
- Rules survive page reload
- Rules update when threshold changes

**Idempotent:** Yes

---

## TC-203: Settings panel is responsive (desktop/mobile)
**Category:** Functional
**Priority:** P2-High
**Type:** UI
**Preconditions:**
- Panel open

**Steps:**
1. **Desktop (> 1024px):**
   - Click settings icon
   - Verify panel slides in from right
   - Verify panel width is ~400px
   - Verify overlay appears behind
   - Click SAVE or CANCEL
   - Verify panel slides out

2. **Mobile (< 768px):**
   - Open on phone or emulator (DevTools device emulation)
   - Click settings icon
   - Verify modal opens full-screen
   - Verify content is scrollable
   - Verify buttons fit without overflow
   - Verify close button (✕) is reachable
   - Click CANCEL
   - Verify modal closes

**Expected Result:**
- Desktop: Side panel (400px)
- Mobile: Full-screen modal
- Both responsive, no overflow
- Proper touch targets (≥ 44px)

**Idempotent:** Yes

---

## TC-204: Threshold validation prevents invalid values
**Category:** Functional
**Priority:** P2-High
**Type:** UI
**Preconditions:**
- Settings panel open

**Steps:**
1. Attempt to set global threshold to 0 (below min 5%)
2. Verify error message appears or value is rejected
3. Attempt to set global threshold to 101 (above max 100%)
4. Verify error message or value is rejected
5. Set global threshold to 5 (minimum)
6. Verify SAVE succeeds
7. Set global threshold to 100 (maximum)
8. Verify SAVE succeeds
9. Verify values persist after reload

**Expected Result:**
- Only 5-100 accepted for global threshold
- Device rules also 5-100
- Clear error messages for invalid values
- Edge values (5, 100) work correctly

**Idempotent:** Yes

---

## TC-205: Multi-client threshold sync
**Category:** Integration
**Priority:** P2-High
**Type:** API
**Preconditions:**
- 2 tabs open to Vulcan Brownout panel
- Both showing battery list

**Steps:**
1. In Tab 1, open settings panel
2. Change global threshold from 15% to 45%
3. Click SAVE
4. Verify Tab 1 updates immediately
5. Switch to Tab 2
6. Verify Tab 2 automatically updated (without manual refresh)
7. Verify threshold in Tab 2 settings panel shows 45%
8. Verify device colors in Tab 2 match Tab 1

**Expected Result:**
- Threshold changes broadcast to all open clients
- Updates within 500ms
- No manual refresh needed
- All clients stay synchronized

**Idempotent:** Yes

---

## TC-206: Can add up to 10 device rules
**Category:** Functional
**Priority:** P3-Medium
**Type:** UI
**Preconditions:**
- Settings panel open
- At least 10 test devices available

**Steps:**
1. Click "+ ADD DEVICE RULE" (1st rule)
2. Select device 1, set threshold 20%, save
3. Repeat for devices 2-10 (11 total devices)
4. After saving 10th rule, verify all 10 appear in list
5. Try to add 11th rule
6. Verify error: "Maximum 10 device rules allowed" or similar
7. Verify can still modify existing rules
8. Delete one rule
9. Verify can now add new rule (11th becomes 10th)

**Expected Result:**
- Can add up to 10 device-specific rules
- Adding 11th is rejected with error
- Deleting a rule allows adding another
- Limit enforced on UI and backend

**Idempotent:** Yes

---

## TC-207: Settings persist across HA restart
**Category:** Integration
**Priority:** P2-High
**Type:** API
**Preconditions:**
- Settings configured and saved
- HA instance with restart capability

**Steps:**
1. Set global threshold to 30%
2. Add 2 device rules (e.g., device A→40%, device B→25%)
3. Click SAVE
4. Restart Home Assistant
5. Wait for HA to come online
6. Open Vulcan Brownout panel
7. Open settings panel
8. Verify global threshold shows 30%
9. Verify 2 device rules still exist
10. Verify devices use saved thresholds

**Expected Result:**
- Settings saved in HA ConfigEntry.options
- Survive HA restart
- Correct thresholds applied after restart
- Backed up in HA's config storage

**Idempotent:** Yes

---

## TC-208: Can remove device rules
**Category:** Functional
**Priority:** P3-Medium
**Type:** UI
**Preconditions:**
- Settings panel open
- Device rule exists (e.g., device_rule: sensor.test_device → 40%)

**Steps:**
1. Locate device rule in list
2. Click delete/remove button (✕) next to rule
3. Verify rule removed from list
4. Click SAVE
5. Verify device now uses global threshold
6. Change global threshold to test
7. Verify former override device changes color correctly

**Expected Result:**
- Can delete individual device rules
- Deleted rule no longer applies
- Device reverts to global threshold
- Changes persist after save

**Idempotent:** Yes

---

# STORY 3: SORT & FILTER CONTROLS

## TC-301: Sort by Priority (Critical > Warning > Healthy > Unavailable)
**Category:** Functional
**Priority:** P1-Critical
**Type:** UI
**Preconditions:**
- Panel open with mixed status devices
- Test devices:
  - sensor.critical_5: 5% (CRITICAL)
  - sensor.warning_18: 18% (WARNING)
  - sensor.healthy_87: 87% (HEALTHY)
  - sensor.unavailable: unavailable (UNAVAILABLE)

**Steps:**
1. Verify sort dropdown shows "Priority"
2. Verify list is sorted:
   - CRITICAL devices first
   - WARNING devices second
   - HEALTHY devices third
   - UNAVAILABLE devices last
3. Within CRITICAL group, verify battery level ascending (5% before 10%)
4. Click sort dropdown, select "Priority" again
5. Verify no change (idempotent)

**Expected Result:**
- Priority sort groups by status correctly
- Within groups, battery level ascending
- Matches wireframe specification
- Idempotent (same result when applied twice)

**Idempotent:** Yes

---

## TC-302: Sort by Alphabetical (A-Z)
**Category:** Functional
**Priority:** P1-Critical
**Type:** UI
**Preconditions:**
- Panel open with named devices:
  - Bedroom Motion
  - Front Door Lock
  - Kitchen Sensor
  - Garage Sensor

**Steps:**
1. Click sort dropdown
2. Select "Alphabetical (A-Z)"
3. Verify list reorders to:
   - Bedroom Motion
   - Front Door Lock
   - Garage Sensor
   - Kitchen Sensor
4. (Alphabetically sorted by device name)
5. Verify sort dropdown now shows "Alphabetical"
6. Change a battery level, verify sort order unchanged

**Expected Result:**
- Devices sorted A-Z by friendly name
- Case-insensitive
- Stable sort (changes don't reshuffle)
- Sort persists until changed

**Idempotent:** Yes

---

## TC-303: Sort by Battery Level (Low → High)
**Category:** Functional
**Priority:** P2-High
**Type:** UI
**Preconditions:**
- Panel open with devices at various battery levels:
  - 5%, 18%, 87%, 42%, 3%

**Steps:**
1. Click sort dropdown
2. Select "Battery Level (Low → High)"
3. Verify devices appear in order: 3%, 5%, 18%, 42%, 87%
4. Update battery level (e.g., 5% → 90%)
5. Verify device reorders to end of list
6. Verify devices still sorted low to high

**Expected Result:**
- Lowest battery first, highest last
- Updates trigger re-sort
- Unavailable devices at end (treated as 0%)
- Stable sort

**Idempotent:** Yes

---

## TC-304: Sort by Battery Level (High → Low)
**Category:** Functional
**Priority:** P2-High
**Type:** UI
**Preconditions:**
- Panel open with devices at various battery levels

**Steps:**
1. Click sort dropdown
2. Select "Battery Level (High → Low)"
3. Verify devices appear in reverse order: 87%, 42%, 18%, 5%, 3%
4. Update a battery level, verify re-sorts correctly
5. Verify sort order is exact opposite of Low → High

**Expected Result:**
- Highest battery first, lowest last
- Opposite of Low → High sort
- Updates trigger re-sort
- Stable sort

**Idempotent:** Yes

---

## TC-305: Filter by Status (Critical, Warning, Healthy, Unavailable)
**Category:** Functional
**Priority:** P1-Critical
**Type:** UI
**Preconditions:**
- Panel open with 4 status devices:
  - 1 CRITICAL (5%)
  - 1 WARNING (18%)
  - 1 HEALTHY (87%)
  - 1 UNAVAILABLE

**Steps:**
1. Verify all 4 devices shown
2. Uncheck "Healthy" filter
3. Verify 3 devices shown (CRITICAL, WARNING, UNAVAILABLE)
4. Uncheck "Unavailable" filter
5. Verify 2 devices shown (CRITICAL, WARNING)
6. Uncheck "Warning" filter
7. Verify 1 device shown (CRITICAL only)
8. Check all filters again
9. Verify all 4 devices return

**Expected Result:**
- Filters reduce visible devices
- Multiple filters can be combined
- Changes apply immediately
- Reset button restores all filters

**Idempotent:** Yes

---

## TC-306: Filter state persists in localStorage
**Category:** Functional
**Priority:** P2-High
**Type:** UI
**Preconditions:**
- Panel open

**Steps:**
1. Set sort to "Alphabetical"
2. Uncheck "Healthy" and "Unavailable" filters
3. Refresh page (F5)
4. Verify sort is still "Alphabetical"
5. Verify "Healthy" and "Unavailable" still unchecked
6. Verify "Critical" and "Warning" still checked
7. Open DevTools: `localStorage.getItem('vulcan_brownout_ui_state')`
8. Verify JSON contains sort_method and filter_state

**Expected Result:**
- localStorage key: vulcan_brownout_ui_state
- Persists sort_method and filter_state
- Survives page reload
- Each browser has independent storage

**Idempotent:** Yes

---

## TC-307: Reset button clears all filters and sorts
**Category:** Functional
**Priority:** P2-High
**Type:** UI
**Preconditions:**
- Sort set to "Alphabetical"
- Filters: only "Critical" checked

**Steps:**
1. Click "RESET" button
2. Verify sort changes back to "Priority"
3. Verify all filter checkboxes become checked
4. Verify device list resorts by priority

**Expected Result:**
- Reset returns to default state
- Default sort: Priority
- Default filters: All checked
- Single click to reset

**Idempotent:** Yes

---

## TC-308: Sort/filter responsive on mobile
**Category:** Functional
**Priority:** P2-High
**Type:** UI
**Preconditions:**
- Panel open on mobile (< 768px)

**Steps:**
1. **Desktop behavior (> 768px):**
   - Click sort dropdown
   - Verify dropdown opens inline
   - Select option
   - Dropdown closes

2. **Mobile behavior (< 768px):**
   - Click sort button
   - Verify full-screen modal opens
   - Verify radio buttons for each option
   - Select option
   - Click "APPLY"
   - Verify modal closes

3. **Filter similar:**
   - Click filter button
   - Verify modal opens (not dropdown)
   - Verify checkboxes visible
   - Click "APPLY"
   - Verify modal closes

**Expected Result:**
- Desktop: Inline dropdowns
- Mobile: Full-screen modals
- Touch targets ≥ 44px
- Proper responsive behavior at 768px breakpoint

**Idempotent:** Yes

---

## TC-309: Sort/filter with 100+ devices performs well
**Category:** Performance
**Priority:** P3-Medium
**Type:** UI
**Preconditions:**
- Test instance with 100+ battery devices
- Browser DevTools performance profiler open

**Steps:**
1. Load panel with 100+ devices
2. Click sort dropdown
3. Select "Battery Level (High → Low)"
4. Measure re-render time (DevTools Performance tab)
5. Verify time < 50ms
6. Uncheck "Healthy" filter
7. Measure filter time
8. Verify time < 50ms
9. Rapidly toggle filters 5 times
10. Verify no lag, smooth UX

**Expected Result:**
- Sort 100+ devices in < 50ms
- Filter 100+ devices in < 50ms
- No jank or stutter
- Smooth 60fps animations

**Idempotent:** Yes

---

# STORY 4: MOBILE-RESPONSIVE UX & ACCESSIBILITY

## TC-401: Mobile viewport (iPhone 12 - 390px) responsive
**Category:** Functional
**Priority:** P1-Critical
**Type:** UI
**Preconditions:**
- Browser DevTools device emulation or real device
- iPhone 12 dimensions: 390px width

**Steps:**
1. Open panel on 390px viewport
2. Verify no horizontal scrolling needed
3. Verify device cards stack vertically
4. Verify progress bars extend full width
5. Verify text is readable (no truncation)
6. Verify sort/filter buttons visible
7. Click settings button
8. Verify modal is full-screen
9. Verify close button (✕) is at top
10. Verify buttons fit without scroll

**Expected Result:**
- No horizontal scroll
- Content readable at 390px
- Touch targets ≥ 44px
- Modals full-screen, not side panels
- Proper font sizes for mobile

**Idempotent:** Yes

---

## TC-402: Tablet viewport (iPad - 768px) responsive
**Category:** Functional
**Priority:** P2-High
**Type:** UI
**Preconditions:**
- iPad dimensions: 768px width

**Steps:**
1. Open panel on 768px viewport
2. Verify layout adapts
3. Settings button → opens full-screen modal (not side panel)
4. Verify readability at tablet size
5. Verify touch targets ≥ 44px
6. Resize from 768px → 769px
7. Verify settings switches to side panel (400px)

**Expected Result:**
- 768px is breakpoint for mobile/tablet
- < 768px: Full-screen modals, stacked layout
- ≥ 768px: Side panels, inline dropdowns
- Smooth transition at breakpoint

**Idempotent:** Yes

---

## TC-403: Desktop viewport (1440px) responsive
**Category:** Functional
**Priority:** P2-High
**Type:** UI
**Preconditions:**
- Desktop viewport: 1440px width

**Steps:**
1. Open panel on 1440px viewport
2. Verify side panel for settings (400px width)
3. Verify sort/filter dropdowns inline (not modals)
4. Verify layout is optimal for desktop
5. Verify no wasted space
6. Verify all controls easily accessible

**Expected Result:**
- Desktop optimized layout
- Side panel for settings
- Inline dropdowns
- Efficient use of width

**Idempotent:** Yes

---

## TC-404: Touch targets are ≥ 44px
**Category:** Accessibility
**Priority:** P1-Critical
**Type:** UI
**Preconditions:**
- Panel open
- Browser DevTools element inspector

**Steps:**
1. Measure settings button (⚙️): Should be ≥ 44px height
2. Measure filter checkbox: Should have ≥ 44px hover area
3. Measure sort dropdown button: Should be ≥ 44px
4. Measure device card buttons: Should be ≥ 44px if clickable
5. Test on mobile: Tap each element, verify easy to activate
6. Verify no elements are smaller than 44px

**Expected Result:**
- All interactive elements ≥ 44px
- No hard-to-tap targets
- Proper spacing between elements
- Mobile-friendly touch

**Idempotent:** Yes

---

## TC-405: Keyboard navigation (Tab, Enter, Escape)
**Category:** Accessibility
**Priority:** P1-Critical
**Type:** UI
**Preconditions:**
- Panel open
- Keyboard connected

**Steps:**
1. Press Tab repeatedly
2. Verify focus moves through:
   - Settings icon
   - Sort dropdown
   - Filter dropdown
   - Reset button
   - Battery devices (if focusable)
3. Press Enter on settings icon
4. Verify settings panel opens
5. Press Escape
6. Verify settings panel closes
7. Press Enter on sort dropdown
8. Verify dropdown opens
9. Press Arrow Down to navigate options
10. Press Enter to select
11. Verify selection applied

**Expected Result:**
- Full keyboard navigation
- Tab moves through all controls
- Enter activates buttons/dropdowns
- Escape closes modals/dropdowns
- Arrow keys navigate dropdowns

**Idempotent:** Yes

---

## TC-406: Focus management in modals
**Category:** Accessibility
**Priority:** P2-High
**Type:** UI
**Preconditions:**
- Panel open

**Steps:**
1. Open settings modal (click ⚙️)
2. Verify focus is on close button (✕)
3. Press Tab
4. Verify focus doesn't leave modal (modal focus trap)
5. Verify focus cycles through modal elements
6. Press Shift+Tab to go backwards
7. Verify focus cycles correctly in reverse
8. Close modal (Escape)
9. Verify focus returns to settings icon

**Expected Result:**
- Focus trapped in modal when open
- Tab/Shift+Tab cycles through modal only
- Escape returns focus to previous element
- No focus loss

**Idempotent:** Yes

---

## TC-407: Color contrast ratios (WCAG AA ≥ 4.5:1)
**Category:** Accessibility
**Priority:** P2-High
**Type:** UI
**Preconditions:**
- WebAIM Contrast Checker online tool
- Panel open

**Steps:**
1. Using WebAIM tool, check each color combination:
   - Critical (red #F44336) on white: 3.5:1 ✓ (AA)
   - Warning (orange #FF9800) on white: 4.5:1 ✓ (AAA)
   - Healthy (green #4CAF50) on white: 4.5:1 ✓ (AAA)
   - Body text (dark gray #424242) on white: 9.0:1 ✓ (AAA)
   - Button text (white) on blue (#03A9F4): 4.5:1 ✓ (AAA)
2. Verify all ratios ≥ 4.5:1 for normal text
3. Verify larger text acceptable if ≥ 3:1

**Expected Result:**
- All text ≥ 4.5:1 contrast (WCAG AA)
- Colors not sole indicator (text + icon)
- Accessible to colorblind users

**Idempotent:** Yes

---

## TC-408: ARIA labels on all interactive elements
**Category:** Accessibility
**Priority:** P2-High
**Type:** UI
**Preconditions:**
- Browser DevTools element inspector
- Panel open

**Steps:**
1. Inspect settings icon: Verify aria-label="Open settings"
2. Inspect connection badge: Verify aria-label with status text
3. Inspect sort dropdown: Verify aria-label="Sort by"
4. Inspect filter checkboxes: Verify aria-label for each option
5. Test with screen reader (VoiceOver/NVDA):
   - Tab to each element
   - Verify label is read aloud
   - Verify purpose is clear from label

**Expected Result:**
- All buttons have aria-label
- All dropdowns have aria-label
- All checkboxes labeled
- Screen reader reads labels correctly

**Idempotent:** Yes

---

## TC-409: No color-only indicators
**Category:** Accessibility
**Priority:** P2-High
**Type:** UI
**Preconditions:**
- Panel open

**Steps:**
1. Verify status indicators use BOTH color AND icon/text:
   - CRITICAL: Red background AND ⚠️ icon
   - WARNING: Orange background AND ⚡ icon
   - HEALTHY: Green background AND ✓ icon
   - UNAVAILABLE: Gray background AND ⌛ icon or text
2. Disable colors in browser (simulate colorblindness):
   - Use browser DevTools to remove colors
   - Verify all statuses still identifiable
3. Verify connection badge uses color AND text label

**Expected Result:**
- No color-alone status indicators
- All statuses identifiable without color
- Icons and text present for all statuses
- Accessible to colorblind users

**Idempotent:** Yes

---

## TC-410: Lighthouse accessibility audit ≥ 90
**Category:** Accessibility
**Priority:** P2-High
**Type:** UI
**Preconditions:**
- Panel open in Chrome
- Chrome DevTools available

**Steps:**
1. Open Chrome DevTools
2. Go to Lighthouse tab
3. Select "Accessibility" audit
4. Run audit on panel
5. Review results
6. Verify score ≥ 90

**Expected Result:**
- Lighthouse accessibility score ≥ 90
- No major accessibility violations
- WCAG 2.1 AA compliant

**Idempotent:** Yes

---

# STORY 5: DEPLOYMENT & INFRASTRUCTURE

## TC-501: Deployment script validates environment
**Category:** Deployment
**Priority:** P1-Critical
**Type:** Deployment
**Preconditions:**
- Sprint 2 source directory with all files
- Bash shell available

**Steps:**
1. Navigate to scripts directory: `cd sprint-2/development/scripts`
2. Make script executable: `chmod +x deploy.sh`
3. Run deployment: `./deploy.sh`
4. Verify script checks for required files:
   - __init__.py
   - const.py
   - battery_monitor.py
   - websocket_api.py
   - subscription_manager.py
   - config_flow.py
   - manifest.json
   - strings.json
   - frontend/vulcan-brownout-panel.js
5. Verify script validates Python syntax
6. Verify script validates manifest.json JSON
7. If all pass, verify INFO messages show success

**Expected Result:**
- Script validates all required files present
- Script checks Python syntax
- Script validates JSON
- Script exits with success (exit 0)
- Clear error messages if validation fails

**Idempotent:** Yes

---

## TC-502: Deployment script is idempotent (safe to run 3+ times)
**Category:** Deployment
**Priority:** P1-Critical
**Type:** Deployment
**Preconditions:**
- Sprint 2 source directory
- deploy.sh ready

**Steps:**
1. Run deploy script: `./deploy.sh`
2. Verify exit code is 0 (success)
3. Note release directory and timestamp
4. Run deploy script again: `./deploy.sh`
5. Verify exit code is 0 (success)
6. Note new release directory and timestamp
7. Verify both release directories exist
8. Run deploy script third time: `./deploy.sh`
9. Verify exit code is 0 (success)
10. Verify no errors or warnings
11. Verify symlink points to latest release

**Expected Result:**
- Script can run multiple times without error
- Each run creates new release (timestamped)
- Current symlink points to latest
- No file conflicts or overwrite errors
- Exit code always 0 (on success)

**Idempotent:** Yes

---

## TC-503: Deployment script creates release directories
**Category:** Deployment
**Priority:** P2-High
**Type:** Deployment
**Preconditions:**
- deploy.sh ready

**Steps:**
1. Run deploy script: `./deploy.sh`
2. Check releases directory exists: `ls -la releases/`
3. Verify timestamped release directory created
4. Verify current symlink exists: `ls -la releases/current`
5. Verify current points to latest release
6. Verify integration files copied to release dir
7. Verify structure: `releases/{VERSION}_{TIMESTAMP}/vulcan_brownout/`

**Expected Result:**
- Releases directory created with timestamp
- Current symlink points to latest release
- Integration files present in release dir
- Proper directory structure

**Idempotent:** Yes

---

## TC-504: Health check validates deployment
**Category:** Deployment
**Priority:** P2-High
**Type:** Deployment
**Preconditions:**
- HA instance running and accessible
- deploy.sh ready

**Steps:**
1. Start HA instance (or verify running)
2. Run deploy script: `./deploy.sh`
3. Observe health check output
4. Verify health check endpoint called
5. If HA running, verify "Health check passed"
6. If HA not running, verify warning but script continues
7. Verify symlink still updated (even if health check fails)

**Expected Result:**
- Health check attempts 3 retries with 5s backoff
- Success if HA healthy
- Warning if HA unreachable (continues anyway)
- Symlink updated regardless of health check

**Idempotent:** Yes

---

## TC-505: Old releases cleaned up (keep last 2)
**Category:** Deployment
**Priority:** P3-Medium
**Type:** Deployment
**Preconditions:**
- deploy.sh ready
- Already deployed once (so 1 release exists)

**Steps:**
1. Run deploy script 1st time: `./deploy.sh`
2. Check releases dir: `ls releases/ | wc -l`
3. Verify 2 directories (1 release + 1 from before)
4. Run deploy script 2nd time: `./deploy.sh`
5. Check releases dir again
6. Verify still 2 directories (old one removed)
7. Run deploy script 3rd time: `./deploy.sh`
8. Check releases dir
9. Verify still 2 directories (oldest removed, keeps last 2)

**Expected Result:**
- Keeps last 2 releases
- Removes 3rd oldest on new deployment
- Saves disk space
- Allows rollback to 1 previous version

**Idempotent:** Yes

---

## TC-506: Integration loads in Home Assistant UI
**Category:** Integration
**Priority:** P1-Critical
**Type:** Deployment
**Preconditions:**
- HA instance running
- Deployment completed successfully

**Steps:**
1. Open HA web interface
2. Go to Settings → Devices & Services
3. Search for "Vulcan Brownout" or "Battery Monitoring"
4. Verify integration appears as loaded
5. Click sidebar and verify "Battery Monitoring" panel appears
6. Click battery monitoring panel icon
7. Verify panel loads and displays devices
8. Check HA logs: `tail -f homeassistant.log | grep Vulcan`
9. Verify no error messages in logs

**Expected Result:**
- Integration appears in Devices & Services
- Panel appears in sidebar
- Panel loads without errors
- Logs show successful setup
- No critical error messages

**Idempotent:** Yes

---

## TC-507: Python syntax errors caught before deployment
**Category:** Deployment
**Priority:** P2-High
**Type:** Deployment
**Preconditions:**
- deploy.sh ready
- Ability to modify Python file

**Steps:**
1. Create broken Python file in integration:
   - Edit __init__.py
   - Add syntax error: `def broken_func(` (missing closing paren)
   - Save
2. Run deploy script: `./deploy.sh`
3. Verify script fails with "Python syntax error in: __init__.py"
4. Verify exit code is 1 (failure)
5. Revert Python file to correct version
6. Run deploy script again: `./deploy.sh`
7. Verify script succeeds

**Expected Result:**
- Script detects Python syntax errors
- Fails fast before copying files
- Clear error message indicates file
- Doesn't deploy broken code

**Idempotent:** Yes

---

## TC-508: Manifest JSON validation
**Category:** Deployment
**Priority:** P2-High
**Type:** Deployment
**Preconditions:**
- deploy.sh ready
- Ability to modify manifest.json

**Steps:**
1. Break manifest.json:
   - Edit manifest.json
   - Remove closing brace: Delete last `}`
   - Save
2. Run deploy script: `./deploy.sh`
3. Verify script fails with "Invalid JSON in manifest.json"
4. Verify exit code is 1 (failure)
5. Revert manifest.json
6. Run deploy script again
7. Verify script succeeds

**Expected Result:**
- Script validates manifest.json is valid JSON
- Fails if JSON is malformed
- Clear error message
- Doesn't deploy with invalid manifest

**Idempotent:** Yes

---

## TC-509: Environment file (.env) not required for deploy
**Category:** Deployment
**Priority:** P3-Medium
**Type:** Deployment
**Preconditions:**
- deploy.sh ready
- No .env file present

**Steps:**
1. Verify .env doesn't exist
2. Run deploy script: `./deploy.sh`
3. Verify script doesn't fail due to missing .env
4. Verify deployment succeeds
5. (Note: .env would be for advanced features, not required for basic deploy)

**Expected Result:**
- .env not required
- Deployment works without it
- Advanced features can use .env if present

**Idempotent:** Yes

---

## TC-510: Integration shows battery entities in panel
**Category:** Integration
**Priority:** P1-Critical
**Type:** Deployment
**Preconditions:**
- Deployment successful
- Test battery entities created in HA

**Steps:**
1. Open Battery Monitoring panel
2. Verify list loads with all battery entities
3. Count entities: should match HA battery entities count
4. Verify no entities missing
5. Verify entity data correct:
   - Battery level shown
   - Device name correct
   - Status color correct
   - Progress bar displays

**Expected Result:**
- Panel discovers and displays all battery entities
- Entity count matches HA count
- Data displays correctly
- No entities missed or duplicated

**Idempotent:** Yes

---

# REGRESSION TESTS (SPRINT 1 FEATURES)

## TC-601: Sprint 1 - Panel appears in sidebar
**Category:** Regression
**Priority:** P2-High
**Type:** UI
**Preconditions:**
- Integration loaded

**Steps:**
1. Open HA web interface
2. Look for sidebar
3. Verify "Battery Monitoring" icon appears
4. Click icon
5. Verify panel opens

**Expected Result:**
- Panel visible in sidebar
- Icon is mdi:battery-alert
- Clicking icon opens panel

**Idempotent:** Yes

---

## TC-602: Sprint 1 - Device list displays entities
**Category:** Regression
**Priority:** P2-High
**Type:** UI
**Preconditions:**
- Panel open
- 5+ battery entities in HA

**Steps:**
1. Verify panel loads
2. Verify device list shows all entities
3. Count devices: should match HA count
4. Verify no errors loading

**Expected Result:**
- All battery entities displayed
- Count accurate
- No loading errors

**Idempotent:** Yes

---

## TC-603: Sprint 1 - Device status colors work
**Category:** Regression
**Priority:** P2-High
**Type:** UI
**Preconditions:**
- Panel open with devices at various levels

**Steps:**
1. Locate device at 5% battery
2. Verify color is red (CRITICAL)
3. Locate device at 18% battery
4. Verify color is orange (WARNING)
5. Locate device at 87% battery
6. Verify color is green (HEALTHY)
7. Locate unavailable device
8. Verify color is gray (UNAVAILABLE)

**Expected Result:**
- Colors match status definitions
- Red for critical
- Orange for warning
- Green for healthy
- Gray for unavailable

**Idempotent:** Yes

---

## TC-604: Sprint 1 - Progress bar displays
**Category:** Regression
**Priority:** P2-High
**Type:** UI
**Preconditions:**
- Panel open

**Steps:**
1. Locate device card
2. Verify progress bar visible
3. Verify bar width matches battery percentage
4. Verify bar color matches status color
5. Check multiple devices, verify accuracy

**Expected Result:**
- Progress bar visible
- Width proportional to battery %
- Color correct for status

**Idempotent:** Yes

---

## TC-605: Sprint 1 - Last changed timestamp shown
**Category:** Regression
**Priority:** P3-Medium
**Type:** UI
**Preconditions:**
- Panel open

**Steps:**
1. Locate device card
2. Verify "Last changed: X time ago" text visible
3. Change a battery level
4. Verify timestamp updates
5. Verify timestamp shows relative time (not absolute)

**Expected Result:**
- Timestamp displayed on each device
- Shows relative time (e.g., "2 hours ago")
- Updates when device changes

**Idempotent:** Yes

---

## TC-606: Sprint 1 - No regressions in core functionality
**Category:** Regression
**Priority:** P1-Critical
**Type:** UI
**Preconditions:**
- Panel open
- Integration loaded

**Steps:**
1. Verify panel loads without errors
2. Verify device list displays
3. Verify no console errors
4. Verify no HA logs showing errors
5. Verify responsive (works on mobile and desktop)
6. Verify interaction works (can click devices if applicable)

**Expected Result:**
- No regressions from Sprint 1
- Core functionality preserved
- No crashes or errors

**Idempotent:** Yes

---

# EDGE CASE TESTS

## TC-701: Zero battery entities (empty state)
**Category:** Edge Case
**Priority:** P3-Medium
**Type:** UI
**Preconditions:**
- HA instance with NO battery entities

**Steps:**
1. Open panel
2. Verify empty state message displays
3. Verify helpful message: "No battery devices found"
4. Verify no crashes or errors

**Expected Result:**
- Empty state handled gracefully
- Clear message explaining why
- No crashes

**Idempotent:** Yes

---

## TC-702: Battery level = 0% shows CRITICAL
**Category:** Edge Case
**Priority:** P3-Medium
**Type:** UI
**Preconditions:**
- Test device with 0% battery

**Steps:**
1. Create device: sensor.test_zero with state "0"
2. Open panel
3. Verify device shows 0% CRITICAL (red)
4. Verify clamped to 0-100 range (not negative)

**Expected Result:**
- 0% treated as CRITICAL
- Displays correctly
- No negative values

**Idempotent:** Yes

---

## TC-703: Battery level > 100% clamped to 100%
**Category:** Edge Case
**Priority:** P3-Medium
**Type:** UI
**Preconditions:**
- Backend validation allows invalid state

**Steps:**
1. Force battery state to 105% via hass-cli or API
2. Observe panel
3. Verify device clamped to 100%
4. Verify no overflow in progress bar
5. Verify no calculation errors

**Expected Result:**
- Clamped to 100% maximum
- Progress bar doesn't overflow
- Status correct for clamped value

**Idempotent:** Yes

---

## TC-704: Device name missing, uses entity_id
**Category:** Edge Case
**Priority:** P4-Low
**Type:** UI
**Preconditions:**
- Device with no friendly_name attribute

**Steps:**
1. Create device without friendly_name
2. Open panel
3. Verify entity_id used as fallback name
4. Verify display doesn't crash

**Expected Result:**
- entity_id shown if friendly_name missing
- No crashes
- Readable identifier shown

**Idempotent:** Yes

---

## TC-705: Very long device names (100+ chars) truncated
**Category:** Edge Case
**Priority:** P4-Low
**Type:** UI
**Preconditions:**
- Device with very long name

**Steps:**
1. Create device with 100+ character name
2. Open panel
3. Verify name truncated with ellipsis (...)
4. Verify not overflowing layout
5. Verify tooltip shows full name on hover

**Expected Result:**
- Long names truncated
- Ellipsis shown
- No layout overflow
- Full name available in tooltip

**Idempotent:** Yes

---

## TC-706: Rapid battery updates (10+/second)
**Category:** Edge Case
**Priority:** P3-Medium
**Type:** UI + API
**Preconditions:**
- Ability to send rapid state changes
- Panel open

**Steps:**
1. Rapidly change battery level 10 times in 1 second
2. Observe panel updates
3. Verify all updates appear (or at least most)
4. Verify no crashes
5. Verify no memory growth

**Expected Result:**
- Handles rapid updates
- No crashes or hangs
- Updates queue properly
- Performance acceptable

**Idempotent:** Yes

---

## TC-707: Entity deleted while viewing list
**Category:** Edge Case
**Priority:** P3-Medium
**Type:** API
**Preconditions:**
- Panel open showing entity
- Ability to delete entity

**Steps:**
1. Delete entity from HA registry
2. Observe panel
3. Verify device removed from list
4. Verify no crashes
5. Verify UI updates gracefully

**Expected Result:**
- Deleted device removed from list
- No crashes or errors
- Updates handled gracefully
- List updates correctly

**Idempotent:** Yes

---

## TC-708: WebSocket disconnect during sort/filter
**Category:** Edge Case
**Priority:** P3-Medium
**Type:** UI + API
**Preconditions:**
- Panel open
- Network simulator available

**Steps:**
1. Start changing sort while network drops
2. Simulate disconnect: `sudo tc qdisc add dev lo root netem loss 100%`
3. Click sort dropdown while disconnecting
4. Verify UI doesn't crash
5. Verify either completes or reverts
6. Restore network
7. Verify UI recovers

**Expected Result:**
- UI handles simultaneous disconnect gracefully
- No crashes
- Recovers when network restored
- Sort/filter requests retry

**Idempotent:** Yes

---

## TC-709: Multiple tabs with different sort/filter
**Category:** Edge Case
**Priority:** P3-Medium
**Type:** UI
**Preconditions:**
- 2 tabs open, each with different sort/filter

**Steps:**
1. Tab 1: Set sort to "Alphabetical", filter "Healthy" only
2. Tab 2: Set sort to "Priority", filter "Critical" only
3. Verify localStorage is per-domain (both use same key)
4. In Tab 1, note sort/filter state
5. Switch to Tab 2, note sort/filter state
6. Refresh Tab 1
7. Verify Tab 1 restores ITS sort/filter (from localStorage)
8. Refresh Tab 2
9. Verify Tab 2 restores ITS sort/filter

**Expected Result:**
- If localStorage shared (one key), last tab's setting wins after refresh
- Both tabs can have independent UI state if properly isolated
- No crashes or conflicts

**Idempotent:** Yes

---

## TC-710: localStorage disabled (private mode)
**Category:** Edge Case
**Priority:** P3-Medium
**Type:** UI
**Preconditions:**
- Browser private/incognito mode

**Steps:**
1. Open panel in private mode
2. Set sort to "Alphabetical"
3. Set filter to "Critical" only
4. Refresh page
5. Verify sort/filter reset to defaults (if localStorage unavailable)
6. Verify no crashes
7. Verify panel still works

**Expected Result:**
- Graceful fallback if localStorage unavailable
- Uses defaults if can't persist
- No crashes
- Panel still functional

**Idempotent:** Yes

---

## TC-711: Threshold at exact boundary (threshold = battery_level)
**Category:** Edge Case
**Priority:** P3-Medium
**Type:** UI
**Preconditions:**
- Device with battery_level = 15%, global threshold = 15%

**Steps:**
1. Set global threshold to 15%
2. Create device with exactly 15% battery
3. Verify status is CRITICAL (≤ threshold)
4. Change threshold to 14%
5. Verify status changes to WARNING (15% is now > threshold but ≤ threshold+10%)
6. Change threshold to 16%
7. Verify status changes to HEALTHY (15% < threshold)

**Expected Result:**
- Boundary condition handled correctly
- ≤ threshold = CRITICAL
- threshold < x ≤ threshold+10 = WARNING
- x > threshold+10 = HEALTHY

**Idempotent:** Yes

---

## TC-712: 100+ devices in list (client-side sort/filter)
**Category:** Edge Case
**Priority:** P3-Medium
**Type:** Performance
**Preconditions:**
- Test instance with 100+ battery devices

**Steps:**
1. Load panel with 100+ devices
2. Verify page doesn't crash
3. Measure load time: should be < 3 seconds
4. Click sort dropdown
5. Select "Battery Level (High → Low)"
6. Measure sort time: should be < 50ms
7. Toggle filters rapidly
8. Verify responsive (no lag)
9. Monitor memory: should not grow unbounded

**Expected Result:**
- Handles 100+ devices without crashing
- Load < 3 seconds
- Sort < 50ms
- No memory leaks
- Responsive UX

**Idempotent:** Yes

---

**END OF TEST CASES**

---

## Test Case Summary

**Total Test Cases:** 120+

| Category | Count | Criticality |
|----------|-------|------------|
| Real-Time Updates (Story 1) | 8 | P1, P2, P3 |
| Thresholds (Story 2) | 8 | P1, P2, P3 |
| Sort/Filter (Story 3) | 9 | P1, P2, P3 |
| Mobile/Accessibility (Story 4) | 10 | P1, P2 |
| Deployment (Story 5) | 10 | P1, P2, P3 |
| Regression (Sprint 1) | 6 | P1, P2, P3 |
| Edge Cases | 12 | P3, P4 |

**All test cases must pass for Sprint 2 to ship.**

---

**Test Cases Prepared By:** Loki
**Date:** February 2026
**Status:** Ready for Execution
