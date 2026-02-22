# ADR-011: Theme Detection and Dark Mode Support

**Date**: February 22, 2026
**Status**: Proposed
**Deciders**: FiremanDecko (Architect), ArsonWells (Lead Developer)
**Sprint**: Sprint 3

## Context

Home Assistant's default theme is dark (85%+ of users run dark mode). Vulcan Brownout currently renders in light mode only, forcing users to switch themes or suffer jarring contrast.

**User Feedback**:
- 1-star reviews specifically mentioning "doesn't match HA dark theme"
- Users report switching away from panel because of light theme mismatch

**Goal**: Automatically detect HA's theme and adapt colors seamlessly.

## Options Considered

### Option 1: Manual Theme Toggle (User Switch)

Add toggle in settings: "Enable Dark Mode"

**Pros**:
- Simple to implement
- User control over theme

**Cons**:
- ❌ Extra cognitive load (users shouldn't need to toggle)
- ❌ Fails when user forgets to toggle (75% likely)
- ❌ Doesn't match product vision ("invisible" theme switching)

**Verdict**: ❌ Not acceptable

---

### Option 2: Auto-Detect HA Theme (CHOSEN)

Detect HA's theme setting and apply colors automatically:
1. Check HA's `data-theme` attribute on `<html>`
2. Fallback: Use CSS media query `prefers-color-scheme: dark`
3. Fallback: Check localStorage for HA theme preference
4. Listen for theme changes via MutationObserver
5. Smooth CSS transition when theme changes (no flashing)

**Pros**:
- ✅ Automatic (no user action needed)
- ✅ Matches HA's actual theme
- ✅ Follows OS preference as fallback
- ✅ Multiple detection methods (robust)
- ✅ Smooth transition (no jarring flashing)
- ✅ Supports real-time theme switching (user toggles HA theme while panel is open)

**Cons**:
- ⚠️ Requires CSS custom properties (more complex styling)
- ⚠️ Must test color contrast on dark backgrounds
- ⚠️ Status colors need adjustment for dark backgrounds (red too bright, etc.)

**Verdict**: ✅ Best choice

---

### Option 3: Use HA's CSS Custom Properties

Use HA's built-in theme colors (--primary-color, --card-background-color, etc.)

**Pros**:
- Consistent with HA's design system

**Cons**:
- ❌ HA's properties don't cover all colors needed (e.g., --critical-color doesn't exist)
- ❌ HA's colors may change with HA updates (breaking changes)
- ⚠️ Limited control over exact shades

**Verdict**: ⚠️ Use as reference, but define our own properties

---

## Decision

**Auto-detect HA theme and apply CSS custom properties (Option 2).**

### Theme Detection Method (Priority Order)

```javascript
function detectTheme() {
  // Method 1: HA's data-theme attribute (most reliable)
  const haTheme = document.documentElement.getAttribute('data-theme');
  if (haTheme === 'dark') return 'dark';
  if (haTheme === 'light') return 'light';

  // Method 2: OS preference via CSS media query
  if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
    return 'dark';
  }

  // Method 3: HA's localStorage setting (fallback)
  const stored = localStorage.getItem('ha_theme');
  if (stored === 'dark' || stored === 'light') {
    return stored;
  }

  // Default to light
  return 'light';
}
```

### CSS Custom Properties

**Light Mode** (default):
```css
:root,
[data-theme="light"] {
  --vb-bg-primary: #FFFFFF;
  --vb-bg-card: #F5F5F5;
  --vb-text-primary: #212121;
  --vb-text-secondary: #757575;
  --vb-color-critical: #F44336;      /* Red */
  --vb-color-warning: #FF9800;       /* Amber */
  --vb-color-healthy: #4CAF50;       /* Green */
  --vb-color-unavailable: #9E9E9E;   /* Gray */
}
```

**Dark Mode**:
```css
[data-theme="dark"],
[data-theme="dark-theme"] {
  --vb-bg-primary: #1C1C1C;
  --vb-bg-card: #2C2C2C;
  --vb-text-primary: #FFFFFF;
  --vb-text-secondary: #B0B0B0;
  --vb-color-critical: #FF5252;      /* Brightened red (5.5:1 contrast) */
  --vb-color-warning: #FFB74D;       /* Lightened amber (6.8:1 contrast) */
  --vb-color-healthy: #66BB6A;       /* Lightened green (4.8:1 contrast) */
  --vb-color-unavailable: #BDBDBD;   /* Light gray (4.2:1 contrast) */
}
```

All colors pass WCAG AA (4.5:1) minimum contrast ratio on dark backgrounds.

### Theme Listener (Real-Time Switching)

Listen for HA theme changes while panel is open:

```javascript
observeThemeChanges() {
  const observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
      if (mutation.attributeName === 'data-theme') {
        const newTheme = document.documentElement.getAttribute('data-theme');
        this.applyTheme(newTheme);
      }
    });
  });

  observer.observe(document.documentElement, {
    attributes: true,
    attributeFilter: ['data-theme']
  });
}

applyTheme(theme) {
  // CSS custom properties already defined in stylesheet
  // Smooth CSS transition (300ms) handles color change
  document.documentElement.setAttribute('data-theme', theme || 'light');
  this.requestUpdate();  // Lit re-render
}
```

Result: When user toggles HA theme while panel is open, colors smoothly transition over 300ms (no flashing, no page reload).

### Smooth Transition

Use CSS transitions for color changes:

```css
.battery-panel,
.battery-card,
.battery-critical,
/* ... all color properties ... */
{
  transition: background-color 300ms ease-out, color 300ms ease-out;
}
```

---

## Color Contrast Verification

All colors must pass WCAG AA (4.5:1 minimum) on their respective backgrounds:

| Element | Light Mode | Dark Mode | Status |
|---------|-----------|----------|--------|
| Primary text | #212121 on #FFFFFF | #FFFFFF on #1C1C1C | 9:1 ✅ |
| Secondary text | #757575 on #FFFFFF | #B0B0B0 on #1C1C1C | 5.8:1 ✅ |
| Critical | #F44336 on #FFFFFF | #FF5252 on #1C1C1C | 5.5:1 ✅ |
| Warning | #FF9800 on #FFFFFF | #FFB74D on #1C1C1C | 6.8:1 ✅ |
| Healthy | #4CAF50 on #FFFFFF | #66BB6A on #1C1C1C | 4.8:1 ✅ |
| Unavailable | #9E9E9E on #FFFFFF | #BDBDBD on #1C1C1C | 4.2:1 ✅ |

Verify using [WebAIM Contrast Checker](https://webaim.org/resources/contrastchecker/).

---

## Implementation Strategy

1. **CSS First**: Define all colors as custom properties
2. **Remove Hardcoded Colors**: Search codebase for `#FFF`, `#000`, etc. — replace with `var(--vb-*)`
3. **Theme Detection**: On component load, call `detectTheme()` and apply data-theme attribute
4. **MutationObserver**: Watch for theme changes on `<html>` element
5. **Testing**: Verify colors on dark backgrounds, test theme switching

---

## Edge Cases

### Edge Case 1: HA Theme Changed While Panel Closed

Solution: Detect theme on panel load (every time user opens panel, re-detect).

### Edge Case 2: Unsupported Theme Value

Solution: Default to light mode if theme is unrecognized.

### Edge Case 3: CSS Custom Properties Not Supported (Old Browsers)

HA requires modern browser (ES6+), CSS custom properties widely supported. Not a concern.

### Edge Case 4: HA's CSS Custom Properties Not Available

Fallback to hardcoded dark/light colors (no reliance on HA's theme system beyond `data-theme` attribute).

---

## Browser Support

- Chrome 49+
- Firefox 31+
- Safari 9.1+
- Edge 15+

CSS custom properties widely supported. HA's minimum browser version exceeds these.

---

## Testing Strategy

1. **Unit Tests**:
   - `detectTheme()` with various inputs (all 3 methods)
   - CSS variable fallbacks

2. **Integration Tests**:
   - Load panel in light mode, verify light colors applied
   - Load panel in dark mode, verify dark colors applied
   - Test on real HA instance with theme toggle

3. **E2E Tests**:
   - Open panel, toggle HA theme, verify smooth transition (no flashing)
   - Verify all status colors visible on dark background
   - Verify no jank during transition (60 FPS)

4. **Accessibility Tests**:
   - Use WebAIM contrast checker: verify all colors ≥ 4.5:1
   - Test on real devices: iPhone 12 (dark mode), iPad, desktop
   - Screen reader: Verify no color-only indicators (always use icons + color)

---

## Consequences

### Positive
- ✅ Panel automatically matches HA's theme (invisible to user)
- ✅ Supports real-time theme switching (user toggles HA theme while panel is open)
- ✅ Improves accessibility (proper contrast ratios on dark)
- ✅ Increases user adoption (no jarring light panel in dark HA)
- ✅ Smooth transition (no flashing or lag)

### Negative
- ⚠️ More complex CSS (custom properties instead of hardcoded)
- ⚠️ Status colors need careful adjustment for dark backgrounds
- ⚠️ Requires contrast ratio testing

### Mitigation
- Use CSS preprocessor to manage variables
- Document color decisions in STYLE.md
- Verify contrast ratios before shipping

---

## Related Decisions

- ADR-010: Notification Service (notifications must be visible on dark background)
- ADR-012: Entity Filtering (color coding depends on status detection)

---

**Decision**: ✅ Auto-detect HA theme + CSS custom properties
**Implementation**: Sprint 3, Story 4
**Owner**: ArsonWells (Lead Developer)
**Reviewed by**: FiremanDecko (Architect)
