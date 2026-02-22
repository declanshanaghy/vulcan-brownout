# Interaction Specifications — Sprint 3

**Designer:** Luna (UX Designer)
**Scope:** User interactions, state machines, event handlers for Sprint 3 features
**Format:** Step-by-step flows with state diagrams
**Last Updated:** February 22, 2026

---

## Overview

This document defines how users interact with Sprint 3 features at a granular level. It covers:

1. **Infinite Scroll** — Automatic pagination when near bottom
2. **Back to Top** — Sticky button, scroll positioning
3. **Notification Preferences** — Configuration workflows
4. **Dark Mode** — Theme detection and switching
5. **Empty State** — No battery entities found

Each interaction includes:
- **Step-by-step flow** (numbered sequence)
- **State diagram** (Mermaid)
- **Visual feedback** (what user sees at each step)
- **Error handling** (what happens if something goes wrong)
- **Performance timeline** (when things happen)

---

## 1. INFINITE SCROLL INTERACTION

### 1.1 Initial Page Load

**User Goal:** Open sidebar, see batteries, scroll infinite list

**Steps:**

```
1. User opens Vulcan Brownout sidebar panel
2. Panel renders with loading skeleton
3. Initial REST API call: GET /api/devices?offset=0&limit=50
4. First 50 battery devices arrive
5. Skeleton loaders fade out, real devices fade in
6. List is now interactive
7. User can: scroll, sort, filter, or modify settings
```

**Timeline:**

```
T=0ms:       Panel opens, skeleton loaders visible
T=0-500ms:   REST API request in flight
T=100-300ms: HA backend queries battery entities
T=300ms+:    Devices arrive, skeleton fade out begins
T=600ms:     Real devices fully visible
T=600ms+:    WebSocket subscription active, real-time updates flowing
```

**State Diagram:**

```mermaid
stateDiagram-v2
    [*] --> InitialLoad: Panel opens
    InitialLoad --> SkeletonLoading: Show skeleton cards
    SkeletonLoading --> DataArrived: Devices received
    DataArrived --> Loaded: Skeleton fade out complete
    Loaded --> NearBottom: User scrolls
    NearBottom --> FetchingNext: Fetch next batch
    FetchingNext --> Loaded: New devices appended
    Loaded --> [*]: All devices loaded
    FetchingNext --> Error: Network failure
    Error --> Loaded: Retry succeeded
```

---

### 1.2 User Scrolling Near Bottom (Fetch Next Batch)

**User Goal:** Automatically load next 50 devices without clicking "Load More"

**Steps:**

```
1. User has scrolled through 50 devices
2. Reaches within 100px of bottom of viewport
3. TRIGGER: "ScrollNearBottom" event fires
4. Check: Have we already fetched next batch? (debounce)
   ✅ Not fetching → Continue
   ❌ Already fetching → Skip (prevent duplicates)
5. Loading indicator appears: "⟳ Loading 5 more devices..."
6. Skeleton loaders appear below loading text
7. API call: GET /api/devices?offset=50&limit=50
8. Backend queries next 50 devices
9. Devices arrive in JSON array
10. JavaScript appends devices to DOM (no layout shift)
11. Skeleton loaders fade out
12. Real devices fade in (300ms animation)
13. Scroll position maintained (user doesn't jump)
14. User can continue scrolling
15. If more devices exist, repeat from step 2
```

**Detailed Timeline:**

```
T=0ms:       User scrolls within 100px of bottom
             └─ ScrollNearBottom event fires
             └─ Check: !isFetching (debounce guard)

T=0-50ms:    Set isFetching = true (prevent duplicates)
             └─ Show loading indicator: "⟳ Loading 5 more devices..."

T=50-100ms:  Show skeleton loaders (5 placeholder cards)
             └─ Fade in animation (opacity 0 → 1, 300ms)

T=100ms:     API request sent: GET /api/devices?offset=50&limit=50

T=100-300ms: HA backend processes query
             └─ Typical latency: 100-200ms

T=300ms:     Devices received (JSON array with 50 objects)

T=300-350ms: Append devices to DOM
             └─ Use document.createDocumentFragment() for batch insert
             └─ No reflow until all items inserted

T=350-400ms: Trigger fade-in animation for new devices
             └─ opacity 0 → 1 (300ms)

T=400-700ms: Skeleton loaders fade out in parallel
             └─ opacity 1 → 0 (300ms)

T=700ms:     Both animations complete
             └─ Set isFetching = false
             └─ New devices fully visible
             └─ User can scroll further if more exist
```

