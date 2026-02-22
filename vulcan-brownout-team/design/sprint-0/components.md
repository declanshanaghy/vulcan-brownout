# Vulcan Brownout: Component Specifications

## Component: Battery Device Card

### Purpose
Displays a single battery-powered device with its current battery level, status icon, and visual indicators. The primary repeating element in the main list.

### Visual Design

#### Layout
- **Structure**: Horizontal flex layout (flex-direction: row)
- **Dimensions**:
  - Height: 72px (base) + 8px progress bar
  - Width: 100% (fills container)
  - Padding: 12px 16px
  - Border radius: 8px
- **Content regions**:
  - Left: Icon area (40px)
  - Center: Device name + battery level text (flex: 1)
  - Right: Status badge (60px)

#### Color Scheme (using HA CSS custom properties)

**Critical State** (battery ≤ threshold, default 15%)
```css
background-color: var(--error-color-background); /* Light red/orange */
--status-icon-color: var(--error-color); /* Red */
--text-color: var(--text-primary-color);
--progress-bar-color: var(--error-color); /* Red fill */
```

**Low State** (threshold < battery ≤ threshold+15%, e.g., 15% to 30%)
```css
background-color: var(--warning-color-background); /* Light amber */
--status-icon-color: var(--warning-color); /* Amber */
--text-color: var(--text-primary-color);
--progress-bar-color: var(--warning-color); /* Amber fill */
```

**Healthy State** (battery > threshold+15%)
```css
background-color: var(--card-background-color); /* Default card bg */
--status-icon-color: var(--success-color); /* Green */
--text-color: var(--text-secondary-color);
--progress-bar-color: var(--success-color); /* Green fill */
```

**Unavailable State**
```css
background-color: var(--divider-color); /* Light gray */
--status-icon-color: var(--disabled-text-color); /* Gray */
--text-color: var(--disabled-text-color);
--progress-bar-color: transparent;
```

#### Typography
- **Device name**: `var(--body1-font-family)`, 14px, weight 500, `--text-primary-color`
- **Battery level**: `var(--body2-font-family)`, 12px, weight 400, `--text-secondary-color`
- **Status badge text**: `var(--caption-font-family)`, 11px, weight 500, `--text-secondary-color`

#### Icons
- **Device icon**: `ha-icon` component, 24px, color matches status
  - Example: `icon="mdi:lock-outline"` (lock icon for door locks)
  - Can be customized per device_class in integration config
- **Status indicator**: Small dot or colored badge
  - Critical: ⚠️ or red dot
  - Healthy: ✓ or green dot
  - Unavailable: ❌ or gray X

#### Progress Bar
- **Location**: Bottom edge of card
- **Height**: 4px
- **Fill width**: Percentage of battery level (0-100%)
- **Color**: Inherits from status color scheme
- **Background**: `var(--divider-color)` (unfilled portion)
- **Animation**: Smooth transition when value changes (300ms cubic-bezier(0.4, 0, 0.2, 1))

### Props/Data

```typescript
interface BatteryDeviceCardProps {
  entityId: string;           // "sensor.front_door_lock_battery"
  friendlyName: string;       // "Front Door Lock"
  batteryLevel: number | null; // 0-100, null if unavailable
  isUnavailable: boolean;      // true if entity state is "unavailable"
  status: "critical" | "low" | "healthy" | "unavailable";
  lastUpdated: ISO8601string;  // "2025-02-22T14:32:00Z"
  threshold: number;           // 15 (default, for display purposes)
  icon?: string;               // "mdi:lock-outline" (optional override)
  deviceClass?: string;        // "door", "motion", etc. (from HA)
}
```

### States

#### Healthy State
```
┌──────────────────────────────────────────┐
│ 🟢 Bedroom Window Sensor    78%           │
├──────────────────────────────────────────┤
│ ██████████████░░░░░░░░░░░░░░░░░░░░░░   │
└──────────────────────────────────────────┘
```
- Card background: Default `--card-background-color`
- Icon color: Green (`--success-color`)
- Text color: Secondary gray
- Progress bar: Green, 78% filled

