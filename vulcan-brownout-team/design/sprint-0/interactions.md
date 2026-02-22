# Vulcan Brownout: Interaction Specifications

## Interaction: Infinite Scroll

### Trigger
User scrolls to within 200px of the bottom of the device list.

### Behavior
1. A loading indicator ("∞ Loading more...") appears at the bottom of the list
2. Server request is sent with current pagination offset and limit parameters
3. New items are appended below the current list (no page reload)
4. Loading indicator disappears once new items render
5. Scroll position is maintained (user doesn't jump to top)
6. Process repeats when user approaches bottom again

### States
- **Default state**: List shows initial batch of devices (~15-20 items), no loading indicator visible
- **Loading state**: Spinner or shimmer animation at bottom with "Loading more devices..." text
- **Append state**: New items fade in smoothly below previous list
- **End-of-list state**: Message "All devices loaded" appears instead of loading indicator
- **Error state**: "Failed to load more devices. [Retry]" appears if fetch fails

### Animations/Transitions
- Loading indicator: Smooth fade-in when threshold reached
- New items: Fade in with subtle slide-up (100ms duration)
- Scroll: No forced jump or layout shift
- Loading spinner: Continuous rotation (1.2s per rotation)

### Edge Cases
- **Network latency**: Show spinner for minimum 300ms even if request completes quickly (prevents flickering)
- **Duplicate prevention**: De-duplicate items by device ID before appending (backend handles, frontend validates)
- **Rapid scrolling**: Queue fetch requests; don't send multiple simultaneous requests for the same page
- **Empty results**: If backend returns 0 items, don't append empty state; just show "All devices loaded"
- **User scrolls up during load**: Keep loading visible; don't cancel request mid-flight

---

## Interaction: Sort Toggle

### Trigger
User clicks on "Sort: [Battery Level ▼]" dropdown or clicks sort direction toggle (↑↓ icon).

### Behavior
1. **First click (dropdown)**: Show sort menu with options:
   - Battery Level (ascending/descending)
   - Device Name (A-Z / Z-A)
   - Status (Critical → Healthy → Unavailable)
   - Last Updated
2. **Selection**: List re-sorts according to selection, scroll position resets to top
3. **Direction toggle (↑↓)**: Reverses current sort order without opening menu
4. Server is called with new sort parameters; list updates with freshly sorted data
5. Selected sort option is visually highlighted in dropdown
6. Sort direction indicator updates (↑ for ascending, ↓ for descending)

### States
- **Default**: Battery Level, descending (Critical first)
- **Sorted**: Applied sort label displays in dropdown
- **Loading**: Spinner appears briefly while server sorts and re-fetches
- **Unsorted**: N/A (always has active sort)

### Animations/Transitions
- Dropdown slide-down (200ms easing: ease-out)
- Sort option highlight fade-in (150ms)
- List transition: Fade out old items (100ms) → Fade in new sorted items (150ms)
- Direction toggle: Instant reversal of ↑↓ icon

### Edge Cases
- **Rapid re-sorting**: Debounce sort requests by 300ms to prevent server overload
- **Sort with filtered list**: Sort applies only to filtered items
- **Sort during infinite scroll**: Reset pagination to page 0, load top 15-20 items
- **No change in sort**: Don't re-fetch if user selects already-active sort

---

## Interaction: Filter Changes

### Trigger
User clicks "Filter: [All Devices ▼]" and selects filter option.

### Behavior
1. Filter dropdown opens showing options:
   - All Devices (default)
   - Critical Only (≤threshold)
   - Healthy Only (>threshold)
   - Unavailable Only
   - Exclude Unavailable
2. **Selection**: List filters immediately, pagination resets to page 0
3. Server request includes filter parameter; list updates with filtered results
4. Item count updates to reflect filtered set (e.g., "Critical (3)")
5. Filter label updates in header
6. Sort order is preserved within filtered set

### States
- **Default**: All Devices
- **Filtered**: Active filter label displays, filtered count shown in section headers
- **Loading**: Spinner appears while server filters and returns results
- **Empty filter**: Empty state displayed with message "No devices match this filter"

### Animations/Transitions
- Dropdown slide-down (200ms)
- List update: Fade out (100ms) → Fade in (150ms)
- Filter badge/label color updates to match filter theme

### Edge Cases
- **Filter + Sort + Infinite Scroll**: All three work together; pagination resets on filter change
- **User has scrolled far, changes filter**: Scroll position resets to top (intentional—shows filtered results immediately)
- **Filter that returns 0 results**: Show empty state with helpful message
- **Toggle Unavailable OFF during unavailable filter**: Switch to empty state gracefully

---

## Interaction: Threshold Configuration

### Trigger
User clicks ⚙️ icon in panel header to open settings.

### Behavior
1. Settings panel slides in from right (or modal opens)
2. Current threshold value displayed with slider
3. User adjusts slider: value updates in real-time, text updates to show new threshold
4. User clicks "Save Changes"
5. New threshold is sent to backend; setting is persisted
6. Panel closes, returns to main list view
7. **Immediate effect**: List re-evaluates all devices against new threshold
   - Devices now below threshold move to Critical section
   - Devices now above threshold move to Healthy section
   - UI updates smoothly without refresh
8. Success toast notification appears: "Threshold updated to {value}%"

### States
- **Default**: Current threshold displayed (default 15%)
- **Editing**: Slider active, text value updates in real-time
- **Saving**: "Save Changes" button shows spinner, is disabled during request
- **Saved**: Toast confirms success, panel closes
- **Error**: Error message appears under Save button: "Failed to save threshold. [Retry]"

### Animations/Transitions
- Panel slide-in from right (300ms easing: ease-out)
- Slider thumb smooth movement as user drags
- Real-time text update (no debounce)
- List re-sort: Fade out (100ms) → Fade in (150ms)
- Panel close: Slide-out to right (250ms) after success

### Edge Cases
- **User adjusts threshold but clicks Cancel**: Changes are discarded, panel closes
- **User adjusts to same value and saves**: No-op; backend acknowledges, toast shows "Threshold unchanged"
- **Network error during save**: Show error message with Retry button
- **Threshold change while user is scrolled down**: List doesn't jump; new critical devices appear above scroll position
- **Invalid input** (if manual entry): Show validation error, prevent save

---

## Interaction: Real-Time Updates via WebSocket

### Trigger
Server pushes battery level update, device state change, or new device added.

### Behavior
1. **Battery level update**: Affected device card updates with new percentage and visual indicators
2. **Status change**: Device moves to new section if crossing threshold (e.g., Critical → Healthy)
3. **New device added**: Appears in appropriate section if it matches current filters
4. **Device goes unavailable**: Moves to Unavailable section (or Healthy section if filter set to "Exclude Unavailable")
5. **Device goes available**: Moves back to Critical/Healthy based on battery level
6. **All updates respect current sort and filter**: Devices reposition within list per sort order
7. Visual feedback: Subtle pulse or highlight animation on updated card (200ms)

### States
- **Sync**: List matches server state
- **Out-of-sync**: (rare) If connection drops, "Connection lost" message appears; user can manually Refresh
- **Updating**: Card shows loading state briefly during update

### Animations/Transitions
- Device card highlight: Subtle background color flash (200ms)
- Percentage bar update: Smooth transition if animated progress bar (300ms cubic-bezier(0.4, 0, 0.2, 1))
- Device reposition in list: Smooth fade-out, re-order, fade-in (200ms total)
- New device append: Slide-up fade-in (250ms)

### Edge Cases
- **Multiple updates to same device in rapid succession**: Debounce by 200ms, only show final state
- **Update to device that's scrolled out of view**: Store in queue, update when device scrolls back into view
- **Update while user has filter applied**: Only update if device still matches filter
- **Device added while list is loading**: Defer append until initial load completes

---

## Interaction: Error States & Recovery

### Trigger
Network error, server error (5xx), entity not found, or connection timeout.

### Behavior

#### Initial Load Failure
1. Loading skeleton state shows briefly
2. Error state appears with message: "Unable to load battery devices. [Retry]"
3. User clicks Retry
4. List attempts to reload; if successful, shows data
5. If retry fails, error message persists

#### Infinite Scroll Failure
1. Loading indicator at bottom shows error: "Failed to load more devices. [Retry]"
2. User clicks Retry to fetch next batch
3. If successful, new items append; if not, error message remains
4. User can continue browsing already-loaded items

#### WebSocket Disconnection
1. Banner appears at top: "⚠️ Real-time updates paused. [Reconnect]"
2. Data shown is stale but still valid
3. User can click Reconnect or manual Refresh button
4. Connection re-established, banner disappears

#### Configuration Save Failure
1. Error message appears under Save button: "Failed to save threshold: {reason}"
2. User remains in settings panel
3. Retry button available or user can cancel and try again

### States
- **Error**: Full error message with icon and action buttons
- **Retrying**: Spinner shows while request is in flight
- **Recovered**: Toast notification: "Connected. Updates resumed." (if WebSocket)

### Animations/Transitions
- Error message slide-in from top (banner) or fade-in (inline, 150ms)
- Spinner animation during retry (continuous rotation)
- Banner slide-out on recovery (200ms)

### Edge Cases
- **Connection timeout**: Show timeout-specific message: "Server not responding. Check your connection."
- **401 Unauthorized**: "Authentication expired. [Log in again]"
- **404 Not Found**: "Vulcan Brownout service not found. Reinstall integration."
- **Multiple failures in succession**: After 3 retries, show "Continuous errors detected. [Contact Support]" button
- **Intermittent connectivity**: Show connection state changes subtly (don't spam user with messages)

---

## Interaction: Manual Refresh

### Trigger
User clicks refresh icon (↺) in the header.

### Behavior
1. Refresh icon rotates (spinner animation)
2. Current list resets; skeleton loading state shows
3. Server is queried for fresh data with current filters and sort
4. List updates with fresh results (pagination resets to page 0)
5. Infinite scroll is re-enabled
6. Refresh icon returns to normal state
7. Toast notification: "Updated: X devices found" (optional, brief)

### States
- **Idle**: Refresh icon is static
- **Loading**: Icon rotates continuously
- **Complete**: Icon stops rotating, data updates

### Animations/Transitions
- Icon rotation: 1s continuous (stops when load complete)
- List fade-out/fade-in (200ms total)

### Edge Cases
- **Rapid refresh clicks**: Debounce; ignore clicks within 1s of previous refresh
- **Refresh during infinite scroll**: Cancel any pending scroll fetches, start fresh
- **Refresh fails**: Show error state; refresh icon returns to normal

---

## Interaction: Mobile Gestures & Touch

### Trigger
User performs swipe, long-press, or tap on mobile device.

### Behavior
- **Tap on device card**: Expands card or navigates to device detail (if implemented)
- **Long-press on card**: Shows context menu: "Locate in Home Assistant", "Copy Entity ID", "Share"
- **Pull-to-refresh** (iOS): Refresh list (same as refresh button)
- **Swipe left on card**: Reveal action buttons (e.g., "Locate" or "View Details")

### States
- Default card state
- Pressed/highlight state
- Expanded/detail state (if implemented)

### Animations/Transitions
- Card highlight on tap (100ms)
- Context menu fade-in (150ms)
- Swipe reveal: Slide in from right (250ms)

---

## Summary of Interaction Priorities

1. **Infinite Scroll**: Core UX; must be smooth and non-intrusive
2. **Filter + Sort**: Essential for users with many devices
3. **Real-time Updates**: Keeps panel fresh without manual refresh
4. **Error Recovery**: Graceful handling with clear user guidance
5. **Threshold Config**: Important but secondary to data display
6. **Mobile Support**: Ensure touch targets are adequate (48px minimum)