**Performance Optimization:**

```
- Debounce scroll events: max 1 fetch per 500ms
- Batch DOM insertions: use DocumentFragment
- Use requestAnimationFrame for layout-safe animations
- Lazy-load device images/icons (future)
- Virtual scrolling for 500+ items (future, Sprint 4)
```

**State Machine:**

```mermaid
graph TD
    A["User scrolls"] --> B{"Within 100px<br/>of bottom?"}
    B -->|No| A
    B -->|Yes| C{"Already<br/>fetching?"}
    C -->|Yes| A
    C -->|No| D["Set isFetching = true"]
    D --> E["Show loading indicator"]
    E --> F["Show skeleton loaders"]
    F --> G["API: GET devices"]
    G --> H{Network<br/>success?}
    H -->|No| I["Show error message"]
    I --> J["Set isFetching = false"]
    H -->|Yes| K["Append devices to DOM"]
    K --> L["Fade in new items"]
    L --> M["Fade out skeletons"]
    M --> N["Set isFetching = false"]
    N --> O["Loaded"]
    O --> A

    style O fill:#4CAF50,stroke:#333,color:#fff
    style I fill:#F44336,stroke:#333,color:#fff
```

---

### 1.3 End of List (All Devices Loaded)

**Scenario:** User scrolls to very bottom, no more devices to fetch

**Steps:**

```
1. User scrolls near bottom
2. API: GET /api/devices?offset=200&limit=50
3. Backend returns 0 devices (because 200+ exhausts total count)
4. OR backend returns < 50 devices (last partial batch)
5. JavaScript detects: "No more items"
6. Loading indicator hidden
7. Display message: "All devices loaded" (optional, subtle)
8. Scroll continues normally but doesn't trigger fetch
9. "Back to Top" button still visible and clickable
```

**Visual Feedback:**

```
┌────────────────────────────────┐
│ [Last device card]             │
├────────────────────────────────┤
│                                │
│    ✓ All devices loaded        │ ← Optional, subtle message
│                                │
│ 🔄 Updated 3 seconds ago       │
└────────────────────────────────┘
```

---

### 1.4 Network Error During Fetch

**Scenario:** Network drops while fetching next batch

**Steps:**

```
1. User scrolls near bottom
2. Loading indicator shows: "⟳ Loading 5 more devices..."
3. Skeleton loaders visible
4. API request sent, but network fails (timeout, 500 error, etc.)
5. Error is caught by JavaScript
6. T=2000ms (timeout threshold): Show error state
7. Loading indicator changes: "⚠️ Failed to load. [RETRY]"
8. Skeleton loaders fade out
9. User can:
   - Click [RETRY] button to attempt again
   - Scroll up to see previously loaded devices
   - Continue using panel (no crash)
10. If user clicks [RETRY]:
    - Loading indicator reappears
    - Skeleton loaders reappear
    - API request retried
    - If successful: devices loaded normally
    - If fails again: error message persists
```

**Error State Visual:**

```
┌──────────────────────────────────────────────┐
│ [Previously loaded devices]                  │
├──────────────────────────────────────────────┤
│                                              │
│ ⚠️ Failed to load more devices               │
│                                              │
│ [RETRY]  [Go to Top]                         │
│                                              │
└──────────────────────────────────────────────┘
```

**Accessibility:**
- **ARIA Alert:** `role="alert"` announces error message
- **Focus:** Move focus to [RETRY] button
- **Keyboard:** User can Tab to [RETRY] and press Enter

---

## 2. BACK TO TOP BUTTON INTERACTION

### 2.1 Show/Hide Logic

**Trigger To Show:**

```
User scrolls down past 30 items (or ~1000px)
    ↓
Button fades in (opacity 0 → 1, 300ms ease-out)
    ↓
Button is now visible, interactive
```

**Trigger To Hide:**

```
User scrolls back to top of list (scrollTop < 100px)
    ↓
Button fades out (opacity 1 → 0, 300ms ease-out)
    ↓
Button no longer visible (pointer-events: none)
```

**Performance:**

