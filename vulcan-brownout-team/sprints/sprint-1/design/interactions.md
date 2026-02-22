# Vulcan Brownout: Sprint 1 Interaction Specifications

## Overview

This document defines how users interact with the Vulcan Brownout sidebar panel during Sprint 1. Focus is on the critical user flows: opening the panel, viewing the battery list, refreshing data, and handling error/empty states.

---

## Interaction 1: Panel Opens (Initial Load)

### Trigger
User clicks "Vulcan Brownout" in the HA sidebar.

### Behavior

#### Step 1: Panel Slides In
- Sidebar panel slides open from the right (standard HA behavior)
- Header with title "Vulcan Brownout" and icons (⚙️ settings, ↻ refresh) appears immediately
- Animation duration: 250ms (standard HA transition)

#### Step 2: Skeleton Loading Appears
- If data fetch is not instant, show 3 skeleton loading placeholders
- Each skeleton is 72px tall, with shimmer animation
- Skeleton appears within 100ms of panel open
- Loading message: "Loading battery devices..." (center of panel)

#### Step 3: Data Loads
- Server fetches all entities with `device_class=battery` from HA
- Fetch should complete within 1-2 seconds on typical network
- Entities are sorted by urgency: critical (≤15%) → unavailable → healthy (>15%)
- No sorting controls visible (implicit sort, Sprint 2 adds UI)

#### Step 4: List Renders
- Skeletons fade out (150ms), list fades in
- Devices appear grouped by status:
  - **Critical** section first (red, uppercase header "CRITICAL (N)")
  - **Unavailable** section second (gray, uppercase header "UNAVAILABLE (N)")
  - **Healthy** section last (green, uppercase header "HEALTHY (N)")
- Each device card displays:
  - Icon (color-coded: red, gray, or green)
  - Device name (friendly name from HA)
  - Battery percentage (e.g., "45%")
  - Progress bar (fill level matching percentage)

#### Step 5: User Sees Battery Status At A Glance
- Critical devices are visually prominent (red background)
- Unavailable devices are clearly marked (gray X icon)
- Healthy devices are calm and quiet (green, lower in list)
- User can immediately identify which devices need attention

### States
- **Loading**: Skeletons + spinner message
- **Loaded**: Device list visible, grouped by status
- **Empty**: No devices found (see Interaction 5)
- **Error**: Server unreachable (see Interaction 6)

### Animations/Transitions
- **Panel open**: 250ms slide-in from right (HA standard)
- **Skeleton fade**: 150ms fade-out when data arrives
- **List fade**: 150ms fade-in
- **Progress bar update**: 300ms smooth fill transition

### Edge Cases
1. **Very slow network (>5s load time)**:
   - Skeletons continue animating
   - No timeout error (loading state persists)
   - User can manually refresh (see Interaction 2)

2. **Network glitch during initial load**:
   - Error state appears if fetch fails completely
   - User sees error message + "Retry" button
   - Last-known data NOT shown (fail-safe approach)

3. **Empty list (no battery devices)**:
   - Skeletons replaced with empty state message
   - User sees helpful guidance about configuring devices

---

## Interaction 2: Manual Refresh

### Trigger
User clicks refresh button (↻) in panel header.

### Behavior

#### Step 1: Refresh Icon Animates
- Icon begins rotating continuously (360°/s)
- Icon color changes to primary color (`--primary-color`)
- Button remains interactive (user can click again if desired)

#### Step 2: Server Fetches Latest Data
- GET request to HA API for battery entities
- Server re-queries `device_class=battery` entities
- Fetch should complete within 1-2 seconds

#### Step 3: List Updates
- On success: Device list replaces smoothly (no skeleton state this time)
- Battery percentages update if changed
- Progress bars animate to new levels (300ms smooth transition)
- Status colors update if device moved between critical/healthy/unavailable
- Icon stops rotating, returns to normal color

#### Step 4: No Disruption to User
- User can scroll while refresh is happening
- List remains visible (graceful update, no clearing)
- No layout shift or flicker

### States
- **Idle**: Refresh icon static, normal color
- **Loading**: Icon rotating, primary color
- **Complete**: Icon stops, normal color, list updated

### Animations/Transitions
- **Icon rotation**: 1s per full rotation, linear easing, continuous during fetch
- **Data update**: 300ms fade-cross transition (old list fades, new list fades in)
- **Progress bar animation**: 300ms cubic-bezier(0.4, 0, 0.2, 1)

### Error Handling
- If refresh fails: Error state appears (see Interaction 6)
- Last-known data is replaced with error message
- User sees "Retry" button to try again
- Previous state is not restored

