# Sprint 3 Implementation Plan

**Prepared by**: FiremanDecko (Architect)
**Date**: February 22, 2026
**Duration**: 2 weeks (10 business days)
**Capacity**: 16 days
**Team**: Lead Developer, QA, Architect (review)

---

## Sprint Overview

Sprint 3 transforms Vulcan Brownout from an active monitoring tool into a truly proactive system by adding five major features:

1. **Infinite Scroll with Server-Side Pagination** (Cursor-based)
2. **Binary Sensor Filtering** (Data quality fix - quick win)
3. **Notification System with Preferences UI** (Smart alerts)
4. **Dark Mode / Theme Support** (Auto-detect HA theme)
5. **Deployment & Infrastructure** (Health checks + idempotent)

**Total Effort**: 16 days (at full capacity)

**Sprint Goal**: Ship proactive battery monitoring with notifications, infinite scroll for large device libraries, and automatic dark mode support.

---

## Story 1: Fix Binary Sensor Filtering

**Priority**: P1 (Data Quality)
**Effort**: 1 day
**Complexity**: Small (S)
**Owner**: Lead Developer
**Dependencies**: None (Quick Win - Do First)

### User Story

```
As a Home Assistant user,
I want binary sensors to be excluded from my battery list,
So that I only see devices with actual battery_level values.
```

### Acceptance Criteria

- [ ] Query filters entities WHERE device_class='battery' AND battery_level IS NOT NULL
- [ ] Binary sensors (even with device_class=battery) are excluded from results
- [ ] Empty state UI shows friendly message if no battery entities found
- [ ] Empty state message: "No battery devices found. Check your Home Assistant configuration."
- [ ] Empty state includes helpful link to docs
- [ ] QA: Verify 45 problematic 0% devices removed from test HA instance
- [ ] Existing user data not affected (no breaking change)
- [ ] Tested on HA 2026.2.2+

### Technical Notes

**Backend Implementation**:
1. Modify `battery_monitor.py`:
   - Update entity discovery filter in `get_battery_entities()`
   - Add check: `battery_level` attribute exists and is numeric (0-100)
   - Exclude domain == 'binary_sensor' explicitly

2. Modify `websocket_api.py`:
   - Update `handle_query_devices()` to use filtered list
   - Return empty devices array if no matches
   - Ensure `device_statuses` reflects filtered count

**Frontend Implementation**:
1. Modify `vulcan-brownout-panel.js`:
   - Add empty state template: Show if `devices.length === 0`
   - Icons, helpful text, link to docs
   - Refresh button to retry query

**Testing**:
- Unit: Filtering logic for battery_level attribute
- Integration: Query real HA instance, count filtered devices
- E2E: Verify 45 binary sensors excluded
- QA: Manual test on test HA

**Why First?**: This is a one-day task that cleans up data quality. Do it immediately to unblock other stories. Loki already identified the issue in QA testing.

---

## Story 2: Infinite Scroll with Server-Side Pagination

**Priority**: P1 (Must Have)
**Effort**: 3 days
**Complexity**: Large (L)
**Owner**: Lead Developer
**Dependencies**: Story 1 (filtering complete)

### User Story

```
As a Home Assistant user with 150+ battery devices,
I want automatic infinite scroll pagination without clicking "Load More",
So that I can browse all my batteries without the UI lagging.
```

### Acceptance Criteria

- [ ] Initial load shows first 50 battery devices
- [ ] When user scrolls within 100px of bottom, fetch next 50 devices
- [ ] Skeleton loaders appear for each loading item (not blank space)
- [ ] New items append smoothly without layout shift or jank
- [ ] "Back to top" button appears after user scrolls past 30 items
- [ ] Button floats sticky, bottom-right corner
- [ ] Scroll position restored if user navigates away and returns (sessionStorage)
- [ ] No duplicate items during rapid scroll
- [ ] Tested with 200+ devices, WebSocket real-time updates continue
- [ ] Sort/filter state preserved during scroll
- [ ] Mobile: Tested on iPhone 12 and iPad, smooth performance
- [ ] Cursor-based pagination: Uses last_changed + entity_id as stable cursor
- [ ] Pagination works with threshold filtering (only affected devices)