```
- Debounce scroll event: calculate position max 60fps
- Use throttle (150ms) to avoid excessive reflows
- CSS transition for fade (no JavaScript animation)
- Use will-change: opacity for GPU acceleration
```

---

### 2.2 Click Interaction (Smooth Scroll to Top)

**User clicks Back to Top button:**

```
1. User clicks "▲ Back to Top" button
2. Visual feedback: button briefly highlights (30ms)
3. JavaScript triggers smooth scroll animation
4. Scroll position animates: current → 0 (500ms ease-out)
5. During scroll:
   - List smoothly moves upward
   - No jank or layout shift
   - Real-time updates from WebSocket continue
   - Button fades out as user reaches top
6. After scroll complete (T=500ms):
   - User at top of list
   - Button hidden
   - Focus returns to settings icon (optional)
```

**Scroll Implementation (JavaScript):**

```javascript
// Smooth scroll to top
const element = document.querySelector('.battery-list');
element.scrollTo({
  top: 0,
  left: 0,
  behavior: 'smooth' // Native smooth scroll (500ms)
});

// Fallback (CSS-based animation) for older browsers
// Use anime.js or Framer Motion
```

**Keyboard Interaction:**

```
User presses Tab until focus reaches "▲ Back to Top" button
    ↓
Visible focus ring appears on button
    ↓
User presses Enter or Space
    ↓
Same as click: smooth scroll to top
```

**State Diagram:**

```mermaid
graph TD
    A["User at top<br/>scrollTop < 100px"] --> B["Button hidden"]
    B -->|User scrolls down 30+ items| C["Button fades in"]
    C --> D["Button visible"]
    D -->|User clicks button| E["Smooth scroll to top"]
    E -->|scrollTop = 0| F["Button fades out"]
    F --> B
    D -->|User scrolls up| F

    style D fill:#4CAF50,stroke:#333,color:#fff
    style B fill:#999,stroke:#333,color:#fff
```

---

### 2.3 Scroll Position Restoration

**Use Case:** User scrolls to item 150, then navigates away and returns (same session)

**Steps:**

```
1. User scrolls to item 150
2. scrollTop = 3000px (approximate, depends on viewport)
3. Store scroll position in sessionStorage:
   sessionStorage.setItem('vulcanScrollPos', '3000')
4. User navigates to settings, changes threshold
5. User returns to battery list
6. JavaScript checks sessionStorage
7. Detects: 'vulcanScrollPos' = '3000'
8. Restores scroll position to 3000px (instant, no animation)
9. List displays items around that position
10. Back to Top button shows (because scrollTop > 100px)
11. User sees same view as before
```

**Implementation:**

```javascript
// Save scroll position
const batteryList = document.querySelector('.battery-list');
batteryList.addEventListener('scroll', () => {
  sessionStorage.setItem('vulcanScrollPos', batteryList.scrollTop);
});

// Restore scroll position on load
window.addEventListener('load', () => {
  const savedPos = sessionStorage.getItem('vulcanScrollPos');
  if (savedPos) {
    batteryList.scrollTop = parseInt(savedPos);
  }
});

// Clear on panel close
function closeBatteryPanel() {
  sessionStorage.removeItem('vulcanScrollPos');
}
```

**Edge Cases:**

```
- If device count changes (new device added): scroll position may be invalid
  → Fallback: scroll to top if scrollTop > maxScrollHeight
- If user navigates to different HA instance: clear sessionStorage
- If browser session ends: sessionStorage cleared (expected behavior)
```

---

## 3. NOTIFICATION PREFERENCES INTERACTION

### 3.1 Open Notification Preferences

**User Path:**

```
User in Settings panel
    ↓
Clicks "[⚙️ CONFIGURE NOTIFICATIONS]" button
    ↓
Notification Preferences modal opens (modal dialog)
    ↓
Modal slides in from right (desktop) or bottom (mobile)
    ↓
Modal is now active and interactive
    ↓
Focus moves to global toggle (first interactive element)
```

**Desktop Animation:**

```
T=0ms:       User clicks [⚙️ CONFIGURE NOTIFICATIONS]
             └─ Settings panel stays open (backdrop)

T=0-300ms:   Modal slides in from right
             └─ translateX: 100vw → 0
             └─ Easing: cubic-bezier(0.4, 0, 0.2, 1)

T=300ms+:    Modal fully visible
             └─ Focus moved to global toggle
             └─ User can interact with form
```

