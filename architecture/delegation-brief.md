# Sprint 4 Delegation Brief

**To**: ArsonWells (Lead Developer) | **From**: FiremanDecko (Architect) | **Date**: 2026-02-22

**Status**: Ready for implementation | **Priority**: P1 | **Timeline**: 2 weeks

---

## Executive Summary

Sprint 4 focuses on **theme detection architecture** (using HA's authoritative `hass.themes.darkMode` API instead of DOM sniffing) and **UX polish** (empty state messaging, verification testing). No WebSocket API changes needed. All work is frontend-only in `vulcan-brownout-panel.js` and `styles.css`.

---

## Architecture Overview

See `system-design.md` section "Sprint 4 New Features: Theme Detection Architecture" for full technical details.

### Key Decision: hass.themes.darkMode as Primary Source

**Previous (Sprint 3)**: DOM sniffing (`data-theme` attribute) + OS preference fallback

**New (Sprint 4)**: `hass.themes.darkMode` boolean as authoritative source, with fallback chain:
1. `hass.themes.darkMode` (primary, must be true or false)
2. DOM `data-theme` attribute
3. OS `prefers-color-scheme` media query
4. Default to `'light'`

This respects users' explicit theme selection from their HA profile (Settings → Person → Theme).

### Real-Time Theme Updates

Listen to `hass_themes_updated` event (fired by HA when user changes theme). This is more reliable than MutationObserver.

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

### CSS Smooth Transition

300ms ease-out transition on color properties only (no layout properties to avoid jank):

```css
.panel, .device-card, .button, .modal {
  transition: background-color 300ms ease-out, color 300ms ease-out, border-color 300ms ease-out;
}
```

---

## Files to Modify

### 1. `development/src/custom_components/vulcan_brownout/frontend/vulcan-brownout-panel.js`

**Changes Required**:

a) **Add `_detect_theme()` method**:
```javascript
_detect_theme() {
  // Primary: hass.themes.darkMode (must check !== undefined)
  if (this.hass?.themes?.darkMode !== undefined) {
    return this.hass.themes.darkMode ? 'dark' : 'light';
  }

  // Fallback 1: DOM attribute
  const domTheme = document.documentElement.getAttribute('data-theme');
  if (domTheme === 'dark' || domTheme === 'light') {
    return domTheme;
  }

  // Fallback 2: OS preference
  if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
    return 'dark';
  }

  // Default
  return 'light';
}
```

b) **Add `_apply_theme(theme)` method**:
```javascript
_apply_theme(theme) {
  document.documentElement.setAttribute('data-theme', theme || 'light');
  // Trigger Lit re-render (will apply CSS custom properties)
  this.requestUpdate();
}
```

c) **Update `connectedCallback()`**:
- Call `this._apply_theme(this._detect_theme())` after super.connectedCallback()
- Store `_themeListener` callback reference
- Attach listener: `this.hass.connection.addEventListener('hass_themes_updated', this._themeListener)`

d) **Update `disconnectedCallback()`**:
- Remove listener: `this.hass.connection.removeEventListener('hass_themes_updated', this._themeListener)`
- Call super.disconnectedCallback()

e) **Update empty state message** (when device list is empty):
- Replace: "No battery devices found"
- With: "No battery entities found. Check that your devices have a `battery_level` attribute and are not binary sensors. [→ Documentation]"
- Keep existing Refresh, Settings, Documentation buttons
- Ensure buttons are 44px+ touch targets

f) **Remove or deprecate MutationObserver**:
- The current MutationObserver watching `data-theme` changes can be removed (no longer needed)
- Or keep as fallback if `hass.connection` is unavailable (edge case)

**Implementation Patterns**:
- Store theme state as class property: `this._currentTheme = 'light'`
- Only call `requestUpdate()` if theme actually changed (avoid unnecessary re-renders)
- Use arrow functions for listener callbacks to maintain `this` context

---

### 2. `development/src/custom_components/vulcan_brownout/frontend/styles.css`

**Changes Required**:

a) **Verify CSS custom properties are defined**:
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
  --vb-color-action: #03A9F4;
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
  --vb-color-action: #03A9F4;
}
```

b) **Ensure all colors use CSS custom properties** (no hardcoded hex in selectors):
- `.panel { background-color: var(--vb-bg-primary); color: var(--vb-text-primary); }`
- `.device-card { background-color: var(--vb-bg-card); }`
- `.status-critical { color: var(--vb-color-critical); }`
- `.status-warning { color: var(--vb-color-warning); }`
- `.status-healthy { color: var(--vb-color-healthy); }`
- `.status-unavailable { color: var(--vb-color-unavailable); }`
- `.button, .modal-btn { color: var(--vb-color-action); }`

c) **Add smooth color transitions**:
```css
.panel, .device-card, .button, .modal, .modal-header, .modal-footer {
  transition: background-color 300ms ease-out, color 300ms ease-out, border-color 300ms ease-out;
}
```

d) **Verify WCAG AA contrast ratios** (document in code comment):
```css
/* Color contrast verified with WebAIM Contrast Checker:
   - Text on bg: 9:1 (WCAG AAA)
   - Critical on bg: 5.5:1 (WCAG AA)
   - Warning on bg: 6.8:1 (WCAG AA)
   - Healthy on bg: 4.8:1 (WCAG AA)
   - Unavailable on bg: 4.2:1 (WCAG AA)
*/
```

**Implementation Patterns**:
- Use CSS custom properties exclusively (no fallbacks needed, HA requires ES6+)
- Define properties on `[data-theme]` selectors, not on `:root` (allows per-theme overrides)
- Keep transition duration consistent (300ms) across all color properties

---

## Implementation Order

**Recommended sequence** (some can run in parallel):

### Phase 1: Core Theme Detection (Story 4.1)
1. Add `_detect_theme()` method to panel component
2. Add `_apply_theme(theme)` method to panel component
3. Update `connectedCallback()` to detect initial theme
4. Add `hass_themes_updated` event listener
5. Update `disconnectedCallback()` to clean up listener
6. Verify CSS custom properties are set correctly
7. Test theme switching manually (light ↔ dark ↔ custom theme)
8. Verify no console errors or warnings

### Phase 2: UX Polish (Stories 4.2, 4.4)
9. Update empty state message in panel template
10. Verify notification modal structure and accessibility
11. Test on mobile viewport (touch target sizes)
12. Run accessibility check (axe-core)

### Phase 3: Testing & Verification (Stories 4.3, 4.4)
13. Run Playwright e2e tests with 150+ mock devices
14. Measure scroll performance (no jank during theme switch)
15. Verify button accessibility and hover states
16. Test modal open/close/save workflows

### Phase 4: Deployment (Story 4.5)
17. Update deployment script for frontend assets
18. Deploy to test HA server via SSH rsync
19. Restart HA service
20. Run health check endpoint
21. Smoke test: Load panel, change theme, verify colors transition smoothly
22. Re-run all Sprint 3 tests (28/28 must pass)

---

## Code Review Checklist

Before submitting for code review, verify:

- [ ] `_detect_theme()` checks `hass.themes.darkMode` first (not DOM)
- [ ] `hass_themes_updated` listener is attached in `connectedCallback()` and removed in `disconnectedCallback()`
- [ ] No MutationObserver watches data-theme (deprecated in favor of event listener)
- [ ] All CSS colors use CSS custom properties (no hardcoded hex in component selectors)
- [ ] 300ms CSS transition applied to color properties only
- [ ] Empty state message mentions `battery_level` attribute and binary sensors
- [ ] All buttons are 44px+ touch targets
- [ ] No console errors or warnings when opening panel
- [ ] Theme switch <300ms visible (measured in DevTools)
- [ ] No layout shifts during theme transition
- [ ] WCAG AA contrast ratios verified in both light and dark
- [ ] Loki (QA) confirms all E2E tests pass

---

## Known Risks & Mitigations

### Risk 1: hass.themes Undefined
**Potential Issue**: Older HA versions might not expose `hass.themes`
**Mitigation**: Check `hass.themes?.darkMode !== undefined` before using. Fallback chain handles this gracefully.

### Risk 2: Event Listener Memory Leak
**Potential Issue**: Listener not removed if panel is opened/closed repeatedly
**Mitigation**: Always remove listener in `disconnectedCallback()`. Store listener reference as `this._themeListener`.

### Risk 3: Double Re-renders
**Potential Issue**: Theme change fires multiple times, causing unnecessary renders
**Mitigation**: Lit's `requestUpdate()` is queued, only one render per microtask. No explicit debounce needed.

### Risk 4: CSS Transition Jank
**Potential Issue**: Transitioning layout properties causes scroll jank
**Mitigation**: Transition only color properties (background-color, color, border-color). No width/height/padding transitions.

### Risk 5: Scroll Regression
**Potential Issue**: New theme logic interferes with infinite scroll performance
**Mitigation**: Theme detection/application is decoupled from scroll logic. Performance tests in Story 4.3 verify no regression.

---

## Testing Expectations

### Unit Tests (If Applicable)
- Test `_detect_theme()` with various inputs (hass.themes.darkMode = true/false/undefined)
- Test fallback chain order
- Verify `_apply_theme()` sets DOM attribute correctly

### Integration Tests (E2E via Playwright)
- Load panel, verify theme is applied on initial render
- Change HA theme in UI, verify panel theme updates <300ms
- Verify scroll performance with 150+ devices (no jank during theme switch)
- Verify buttons and modals are accessible (44px touch targets, labels, WCAG AA)

### Manual Testing
- Open panel in light HA theme, verify light colors
- Switch HA theme to dark, verify dark colors transition smoothly
- Switch to custom theme (e.g., "Solarized Dark"), verify colors apply correctly
- Close and reopen panel, verify theme persists
- Test on mobile viewport (iPhone, Android), verify touch targets work

### Performance Testing
- CSS transition duration: 300ms ± 50ms
- No layout shifts during transition
- Scroll FPS remains >50 fps during theme switch
- Theme detection <50ms (hass.themes lookup)

---

## QA Handoff

**What Loki (QA) will verify**:
1. All 5 stories implement acceptance criteria correctly
2. All Sprint 3 tests continue to pass (28/28)
3. New themes work correctly (light/dark/custom)
4. Empty state message is clear and accessible
5. Scroll performance unchanged (150+ devices)
6. Notification modal is discoverable and functional
7. Deployment is clean and rollback works
8. No console errors or accessibility violations
9. Touch targets are 44px+ on mobile

**QA Test Artifacts** (to be generated):
- Playwright test results (pass/fail per story)
- Performance metrics (scroll FPS, transition time)
- Accessibility report (axe-core results)
- Deployment test log (SSH commands, HA restart, health check)
- Device list with 150+ mock entities (for performance testing)

---

## Success Criteria (Architect's Definition)

✅ Sprint 4 is complete when:
1. 5/5 stories implemented and code-reviewed
2. All Sprint 3 tests pass (28/28) — no regressions
3. Theme detection uses `hass.themes.darkMode` as primary source
4. Theme switching is smooth, <300ms visible transition
5. Empty state messaging is improved and helpful
6. Notification modal is discoverable (button visible, 44px touch target)
7. Scroll performance remains smooth (150+ devices, no jank)
8. Deployment to test HA server succeeds and is reversible
9. All accessibility requirements met (WCAG AA, touch targets, contrast ratios)
10. No console errors or warnings in production build

---

## Architecture Support

I (FiremanDecko) am available for:
- Design review of theme detection implementation
- Consultation on CSS custom properties and transitions
- Analysis of performance regressions (if any)
- Guidance on HA API usage (hass.themes, hass_themes_updated)
- Code review feedback before QA handoff

---

## References

- **System Design**: `architecture/system-design.md` (full theme architecture)
- **Sprint Plan**: `architecture/sprint-plan.md` (5 stories with AC)
- **Design Brief**: `design/product-design-brief.md` (UX requirements)
- **ADR-011**: `architecture/adrs/ADR-011-dark-mode-support.md` (Sprint 3 dark mode decision)
- **ADR-014**: `architecture/adrs/ADR-014-theme-detection-strategy.md` (NEW: Sprint 4 theme strategy)
- **API Contracts**: `architecture/api-contracts.md` (no API changes in Sprint 4)
- **Wireframes**: `design/wireframes.md` (UX layouts)

---

**Good luck! Let's ship this sprint. — FiremanDecko**