### Edge Cases
1. **User clicks refresh multiple times**:
   - Only one fetch is active at a time
   - Subsequent clicks are ignored (debounced)
   - No cascading requests

2. **Refresh completes but data is identical**:
   - List still updates (visual confirmation refresh happened)
   - Progress bars animate even if percentages unchanged
   - Subtle cue: "Last updated: now" timestamp (if shown)

3. **Device disappears during refresh**:
   - Device card fades out (150ms)
   - Remaining cards shift up to fill space (smooth animation)
   - User sees device is no longer in list

---

## Interaction 3: Viewing Device Details

### Trigger
User hovers over or clicks on a device card.

### Behavior (Desktop - Hover)

#### Step 1: Card Highlights on Hover
- Card background color shifts slightly (5% lighter or darker)
- Cursor changes to pointer
- Optional: Context menu button (⋯) appears on right side

#### Step 2: User Sees Card is Interactive
- Visual cue indicates card can be clicked for more info
- No action required (hover is informational)

### Behavior (Mobile - Tap)

#### Step 1: Card Becomes Active
- Card background color shifts
- Optional: Context menu button (⋯) becomes visible

#### Step 2: Card Details Available (Optional for Sprint 1)
- **Sprint 1 scope**: Tapping a card is optional. Can link to HA device page or show a popup.
- **Spring 2 scope**: Expand card to show more details (last updated, device history, etc.)

### States
- **Default**: Card in normal state
- **Hover/Active**: Background shift, cursor change
- **Expanded**: Additional details shown (Sprint 2)

### Animations/Transitions
- **Hover effect**: 100ms background color fade
- **Context menu**: 150ms slide-in from right (optional)

### Edge Cases
1. **Device goes offline while hovering**:
   - Card remains hovered but status updates
   - Card background may shift to gray (unavailable)
   - User sees device is no longer healthy

2. **Battery level changes while device is active**:
   - Progress bar animates to new level (300ms)
   - Device may move to different status group
   - Card slides to new position in list

---

## Interaction 4: Scrolling and List Navigation

### Trigger
User scrolls within the panel.

### Behavior

#### Step 1: Smooth Scroll
- Device list scrolls smoothly (standard browser scrolling)
- No jank or layout shift
- Cards maintain dimensions and spacing

#### Step 2: Section Headers Stay Visible (Optional)
- Section headers ("Critical", "Unavailable", "Healthy") may be sticky
- Optional for Sprint 1 (implementation detail for Architect)
- If sticky: Headers stay at top while scrolling list items

#### Step 3: Scroll Position Preserved
- If user leaves panel and returns, scroll position is maintained
- (Implementation: Store scroll position in component state)

#### Step 4: Keyboard Navigation (Accessibility)
- User can Tab to navigate between cards
- Enter key on a card triggers click handler (if implemented)
- Shift+Tab goes backward
- Cards receive visible focus indicator (outline, 2px offset)

### States
- **Scroll up**: Cards move down off-screen
- **Scroll down**: Cards move up off-screen, new cards appear
- **Top of list**: First card visible
- **Bottom of list**: Last card visible, no infinite scroll in Sprint 1

### Animations/Transitions
- **Scroll**: Native browser behavior, no custom animation
- **Focus indicator**: Appears immediately on Tab, 150ms fade when lost

### Edge Cases
1. **User scrolls while refresh is happening**:
   - Scroll is not interrupted
   - New data appears while scroll position maintained
   - No conflicting animations

2. **Very long list (100+ devices)**:
   - All devices load at once (no pagination in Sprint 1)
   - Scroll performance depends on browser capabilities
   - Spring 2 adds infinite scroll/pagination if needed

3. **Panel resized (responsive)**:
   - Scroll position maintained
   - Cards reflow to new width
   - No content loss

---

## Interaction 5: Empty State

### Trigger
User opens panel when no battery-powered devices are configured in HA.

### Behavior

#### Step 1: Panel Opens (Same as Normal)
- Header and icons appear
- Skeleton loading state shown briefly

#### Step 2: Empty State Appears
- Skeletons fade out
- Large battery icon appears (⚙️ 64px, light gray)
- Heading: "No battery devices found" (20px, weight 500)
- Body text: "Configure entities with device_class=battery in Home Assistant to appear here." (13px, secondary color)

#### Step 3: CTA Button
- Button: "Browse Home Assistant Devices"
- Links to HA device configuration page or dashboard
- Click triggers new browser tab/window (link target)

#### Step 4: User Understands Next Steps
- User sees why panel is empty
- User knows how to configure devices
- User has direct path to resolution

