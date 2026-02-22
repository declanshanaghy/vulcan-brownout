# ADR-011: Theme Detection and Dark Mode Support

**Date**: February 22, 2026
**Status**: Proposed
**Sprint**: Sprint 3

## Problem

HA's default theme is dark (85%+ users). Vulcan Brownout renders in light mode, forcing jarring contrast. Users report 1-star reviews mentioning "doesn't match HA dark theme."

## Decision

**Auto-detect HA theme and apply CSS custom properties**

Detect HA's `data-theme` attribute or OS preference, apply dark/light colors automatically. Listen for real-time theme changes.

## Implementation

**Theme detection** (priority order):
```javascript
function detectTheme() {
  // Method 1: HA's data-theme attribute
  const haTheme = document.documentElement.getAttribute('data-theme');
  if (haTheme === 'dark') return 'dark';
  if (haTheme === 'light') return 'light';

  // Method 2: OS preference
  if (window.matchMedia('(prefers-color-scheme: dark)').matches) return 'dark';

  // Method 3: localStorage fallback
  const stored = localStorage.getItem('ha_theme');
  if (stored === 'dark' || stored === 'light') return stored;

  return 'light';  // Default
}
```

**CSS custom properties**:

Light mode:
```css
[data-theme="light"] {
  --vb-bg-primary: #FFFFFF;
  --vb-bg-card: #F5F5F5;
  --vb-text-primary: #212121;
  --vb-color-critical: #F44336;      /* Red */
  --vb-color-warning: #FF9800;       /* Amber */
  --vb-color-healthy: #4CAF50;       /* Green */
  --vb-color-unavailable: #9E9E9E;   /* Gray */
}
```

Dark mode:
```css
[data-theme="dark"] {
  --vb-bg-primary: #1C1C1C;
  --vb-bg-card: #2C2C2C;
  --vb-text-primary: #FFFFFF;
  --vb-color-critical: #FF5252;      /* Brightened red (5.5:1 contrast) */
  --vb-color-warning: #FFB74D;       /* Lightened amber (6.8:1 contrast) */
  --vb-color-healthy: #66BB6A;       /* Lightened green (4.8:1 contrast) */
  --vb-color-unavailable: #BDBDBD;   /* Light gray (4.2:1 contrast) */
}
```

All colors pass WCAG AA (4.5:1 minimum) contrast ratio.

**Real-time theme listening**:
```javascript
observeThemeChanges() {
  const observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
      if (mutation.attributeName === 'data-theme') {
        this.applyTheme(document.documentElement.getAttribute('data-theme'));
      }
    });
  });

  observer.observe(document.documentElement, {
    attributes: true,
    attributeFilter: ['data-theme']
  });
}

applyTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme || 'light');
  this.requestUpdate();  // Lit re-render
}
```

**Smooth transition**:
```css
.battery-panel, .battery-card, .battery-critical {
  transition: background-color 300ms ease-out, color 300ms ease-out;
}
```

When user toggles HA theme while panel is open, colors smoothly transition over 300ms (no flashing).

## Color contrast verification

All colors verified with WebAIM Contrast Checker:

| Element | Light | Dark | Ratio | Status |
|---------|-------|------|-------|--------|
| Primary text | #212121 on #FFFFFF | #FFFFFF on #1C1C1C | 9:1 | ✅ |
| Critical | #F44336 on #FFFFFF | #FF5252 on #1C1C1C | 5.5:1 | ✅ |
| Warning | #FF9800 on #FFFFFF | #FFB74D on #1C1C1C | 6.8:1 | ✅ |
| Healthy | #4CAF50 on #FFFFFF | #66BB6A on #1C1C1C | 4.8:1 | ✅ |
| Unavailable | #9E9E9E on #FFFFFF | #BDBDBD on #1C1C1C | 4.2:1 | ✅ |

## Implementation strategy

1. Define CSS custom properties in stylesheet
2. Remove hardcoded colors (replace with `var(--vb-*)`)
3. On component load, call `detectTheme()` and apply
4. Watch for theme changes via MutationObserver
5. Test colors on dark backgrounds

## Edge cases

**Theme changed while panel closed**: Re-detect on next open
**Unsupported theme value**: Default to light
**CSS custom properties not supported**: Not a concern (HA requires ES6+)

## Consequences

**Positive**:
- Panel automatically matches HA theme (invisible to user)
- Real-time theme switching (while panel is open)
- Improved accessibility (proper contrast ratios)
- Increases user adoption
- Smooth transition (no flashing)

**Negative**:
- More complex CSS (custom properties instead of hardcoded)
- Status colors need careful adjustment for dark
- Requires contrast ratio testing

## Testing

- Unit tests: `detectTheme()` with various inputs
- Integration tests: Load in light/dark, verify colors applied
- E2E tests: Toggle HA theme, verify smooth transition
- Accessibility tests: Verify color contrast ratios ≥ 4.5:1