### Technical Notes

**Backend Implementation**:
1. Modify `websocket_api.py`:
   - Update `handle_query_devices()` to support cursor-based pagination
   - Replace `offset` parameter with `cursor` parameter
   - Generate `next_cursor` from last item in response
   - Limit page size to max 100 items

2. Modify `battery_monitor.py`:
   - Add pagination helper: `get_devices_paginated(cursor, limit, sort_key)`
   - Cursor format: base64-encoded `{last_changed}|{entity_id}`
   - Stable ordering: Sort by status + battery_level, then use cursor

**Frontend Implementation**:
1. Modify `vulcan-brownout-panel.js`:
   - Add infinite scroll detection (Intersection Observer)
   - Track current cursor and has_more flag
   - Implement fetch logic with debounce (prevent duplicates)
   - Add skeleton loaders (5 placeholders per batch)

2. Create skeleton loader component:
   - Animation: Shimmer gradient, 2s cycle
   - Colors: Dark mode #444444, light mode #E0E0E0
   - Fade in/out with real items

3. Add "Back to Top" button:
   - Sticky positioning: bottom-right corner, 16px from edges
   - Show trigger: scrolled past 30 items
   - Click handler: smooth scroll to top (500ms)
   - Fade in/out animation (300ms)

4. Add scroll position restoration:
   - Save to sessionStorage on scroll
   - Restore on component init
   - Clear on panel close

**Testing**:
- Unit: Cursor encoding/decoding, pagination logic
- Integration: Query 200+ device HA instance, fetch multiple pages
- E2E: Scroll to bottom multiple times, verify no duplicates
- Performance: Monitor framerate during scroll (target: 60 FPS)
- Mobile: iPhone 12 + iPad, test on real devices

**QA Acceptance**:
- Load panel, scroll to bottom, verify next 50 devices load automatically
- Verify skeleton loaders visible during load (no blank space)
- Verify "Back to Top" button appears after scrolling 30+ items
- Scroll to top, button disappears
- Click button, smooth scroll to top
- Refresh page mid-scroll, verify position restored
- Tested with 200 device HA instance (performance OK)

---

## Story 3: Notification System with Preferences UI

**Priority**: P1 (Market Fit)
**Effort**: 4 days
**Complexity**: Large (L)
**Owner**: Lead Developer
**Dependencies**: Story 1 (filtering), Story 2 (pagination) - can start after Story 1

### User Story

```
As a Home Assistant user with critical battery devices,
I want to receive HA notifications when devices drop below their threshold,
So that I can proactively replace batteries before devices fail.
```

### Acceptance Criteria

- [ ] Notification Preferences UI: Accessible from Settings panel
- [ ] Global toggle: Enable/disable all notifications (default: ON)
- [ ] Per-device toggles: Users can opt-in/out of notifications per device
- [ ] Frequency cap options: 1 hour / 6 hours / 24 hours (default: 6 hours)
- [ ] Severity filter: Critical only, or Critical + Warning (default: Critical only)
- [ ] WebSocket integration: When battery drops below threshold, queue notification via HA service
- [ ] Notification payload: "{Device} battery {status} ({X}%) — action needed soon"
- [ ] Notifications logged in HA's notification center (visible in history)
- [ ] User can review past notifications from HA UI
- [ ] Frequency cap enforced: Max 1 notification per device per cap period
- [ ] Mobile: UI responsive and usable on 375px screens
- [ ] Accessibility: All controls have ARIA labels, keyboard navigable
- [ ] QA: Test notification delivery on HA 2026.2.2+
- [ ] Notification preferences persist in HA ConfigEntry.options
- [ ] Changes survive HA restart

### Technical Notes

**Backend Implementation**:
1. Create `NotificationManager` class:
   - Monitor battery levels in real-time (via subscription manager)
   - Check thresholds and notification preferences
   - Enforce frequency caps (track last_notification_time per device)
   - Queue notifications to HA persistent_notification service