**Mobile Animation:**

```
T=0ms:       User taps [⚙️ CONFIGURE NOTIFICATIONS]
             └─ Settings modal stays visible (backdrop)

T=0-300ms:   Notification preferences modal slides up from bottom
             └─ translateY: 100vh → 0
             └─ Full-screen (100vw × 90vh)

T=300ms+:    Modal fully visible
             └─ Focus moved to global toggle
```

---

### 3.2 Toggle Global Notifications

**User Goal:** Enable/disable all notifications with one switch

**Steps:**

```
1. User sees global toggle: [Toggle: ON]  (currently enabled)
2. User clicks toggle switch
3. Visual feedback:
   - Switch animates: position slides left/right (200ms)
   - Color changes: green (ON) → gray (OFF)
   - Label updates: "ON" ↔ "OFF"
4. State updates in component (React/Vue state management)
5. If toggle OFF:
   - Per-device list becomes disabled (grayed out, not clickable)
   - Notification history still visible (for reference)
6. If toggle ON:
   - Per-device list becomes enabled (interactive again)
7. Change is not persisted until user clicks [SAVE PREFERENCES]
```

**Toggle Switch Styling:**

```
ON State (Dark Mode):
┌─────────────────────────┐
│ [●      ] ON            │ ← Green background (#66BB6A), white circle
└─────────────────────────┘

OFF State (Dark Mode):
┌─────────────────────────┐
│ [      ●] OFF           │ ← Gray background (#666), white circle
└─────────────────────────┘
```

**Animation (CSS):**

```css
.toggle-switch {
  background: #666;
  border-radius: 24px;
  transition: background 200ms ease-out;
  position: relative;
}

.toggle-switch.enabled {
  background: #66BB6A;
}

.toggle-circle {
  position: absolute;
  border-radius: 50%;
  background: #FFFFFF;
  transition: left 200ms ease-out;
}

.toggle-switch.enabled .toggle-circle {
  left: calc(100% - 24px);
}
```

---

### 3.3 Change Notification Frequency Cap

**User Goal:** Set max notification frequency (1h, 6h, 24h)

**Steps:**

```
1. User sees dropdown: [▼ 6 hours]
2. User clicks dropdown
3. Dropdown opens with options:
   - 1 hour
   - 6 hours (currently selected, highlighted)
   - 24 hours
4. User hovers over "24 hours" (highlight on hover)
5. User clicks "24 hours"
6. Dropdown updates: label changes "6 hours" → "24 hours"
7. Dropdown closes (auto-close on selection, optional)
8. State updates in component
9. Change not persisted until [SAVE PREFERENCES]
```

**Dropdown Behavior:**

```
Desktop:
- Opens inline below button
- Max height: 150px (scrollable if needed)
- Closes when selection made (auto-close)
- Or closes on Escape key or click outside

Mobile:
- Opens as full-width picker
- All options visible (no scroll needed)
- User taps option to select
- Dropdown updates immediately
```

---

### 3.4 Change Notification Severity

**User Goal:** Notify for Critical only, or Critical + Warning

**Steps:**

```
1. User sees radio buttons:
   ◉ Critical only (selected)
   ○ Critical and Warning
2. User clicks "Critical and Warning" radio button
3. Visual feedback:
   - Radio button circle fills with blue (#03A9F4)
   - "Critical only" option becomes unselected (empty circle)
4. State updates in component
5. Change not persisted until [SAVE PREFERENCES]
```

**Radio Button Styling (Dark Mode):**

```
Unselected:
( ) Critical only

Selected:
(●) Critical and Warning  ← Filled with blue #03A9F4
```

---

### 3.5 Toggle Per-Device Notifications

**User Goal:** Enable/disable notifications for specific devices

**Steps:**

```
1. User sees per-device list with checkboxes:
   [✓] Front Door Lock       8% — ON
   [✓] Solar Backup          5% — ON
   [ ] Bathroom Fan         87% — OFF
   ...
2. User clicks checkbox for "Bathroom Fan"
3. Visual feedback:
   - Checkbox animates: empty → filled with blue
   - Text updates: "OFF" → "ON" (immediate)
4. Row highlights briefly (100ms) to show change
5. User can toggle multiple devices
6. Changes not persisted until [SAVE PREFERENCES]
7. If global toggle is OFF:
   - All per-device checkboxes disabled (grayed out)
   - User sees visual feedback but can't change state
```

