# Sprint 4 QA Handoff

**From**: ArsonWells → Loki | **Status**: READY FOR QA

## What Was Built

All 5 stories implemented with frontend-only changes (no backend modifications).

**Story 4.1**: Theme Detection Architecture
- Replaced DOM sniffing with `hass.themes.darkMode` as primary theme source
- Added `hass_themes_updated` event listener for real-time theme switching
- Smooth 300ms CSS transitions on color properties (no layout shifts)
- Fallback chain: `hass.themes.darkMode` → DOM `data-theme` → OS preference → light

**Story 4.2**: Empty State Messaging
- Updated empty state to explain `battery_level` attribute requirement
- Added guidance about binary sensor exclusion
- Three action buttons: Refresh, Settings, Docs

**Story 4.3**: Scroll Performance Verification
- Sentinel element has `min-height: 1px` to prevent layout shifts
- Skeleton loaders set to consistent 68px height
- Back-to-top button has `touch-action: manipulation` for mobile performance

**Story 4.4**: Notification Modal UX
- Notification button has min 44px touch target
- Modal close button meets 44px touch target requirement
- Added `aria-label` attributes for accessibility

**Story 4.5**: Deployment & Versioning
- Updated `manifest.json` version to 4.0.0
- Enhanced deploy script with SSH rsync, health checks, and rollback capability
- Script is idempotent (safe to run multiple times)

## Files Changed

- **vulcan-brownout-panel.js**: Added `_detect_theme()`, `_apply_theme()`, `_setup_theme_listener()`. Updated `connectedCallback()` and `disconnectedCallback()`. Added CSS transitions. Updated empty state messaging. Added aria-labels.
- **manifest.json**: Version bumped to 4.0.0
- **deploy.sh**: Complete rewrite for Sprint 4 - sources `.env`, includes SSH rsync to HA server, health checks with authorization, service restart, and idempotent cleanup

## Setup (Redeploy Sprint 3 First)

The Sprint 3 code is already correct — bugs reported by Loki were already in the codebase.
Just re-run the deployment script to ensure the test HA server is running Sprint 3 code:

```bash
cd /sessions/confident-charming-pascal/mnt/vulcan-brownout
source .env
bash development/scripts/deploy.sh
```

## Sprint 3 Regression Tests (Run First)

Re-run the existing Sprint 3 suite to confirm 28/28 pass:

```bash
cd /sessions/confident-charming-pascal/mnt/vulcan-brownout/quality
python3 scripts/test_sprint3_integration.py
```

**Expected**: 28/28 pass. If not, stop — do not proceed to Sprint 4 tests.

## Sprint 4 Test Checklist

### S4.1: Theme Detection

- [ ] Panel loads with correct theme (dark if HA profile is dark, light if light)
- [ ] Change HA profile theme in Settings → Person → Theme
- [ ] Panel updates color within 300ms (smooth transition, no flicker)
- [ ] No console errors on theme change
- [ ] Fallback works: if `hass.themes` unavailable, DOM detection kicks in
- [ ] Close and reopen panel → theme persists correctly
- [ ] Test light theme: white bg, dark text, blue action buttons
- [ ] Test dark theme: dark gray bg, white text, blue action buttons
- [ ] Contrast ratios verified: text on bg ≥ 4.5:1 (WCAG AA minimum)
- [ ] Listener cleaned up: open/close panel multiple times, memory stable

### S4.2: Empty State

- [ ] Empty state displays when no battery entities found
- [ ] Message says: "No battery entities found. Check that your devices have a `battery_level` attribute..."
- [ ] Three buttons visible and functional: Refresh, Settings, Docs
- [ ] All buttons 44px+ touch target
- [ ] Message text color matches theme (white in dark, dark in light)
- [ ] Mobile viewport: buttons stack or wrap, all clickable

### S4.3: Scroll Performance

- [ ] Load test with 150+ mock battery devices (Playwright or manual)
- [ ] Scroll down to bottom smoothly (no jank)
- [ ] 60 FPS maintained during scroll (DevTools Performance tab)
- [ ] Theme switch while scrolling: no layout shift (colors change smoothly)
- [ ] Pagination fetch completes <500ms, items append without jumping
- [ ] Skeleton loader cards have consistent 68px height
- [ ] Back-to-top button appears after scrolling 30+ items
- [ ] Back-to-top scroll animation smooth (300ms)
- [ ] Sentinel element (1px) doesn't cause layout shift

### S4.4: Notification Modal

- [ ] Notification button visible in header, clearly labeled "Notifications"
- [ ] Button min-height: 44px, min-width: 44px (touch target)
- [ ] Click button → modal slides up from bottom
- [ ] Modal header shows "🔔 Notification Preferences"
- [ ] Close button (✕) visible, 44px+ touch target
- [ ] Modal sections visible: Enable, Frequency Cap, Severity Filter
- [ ] Notification history list scrollable if >5 items
- [ ] Save and Cancel buttons clearly visible, functional
- [ ] Modal closes on Cancel or overlay click
- [ ] Settings persist after save (via WebSocket)

### S4.5: Deployment

- [ ] manifest.json version is 4.0.0
- [ ] deploy.sh runs without errors: `bash development/scripts/deploy.sh`
- [ ] Run deploy.sh twice → same result (idempotent)
- [ ] Health check endpoint responds: `/api/vulcan_brownout/health`
- [ ] No console errors post-deploy
- [ ] Integration loads in HA UI (Settings → Devices & Services → Vulcan Brownout)
- [ ] Panel opens and displays battery devices without error
- [ ] SSH deployment to remote HA works (if SSH_HOST configured in .env)

## Blocking Issues

If any test fails, open a GitHub issue and notify ArsonWells with:
- Test case that failed
- Expected vs actual behavior
- Steps to reproduce
- Screenshots (if applicable)

Do not mark Sprint 4 complete until all tests pass.

## Browser/Environment

- **HA Version**: 2026.2.0+
- **Browser**: Chrome/Firefox (ES6+ support required)
- **Mobile**: Test on iPhone (390px) and Android devices
- **Network**: Test on stable + throttled connections (slow 3G)

## Post-QA

Once all tests pass:
1. Update this document with test results
2. Notify ArsonWells: "Sprint 4 QA COMPLETE - 5/5 stories PASS"
3. Prepare for Sprint 5 work