#### Critical State
```
┌──────────────────────────────────────────┐
│ 🔴 Front Door Lock          12%  ⚠️       │
├──────────────────────────────────────────┤
│ ████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │
└──────────────────────────────────────────┘
```
- Card background: Light red/orange (`--error-color-background`)
- Icon color: Red (`--error-color`)
- Status badge: "Battery Critical" in red
- Progress bar: Red, 12% filled
- Text: High contrast on colored background

#### Unavailable State
```
┌──────────────────────────────────────────┐
│ ❌ Garage Door Sensor    Unavailable      │
├──────────────────────────────────────────┤
│                                          │
└──────────────────────────────────────────┘
```
- Card background: Light gray (`--divider-color`)
- Icon: X mark or error icon, gray color
- Battery level: Hidden or shown as "—"
- Progress bar: Hidden or very faint gray
- Text: Gray/disabled color
- Optional subtitle: "Device offline or battery depleted"

#### Hover State (Desktop)
```
┌──────────────────────────────────────────┐
│ 🟢 Bedroom Window Sensor    78%  [⋯]     │
├──────────────────────────────────────────┤
│ ██████████████░░░░░░░░░░░░░░░░░░░░░░   │
└──────────────────────────────────────────┘
```
- Subtle background color shift (5% lighter/darker)
- Context menu button (three dots) appears on right
- Cursor changes to pointer

#### Loading/Skeleton State
```
┌──────────────────────────────────────────┐
│ ░░░░░░░░░░░░░░░░░░ ░░░░░░░░░░░░░░░░░░ │
│                                          │
└──────────────────────────────────────────┘
```
- Content replaced with shimmer animation
- Height: 72px (same as card)
- Gray placeholder background
- Shimmer effect (left to right, 1.2s duration)

### Accessibility

#### ARIA Attributes
```html
<div
  role="article"
  aria-label="Front Door Lock battery at 12 percent, below threshold"
  aria-live="polite"
  aria-atomic="false"
>
  <!-- Card content -->
</div>
```

#### Keyboard Navigation
- **Focusable**: Yes, via Tab key
- **Interaction**: Enter to expand/view details (if implemented)
- **Visual focus indicator**: `outline: 2px solid var(--primary-color)`, offset 2px

#### Screen Reader Text
- Device name is primary label
- Battery level announced: "Battery at 12 percent"
- Status announced: "Critical - below 15 percent threshold" or "Unavailable - sensor offline"
- Last updated time provided via aria-label or hidden visually

#### Color Contrast
- All text meets WCAG AA (4.5:1 for normal text, 3:1 for large text)
- Status colors not relied upon alone; icons and text backup meaning
- Progress bar visible to colorblind users (shape + color)

---

## Component: Status Badge

### Purpose
Compact indicator showing the device's battery status at a glance. Positioned on right side of card or as standalone element.

### Visual Design

#### Layout
- **Dimensions**: 56px width, 32px height
- **Border radius**: 4px
- **Padding**: 6px 8px
- **Font**: `var(--caption-font-family)`, 11px, weight 500

#### Color Scheme

**Critical Badge**
```css
background-color: var(--error-color); /* Red */
color: white;
border: 1px solid var(--error-color-dark);
```

**Low Badge**
```css
background-color: var(--warning-color); /* Amber */
color: white;
border: 1px solid var(--warning-color-dark);
```

**Healthy Badge** (hidden or subtle)
```css
background-color: transparent;
color: var(--text-secondary-color);
```

**Unavailable Badge**
```css
background-color: var(--disabled-text-color-background);
color: var(--disabled-text-color);
border: 1px solid var(--divider-color);
```

#### Icons
- **Critical**: Warning triangle or exclamation mark icon (mdi:alert)
- **Low**: Yellow warning icon
- **Healthy**: Check mark (hidden until critical)
- **Unavailable**: X or error icon (mdi:alert-circle-outline)