### States
- **Loading**: Skeletons appear
- **Empty**: Message and CTA shown
- **Post-action**: User navigates away to configure devices

### Animations/Transitions
- **Skeleton fade**: 150ms fade-out
- **Empty state fade**: 150ms fade-in
- **Button hover**: 100ms background shift

### Edge Cases
1. **User configures a device while panel is open**:
   - Empty state remains (data was already fetched)
   - User must manually refresh to see new device
   - Refresh button (↻) triggers new fetch

2. **User leaves and returns to panel**:
   - Empty state shown again (no caching across sessions)
   - User must refresh after configuring devices

---

## Interaction 6: Error State

### Trigger
HA server becomes unreachable, or integration fails to fetch data.

### Behavior

#### Step 1: Initial Load Fails
- Panel opens, skeletons appear
- Fetch to HA API fails (timeout, connection error, or 500 status)
- After 3-5s, error state appears

#### Step 2: Error Message Shown
- Large warning icon (⚠️ 64px, `--error-color`)
- Heading: "Unable to load battery devices" (20px, weight 500)
- Body text: "The Home Assistant server is unreachable. Check your connection and try again." (13px, secondary color)

#### Step 3: Retry Button
- Button: "Retry"
- Click triggers new fetch attempt
- Same loading → success or error flow

#### Step 4: Last Successful Update Timestamp
- Optional helper text: "Last successful update: 2 minutes ago"
- Tells user when data was last known to be valid
- Provides context for deciding whether to retry

#### Step 5: User Decides to Retry or Wait
- User can click "Retry" immediately
- Or user can wait (in case server is restarting)
- Or user can refresh manually (↻ button still works)

### States
- **Loading**: Skeletons appear, fetch in progress
- **Error**: Error message, Retry button, timestamp
- **Retrying**: After Retry click, loading state reappears
- **Success**: After successful retry, list appears

### Animations/Transitions
- **Skeleton to error**: 150ms fade-out/fade-in
- **Retry click**: Skeletons reappear (same as initial load)

### Error Handling Details

#### Type 1: Network Timeout
- Symptom: Fetch takes >5 seconds, then fails
- Message: "The Home Assistant server is unreachable."
- Cause: Network disconnected, HA server down, or very slow connection

#### Type 2: HA API Error (401, 403)
- Symptom: API returns authentication error
- Message: "Unable to load battery devices. Check your HA token."
- Cause: Integration lost HA token, token expired, or HA config error
- (Detailed error handling depends on Architect implementation)

#### Type 3: Integration Error (Exception)
- Symptom: Integration throws exception while fetching entities
- Message: "An error occurred while fetching battery devices."
- Cause: Bug in integration, corrupted HA config, or unexpected entity state
- (Log captured for debugging)

### Edge Cases
1. **User clicks Retry while still retrying**:
   - Ignored (debounced)
   - Only one fetch active at a time

2. **User refreshes (↻) while in error state**:
   - Same as Retry button
   - New fetch attempt starts
   - Skeletons reappear

3. **Server recovers during error state**:
   - User doesn't see automatic recovery (no polling)
   - User must click Retry or refresh to check

4. **Intermittent failures**:
   - First retry: Still fails
   - Second retry: Succeeds
   - User sees list appear after persistence

---

## Interaction 7: Settings Button

### Trigger
User clicks settings gear (⚙️) in header.

### Behavior (Sprint 1)
- **Button exists** in header (right side, next to refresh)
- **No interaction** for Sprint 1 (settings deferred to Sprint 2)
- Button is visible but may be disabled or show "Coming soon"
- Click can either:
  - Do nothing (no-op)
  - Show placeholder tooltip: "Settings coming in Sprint 2"
  - Navigate to settings panel (Spring 2 feature)

### Behavior (Spring 2 — Planned)
- Clicking opens settings slide-panel
- User can adjust:
  - Low battery threshold (default 15%)
  - Filter visibility (show unavailable, show healthy)
  - Auto-refresh interval
  - WebSocket connection toggle
- User saves changes
- List updates to reflect new settings

### States (Sprint 1)
- **Idle**: Icon visible, may be disabled/grayed
- **Hover**: Cursor indicates interactive (if clickable)

### Note for Implementation
- Even though settings don't work in Sprint 1, include the button in the UI
- This prevents layout shift and jarring UI changes when Sprint 2 ships
- QA: Verify button exists and doesn't break panel

---

## Interaction 8: Settings Icon Button Tooltip (Accessibility)

### Trigger
User hovers over or focuses settings (⚙️) or refresh (↻) button.

### Behavior
- Tooltip appears near button
- Text: "Settings" (for ⚙️) or "Refresh" (for ↻)
- Appears after 500ms hover delay
- Disappears on blur or mouse leave