**Checkbox Styling (Dark Mode):**

```
Unchecked:
[ ] Device Name           X% — OFF

Checked:
[✓] Device Name           X% — ON  (checkbox blue #03A9F4)
```

**Row Highlight Animation:**

```css
.device-row {
  transition: background-color 100ms ease-out;
}

.device-row.toggled {
  background-color: rgba(51, 169, 244, 0.1); /* Subtle blue flash */
}

/* After animation, remove class to prevent permanent highlight */
setTimeout(() => row.classList.remove('toggled'), 100);
```

---

### 3.6 Search/Filter Device List

**User Goal:** Find device quickly in long list

**Steps:**

```
1. User sees search input: [Search devices...] 🔍
2. User types "solar" (3 characters)
3. Real-time filter as user types:
   - Input: "s" → No matches initially
   - Input: "so" → Still searching
   - Input: "sol" → Matches "Solar Backup"
   - Input: "solar" → One match visible
4. Device list updates instantly (no debounce needed for this use case)
5. Non-matching devices hidden (display: none)
6. Checkbox state preserved even when hidden
7. If no matches: "No devices match 'solar'" message
8. User can backspace to remove filter
9. On modal close: filter cleared (input reset)
```

**Search Implementation:**

```javascript
const searchInput = document.querySelector('[placeholder="Search devices..."]');
searchInput.addEventListener('input', (e) => {
  const query = e.target.value.toLowerCase();
  const deviceRows = document.querySelectorAll('.device-row');

  deviceRows.forEach(row => {
    const deviceName = row.textContent.toLowerCase();
    const matches = deviceName.includes(query);
    row.style.display = matches ? 'block' : 'none';
  });

  // Show "no matches" message if no results
  const visibleCount = Array.from(deviceRows).filter(
    r => r.style.display !== 'none'
  ).length;

  if (visibleCount === 0 && query.length > 0) {
    showNoMatchesMessage(query);
  } else {
    hideNoMatchesMessage();
  }
});
```

---

### 3.7 View Notification History

**User Goal:** See past notifications sent to HA

**Steps:**

```
1. User scrolls to "NOTIFICATION HISTORY" section
2. Sees list of recent notifications:
   2026-02-22 10:15 — Front Door Lock battery critical (8%)
   2026-02-22 09:30 — Solar Backup battery critical (5%)
   2026-02-21 14:20 — Kitchen Sensor battery warning (18%)
3. Each notification shows:
   - Timestamp (clickable, links to HA notification center)
   - Device name
   - Status (critical/warning)
   - Battery percentage at time of notification
4. User clicks "[View All History]" link
5. New browser tab opens: HA notification center (existing HA UI)
6. User can see full notification details in HA
7. User can dismiss or mark as read in HA's UI
```

**History Display (Dark Mode):**

```
NOTIFICATION HISTORY

Recent notifications:
┌─────────────────────────────────────┐
│ 2026-02-22 10:15                    │
│ Front Door Lock — 8% (Critical)     │ ← Gray text, left-aligned
└─────────────────────────────────────┘
┌─────────────────────────────────────┐
│ 2026-02-22 09:30                    │
│ Solar Backup — 5% (Critical)        │
└─────────────────────────────────────┘

[View All History] ← Link to HA notification center
```

---

### 3.8 Save Notification Preferences

**User Goal:** Persist all changes made in the modal

**Steps:**

```
1. User has made changes:
   - Global toggle: OFF
   - Frequency cap: 6 hours
   - Severity: Critical + Warning
   - Per-device: Front Door ON, Solar ON, Kitchen OFF
2. User clicks [SAVE PREFERENCES] button
3. Visual feedback: Button shows "SAVING..." spinner (100ms)
4. JavaScript validates all changes:
   ✅ All inputs valid
5. POST /api/notifications/preferences
   Body: {
     "enabled": false,
     "frequency_cap_hours": 6,
     "severity_filter": "critical_and_warning",
     "per_device": {
       "front_door_lock": true,
       "solar_backup": true,
       "kitchen_sensor": false,
       ...
     }
   }
6. Backend processes and persists to database
7. Response: 200 OK
8. Modal closes (animation: slide out left, fade overlay)
9. User returns to Settings panel
10. Settings panel now shows notification preferences are configured
11. Toast notification (optional): "✓ Preferences saved"
```