### Props/Data

```typescript
interface StatusBadgeProps {
  status: "critical" | "low" | "healthy" | "unavailable";
  batteryLevel?: number; // 12, null for unavailable
  threshold?: number;    // 15
}
```

### States

- **Critical**: Red background, white text, warning icon, text "Battery Critical"
- **Low**: Amber background, white text, text "Battery Low"
- **Healthy**: Transparent, hidden or very subtle
- **Unavailable**: Gray background, gray text, error icon, text "Unavailable"

### Accessibility

```html
<span
  role="status"
  aria-label="Battery Critical - 12 percent, below 15 percent threshold"
>
  ⚠️ Battery Critical
</span>
```

- Semantic `role="status"` for dynamic updates
- aria-label provides full context
- Icon + text ensures clarity for all users

---

## Component: Sort Controls

### Purpose
Dropdown and toggle buttons for changing list sort order and direction.

### Visual Design

#### Layout
- **Container**: Horizontal flex, gap 8px
- **Dropdown**: 140px width, height 36px
- **Toggle button**: 36px × 36px square
- **Spacing**: Integrated into header (16px padding)

#### Color Scheme
```css
background-color: var(--mdc-theme-surface);
border: 1px solid var(--divider-color);
border-radius: 4px;
color: var(--text-primary-color);
```

Hover state:
```css
background-color: var(--hover-color);
border-color: var(--primary-color);
```

Active/dropdown open:
```css
border-color: var(--primary-color);
box-shadow: 0 2px 6px rgba(0, 0, 0, 0.12);
```

#### Typography
- Label: `var(--body2-font-family)`, 13px, weight 500
- Menu items: `var(--body2-font-family)`, 13px, weight 400

#### Icons
- Dropdown chevron: `mdi:chevron-down`
- Sort direction: `mdi:chevron-up` (ascending) or `mdi:chevron-down` (descending)
- Toggle button shows both icons side-by-side with divider

### Props/Data

```typescript
interface SortControlsProps {
  currentSort: "level" | "name" | "status" | "updated";
  sortDirection: "asc" | "desc";
  onSortChange: (sort: string) => void;
  onDirectionToggle: () => void;
}

const sortOptions = [
  { label: "Battery Level", value: "level" },
  { label: "Device Name", value: "name" },
  { label: "Status", value: "status" },
  { label: "Last Updated", value: "updated" },
];
```

### States

#### Closed Dropdown
```
┌─────────────────────┬──────┐
│ 🔋 Battery Level ▼  │ ↑↓  │
└─────────────────────┴──────┘
```
- Clean label showing current sort
- Chevron indicates expandable

#### Open Dropdown
```
┌─────────────────────┐
│ 🔋 Battery Level ✓  │
├─────────────────────┤
│ Device Name         │
│ Status              │
│ Last Updated        │
└─────────────────────┘
```
- Current selection has checkmark
- Hover highlights menu items (background color shift)

#### Toggle Direction
```
┌──────┐
│ ↓    │ (descending, critical-first)
└──────┘

↓ (after click) ↑ (ascending, healthy-first)
┌──────┐
│ ↑    │
└──────┘
```
- Icon rotates or flips based on direction

### Accessibility

```html
<select
  aria-label="Sort by"
  aria-describedby="sort-info"
>
  <option value="level" selected>Battery Level</option>
  <option value="name">Device Name</option>
  <option value="status">Status</option>
  <option value="updated">Last Updated</option>
</select>

<button
  aria-label="Reverse sort order"
  aria-pressed="false"
>
  ↑↓
</button>
```

- Select semantic element for dropdown
- Button with `aria-pressed` for toggle
- Keyboard navigation: Tab to controls, Enter/Space to activate
- Dropdown: Arrow keys to navigate options

---

## Component: Filter Bar

### Purpose
Dropdown selector for filtering devices by status or type.

