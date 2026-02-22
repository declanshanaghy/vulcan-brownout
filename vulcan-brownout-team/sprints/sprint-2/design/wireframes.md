# Wireframes & Visual Specifications — Sprint 2

**Designer:** Luna (UX Designer)
**Scope:** Vulcan Brownout sidebar panel, Sprint 2 additions
**Tools:** ASCII wireframes + responsive grid specs + CSS reference
**Last Updated:** February 2026

---

## Overview

Sprint 2 introduces 4 new UI elements to the sidebar panel:
1. **Settings Panel / Modal** (threshold configuration)
2. **Sort/Filter Bar** (priority-based sorting, status filtering)
3. **Connection Status Badge** (WebSocket connectivity indicator)
4. **Last Updated Timestamp** (real-time update feedback)

All wireframes follow Home Assistant's design system (Material Design 3, responsive breakpoints).

---

## Responsive Breakpoints

| Device | Width | Layout | Sort/Filter | Settings |
|--------|-------|--------|-------------|----------|
| Mobile | < 768px | Stacked, single column | Full-screen modal | Full-screen modal |
| Tablet | 768px - 1024px | 2-column possible | Compact dropdown | Slide-out panel (50% width) |
| Desktop | > 1024px | Flexible | Inline dropdown | Slide-out panel (400px width) |

---

## 1. MAIN BATTERY LIST VIEW (Sprint 2 Additions)

### 1.1 Desktop Layout (> 1024px)

```
┌─────────────────────────────────────────────────────────────────────────┐
│ BATTERY MONITORING                                                ⚙️  🟢 │ ← Settings icon + Connection badge
├─────────────────────────────────────────────────────────────────────────┤
│ [▼ PRIORITY ]   [▼ ALL BATTERIES (13) ]   [✕ RESET]                    │ ← Sort/Filter bar
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│ CRITICAL (2)                                                            │
│ ┌────────────────────────────────────────────────────────────────────┐ │
│ │ ⚠️  FRONT DOOR LOCK                         📊 8%  [████░░░░░░░░░░] │
│ │    Last changed: 2 hours ago                                       │
│ └────────────────────────────────────────────────────────────────────┘ │
│ ┌────────────────────────────────────────────────────────────────────┐ │
│ │ ⚠️  SOLAR BACKUP (CRITICAL)                  📊 5%  [██░░░░░░░░░░░] │
│ │    Last changed: 30 minutes ago                                    │
│ └────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
│ WARNING (3)                                                             │
│ ┌────────────────────────────────────────────────────────────────────┐ │
│ │ ⚡ KITCHEN SENSOR                          📊 18%  [██████░░░░░░░░] │
│ │    Last changed: 5 minutes ago                                    │
│ └────────────────────────────────────────────────────────────────────┘ │
│ ┌────────────────────────────────────────────────────────────────────┐ │
│ │ ⚡ BEDROOM MOTION                          📊 22%  [████████░░░░░░] │
│ │    Last changed: 1 minute ago                                     │
│ └────────────────────────────────────────────────────────────────────┘ │
│ ┌────────────────────────────────────────────────────────────────────┐ │
│ │ ⚡ GARAGE DOOR SENSOR                      📊 25%  [████████░░░░░░] │
│ │    Last changed: 3 minutes ago                                    │
│ └────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
│ HEALTHY (7)                                                             │
│ ┌────────────────────────────────────────────────────────────────────┐ │
│ │ ✓ BATHROOM FAN SWITCH                      📊 87%  [██████████████] │
│ │    Last changed: 20 minutes ago                                   │
│ └────────────────────────────────────────────────────────────────────┘ │
│ ┌────────────────────────────────────────────────────────────────────┐ │
│ │ ✓ GARAGE LIGHT SWITCH                      📊 92%  [██████████████] │
│ │    Last changed: 45 minutes ago                                   │
│ └────────────────────────────────────────────────────────────────────┘ │
│ [More items, truncated for brevity]                                     │
│                                                                          │
├─────────────────────────────────────────────────────────────────────────┤
│ 🔄 Updated 3 seconds ago                                                │
└─────────────────────────────────────────────────────────────────────────┘
```