2. Modify `__init__.py`:
   - Create NotificationManager on setup
   - Load notification preferences from config entry
   - Register handler for state_changed events

3. Modify `config_flow.py`:
   - Add notification preferences to ConfigEntry.options
   - Schema validation: frequency_cap_hours in [1, 6, 24]
   - Schema validation: severity_filter in ['critical_only', 'critical_and_warning']

4. Modify `websocket_api.py`:
   - Add `handle_get_notification_preferences()` command
   - Add `handle_set_notification_preferences()` command
   - Add `notification_sent` event broadcast (for history UI)

5. API call to HA:
   - Use `hass.services.async_call('persistent_notification', 'create', ...)`
   - Payload: title, message, notification_id (for deduplication)

**Frontend Implementation**:
1. Create Notification Preferences Modal:
   - Global enable/disable toggle (44px touch target)
   - Frequency dropdown: 1h, 6h, 24h (default: 6h)
   - Severity radio buttons: Critical only (default) or Critical+Warning
   - Per-device list with checkboxes (searchable)
   - Show 5 devices, "Show More" if > 5
   - Notification history: Last 3-5 notifications with timestamps
   - Buttons: Save, Cancel

2. Modify Settings Panel:
   - Add "[⚙️ CONFIGURE NOTIFICATIONS]" button
   - Opens notification preferences modal

3. Add notification history display:
   - Subscribe to `notification_sent` events
   - Append to history list
   - Show timestamp, device, battery %, status
   - Limit to 10-20 items in UI

**Testing**:
- Unit: Notification frequency cap logic, preference validation
- Integration: Create test device at critical level, verify notification sent
- Integration: Change frequency cap, verify cap enforced (no spam)
- E2E: Disable device notifications, verify device no longer triggers alerts
- QA: Multi-device scenario (5 devices drop critical simultaneously, verify notifications sent with correct frequency caps)
- QA: Restart HA, verify preferences persist

**QA Acceptance**:
- Set global threshold 30%, verify notification sent when device drops below
- Configure frequency cap 1 hour, device drops critical twice within 1 hour, verify only 1 notification sent
- Disable notifications for "Kitchen Sensor", set threshold 15%, drop kitchen sensor below 15%, verify no notification
- Check HA notification center, verify notification history shows all sent notifications
- Mobile: Open preferences modal on iPhone 12, verify all controls usable (touch targets ≥ 44px)
- Keyboard: Tab through modal, toggle per-device, save preferences using keyboard only

---

## Story 4: Dark Mode / Theme Support

**Priority**: P1 (User Adoption)
**Effort**: 2 days
**Complexity**: Medium (M)
**Owner**: Lead Developer
**Dependencies**: Stories 1-3 can happen in parallel

### User Story

```
As a Home Assistant user with dark mode enabled,
I want Vulcan Brownout to automatically render in dark colors,
So that the integration feels native and doesn't force me to switch to light mode.
```

### Acceptance Criteria

- [ ] Panel detects HA's theme setting (dark / light / auto)
- [ ] Colors automatically adapt: dark backgrounds, light text
- [ ] Status colors tested for contrast on dark background (WCAG AA minimum)
  - [ ] Critical: #FF5252 (lightened red) on #1C1C1C
  - [ ] Warning: #FFB74D (lightened amber) on #1C1C1C
  - [ ] Healthy: #66BB6A (lightened green) on #1C1C1C
  - [ ] Unavailable: #BDBDBD (unchanged gray)
- [ ] All text passes 4.5:1 contrast ratio on dark backgrounds
- [ ] Settings panel: dark backgrounds, light inputs
- [ ] Buttons, icons, badges: adapt to dark theme
- [ ] Sort/filter dropdowns: dark theme colors
- [ ] Connection badge: visible and clear on dark background
- [ ] No hardcoded colors in CSS — use HA CSS custom properties (--primary-color, --card-background-color, etc.)
- [ ] Tested on HA light and dark themes
- [ ] No flashing or theme-switch lag (smooth 300ms transition)
- [ ] Mobile: dark mode readable on small screens
- [ ] Automatically re-detect theme if user toggles HA theme while panel is open (MutationObserver)

