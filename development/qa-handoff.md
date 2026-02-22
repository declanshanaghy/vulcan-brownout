# Sprint 3 QA Handoff

**From**: ArsonWells → Loki | **Status**: READY FOR QA

All 5 stories implemented and developer-tested. See implementation-plan.md for details.

## Setup
1. Copy custom_components/vulcan_brownout/ to HA 2026.2.2
2. Restart HA, add integration via UI
3. Check logs for "Vulcan Brownout integration setup complete"

## Test Checklist

### S1: Binary Sensor Filtering
- [ ] 45 binary sensors excluded from 150+ entity test HA
- [ ] Empty state UI shows with no battery devices
- [ ] Invalid battery_level values excluded

### S2: Infinite Scroll
- [ ] First 50 devices load <1s
- [ ] Scroll to bottom → next 50 auto-load with skeleton loaders
- [ ] No duplicates across 200+ devices
- [ ] Back-to-top button appears after 30 items
- [ ] Scroll position restored on refresh
- [ ] Mobile 60 FPS (390px)

### S3: Notifications
- [ ] Notification sent within 2s when device drops below threshold
- [ ] Frequency cap enforced (2 drops in 1h with 1h cap → 1 notification)
- [ ] Severity filter works (critical_only blocks warning)
- [ ] Per-device disable works
- [ ] 5 devices critical simultaneously → 5 notifications
- [ ] Preferences persist after HA restart

### S4: Dark Mode
- [ ] Auto-detects HA theme correctly
- [ ] Toggle theme while panel open → smooth transition
- [ ] All colors WCAG AA (4.5:1) on dark bg
- [ ] Mobile dark mode readable (390px)

### S5: Deployment
- [ ] manifest.json: version 3.0.0, requirement 2026.2.0
- [ ] No console errors

## Blocking Issues
Reproduce, document, open GitHub issue, notify ArsonWells.