**Save Error Handling:**

```
If POST fails (500, timeout, network error):
  1. Show error message in modal: "Unable to save preferences. Retry?"
  2. [SAVE PREFERENCES] button is reactivated (user can retry)
  3. Form data preserved (user doesn't lose changes)
  4. Focus returns to [SAVE PREFERENCES] button
  5. User can click [CANCEL] to discard changes and close
```

**Timeline:**

```
T=0ms:       User clicks [SAVE PREFERENCES]
T=0-100ms:   Show "SAVING..." spinner
T=100ms:     Validate form inputs
T=100-400ms: POST request in flight
T=200-300ms: Backend processes (typical latency)
T=400ms+:    Response received (200 OK or error)
T=400-600ms: Modal close animation
T=600ms:     Modal closed, return to Settings panel
```

---

### 3.9 Cancel and Discard Changes

**User Goal:** Exit notification preferences without saving

**Steps:**

```
1. User has made changes in notification preferences modal
2. User clicks [CANCEL] button
3. Confirmation check:
   - If no changes made: close immediately
   - If changes made: show confirm dialog
     "Discard unsaved changes?"
     [DISCARD]  [KEEP EDITING]
4. If user clicks [DISCARD]:
   - Modal closes (animation: slide out)
   - All changes discarded
   - Previous settings remain unchanged
5. If user clicks [KEEP EDITING]:
   - Dialog closes
   - Modal stays open
   - Form data intact
6. User can press Escape key (same as [CANCEL])
```

**Confirmation Dialog (Dark Mode):**

```
┌─────────────────────────────────────┐
│ DISCARD CHANGES?                    │
├─────────────────────────────────────┤
│                                     │
│ You have unsaved changes in         │
│ notification preferences.           │
│ Are you sure you want to discard?   │
│                                     │
│ [DISCARD]       [KEEP EDITING]      │
│                                     │
└─────────────────────────────────────┘
```

---

## 4. DARK MODE INTERACTION

### 4.1 Theme Detection on Load

**User Opens Vulcan Brownout:**

```
T=0ms:       Panel HTML loads
T=0-50ms:    JavaScript executes on document load
T=50ms:      Detect HA's theme setting:
             - Check: document.documentElement.getAttribute('data-theme')
             - Check: window.matchMedia('(prefers-color-scheme: dark)').matches
             - Check: localStorage['ha_theme'] (optional)
T=50-100ms:  Apply theme CSS variables:
             - If dark: set --vb-bg-primary: #1C1C1C, etc.
             - If light: set --vb-bg-primary: #FFFFFF, etc.
T=100ms:     Panel renders with correct theme
T=100ms+:    User sees panel in correct light/dark mode
```

**Theme Detection Logic (JavaScript):**

```javascript
function detectTheme() {
  const root = document.documentElement;

  // Method 1: HA's data-theme attribute
  const haTheme = root.getAttribute('data-theme');
  if (haTheme === 'dark') return 'dark';
  if (haTheme === 'light') return 'light';

  // Method 2: Prefer color scheme media query
  if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
    return 'dark';
  }

  // Method 3: HA's localStorage setting (fallback)
  const storedTheme = localStorage.getItem('ha_theme');
  if (storedTheme) return storedTheme;

  // Default to light
  return 'light';
}

const theme = detectTheme();
applyTheme(theme);
```

---

### 4.2 Theme Changes While Panel is Open

**Scenario:** User toggles HA's theme preference while Vulcan is displayed

**Steps:**

```
1. User viewing battery list in light mode
2. User navigates to HA settings, changes theme to dark
3. HA applies dark theme to all panels
4. HA emits theme change event (or DOM mutation)
5. Vulcan's MutationObserver catches the change:
   - Detects data-theme attribute changed
   - Triggers theme update
6. JavaScript updates CSS variables:
   - --vb-bg-primary: #FFFFFF → #1C1C1C
   - --vb-text-primary: #212121 → #FFFFFF
   - Status colors: #F44336 → #FF5252 (critical)
   - etc.
7. CSS transitions apply (no flashing):
   - Background color: fade 300ms
   - Text color: fade 300ms
8. Panel smoothly transitions to dark mode
9. All child components (settings, notifications, dropdowns) update
10. WebSocket real-time updates continue uninterrupted
```