### Visual Design

#### Layout
- **Container**: 140px width (matching sort dropdown), height 36px
- **Padding**: 8px 12px
- **Border radius**: 4px
- **Positioned**: Left side of control bar, next to sort controls

#### Color Scheme
```css
background-color: var(--mdc-theme-surface);
border: 1px solid var(--divider-color);
color: var(--text-primary-color);

&:hover {
  border-color: var(--primary-color);
  background-color: var(--hover-color);
}

&:active {
  border-color: var(--primary-color);
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.12);
}
```

#### Typography
- `var(--body2-font-family)`, 13px, weight 500

#### Icons
- Dropdown chevron: `mdi:chevron-down`
- Filter icon (optional): `mdi:filter` or `mdi:funnel`

### Props/Data

```typescript
interface FilterBarProps {
  currentFilter: "all" | "critical" | "healthy" | "unavailable" | "exclude-unavailable";
  onFilterChange: (filter: string) => void;
  counts: {
    critical: number;
    healthy: number;
    unavailable: number;
  };
}

const filterOptions = [
  { label: "All Devices", value: "all", count: 24 },
  { label: "Critical Only", value: "critical", count: 3 },
  { label: "Healthy Only", value: "healthy", count:18 },
  { label: "Unavailable Only", value: "unavailable", count: 3 },
  { label: "Exclude Unavailable", value: "exclude-unavailable", count: 21 },
];
```

### States

#### Closed
```
┌──────────────────────┐
│ All Devices ▼        │
└──────────────────────┘
```

#### Open
```
┌──────────────────────┐
│ All Devices      ✓   │
├──────────────────────┤
│ Critical Only (3)    │
│ Healthy Only (18)    │
│ Unavailable (3)      │
│ Exclude Unavailable  │
└──────────────────────┘
```
- Checkmark next to active filter
- Count in parentheses for quick reference

### Accessibility

```html
<select aria-label="Filter devices by status">
  <option value="all" selected>All Devices</option>
  <option value="critical">Critical Only</option>
  <option value="healthy">Healthy Only</option>
  <option value="unavailable">Unavailable Only</option>
  <option value="exclude-unavailable">Exclude Unavailable</option>
</select>
```

- Native select for semantic HTML
- aria-label describes purpose
- Keyboard accessible (Tab, Arrow keys, Enter)

---

## Component: Loading Skeleton

### Purpose
Placeholder during initial panel load or refresh, preventing layout shift while data fetches.

### Visual Design

#### Layout
- **Height**: 72px (matches battery card)
- **Width**: 100% (fills list container)
- **Margin bottom**: 12px (matches card spacing)
- **Border radius**: 8px