### Technical Notes

**Frontend Implementation**:
1. Create CSS custom properties for all colors:
   - `--vb-bg-primary`, `--vb-bg-card`, `--vb-text-primary`, `--vb-color-critical`, etc.
   - Define in `:root` (light mode) and `[data-theme="dark"]` (dark mode)

2. Add theme detection:
   - On component load, call `detectTheme()` function
   - Check: `document.documentElement.getAttribute('data-theme')`
   - Fallback: `window.matchMedia('(prefers-color-scheme: dark)').matches`
   - Fallback: `localStorage.getItem('ha_theme')`

3. Add theme listener (MutationObserver):
   - Watch for `data-theme` attribute changes on `<html>`
   - Trigger re-render when theme toggles
   - Smooth transition (300ms CSS) between themes

4. Apply CSS variables to all components:
   - Battery cards: `background: var(--vb-bg-card)`
   - Status colors: `color: var(--vb-color-critical)` or `--vb-color-warning` or `--vb-color-healthy`
   - Text: `color: var(--vb-text-primary)` or `--vb-text-secondary`

**Testing**:
- Unit: Theme detection logic (all three methods)
- Integration: Load panel in light mode, verify light colors
- Integration: Load panel in dark mode, verify dark colors
- E2E: Start in light mode, toggle HA theme to dark, verify panel transitions smoothly
- Contrast: Use WebAIM contrast checker, verify all colors meet WCAG AA (4.5:1)
- Mobile: Load on iPhone 12 in dark mode, verify readable
- Performance: Measure theme switch time (should be < 100ms total)