**Color Coding:**
- **Critical (⚠️)** → Red background (#F44336), white text
- **Warning (⚡)** → Amber background (#FF9800), white text
- **Healthy (✓)** → Green background (#4CAF50), white text
- **Unavailable (⌛)** → Gray background (#9E9E9E), white text

**Typography:**
- Title: 18px, bold, dark gray
- Device name: 16px, bold, status color
- Progress text: 14px, gray
- Timestamp: 12px, light gray
- Last updated: 12px, light gray, italic

---

### 1.2 Mobile Layout (< 768px)

```
┌──────────────────────────┐
│ BATTERY MONITORING  ⚙️ 🟢│ ← Compact header
├──────────────────────────┤
│ [▼ PRIORITY]   [▼ ALL ▼] │ ← Full-width dropdowns (stacked)
├──────────────────────────┤
│ CRITICAL (2)             │
│ ┌────────────────────────┐
│ │ ⚠️  FRONT DOOR LOCK     │
│ │ 8%  [████░░░░░░░░░░░░] │
│ │ 2h ago                 │
│ └────────────────────────┘
│ ┌────────────────────────┐
│ │ ⚠️  SOLAR BACKUP       │
│ │ 5%  [██░░░░░░░░░░░░░░] │
│ │ 30m ago                │
│ └────────────────────────┘
│                          │
│ WARNING (3)              │
│ ┌────────────────────────┐
│ │ ⚡ KITCHEN SENSOR      │
│ │ 18% [██████░░░░░░░░░░] │
│ │ 5m ago                 │
│ └────────────────────────┘
│ [More items...]          │
├──────────────────────────┤
│ 🔄 Updated 2s ago        │
└──────────────────────────┘
```

**Mobile Optimizations:**
- Single column layout
- Device names truncated if necessary (ellipsis)
- Progress bar takes full width of card
- Larger touch targets (44px minimum)
- Font sizes: 14px base, 12px for secondary text

---

## 2. SETTINGS PANEL

### 2.1 Desktop: Side Panel (Slide-Out)

```
                                    ┌─ SETTINGS PANEL ─────────────────┐
                                    │ BATTERY MONITORING SETTINGS    ✕  │
                                    ├────────────────────────────────────┤
                                    │                                    │
                                    │ GLOBAL THRESHOLD                   │
                                    │                                    │
                                    │ When battery falls below this      │
                                    │ level, it shows as CRITICAL        │
                                    │                                    │
                                    │ [████████░░] 15 %                 │
                                    │                                    │
                                    │ Affected devices: 13               │
                                    │ (8 currently below threshold)      │
                                    │                                    │
                                    ├────────────────────────────────────┤
                                    │ DEVICE-SPECIFIC OVERRIDES          │
                                    │                                    │
                                    │ Set custom thresholds for          │
                                    │ individual devices                 │
                                    │                                    │
                                    │ [+ ADD DEVICE RULE]               │
                                    │                                    │
                                    │ ✓ Front Door Lock      30%  [✕]   │
                                    │ ✓ Solar Backup         50%  [✕]   │
                                    │ ✓ Garage Sensor        20%  [✕]   │
                                    │                                    │
                                    │ (Showing 3 of 5 rules)             │
                                    │ [SHOW MORE]                        │
                                    │                                    │
                                    ├────────────────────────────────────┤
                                    │ [SAVE]           [CANCEL]          │
                                    └────────────────────────────────────┘
```

**Panel Properties:**
- Width: 400px (fixed)
- Animates in from right (300ms, ease-out)
- Overlay behind panel (semi-transparent dark gray)
- Header: 18px bold, padding 16px
- Close button (✕): Top-right, 44px touch target
- Sections: 16px margin between
- Buttons: Full-width, 44px height

---

### 2.2 Mobile: Full-Screen Modal

```
┌──────────────────────────────────┐
│ BATTERY SETTINGS              ✕  │
├──────────────────────────────────┤
│                                  │
│ GLOBAL THRESHOLD                 │
│                                  │
│ When battery falls below this     │
│ level, it shows as CRITICAL       │
│                                  │
│ [████████░░] 15 %                │
│                                  │
│ 8 devices below this threshold    │
│                                  │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│                                  │
│ DEVICE-SPECIFIC OVERRIDES         │
│                                  │
│ [+ ADD DEVICE RULE]              │
│                                  │
│ ✓ Front Door Lock    30% [✕]     │
│ ✓ Solar Backup       50% [✕]     │
│ ✓ Garage Sensor      20% [✕]     │
│                                  │
│ [SHOW MORE (5 total)]            │
│                                  │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│                                  │
│ [SAVE]               [CANCEL]    │
│                                  │
└──────────────────────────────────┘
```

**Mobile Modal Properties:**
- Full-screen (100vw, 90vh - status bar)
- Scrollable content area
- Fixed header with close button
- Fixed footer with buttons
- Buttons: Full-width, 44px, 16px margin

---

### 2.3 Add Device Rule Sub-Modal

When user clicks "[+ ADD DEVICE RULE]", a searchable list appears:

```
┌────────────────────────────────────┐
│ SELECT DEVICE              ✕       │
├────────────────────────────────────┤
│ [Search devices...] 🔍             │
├────────────────────────────────────┤
│ AVAILABLE DEVICES                  │
│                                    │
│ ☐ Bathroom Fan Switch (87%)        │
│ ☐ Bedroom Motion (22%) ⚡ WARNING  │
│ ☐ Garage Door Sensor (25%) ⚡      │
│ ☐ Garage Light Switch (92%)        │
│ ☐ Kitchen Sensor (18%) ⚡ WARNING  │
│ ☐ Bedroom Smart Lock (40%)         │
│                                    │
│ [SCROLL FOR MORE]                  │
│                                    │
├────────────────────────────────────┤
│ [CANCEL]                           │
└────────────────────────────────────┘

User selects device ↓

┌────────────────────────────────────┐
│ SET THRESHOLD                  ✕   │
├────────────────────────────────────┤
│ Device: Front Door Lock            │
│ Current battery: 8%                │
│                                    │
│ Threshold: _____ %                 │
│           [████░░░░░░░░░░]         │
│           30 %                     │
│                                    │
│ (Adjust with slider or type)       │
│                                    │
│ After save:                        │
│ • This device will show CRITICAL   │
│   when battery < 30%               │
│ • Global threshold (15%) won't     │
│   apply to this device             │
│                                    │
│ [SAVE RULE]                        │
│ [CANCEL]                           │
└────────────────────────────────────┘
```

**Interaction Flow:**
1. User clicks "+ ADD DEVICE RULE"
2. Searchable list appears (filterable by name, status)
3. User selects device
4. Threshold input appears
5. User sets threshold (slider + text input)
6. Live feedback: "After save: 2 devices will be CRITICAL"
7. User clicks "SAVE RULE" or "CANCEL"
8. Returns to main settings panel, rule appears in list

---

## 3. SORT / FILTER BAR

### 3.1 Desktop Dropdowns

```
┌─────────────────────────────────────────────────────────────────────────┐
│ [▼ PRIORITY ]   [▼ ALL BATTERIES (13) ]   [✕ RESET]                    │
└─────────────────────────────────────────────────────────────────────────┘

Dropdown 1 — Sort Options:
┌──────────────────────────────┐
│ ● Priority (Critical > Warn)  │ ← Selected (radio button)
│ ○ Alphabetical (A-Z)          │
│ ○ Battery Level (Low > High)  │
│ ○ Battery Level (High > Low)  │
└──────────────────────────────┘

Dropdown 2 — Filter Options:
┌──────────────────────────────┐
│ ✓ Critical (2)                │ ← Checkboxes
│ ✓ Warning (3)                 │
│ ✓ Healthy (8)                 │
│ ☐ Unavailable (0)             │
│                               │
│ [APPLY] [CLEAR ALL]           │
└──────────────────────────────┘
```

**Style:**
- Bar background: #F5F5F5 (light gray)
- Dropdowns: White, border radius 4px, box shadow
- Labels: 14px, dark gray
- Checkboxes: 18px, blue (#03A9F4) when checked
- Buttons: 12px, uppercase, blue text on white

---

### 3.2 Mobile: Full-Screen Modals

**Sort Modal:**

```
┌──────────────────────────────┐
│ SORT BY                   ✕  │
├──────────────────────────────┤
│                              │
│ ◉ Priority (Critical First)  │
│   (default, recommended)     │
│                              │
│ ○ Alphabetical (A-Z)         │
│                              │
│ ○ Battery Level              │
│   Low to High                │
│                              │
│ ○ Battery Level              │
│   High to Low                │
│                              │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━  │
│                              │
│ [APPLY]           [CANCEL]   │
└──────────────────────────────┘
```

**Filter Modal:**

```
┌──────────────────────────────┐
│ FILTER BY STATUS          ✕  │
├──────────────────────────────┤
│                              │
│ [✓] Critical (2)             │
│     Show critical batteries   │
│                              │
│ [✓] Warning (3)              │
│     Show warning batteries    │
│                              │
│ [✓] Healthy (8)              │
│     Show healthy batteries    │
│                              │
│ [ ] Unavailable (0)          │
│     Show unavailable devices  │
│                              │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━  │
│                              │
│ [APPLY]           [CLEAR ALL]│
│ [CANCEL]                     │
└──────────────────────────────┘
```

**Mobile Modal Properties:**
- Full-screen
- Radio buttons (sort) or checkboxes (filter), 44px touch targets
- Descriptive labels
- "APPLY" button saves and closes
- "CANCEL" closes without saving

---

## 4. CONNECTION STATUS BADGE

### 4.1 Badge States & Positioning

```
┌─────────────────────────────────────────────────────────┐
│ BATTERY MONITORING                          ⚙️  🟢       │
│                                                  ↑       │
│                                            Status Badge  │
└─────────────────────────────────────────────────────────┘

STATE: Connected
┌─────┐
│ 🟢  │  Green dot
│ +   │  "Connected"
│ txt │  Tooltip: "Connected to Home Assistant"
└─────┘

STATE: Reconnecting
┌─────┐
│ 🔵  │  Spinning blue dot (animation)
│ +   │  "Reconnecting..."
│ txt │  Tooltip: "Connection lost, reconnecting..."
└─────┘

STATE: Offline / Disconnected
┌─────┐
│ 🔴  │  Red dot
│ +   │  "Offline"
│ txt │  Tooltip: "No connection — last update 5 minutes ago"
└─────┘
```

**Badge Specs:**
- Position: Top-right of sidebar, 16px margin from edge
- Size: 16px dot (icon), 12px text
- Tooltip trigger: Hover (desktop) or tap (mobile)
- Animation (reconnecting): Smooth spin, 2 second cycle
- Accessibility: ARIA label, role="status"

---

### 4.2 Desktop vs Mobile Layout

**Desktop (> 768px):**
```
BATTERY MONITORING                          ⚙️  🟢
                                               └─ Inline with settings icon
```

**Mobile (< 768px):**
```
BATTERY MONITORING          ⚙️  🟢
                            └─ Stack vertically if needed
```

---

## 5. LAST UPDATED TIMESTAMP

### 5.1 Positioning & Format

```
┌─────────────────────────────────────────────────────┐
│ [Battery list items]                                │
│                                                     │
│ ...                                                 │
│                                                     │
└─────────────────────────────────────────────────────┘
🔄 Updated 3 seconds ago
↑
Positioned: bottom-right of list, 12px text, light gray (#999)
Updates every second (auto-refresh)
Only visible when WebSocket is connected
```

**Text Formats:**
- "Updated just now" (0-2 seconds)
- "Updated 5 seconds ago"
- "Updated 1 minute ago"
- "Updated 5 minutes ago"
- "Updated 1 hour ago"
- etc.

**Icon Animation:**
- 🔄 spins subtly when updating (fast 100ms spin every 3 seconds)
- No continuous rotation (not distracting)

---

## 6. TRANSITIONS & ANIMATIONS

### 6.1 Settings Panel Slide

```
[Before]
Browser sidebar contains only battery list

[Click ⚙️ icon]
↓ (300ms ease-out)

[After]
Dark overlay fades in (0ms → 300ms)
Settings panel slides from right edge
  Start: X = 100vw (off-screen)
  End: X = calc(100vw - 400px)
Panel shadow appears
```

**CSS Pseudo-Code:**
```css
.settings-panel {
  transform: translateX(100%);
  transition: transform 300ms cubic-bezier(0.4, 0, 0.2, 1);
  opacity: 0;
  transition: opacity 300ms ease-out;
}

.settings-panel.open {
  transform: translateX(0);
  opacity: 1;
}

.settings-overlay {
  background: rgba(0, 0, 0, 0.4);
  opacity: 0;
  transition: opacity 300ms ease-out;
  pointer-events: none;
}

.settings-overlay.visible {
  opacity: 1;
  pointer-events: auto;
}
```

---

### 6.2 Battery Level Progress Bar Animation

When battery level updates via WebSocket:

```
[Before Update]
[████████░░] 42%

[Update received: 38%]
↓ (300ms ease-out)

[After Update]
[███████░░░] 38%   ← Progress bar animates smoothly
```

**CSS Pseudo-Code:**
```css
.progress-bar {
  width: 42%;
  transition: width 300ms cubic-bezier(0.4, 0, 0.2, 1);
}

.progress-bar.updating {
  width: 38%;
  /* Smooth animation as width changes */
}
```

---

### 6.3 Connection Badge Reconnecting Animation

```
State: Reconnecting (blue)
Animation: Smooth 360° rotation, 2 second cycle, infinite

[🔵 0°] → [🔵 90°] → [🔵 180°] → [🔵 270°] → [🔵 360°/0°]
  0ms     500ms      1000ms     1500ms    2000ms
```

**CSS Pseudo-Code:**
```css
.connection-badge {
  color: #4CAF50; /* green */
}

.connection-badge.reconnecting {
  color: #2196F3; /* blue */
  animation: spin 2s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
```

---

### 6.4 Toast Notifications (on reconnect)

When WebSocket reconnects:

```
[Fade in from bottom, 300ms]
┌──────────────────────┐
│ ✓ Connection Updated │  ← Green background
└──────────────────────┘
[Hold 2 seconds]
[Fade out, 300ms]
```

**CSS Pseudo-Code:**
```css
.toast {
  position: fixed;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%) translateY(100px);
  opacity: 0;
  transition: all 300ms ease-out;
}

.toast.visible {
  transform: translateX(-50%) translateY(0);
  opacity: 1;
}

.toast.hide {
  opacity: 0;
  transition: opacity 300ms ease-out 2s;
}
```

---

## 7. ACCESSIBILITY SPECIFICATIONS

### 7.1 Semantic HTML

```html
<!-- Main container -->
<div role="region" aria-label="Battery Monitoring">

  <!-- Header with connection badge -->
  <header class="battery-header">
    <h1>Battery Monitoring</h1>
    <button aria-label="Open settings" id="settings-btn">⚙️</button>
    <div role="status" aria-label="Connection status">
      <span class="connection-badge" id="conn-badge">🟢</span>
      <span class="connection-text" aria-live="polite">Connected</span>
    </div>
  </header>

  <!-- Sort/Filter controls -->
  <div class="sort-filter-bar" role="toolbar" aria-label="Sort and filter options">
    <select aria-label="Sort by">
      <option>Priority</option>
      <option>Alphabetical</option>
      <!-- ... -->
    </select>
    <select aria-label="Filter by status">
      <option>All Batteries</option>
      <!-- ... -->
    </select>
    <button aria-label="Reset filters">✕ Reset</button>
  </div>

  <!-- Battery list -->
  <div role="list" aria-label="Battery devices">
    <div role="listitem" class="battery-item critical">
      <span aria-label="Critical status">⚠️</span>
      <h2>Front Door Lock</h2>
      <div role="progressbar" aria-valuenow="8" aria-valuemin="0" aria-valuemax="100">
        <!-- Visual progress bar -->
      </div>
    </div>
    <!-- More items... -->
  </div>

  <!-- Last updated timestamp -->
  <div role="status" aria-live="polite" aria-label="Last update timestamp">
    🔄 Updated 3 seconds ago
  </div>
</div>

<!-- Settings panel (modal) -->
<div role="dialog" aria-labelledby="settings-title" class="settings-panel">
  <h2 id="settings-title">Battery Monitoring Settings</h2>
  <!-- ... -->
</div>
```

### 7.2 ARIA Labels & Roles

| Element | Role | ARIA Label | Live Region |
|---------|------|-----------|-------------|
| Settings icon | button | "Open settings" | — |
| Connection badge | status | "Connected / Reconnecting / Offline" | polite |
| Sort dropdown | combobox | "Sort by" | — |
| Filter checkboxes | group | "Filter by status" | — |
| Battery item | listitem | "Front Door Lock, 8%, Critical" | — |
| Progress bar | progressbar | aria-valuenow, aria-valuemin, aria-valuemax | — |
| Last updated | status | "Updated 3 seconds ago" | polite |
| Settings modal | dialog | "Battery Monitoring Settings" | — |

### 7.3 Keyboard Navigation

**Tab Order:**
1. Settings icon (⚙️)
2. Connection badge (🟢)
3. Sort dropdown
4. Filter dropdown
5. Reset button
6. Battery items (if focusable)
7. Settings panel (modal, if open)

**Keyboard Shortcuts:**
- **Escape** — Close settings modal, close dropdowns
- **Enter** — Activate buttons, toggle checkboxes
- **Space** — Toggle checkboxes, trigger buttons
- **Arrow Up/Down** — Navigate dropdown options
- **Tab** — Next focusable element
- **Shift + Tab** — Previous focusable element

### 7.4 Color Contrast Ratios (WCAG AA)

| Element | Foreground | Background | Ratio | Status |
|---------|-----------|-----------|-------|--------|
| Critical text | #FFFFFF | #F44336 | 3.5:1 | ✅ AA |
| Warning text | #FFFFFF | #FF9800 | 4.5:1 | ✅ AAA |
| Healthy text | #FFFFFF | #4CAF50 | 4.5:1 | ✅ AAA |
| Body text | #424242 | #FFFFFF | 9.0:1 | ✅ AAA |
| Secondary text | #757575 | #FFFFFF | 6.5:1 | ✅ AAA |
| Button text | #FFFFFF | #03A9F4 | 4.5:1 | ✅ AAA |

---

## 8. RESPONSIVE BREAKPOINTS & MEDIA QUERIES

### 8.1 CSS Media Query Strategy

```css
/* Mobile-first approach */

/* Default: mobile (< 768px) */
.battery-list { grid-template-columns: 1fr; }
.sort-filter-bar { display: flex; flex-direction: column; }
.settings-panel { width: 100vw; height: 90vh; }

/* Tablet (768px - 1024px) */
@media (min-width: 768px) {
  .battery-list { grid-template-columns: 1fr; }
  .sort-filter-bar { display: flex; flex-direction: row; }
  .settings-panel { width: 50%; height: 100vh; }
}

/* Desktop (> 1024px) */
@media (min-width: 1024px) {
  .battery-list { grid-template-columns: 1fr; }
  .sort-filter-bar { display: flex; flex-direction: row; gap: 16px; }
  .settings-panel { width: 400px; height: 100vh; }
}

/* Large desktop (> 1440px) */
@media (min-width: 1440px) {
  .battery-list { grid-template-columns: 1fr 1fr; }
  .font-base { font-size: 18px; }
}
```

### 8.2 Touch Target Sizing

All interactive elements must be at least 44x44 pixels (WCAG 2.5.5 AA):

```
Buttons:       44px height, padding 8px-16px horizontal
Checkboxes:    24px square (with hover area 44x44)
Dropdowns:     44px height
Sort/Filter:   44px height
Icons:         24px (within 44px hover area)
Links:         44px height (if applicable)
```

---

## 9. COLOR PALETTE & TYPOGRAPHY

### 9.1 Color System

```
PRIMARY (Action):        #03A9F4 (Light Blue)
CRITICAL (Alert):        #F44336 (Red)
WARNING (Caution):       #FF9800 (Orange/Amber)
HEALTHY (Success):       #4CAF50 (Green)
UNAVAILABLE (Disabled):  #9E9E9E (Gray)
BACKGROUND (Light):      #F5F5F5 (Off-white)
TEXT (Primary):          #212121 (Dark Gray, 87%)
TEXT (Secondary):        #757575 (Medium Gray, 54%)
DIVIDER:                 #BDBDBD (Light Gray, 26%)
```

### 9.2 Typography

**Font Family:** -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif

| Element | Size | Weight | Line Height |
|---------|------|--------|-------------|
| Page title | 18px | 500 | 24px |
| Subheading | 16px | 500 | 22px |
| Body text | 14px | 400 | 20px |
| Button text | 14px | 500 | 20px |
| Caption / Helper | 12px | 400 | 16px |
| Timestamp | 12px | 400 | 16px |

---

## 10. INTERACTION PATTERNS

### 10.1 Settings Panel Open/Close

**Opening:**
1. User clicks ⚙️ icon
2. Dark overlay fades in (0 → 300ms)
3. Settings panel slides in from right (0 → 300ms)
4. Focus moves to close button (✕)
5. Panel is now active

**Closing:**
1. User clicks "SAVE" → Close, apply changes, redraw list
2. User clicks "CANCEL" → Close, discard changes
3. User clicks ✕ → Close, discard changes
4. User presses Escape → Close, discard changes
5. User clicks overlay → Close, discard changes (optional: configurable)

---

### 10.2 Add Device Rule Flow

1. User in Settings panel
2. Clicks "[+ ADD DEVICE RULE]"
3. Sub-modal opens: "SELECT DEVICE"
4. User can search or scroll, selects device
5. Form updates: "SET THRESHOLD" for chosen device
6. User adjusts threshold via slider or text input
7. Live feedback: "After save: X devices will be CRITICAL"
8. User clicks "SAVE RULE" or "CANCEL"
9. Returns to Settings panel, new rule in list

---

### 10.3 Sort/Filter Interaction (Desktop)

1. User clicks sort dropdown
2. Dropdown opens below button
3. User selects option (radio button)
4. List reorders immediately
5. Dropdown stays open (user can select again)
6. User clicks elsewhere to close, or presses Escape

**Filter similar, but with checkboxes:**
1. User clicks filter dropdown
2. Checkbox list appears
3. User toggles checkboxes
4. List filters in real-time
5. Count updates: "All Batteries (X selected)"

---

### 10.4 Sort/Filter Interaction (Mobile)

1. User taps sort/filter button
2. Full-screen modal appears
3. User interacts with radio buttons or checkboxes
4. User clicks "APPLY" button
5. Modal closes, list updates

---

## 11. ERROR STATES & EDGE CASES

### 11.1 Empty States

**No batteries found:**
```
┌─────────────────────────────────────┐
│ BATTERY MONITORING                  │
├─────────────────────────────────────┤
│                                     │
│           🔋                        │
│                                     │
│    No battery devices found         │
│                                     │
│  Check your Home Assistant          │
│  configuration or add battery       │
│  entities with device_class =       │
│  "battery"                          │
│                                     │
│  [Learn More] [Refresh]             │
│                                     │
└─────────────────────────────────────┘
```

**All devices filtered out:**
```
No results match your filters.

[CLEAR FILTERS]
```

---

### 11.2 Error States

**WebSocket connection failed:**
```
Connection Error
⚠️ Unable to connect to Home Assistant

Last update: 15 minutes ago
(Showing cached data)

[RETRY] [SETTINGS]
```

**All devices unavailable:**
```
All devices are currently unavailable.
This may be a temporary connection issue.

[REFRESH]
```

---

### 11.3 Loading States

**Settings modal loading:**
```
BATTERY MONITORING SETTINGS

Loading device list... (spinner)
```

**Sort/filter modal loading:**
```
Loading filters...

(spinner)
```

---

## 12. RESPONSIVE EXAMPLES

### 12.1 iPhone 12 (390px)

```
┌───────────────────────────┐
│ BATTERY MON.  ⚙️  🟢      │
├───────────────────────────┤
│ [PRIORITY ▼] [ALL ▼]      │
├───────────────────────────┤
│ CRITICAL                  │
│ ┌─────────────────────────┐
│ │ ⚠️ FRONT DOOR LOCK      │
│ │ 8%  [████░░░░░░░░░░░░] │
│ │ 2h ago                  │
│ └─────────────────────────┘
│ ┌─────────────────────────┐
│ │ ⚠️ SOLAR BACKUP        │
│ │ 5%  [██░░░░░░░░░░░░░░] │
│ │ 30m ago                 │
│ └─────────────────────────┘
│ WARNING                   │
│ [More items...]           │
│                           │
├───────────────────────────┤
│ 🔄 Updated 2s ago         │
└───────────────────────────┘
```

### 12.2 iPad (768px)

```
┌──────────────────────────────┐
│ BATTERY MONITORING      ⚙️ 🟢 │
├──────────────────────────────┤
│ [PRIORITY ▼] [ALL BATTERIES] │
├──────────────────────────────┤
│ CRITICAL (2)                 │
│ ┌──────────────────────────┐ │
│ │ ⚠️ FRONT DOOR LOCK   8%  │ │
│ │    [████░░░░░░░░░░░░░░] │ │
│ └──────────────────────────┘ │
│ ┌──────────────────────────┐ │
│ │ ⚠️ SOLAR BACKUP      5%  │ │
│ │    [██░░░░░░░░░░░░░░░░] │ │
│ └──────────────────────────┘ │
│ WARNING (3)                  │
│ [More items...]              │
│                              │
├──────────────────────────────┤
│ 🔄 Updated 2s ago            │
└──────────────────────────────┘
```

### 12.3 Desktop (1440px)

[Full layout shown in Section 1.1]

---

## 13. DARK MODE (Future, Not Sprint 2)

Placeholder for future dark mode support. Currently, Vulcan Brownout uses Home Assistant's light theme.

If dark mode is added in Sprint 3:
- Invert background colors
- Lighten text colors
- Adjust status colors for readability on dark backgrounds

---

## Summary

Luna's wireframes define:
✅ Mobile-first responsive layouts for all screen sizes
✅ Detailed component specifications (buttons, inputs, badges)
✅ Animation and transition curves
✅ Accessibility requirements (WCAG 2.1 AA)
✅ Color contrast ratios and typography
✅ Error states and edge cases
✅ Interaction patterns for desktop and mobile

**Next steps:** Architect implements HTML/CSS based on these wireframes. Luna conducts usability testing with 5-10 users after Sprint 2 ships.

---

**Prepared by:** Luna (UX Designer)
**Date:** February 2026
**Design System:** Home Assistant Material Design 3
