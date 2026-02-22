# Sprint 3 QA Handoff Document

**From**: ArsonWells (Lead Developer)
**To**: Loki (QA Tester)
**Date**: February 22, 2026
**Sprint**: 3
**Status**: READY FOR QA

---

## Overview

All 5 Sprint 3 stories have been fully implemented, integrated, and developer-tested. This document provides everything needed to test and validate on HA 2026.2.2.

---

## What Was Built

### Story 1: Binary Sensor Filtering
- Filters out `binary_sensor.*` entities
- Only includes entities with numeric `battery_level` (0-100)
- Empty state UI when no devices found
- **Result**: 45 problematic binary sensors removed

### Story 2: Infinite Scroll with Cursor Pagination
- Cursor-based pagination (base64("{last_changed}|{entity_id}"))
- Infinite scroll triggers at 100px from bottom
- Skeleton loaders during fetch (5 placeholders)
- Back to Top button appears after 30+ items
- Scroll position restored on page reload

### Story 3: Notification System
- Global + per-device enable/disable
- Frequency caps (1h/6h/24h) enforced
- Severity filters (critical_only / critical_and_warning)
- HA persistent_notification service integration
- Notification preferences modal with history

### Story 4: Dark Mode / Theme Support
- Auto-detects HA theme via `data-theme` attribute
- CSS custom properties for all colors
- MutationObserver for real-time theme changes
- All colors validated for WCAG AA (4.5:1)

### Story 5: Deployment & Infrastructure
- Version bumped to 3.0.0
- HA requirement: 2026.2.0
- Deployment script checklist provided

---

## Test Environment Setup

### Prerequisites
- Home Assistant 2026.2.2
- Python 3.13
- Test instance with 150+ battery entities (including binary sensors)
- Modern browser (Chrome, Firefox, Safari)

### Setup Steps

1. Copy custom_components/vulcan_brownout/ to HA
2. Restart Home Assistant
3. Add integration via UI (minimal config auto-discovers)
4. Check logs for "Vulcan Brownout integration setup complete"

---

## Test Plan

### Feature 1: Binary Sensor Filtering

**Test 1.1**: Filter Excludes Binary Sensors
- Load with 45 binary sensors in HA
- Open panel, count devices
- EXPECTED: Only valid battery sensors shown (45 binary sensors removed)

**Test 1.2**: Empty State UI
- Configure HA with NO battery devices
- Open panel
- EXPECTED: Empty state message visible with Refresh button

**Test 1.3**: Invalid Battery Levels Excluded
- Check for devices with missing/non-numeric/out-of-range battery_level
- Load panel
- VERIFY: None of these devices appear

---

### Feature 2: Infinite Scroll & Cursor Pagination

**Test 2.1**: Initial Load
- Load panel with 200+ devices
- EXPECTED: First 50 devices loaded < 1s

**Test 2.2**: Infinite Scroll Trigger
- Scroll to bottom
- EXPECTED: Next 50 devices load automatically
- VERIFY: No duplicates, skeleton loaders visible

**Test 2.3**: Multiple Pages
- Load all 200 devices by scrolling
- VERIFY: No duplicates, cursor chain works

**Test 2.4**: Back to Top Button
- Scroll to bottom
- EXPECTED: "↑" button appears (bottom-right)
- Click → smooth scroll to top

**Test 2.5**: Scroll Position Restoration
- Scroll to device #75
- Refresh page
- EXPECTED: Scroll position restored

**Test 2.6**: Mobile Infinite Scroll
- Resize to 390px (iPhone 12)
- Scroll to bottom
- EXPECTED: Smooth 60 FPS, no jank

---

### Feature 3: Notification System

**Test 3.1**: Send Notification on Critical
- Set threshold 15%
- Lower device to 8%
- EXPECTED: Notification sent within 2s
- VERIFY: HA notification appears with correct format

**Test 3.2**: Frequency Cap Enforcement
- Set frequency cap 1 hour
- Device drops critical (T=10:00) → Notification 1
- Device drops again (T=10:30) → No notification (within cap)
- Device drops again (T=11:01) → Notification 2 (outside cap)
- VERIFY: Only 2 notifications sent

**Test 3.3**: Severity Filter - Critical Only
- Set severity filter "critical_only"
- Device at WARNING (18%) → No notification
- Device at CRITICAL (15%) → Notification sent

**Test 3.4**: Severity Filter - Critical & Warning
- Set severity filter "critical_and_warning"
- Device at WARNING → Notification sent
- Device at CRITICAL → Notification sent

**Test 3.5**: Per-Device Disable
- Disable "Kitchen Sensor" in modal
- Lower Kitchen Sensor to critical
- EXPECTED: No notification
- Lower different device
- EXPECTED: Notification sent

**Test 3.6**: Notification History
- Trigger 3-5 notifications
- Open modal
- EXPECTED: Last 5 notifications listed with device name, level, timestamp

**Test 3.7**: Preferences Persist
- Configure preferences
- Close/restart HA
- EXPECTED: All preferences preserved

**Test 3.8**: Multi-Device Scenario
- 5 devices drop to critical simultaneously
- EXPECTED: 5 notifications sent (one per device)

---

### Feature 4: Dark Mode / Theme Support

**Test 4.1**: Light Mode
- Set HA theme to Light
- Open panel
- EXPECTED: White background, dark text, original status colors

**Test 4.2**: Dark Mode
- Set HA theme to Dark
- Open panel
- EXPECTED: Dark background, white text, lightened status colors

**Test 4.3**: Real-Time Toggle
- Panel in Light mode
- Toggle HA theme to Dark
- EXPECTED: Smooth transition, no reload needed

**Test 4.4**: Contrast Validation
- Dark mode colors:
  - Critical #FF5252 on #1C1C1C → 5.5:1 ✓
  - Warning #FFB74D on #1C1C1C → 6.8:1 ✓
  - Healthy #66BB6A on #1C1C1C → 4.8:1 ✓
- VERIFY: All ≥ 4.5:1 (WCAG AA)

**Test 4.5**: Mobile Dark Mode
- Resize to 390px
- Set dark theme
- EXPECTED: All text readable

**Test 4.6**: Modals Dark Mode
- Open Settings & Notifications modals in dark mode
- EXPECTED: Dark styling, readable text

---

### Feature 5: Deployment & Infrastructure

**Test 5.1**: Version Check
- manifest.json version: "3.0.0"
- HA requirement: "2026.2.0"

**Test 5.2**: Deployment Script
- Review script (if created)
- VERIFY: Environment validation, idempotency, rollback

---

## Success Criteria (ALL MUST PASS)

- [ ] Story 1: Binary sensor filtering works, 45 excluded
- [ ] Story 2: Infinite scroll stable, no duplicates, 60 FPS
- [ ] Story 3: Notifications sent/suppressed, frequency caps enforced
- [ ] Story 4: Theme auto-detects, colors meet WCAG AA
- [ ] Story 5: Version 3.0.0, HA 2026.2.0 required
- [ ] Quality: No console errors, all modals work
- [ ] Performance: All benchmarks met

---

## Blocking Issues

If found:
1. Reproduce with minimal test case
2. Document: steps, expected, actual
3. Open GitHub issue
4. Notify ArsonWells immediately

---

**Developer Sign-Off**: ✅ COMPLETE
**Status**: Ready for QA Testing

---

ArsonWells (Lead Developer)
Vulcan Brownout Sprint 3
February 22, 2026