#### Animation
- **Shimmer effect**:
  - Background: Linear gradient left to right
  - Start color: `var(--skeleton-color-light)` (#E0E0E0 or HA equivalent)
  - Shimmer color: `var(--skeleton-color-highlight)` (lighter, ~20% opacity white)
  - Duration: 1.2 seconds
  - Easing: Linear, infinite loop
  - Gradient angle: 45deg

```css
@keyframes shimmer {
  0% { background-position: -1000px 0; }
  100% { background-position: 1000px 0; }
}

background: linear-gradient(
  90deg,
  var(--skeleton-color-light) 0%,
  var(--skeleton-color-highlight) 50%,
  var(--skeleton-color-light) 100%
);
background-size: 1000px 100%;
animation: shimmer 1.2s infinite;
```

### Props/Data

```typescript
interface LoadingSkeletonProps {
  count?: number; // Number of skeleton rows to show (default 3)
}
```

### States

- **Idle/visible**: Shimmer animation plays
- **Hidden**: Removed from DOM when data loads

### Accessibility

```html
<div
  role="status"
  aria-label="Loading battery devices"
  aria-busy="true"
>
  <!-- Skeleton content -->
</div>
```

- `role="status"` announces loading state
- `aria-busy="true"` indicates operation in progress
- Screen reader text: "Loading battery devices"

---

## Component: Empty State

### Purpose
Friendly message when no battery devices are found or filter returns no results.

### Visual Design

#### Layout
- **Container**: Centered column flex layout
- **Height**: Minimum 200px (vertically centered in panel)
- **Padding**: 32px 16px
- **Gap**: 16px between elements

#### Color Scheme
```css
text-align: center;
color: var(--text-secondary-color);
```

#### Typography
- **Title**: `var(--headline6-font-family)`, 20px, weight 500, `--text-primary-color`
- **Description**: `var(--body2-font-family)`, 13px, weight 400, `--text-secondary-color`
- **Link**: `var(--primary-color)`, underlined on hover

#### Icons
- Large battery icon: `mdi:battery-unknown` or custom illustration (64px)
- Color: `var(--text-tertiary-color)` (light gray)

### Props/Data

```typescript
interface EmptyStateProps {
  reason: "no-entities" | "filter-empty" | "error";
  filterActive?: string; // "Critical Only", etc.
  actionLabel?: string;  // "Browse Devices"
  actionUrl?: string;    // Link to HA device page
}
```

### States

#### No Battery Entities
```
          🔋

    No battery devices found

Configure entities with device_class=battery
in Home Assistant to appear here.

   [Browse Home Assistant Devices]
```

#### Filter Returns Empty
```
          🔋

No devices match "Critical Only" filter

Try adjusting your filter or threshold.

     [Clear Filter] [Adjust Threshold]
```

#### Load Error
```
          ⚠️

Unable to load battery devices

Check your connection and try again.

          [Retry]
```

### Accessibility

```html
<div role="status" aria-label="No battery devices found">
  <h2>No battery devices found</h2>
  <p>Configure entities with device_class=battery...</p>
  <a href="#" role="button">Browse Home Assistant Devices</a>
</div>
```

- `role="status"` for dynamic empty states
- Semantic h2 for title
- Links or buttons for actions
- Full descriptive text (not just icon)

---

## Component: Settings Panel

### Purpose
Modal or slide-out panel for configuring threshold, filter behavior, and auto-refresh settings.

### Visual Design

#### Layout
- **Width**: 340px (full sidebar width) or 100% on mobile
- **Height**: 100% viewport or modal max-height 500px on desktop
- **Slide-in from right**: 300ms animation
- **Content padding**: 16px
- **Header height**: 56px (HA toolbar standard)

#### Header
```
< Vulcan Brownout Settings     [✕]
```
- Back arrow or close button
- Title: "Vulcan Brownout Settings" (16px, weight 500)
- Positioned: sticky to top

#### Sections

**1. Low Battery Threshold**
- Label: "Low Battery Threshold" (14px, weight 500)
- Slider: 5% to 50%, default 15%, step 1%
- Display value: "Current setting: 15%"
- Description: "Devices with battery below X% will be flagged as critical."

```css
/* Slider track */
background: linear-gradient(
  90deg,
  var(--primary-color) 0%,
  var(--primary-color) 30%, /* 30% is thumb position */
  var(--divider-color) 30%,
  var(--divider-color) 100%
);
height: 4px;
border-radius: 2px;

/* Thumb */
width: 20px;
height: 20px;
border-radius: 50%;
background: var(--primary-color);
box-shadow: 0 2px 4px rgba(0, 0, 0, 0.15);
```

**2. Filter Behavior**
```
Visibility Options
☑ Show unavailable devices
☑ Show healthy devices (>threshold)
```
- Checkboxes with labels
- Toggle updates preference immediately (no save needed)

**3. Auto-Refresh**
```
Update Interval
[5 minutes ▼]

☑ Real-time updates via WebSocket
  (Connected)
```
- Dropdown: 1, 5, 15, 30 minutes, or "Never"
- WebSocket toggle with status badge
- Status: "Connected", "Disconnected", "Connecting..."

#### Color Scheme
```css
background-color: var(--card-background-color);
```

#### Footer
```
[Cancel]                    [Save Changes]
```
- Two buttons, right-aligned
- Save button primary color
- Cancel cancels any pending changes

### Props/Data

```typescript
interface SettingsPanelProps {
  threshold: number;
  showUnavailable: boolean;
  showHealthy: boolean;
  updateInterval: "1min" | "5min" | "15min" | "30min" | "never";
  webSocketConnected: boolean;
  onThresholdChange: (value: number) => void;
  onSettingChange: (key: string, value: boolean | string) => void;
  onSave: () => Promise<void>;
  onCancel: () => void;
}
```

### States

- **Idle**: All fields editable, Save button enabled
- **Saving**: Save button shows spinner, is disabled
- **Saved**: Toast confirmation, panel closes
- **Error**: Error message below Save button

### Accessibility

```html
<form aria-label="Vulcan Brownout Settings">
  <h2>Low Battery Threshold</h2>
  <input
    type="range"
    min="5"
    max="50"
    value="15"
    aria-label="Low battery threshold percentage"
    aria-valuetext="15%"
  />

  <fieldset>
    <legend>Visibility Options</legend>
    <input type="checkbox" id="show-unavailable" />
    <label for="show-unavailable">Show unavailable devices</label>
  </fieldset>
</form>
```

- Form semantic element
- Fieldset + legend for checkbox groups
- aria-label/valuetext for slider context
- Keyboard navigation: Tab through controls
- Save/Cancel buttons accessible via Enter key

---

## Component: Back to Top Button

### Purpose
Fixed button that appears after scrolling past ~20 items, allowing quick return to list top.

### Visual Design

#### Layout
- **Position**: Fixed or sticky to bottom-right of list
- **Size**: 48px × 48px circular button (Material Design FAB)
- **Margin**: 16px from edges
- **Elevation**: 4px (box-shadow per HA standards)

#### Color Scheme
```css
background-color: var(--primary-color);
color: white;
border-radius: 50%;
box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);

&:hover {
  box-shadow: 0 6px 12px rgba(0, 0, 0, 0.3);
}

&:active {
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.15);
}
```

#### Icon
- `mdi:chevron-up` or `mdi:arrow-up`
- 24px size, white color
- Centered in button

### Props/Data

```typescript
interface BackToTopButtonProps {
  isVisible: boolean;
  onClick: () => void;
}
```

### States

- **Hidden**: `opacity: 0`, `pointer-events: none`, off-screen or below viewport
- **Visible**: `opacity: 1`, `pointer-events: auto`, smooth fade-in (200ms)
- **Hover**: Elevation increases, cursor pointer
- **Active**: Elevation decreases, smooth scroll-to-top animation (500ms)

### Accessibility

```html
<button
  aria-label="Back to top"
  aria-hidden="false"
  class="back-to-top"
>
  ↑
</button>
```

- Clear aria-label
- Visible focus indicator (outline)
- Keyboard accessible: Tab + Enter/Space
- Semantic button element

---

## Component: Refresh Button

### Purpose
Header button to manually trigger data refresh.

### Visual Design

#### Layout
- **Position**: Header right side, next to settings icon
- **Size**: 36px × 36px
- **Icon**: `mdi:refresh`
- **Padding**: 8px

#### Color Scheme
```css
color: var(--text-primary-color);
background: transparent;
border: none;
border-radius: 4px;

&:hover {
  background-color: var(--hover-color);
}

&:active {
  background-color: var(--active-color);
}
```

#### Animation
- Icon rotation when loading (1s continuous rotation, stops on complete)
- Color changes to primary during active load

### Props/Data

```typescript
interface RefreshButtonProps {
  isLoading: boolean;
  onRefresh: () => void;
}
```

### States

- **Idle**: Static icon, `color: --text-primary-color`
- **Loading**: Icon rotates, `color: --primary-color`
- **Done**: Icon stops, fades back to normal color

### Accessibility

```html
<button
  aria-label="Refresh device list"
  aria-busy="false"
  class="refresh-btn"
>
  <ha-icon icon="mdi:refresh"></ha-icon>
</button>
```

- aria-label describes action
- aria-busy indicates loading state
- Keyboard: Tab + Enter/Space
- Tooltip (optional): "Refresh" on hover

---

## Component: Status Grouping Header

### Purpose
Section header indicating device status category (Critical, Healthy, Unavailable).

### Visual Design

#### Layout
- **Height**: 32px
- **Padding**: 8px 16px
- **Sticky**: Stays at top of section when scrolling (optional)
- **Margin top**: 12px (first section has no margin)

#### Typography
- **Font**: `var(--subtitle2-font-family)`, 12px, weight 600
- **Color**: `var(--text-secondary-color)`
- **Text transform**: Uppercase
- **Letter spacing**: 0.5px

#### Content
```
Critical (3)
Healthy (5)
Unavailable (1)
```

**Format**: "[Status Name] ([count])"

#### Color Coding
- **Critical section**: Light red/orange left border (4px)
- **Healthy section**: Light green left border (4px)
- **Unavailable section**: Light gray left border (4px)

```css
border-left: 4px solid var(--status-color);
background-color: var(--status-background-color);
```

### Props/Data

```typescript
interface StatusGroupHeaderProps {
  status: "critical" | "healthy" | "unavailable";
  count: number;
  isSticky?: boolean;
}
```

### States

- **Default**: Visible with correct styling
- **Empty**: Hidden if count === 0
- **Sticky**: Stays visible at top during scroll (if enabled)

### Accessibility

```html
<h3
  role="heading"
  aria-level="3"
  aria-label="Critical devices, 3 total"
>
  Critical (3)
</h3>
```

- Semantic heading element
- aria-label provides full context
- Screen reader announces: "Critical devices, 3 total"

---

## Design Token Reference

### Colors (HA CSS Custom Properties)

| Token | Default | Usage |
|-------|---------|-------|
| `--primary-color` | #1976D2 | Buttons, focus, active states |
| `--error-color` | #C33C3C | Critical status, warnings |
| `--warning-color` | #F5A623 | Low status, amber indicators |
| `--success-color` | #4CAF50 | Healthy status, green indicators |
| `--text-primary-color` | #212121 | Primary text |
| `--text-secondary-color` | #727272 | Secondary text |
| `--text-tertiary-color` | #A0A0A0 | Disabled/tertiary text |
| `--card-background-color` | #FFFFFF | Card backgrounds |
| `--divider-color` | #ECECEC | Borders, dividers |
| `--hover-color` | #F5F5F5 | Hover states |
| `--disabled-text-color` | #BDBDBD | Disabled elements |

### Typography (HA Type Scale)

| Role | Font Family | Size | Weight |
|------|-------------|------|--------|
| Headline | `--headline-font-family` | 24px | 600 |
| Title | `--title-font-family` | 20px | 500 |
| Subtitle | `--subtitle-font-family` | 16px | 500 |
| Body 1 | `--body1-font-family` | 14px | 400 |
| Body 2 | `--body2-font-family` | 13px | 400 |
| Caption | `--caption-font-family` | 11px | 400 |

### Spacing

| Unit | Value | Usage |
|------|-------|-------|
| xs | 4px | Micro-spacing |
| sm | 8px | Small gaps |
| md | 12px | Standard spacing |
| lg | 16px | Large gaps |
| xl | 24px | Section spacing |
| xxl | 32px | Major sections |

### Animations

| Property | Duration | Easing | Usage |
|----------|----------|--------|-------|
| Fade in | 150ms | ease-out | Show/reveal |
| Fade out | 100ms | ease-in | Hide |
| Slide | 250ms | ease-out | Navigation |
| Scale | 200ms | cubic-bezier(0.4, 0, 0.2, 1) | Growth |
| Rotate | 1s | linear | Loading spinner |