### Tooltip Properties
- **Text**: Small, 11px, secondary color
- **Background**: Dark gray (`--tooltip-background`)
- **Padding**: 8px 12px
- **Border radius**: 4px
- **Position**: Below or above button (auto-adjust for viewport)
- **Pointer**: Small arrow pointing to button

### Accessibility
- aria-label on button: "Settings" or "Refresh"
- Tooltip text matches aria-label
- Screen readers announce aria-label, don't need to announce tooltip

---

## State Machine Diagram

```
┌─────────────────────┐
│  Panel Closed       │
└──────────┬──────────┘
           │ User clicks Vulcan Brownout
           ▼
     ┌──────────────┐
     │  Panel Open  │
     │ (Slide-in)   │
     └──────┬───────┘
            │
            ├─→ [Loading] ──┬─→ [List Loaded] ──┬─→ (idle)
            │   (Skeletons) │   (devices)       └─→ [Refreshing] ──→ back to List
            │               │                  or [Error]
            │               │
            │               └─→ [Empty State]
            │                  (no devices)
            │
            └─→ [Error State] ─┬─→ [Retrying] ─→ (back to Loading/List/Empty)
                               │
                               └─→ (user waits)

From any state:
- User clicks Refresh (↻) → [Refreshing/Loading] → back to current state
- User clicks Settings (⚙️) → (Sprint 2 behavior)
- User scrolls → (List Navigation)
- Panel closes → (Panel Closed)
```

---

## Keyboard Navigation

### Accessible Keyboard Flows

#### Opening Panel
1. User presses Tab until Vulcan Brownout sidebar item is focused (visible outline)
2. User presses Enter to open panel
3. Panel opens, focus moves to first interactive element (Refresh button)

#### Navigating List
1. User Tab-navigates through device cards
2. Each card receives focus (visible outline)
3. User presses Enter to view card details (optional, Spring 2)
4. Shift+Tab to go backward

#### Refreshing
1. User Tab-navigates to Refresh button (↻)
2. User presses Enter or Space
3. Refresh starts, icon rotates
4. User can Tab to other elements while loading

#### Settings (Spring 2)
1. User Tab-navigates to Settings button (⚙️)
2. User presses Enter or Space
3. Settings panel opens
4. User Tab-navigates through form inputs

#### Closing Panel
1. User presses Escape key (standard HA behavior)
2. Panel closes, focus returns to HA main UI

### Focus Order (Logical)
1. Refresh button (↻)
2. Settings button (⚙️)
3. Device cards (in order from top to bottom)
4. (Spring 2: Filter/Sort dropdowns)

### Focus Indicator Styling
```css
:focus {
  outline: 2px solid var(--primary-color);
  outline-offset: 2px;
}
```

---

## Touch & Mobile Interactions

### Touch Targets
- All buttons: Min 44px × 44px (48px ideal)
- Device cards: Min 72px height (comfortable for touch)
- Spacing between cards: 12px (prevents accidental multi-touch)

### Gestures
- **Tap**: Activate button or card (same as click)
- **Long press**: (Optional Spring 2 feature: Context menu)
- **Scroll**: Native list scroll (standard mobile behavior)
- **Pull to refresh**: (Not implemented in Sprint 1; manual refresh button used)

### Mobile Optimization
- No hover effects (switches to active/pressed states on tap)
- Settings button (⚙️) always visible (not hidden on small screens)
- Refresh button (↻) always visible (critical for mobile user)
- Device cards scale to full width (100% - 16px padding)

---

## Performance Expectations

### Loading Times (User-Perceived)
- **Panel open to first render**: <100ms
- **Skeletons appear**: <100ms
- **Data fetch**: 1-2 seconds typical
- **List visible**: 2-3 seconds total (including skeleton + fade transitions)
- **Refresh complete**: 1-2 seconds

### Animation Durations
- **Panel slide**: 250ms (HA standard)
- **Fade in/out**: 150ms
- **Progress bar**: 300ms
- **Refresh icon rotation**: 1s per rotation

### No Jank
- 60 FPS scrolling (smooth list navigation)
- No layout shift (cards maintain dimensions)
- No visual flicker (proper skeleton states)

---

## Summary

Sprint 1 interactions are straightforward and predictable:

1. **Open → Load → View**: User opens panel, sees loading state, list appears
2. **Refresh**: Click refresh button, icon spins, list updates
3. **Error/Empty Handling**: Clear messaging with clear next steps
4. **Accessibility**: Full keyboard navigation, WCAG AA compliant

This keeps the experience clean, native to HA, and easy to test.