**QA Acceptance**:
- Load panel with HA in light mode, verify light background + dark text
- Load panel with HA in dark mode, verify dark background + light text
- Verify critical status color (#FF5252) is readable on dark background
- Toggle HA theme while panel is open, verify smooth transition (no flashing)
- All status colors pass WCAG AA contrast ratio
- Mobile (390px): Dark mode text is readable

---

## Story 5: Deployment & Infrastructure (Idempotent + Health Checks)

**Priority**: P0 (Mandatory)
**Effort**: 2 days
**Complexity**: Medium (M)
**Owner**: Lead Developer
**Dependencies**: Stories 1-4 (all features complete)

### User Story

```
As an operations team managing Vulcan Brownout production instance,
I want idempotent deployment with health checks for all services,
So that deployments are safe and failures are caught before users notice.
```

### Acceptance Criteria

- [ ] Deployment script is fully idempotent (safe to run 2+ times)
- [ ] Database migrations are reversible (rollback support for notification settings table)
- [ ] .env validation: Check required env vars before deploy (HASS_URL, HASS_TOKEN, etc.)
- [ ] Health check endpoint: GET /health returns JSON with service statuses
  - [ ] WebSocket connectivity: ping HA, verify response
  - [ ] Notification service: verify HA notification service is available
  - [ ] Database: verify connection and migrations complete
- [ ] Health check response example:
  ```json
  {
    "status": "healthy",
    "services": {
      "websocket": "connected",
      "notifications": "ready",
      "database": "migrated"
    },
    "timestamp": "2026-02-22T10:30:00Z"
  }
  ```
- [ ] Failed health check triggers rollback to previous version
- [ ] Deployment logs clearly indicate success/failure/rollback
- [ ] Rollback script tested: confirm previous version is active after rollback
- [ ] Secrets: All HA tokens sourced from .env, never logged or committed
- [ ] SSH keys: Not stored in repo, managed via environment or CI/CD secrets
- [ ] Post-deployment smoke test: Manually trigger battery critical notification, verify HA receives it
- [ ] No downtime during deployment (blue-green deployment or service restart strategy)
- [ ] Deployment < 5 minutes total time
- [ ] Tested: 3+ idempotent runs with zero errors

### Technical Notes

**Backend Implementation**:
1. Create health check endpoint:
   - Route: `GET /api/vulcan_brownout/health`
   - Verify: WebSocket ready, notification service available, database connected
   - Return: JSON with status, services dict, timestamp
   - Retry: 3 attempts with backoff if fails

2. Database migration support:
   - Create `alembic` migration for notification preferences table (if using SQLAlchemy)
   - Or: HA ConfigEntry options (simpler, no separate DB)
   - Migration must be reversible (for rollback)

3. Error logging:
   - Log all deployment steps (start, config validation, install, health check, rollback)
   - Include timestamps and latencies
   - Log to systemd journal or file

**Deployment Script (`deploy.sh` UPDATED)**:
1. Environment validation:
   - Check required .env variables exist (HASS_URL, HASS_TOKEN, SSH_HOST, SSH_USER)
   - Validate format (IP addresses, ports, tokens non-empty)
   - Exit with clear error if missing

2. Idempotent operations:
   - Use `set -e` (exit on error)
   - Use `rsync` with `--delete` (safe for repeated runs)
   - Skip steps if already complete (check flags)

3. Rollback mechanism:
   - Keep previous version in `releases/` directory
   - Use symlink: `current/ -> releases/{version}/`
   - On failure: Swap symlink to previous version
   - Log: "Rollback: Version X active"

4. Health check:
   - POST-deploy, call health check endpoint
   - Retry 3 times with backoff (1s, 2s, 4s)
   - Timeout: 30s total
   - If fails: Trigger rollback

5. Smoke test:
   - After health check passes
   - Manually set device battery to critical level
   - Wait for notification to appear in HA
   - Verify notification received within 5s
   - Log result

**Testing**:
- Manual: Run deploy script 3+ times, verify idempotent (no errors on repeat runs)
- Manual: Deploy with missing .env variable, verify validation catches it + clear error
- Manual: Simulate health check failure, verify rollback triggers + previous version active
- Manual: Check git history, verify no secrets committed
- Manual: Monitor HA logs, check for errors or warnings post-deploy
- Performance: Measure full deploy time (target: < 5 minutes)

**QA Acceptance**:
- Run deployment script twice, both succeed with no errors
- Deploy with invalid .env, get clear error message + no changes made
- Deploy with health check failure, verify automatic rollback to previous version
- Verify previous version is active after rollback (test real-time updates work)
- Check git history: No .env or secrets found
- Check HA logs: No integration errors post-deploy

---

## Implementation Timeline

### Week 1

| Day | Story | Tasks | Lead Dev | QA |
|-----|-------|-------|----------|-----|
| Mon (2/24) | Story 1 | Backend: Binary sensor filtering query | START | Setup |
| Tue (2/25) | Story 1 | Frontend: Empty state UI + Docs link | CONTINUE | Review |
| Wed (2/26) | Story 2 | Backend: Cursor-based pagination API | START | Story 1 QA |
| Thu (2/27) | Story 2 | Frontend: Infinite scroll, skeleton loaders, back-to-top button | CONTINUE | Review |
| Fri (2/28) | Story 3 | Backend: NotificationManager, HA service integration | START | Story 2 QA |

### Week 2

| Day | Story | Tasks | Lead Dev | QA |
|-----|-------|-------|----------|-----|
| Mon (3/3) | Story 3 | Frontend: Notification preferences modal, history | CONTINUE | Story 2 QA |
| Tue (3/4) | Story 3 | Testing, frequency cap logic, multi-device scenarios | CONTINUE | Testing |
| Wed (3/5) | Story 4 | Theme detection, CSS variables, dark mode colors | START | Story 3 QA |
| Thu (3/6) | Story 4 | Theme listener, MutationObserver, dark mode testing | CONTINUE | Testing |
| Fri (3/7) | Story 5 | Deployment script, health check, rollback mechanism | START | Final Testing |

### Sprint End

- **Code Review**: All PRs approved by Architect (Wed-Fri)
- **QA Sign-Off**: All stories accepted by QA (Fri)
- **Documentation**: Updated README, API docs (Fri)
- **Retrospective**: Team review (Fri afternoon)

---

## Dependencies & Risks

### External Dependencies

- **Home Assistant 2026.2.2+**: Required for theme detection, persistent_notification service
- **Browser WebSocket Support**: All modern browsers supported
- **localStorage Availability**: Must work in incognito/private mode (graceful fallback)

### Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Cursor pagination edge cases | Medium | Some items missed or duplicated | Thorough testing with 200+ devices, cursor format validation |
| Notification spam | Medium | Users disable notifications | Frequency cap logic tested with 10+ devices dropping critical simultaneously |
| Dark mode contrast issues | Low | Inaccessible colors | Use contrast checker, test on real dark backgrounds |
| Theme detection failure | Low | Wrong colors applied | Multiple fallback detection methods, default to light |
| Deployment rollback fails | Low | Service down 1-5 minutes | Test rollback 3+ times before release, keep 2 version releases |

### Mitigation Strategies

1. **Cursor Pagination**: Extensive testing with large device sets, cursor encoding/decoding validation
2. **Notification Spam**: Unit tests for frequency cap logic, QA multi-device testing
3. **Dark Mode**: Use WebAIM contrast checker, test on real devices, WCAG AA compliance
4. **Theme Detection**: Three methods (HA data-theme, matchMedia, localStorage), default to light
5. **Deployment**: Test 3+ idempotent runs, dry-run before production, keep previous version active

---

## Success Criteria

**All Criteria Must Be Met for Sprint 3 Acceptance:**

1. **Story 1 (Binary Sensor Filter)**: 45 problematic devices filtered out, empty state shows on no devices
2. **Story 2 (Infinite Scroll)**: Pagination stable with 200+ devices, smooth scrolling (60 FPS), back-to-top works
3. **Story 3 (Notifications)**: Notifications sent/suppressed correctly, frequency caps enforced, preferences persist
4. **Story 4 (Dark Mode)**: Auto-detect theme, colors adjusted, smooth transition on theme change, WCAG AA contrast
5. **Story 5 (Deployment)**: Idempotent script, rollback works, health checks pass, secrets not in git
6. **Quality**: Zero critical bugs, ≤ 3 minor bugs, all console errors resolved
7. **Testing**: > 80% code coverage, all acceptance criteria met
8. **Documentation**: Architecture docs complete, API contracts updated, README current

---

## Resource Plan

**Team**:
- Lead Developer: 8 days (full-time, all 5 stories)
- QA: 6 days (testing, regression, acceptance)
- Architect: 2 days (design review, code review, ADR approval)

**Tools**:
- Home Assistant test instance (pre-provisioned at HA 2026.2.2)
- GitHub for version control
- GitHub Actions for CI/CD (optional for Sprint 3)
- Lighthouse for accessibility audits
- Chrome DevTools for performance profiling
- WebAIM contrast checker for dark mode colors

**Capacity Planning**:
- Total capacity: 16 days
- Planned work: 1 + 3 + 4 + 2 + 2 = **12 days** ✅
- Contingency: 4 days buffer for unexpected issues

**Risk**: Story 3 (Notifications) is most complex. If it overruns, buffer absorbs slip. If slip > 4 days, may need to cut scope.

---

## Handoff Criteria

Before Sprint 3 ships to production:

- [ ] All 5 stories implemented and merged to `develop` branch
- [ ] All code reviewed and approved by Architect
- [ ] All tests passing (> 80% coverage)
- [ ] QA acceptance for all stories
- [ ] Zero critical bugs
- [ ] No console errors or warnings
- [ ] Deployment script tested 3+ times (idempotent)
- [ ] Documentation complete (README, API docs, ADRs)
- [ ] Performance targets met (infinite scroll smooth, notifications < 2s)
- [ ] Accessibility testing complete (dark mode, WCAG AA contrast)
- [ ] Mobile testing complete (iPhone 12, iPad)
- [ ] Binary sensor filtering verified (45 devices removed)

---

**Prepared by**: FiremanDecko (Architect)
**Reviewed by**: [Product Owner], [Tech Lead]
**Approved**: [Sprint 3 Kickoff]
**Last Updated**: February 22, 2026