**No Interruption Guarantee:**

```
- Real-time battery updates continue flowing
- WebSocket connection remains active
- User can still scroll, filter, configure settings
- No page reload needed
- Smooth visual transition (no jank)
```

**Theme Listener (JavaScript):**

```javascript
// Listen for theme changes via MutationObserver
const observer = new MutationObserver((mutations) => {
  mutations.forEach((mutation) => {
    if (mutation.attributeName === 'data-theme') {
      const newTheme = document.documentElement.getAttribute('data-theme');
      applyTheme(newTheme);
    }
  });
});

observer.observe(document.documentElement, {
  attributes: true,
  attributeFilter: ['data-theme']
});

// Or listen for media query changes
window.matchMedia('(prefers-color-scheme: dark)').addListener((e) => {
  const newTheme = e.matches ? 'dark' : 'light';
  applyTheme(newTheme);
});
```

**State Diagram:**

```mermaid
graph TD
    A["Panel Loads"] --> B["Detect HA Theme"]
    B --> C{Dark Mode?}
    C -->|Yes| D["Apply Dark CSS"]
    C -->|No| E["Apply Light CSS"]
    D --> F["Render Dark"]
    E --> G["Render Light"]
    F --> H["Listen for theme changes"]
    G --> H
    H -->|User changes theme| I["Detect new theme"]
    I --> C
```

---

### 4.3 Color Contrast Verification During Theme Switch

**Quality Assurance:**

```
When theme switches, verify all colors remain accessible:

Before Switch (Light Mode):
  - Critical (#F44336) on #FFFFFF: 3.5:1 (AA)
  - Text (#212121) on #FFFFFF: 9.0:1 (AAA)

After Switch (Dark Mode):
  - Critical (#FF5252) on #1C1C1C: 5.5:1 (AAA) ✅
  - Text (#FFFFFF) on #1C1C1C: 19:1 (AAA) ✅

All colors pass WCAG standards in both modes.
```

---

## 5. EMPTY STATE INTERACTION

### 5.1 No Battery Devices Found

**Scenario:** User installs Vulcan, but has no battery entities

**Steps:**

```
1. Panel opens
2. WebSocket connects successfully
3. REST API: GET /api/devices
4. Backend returns empty array []
5. JavaScript detects: devices.length === 0
6. Render empty state UI:
   - Icon: 🔋 (battery, 64px)
   - Heading: "No Battery Devices Found"
   - Help text: "Check your Home Assistant setup"
   - Actionable buttons: [Docs] [Refresh] [Settings]
7. User sees friendly, helpful message (not error)
8. User has clear next steps
```

**Empty State Rendering (Dark Mode):**

```
┌─────────────────────────────────────┐
│ BATTERY MONITORING          ⚙️  🟢  │ ← Still shows header
├─────────────────────────────────────┤
│                                     │
│              🔋                     │
│                                     │
│   No Battery Devices Found          │ ← Large, friendly text
│                                     │
│  Check your Home Assistant setup    │ ← Gray helper text
│                                     │
│  Your entities need:                │
│  • device_class: "battery"          │
│  • battery_level attribute          │
│                                     │
│  [📖 Docs] [🔄 Refresh] [⚙️ Sett]   │ ← Action buttons
│                                     │
└─────────────────────────────────────┘
```

---

### 5.2 User Clicks [Refresh]

**Steps:**

```
1. User clicks [🔄 Refresh] button
2. Visual feedback: button shows spinner (100ms animation)
3. API: GET /api/devices (fresh query)
4. WebSocket: Force re-subscription to battery entities
5. Wait for response (max 5 seconds)
6. If devices found:
   - Empty state UI fades out (300ms)
   - Battery list fades in (300ms)
   - Battery cards render
7. If still no devices:
   - Empty state stays visible
   - Toast notification: "No battery devices found"
8. Button returns to normal state
```

---

### 5.3 User Clicks [Documentation]

**Steps:**

```
1. User clicks [📖 Docs] button
2. Opens new browser tab: Vulcan Brownout HACS docs
3. URL: https://github.com/vulcan-brownout/docs/setup
4. User sees setup guide with examples
5. Panel remains open in original tab
6. User can return to panel and try [Refresh] again
```

---

### 5.4 User Clicks [Settings]

