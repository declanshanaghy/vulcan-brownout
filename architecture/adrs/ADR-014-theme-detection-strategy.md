# ADR-014: Theme Detection Strategy Using hass.themes.darkMode

**Date**: 2026-02-22
**Status**: Accepted
**Sprint**: Sprint 4
**Author**: FiremanDecko (Architect)

---

## Problem

**Sprint 3 Implementation (Current)**: The panel detects dark/light mode via DOM sniffing (`data-theme` attribute) and OS preference (`prefers-color-scheme`), but **ignores the user's explicit theme selection from their Home Assistant profile**.

Home Assistant exposes `hass.themes.darkMode` (boolean) and `hass.themes.name` (string: "default", "Google - Dark", "Solarized Dark", etc.), which represent the **authoritative source of truth** for the user's theme preference (set in HA Settings → Person → Theme).

**User Impact**: Users who have set a named theme in their HA profile expect the Vulcan Brownout panel to respect that choice. Currently, if their HA theme doesn't set the `data-theme` attribute on the DOM (some custom themes don't), our detection fails and defaults to the OS preference — potentially showing the wrong theme to the user.

**Example Scenario**:
- User has "Solarized Dark" theme selected in HA Settings
- `hass.themes.darkMode` = true (correctly indicates dark mode)
- But `data-theme` attribute is not set by the theme (some themes don't set it)
- Panel falls back to OS preference, which might be light mode
- Result: Panel shows light colors while rest of HA is dark (poor UX)

---

## Options Considered

### Option 1: Continue DOM Sniffing (Current)
**Approach**: Keep current detection: DOM `data-theme` → OS `prefers-color-scheme` → localStorage

**Pros**:
- No code changes needed
- Works for most HA users (most themes set data-theme)
- Familiar pattern (MutationObserver already implemented)

**Cons**:
- Ignores user's explicit theme choice from profile
- Fails when custom theme doesn't set data-theme
- Less reliable (DOM attribute is not authoritative)
- MutationObserver is resource-intensive (watches all attribute changes)
- Not "HA way" (ignores HA's built-in theme API)

**Verdict**: Rejected. Doesn't solve the core problem.

---

### Option 2: Use hass.themes.darkMode as Primary Source (CHOSEN)
**Approach**: Check `hass.themes.darkMode` first (authoritative), then fall back to DOM + OS preference

**Primary**: `hass.themes.darkMode` (if available, always use this)
**Fallback 1**: DOM `data-theme` attribute
**Fallback 2**: OS `prefers-color-scheme`
**Default**: Light mode

**Detection on initial load** (connectedCallback):
```javascript
function _detect_theme() {
  // Primary: hass.themes.darkMode is the authoritative source
  if (this.hass?.themes?.darkMode !== undefined) {
    return this.hass.themes.darkMode ? 'dark' : 'light';
  }

  // Fallback 1: DOM attribute (for backward compat)
  const domTheme = document.documentElement.getAttribute('data-theme');
  if (domTheme === 'dark' || domTheme === 'light') {
    return domTheme;
  }

  // Fallback 2: OS preference
  if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
    return 'dark';
  }

  // Default to light
  return 'light';
}
```

**Real-time updates** (listen to `hass_themes_updated` event):
```javascript
// In connectedCallback():
if (this.hass?.connection) {
  this._themeListener = () => {
    const newTheme = this._detect_theme();
    this._apply_theme(newTheme);
  };
  this.hass.connection.addEventListener('hass_themes_updated', this._themeListener);
}

// In disconnectedCallback():
if (this._themeListener && this.hass?.connection) {
  this.hass.connection.removeEventListener('hass_themes_updated', this._themeListener);
}
```

**Pros**:
- Uses HA's authoritative API (respects user's explicit profile choice)
- Handles custom themes correctly (doesn't rely on data-theme)
- Event-driven (more reliable than DOM sniffing)
- Removes need for MutationObserver (more efficient)
- Real-time updates (panel responds to theme changes in HA UI)
- Graceful degradation (fallback chain ensures compatibility)
- Minimal code changes (only panel, no backend changes)

**Cons**:
- Requires `hass.themes` to be exposed by HA (available 2023.2+, we require 2026.2+)
- If hass.connection unavailable (edge case), event listener won't attach (but fallback chain handles it)
- Event listener must be cleaned up properly (risk of memory leaks if not careful)

**Verdict**: Chosen. Solves the problem elegantly, uses HA's intended API, provides better UX.

---

### Option 3: Polling hass.themes.darkMode
**Approach**: Set up an interval to periodically check `hass.themes.darkMode`

**Pros**:
- Guaranteed to detect theme changes
- No event listener needed

**Cons**:
- Resource-intensive (unnecessary polling when no change)
- Slower response time than event-driven
- Goes against reactive programming principles
- Less efficient than event listener

**Verdict**: Rejected in favor of event-driven approach (Option 2).

---

## Decision

**Use Option 2: hass.themes.darkMode as primary source with event-driven updates**

The panel will:
1. Detect `hass.themes.darkMode` on initial load (connectedCallback)
2. Listen to `hass_themes_updated` event for real-time theme changes
3. Fall back to DOM and OS preference if `hass.themes` unavailable
4. Apply smooth CSS transition (300ms) when theme changes
5. Clean up event listener on disconnect (disconnectedCallback)

---

## Implementation

### Detection Algorithm

```javascript
_detect_theme() {
  // Check in order of authority:
  // 1. hass.themes.darkMode (explicit user choice, authoritative)
  if (this.hass?.themes?.darkMode !== undefined) {
    return this.hass.themes.darkMode ? 'dark' : 'light';
  }

  // 2. DOM data-theme attribute (fallback, some HA themes set this)
  const domTheme = document.documentElement.getAttribute('data-theme');
  if (domTheme === 'dark' || domTheme === 'light') {
    return domTheme;
  }

  // 3. OS/browser preference (fallback)
  if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
    return 'dark';
  }

  // 4. Default (safe default)
  return 'light';
}
```

### Theme Application

```javascript
_apply_theme(theme) {
  // Set data-theme attribute on <html> element
  document.documentElement.setAttribute('data-theme', theme || 'light');
  // Trigger Lit re-render (applies CSS custom properties)
  this.requestUpdate();
}
```

### Lifecycle Integration

**connectedCallback** (component mounted):
```javascript
async connectedCallback() {
  super.connectedCallback();

  // Step 1: Detect and apply initial theme
  const initialTheme = this._detect_theme();
  this._apply_theme(initialTheme);

  // Step 2: Listen for theme changes
  if (this.hass?.connection) {
    this._themeListener = () => {
      const newTheme = this._detect_theme();
      this._apply_theme(newTheme);
    };
    this.hass.connection.addEventListener('hass_themes_updated', this._themeListener);
  }
}
```

**disconnectedCallback** (component unmounted):
```javascript
disconnectedCallback() {
  super.disconnectedCallback();

  // Clean up event listener to prevent memory leaks
  if (this._themeListener && this.hass?.connection) {
    this.hass.connection.removeEventListener('hass_themes_updated', this._themeListener);
  }
}
```

### CSS Custom Properties

Define theme-specific values on `[data-theme]` selector:

```css
[data-theme="light"] {
  --vb-bg-primary: #FFFFFF;
  --vb-bg-card: #F5F5F5;
  --vb-text-primary: #212121;
  --vb-text-secondary: #757575;
  --vb-color-critical: #F44336;
  --vb-color-warning: #FF9800;
  --vb-color-healthy: #4CAF50;
  --vb-color-unavailable: #9E9E9E;
}

[data-theme="dark"] {
  --vb-bg-primary: #1C1C1C;
  --vb-bg-card: #2C2C2C;
  --vb-text-primary: #FFFFFF;
  --vb-text-secondary: #B0B0B0;
  --vb-color-critical: #FF5252;
  --vb-color-warning: #FFB74D;
  --vb-color-healthy: #66BB6A;
  --vb-color-unavailable: #BDBDBD;
}
```

### Smooth Transition

Apply CSS transitions on color properties only (no layout properties to avoid jank):

```css
.panel, .device-card, .button, .modal {
  transition: background-color 300ms ease-out,
              color 300ms ease-out,
              border-color 300ms ease-out;
}
```

---

## Consequences

### Positive
- **Correct theme detection**: Respects user's explicit profile choice
- **Reliable**: Uses HA's authoritative API, not DOM sniffing
- **Real-time updates**: Panel responds immediately to theme changes in HA UI
- **Efficient**: Event-driven, no polling or MutationObserver overhead
- **Graceful degradation**: Fallback chain ensures backward compatibility
- **HA-aligned**: Follows HA's intended patterns for theme integration
- **Better UX**: Eliminates cases where panel shows wrong theme

### Negative
- **Memory leak risk**: Event listener must be cleaned up in disconnectedCallback (mitigated by careful implementation)
- **HA dependency**: Requires HA 2023.2+ for hass_themes_updated event (we already require 2026.2+)
- **Complexity**: Slightly more code than current DOM sniffing approach (minimal)

### Trade-offs
- **vs Option 1 (DOM sniffing)**: Lose simplicity, gain correctness
- **vs Option 3 (polling)**: Lose guaranteed detection (very unlikely to miss), gain efficiency

---

## Testing Strategy

### Unit Tests
- Test `_detect_theme()` with various inputs:
  - `hass.themes.darkMode = true` → returns 'dark'
  - `hass.themes.darkMode = false` → returns 'light'
  - `hass.themes.darkMode = undefined` → falls back to DOM/OS
  - DOM `data-theme = 'dark'` → returns 'dark'
  - OS preference dark → returns 'dark'
  - All undefined/false → returns 'light' (default)

### Integration Tests (E2E via Playwright)
- Load panel, verify theme matches `hass.themes.darkMode` on initial render
- Change HA theme in UI, verify `hass_themes_updated` event fires
- Verify panel theme updates within 300ms of event
- Verify smooth CSS transition (no flicker, no layout shift)
- Test with 150+ battery devices (verify no scroll jank during theme switch)

### Manual Testing
- Open panel in light HA theme, verify light colors apply
- Switch HA theme to dark, verify smooth transition to dark colors
- Switch to custom theme (e.g., "Solarized Dark"), verify colors apply correctly
- Close and reopen panel, verify theme persists
- Test on mobile viewport, verify touch targets and accessibility

### Accessibility Testing
- Verify WCAG AA contrast ratios in both light and dark modes
- Test keyboard navigation (theme changes shouldn't break focus)
- Verify no announcements or alerts on theme change (silent update)

---

## Alternatives Rejected

| Alternative | Why Rejected |
|-------------|-------------|
| DOM sniffing only (current) | Ignores user's explicit theme choice; fails on custom themes |
| Polling hass.themes.darkMode | Resource-intensive; slower than event-driven |
| MutationObserver on html element | Less efficient than event listener; less specific |
| Hardcode light/dark toggle | Ignores HA's theme system entirely |

---

## Migration Path

**From Sprint 3 to Sprint 4**:
1. Keep MutationObserver as fallback (for edge case where hass.connection unavailable)
2. Add new `_detect_theme()` and `_apply_theme()` methods
3. Add event listener in connectedCallback
4. Update disconnectedCallback to clean up listener
5. Keep CSS custom properties and transitions unchanged
6. Test thoroughly to ensure no regressions

**Backward compatibility**: Full. Existing users will see improved theme detection; no breaking changes.

---

## References

- **Home Assistant Theme API**: https://developers.home-assistant.io/docs/frontend/custom-ui/
- **hass.themes.darkMode**: Available in HA 2023.2+
- **hass_themes_updated event**: Fired when user changes theme in HA Settings
- **HA Custom Component Best Practices**: Follow event-driven architecture
- **Sprint 4 Design Brief**: `design/product-design-brief.md` (technical feasibility questions answered here)

---

## Review Notes

**Freya (PO)**: Approved — respects user theme choice, improves UX
**Luna (UX)**: Approved — theme switching is smooth and responsive
**Loki (QA)**: Will verify — 28/28 Sprint 3 tests continue to pass, new theme detection tested in Sprint 4

---

## Revision History

| Date | Status | Author | Notes |
|------|--------|--------|-------|
| 2026-02-22 | Accepted | FiremanDecko | Initial ADR for Sprint 4 |