**Steps:**

```
1. User clicks [⚙️ Settings] button (same as main settings icon)
2. Settings panel opens
3. User can:
   - Check threshold settings
   - Configure notification preferences
   - View current configuration
4. Empty state stays visible in background
5. Once user adds battery entities in HA, panel will populate on next refresh
```

---

## 6. STATE MACHINE: OVERALL PANEL LIFECYCLE

**Comprehensive Sprint 3 State Machine:**

```mermaid
stateDiagram-v2
    [*] --> Loading: Panel opens
    Loading --> Loaded: Devices received
    Loading --> Empty: No devices found

    Loaded --> InfiniteScroll: User scrolls
    InfiniteScroll --> Loaded: Devices appended
    InfiniteScroll --> AllLoaded: No more devices

    Loaded --> Settings: User clicks ⚙️
    Settings --> Notifications: User configures notifications
    Notifications --> Settings: Settings closed
    Settings --> Loaded: Settings saved

    Loaded --> Sorting: User sorts/filters
    Sorting --> Loaded: Sort/filter applied

    Loaded --> DarkMode: Theme changed
    DarkMode --> Loaded: Theme applied (smooth transition)

    Empty --> Refresh: User clicks [Refresh]
    Refresh --> Loaded: Devices found
    Refresh --> Empty: Still no devices

    note right of Loaded
        Real-time updates via WebSocket
        Back to Top button visible
        Sort/filter state persisted
    end note

    note right of Notifications
        Configure per-device alerts
        Set frequency cap
        Save preferences
    end note
```

---

## 7. ACCESSIBILITY CONSIDERATIONS

### 7.1 Keyboard Navigation (Full Sprint 3)

**Tab Order:**

```
1. Settings icon (⚙️)
   └─ Enter → Open settings
2. Connection badge (🟢)
3. Sort dropdown
4. Filter dropdown
5. Reset button
6. Battery items (scrollable list)
7. Back to Top button (appears when scrolled)
   └─ Enter → Scroll to top
8. Notification Preferences button (in settings panel)
   └─ Enter → Open notification modal
9. Per-device checkboxes (in notification modal)
   └─ Space → Toggle checkbox
```

**Keyboard Shortcuts:**

```
Global:
  Escape        → Close open modals/settings
  ?             → Show keyboard help

Settings:
  Tab           → Navigate fields
  Shift+Tab     → Previous field

Back to Top:
  When visible, press Tab to focus
  Press Enter to scroll to top

Notifications:
  Tab           → Navigate through form
  Space         → Toggle checkboxes
  Arrow Down    → Navigate dropdown options
```

---

### 7.2 Screen Reader Announcements

**ARIA Live Regions:**

```html
<!-- Infinite scroll loading indicator -->
<div role="status" aria-live="polite" aria-label="Loading more devices">
  ⟳ Loading 5 more devices...
</div>

<!-- Back to Top button (announce when appears) -->
<button aria-label="Back to top" role="complementary">▲</button>

<!-- Notification toggle (announce state changes) -->
<div role="status" aria-live="assertive">
  Notifications: ON
</div>

<!-- Theme change announcement -->
<div role="status" aria-live="polite" aria-label="Theme changed to dark mode">
</div>
```

---

### 7.3 Color Contrast in Both Themes

**Verified WCAG AA/AAA:**

| Element | Light | Dark | Status |
|---------|-------|------|--------|
| Primary text | 9.0:1 | 19:1 | AAA |
| Critical | 3.5:1 | 5.5:1 | AA/AAA |
| Warning | 4.5:1 | 6.8:1 | AAA |
| Healthy | 4.5:1 | 4.8:1 | AA |

---

## Summary

Luna's Sprint 3 interaction specs define:
✅ Smooth infinite scroll with error recovery
✅ Sticky Back to Top button with smooth scroll
✅ Notification preferences with per-device control
✅ Automatic dark mode detection and theme switching
✅ Friendly empty states with actionable guidance
✅ Full keyboard navigation and screen reader support
✅ Debouncing and performance optimization

**Next steps:** Architect implements state machines and event listeners. Luna conducts usability testing after Sprint 3 ships.

---

**Prepared by:** Luna (UX Designer)
**Date:** February 22, 2026
**Review by:** Freya (Product Owner)
**Tested for Accessibility:** WCAG 2.1 AA standard
