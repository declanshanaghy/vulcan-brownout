# Sprint 2 Implementation Plan

**Prepared by**: FiremanDecko (Architect)
**Date**: February 2026
**Duration**: 2 weeks (10 business days)
**Capacity**: 16 days
**Team**: Lead Developer, QA, Architect (review)

---

## Sprint Overview

Sprint 2 transforms Vulcan Brownout from a passive display into an active monitoring tool by adding three major features:

1. **Real-Time Updates** (WebSocket subscriptions)
2. **Configurable Thresholds** (global + per-device)
3. **Sorting & Filtering** (user controls for device list)
4. **Responsive Mobile UX** (touch-friendly modals & controls)
5. **Deployment Infrastructure** (idempotent rollback-enabled deployment)

**Total Effort**: 16 days (at full capacity)

---

## Story 1: WebSocket Real-Time Updates

**Priority**: P1 (Should Have)
**Effort**: 4 days
**Complexity**: Large (L)
**Owner**: Lead Developer

### User Story

```
As a power user managing 20+ battery devices,
I want to see battery levels update in real-time without refreshing,
So that I have confidence the system is actively monitoring my devices.
```

### Acceptance Criteria

- [ ] WebSocket connection persists after initial load
- [ ] Backend sends `device_changed` event when battery level updates (< 100ms latency)
- [ ] Frontend receives event and updates device in list (smooth animation, 300ms)
- [ ] Connection badge shows status: 🟢 (connected), 🔵 (reconnecting), 🔴 (offline)
- [ ] Last Updated timestamp displays and updates every second
- [ ] Exponential backoff reconnection on disconnect (1s, 2s, 4s, 8s, max 30s)
- [ ] Max 10 retries before showing offline state
- [ ] Toast notification on reconnection ("✓ Connection updated")
- [ ] No full-page refresh, no flashing (smooth animations only)
- [ ] Works on mobile (no jank during scrolling while updates flow)
- [ ] Handles HA restart gracefully (reconnects automatically)
- [ ] WCAG 2.1 AA: Connection badge has aria-label, role="status"

### Technical Notes

**Backend Implementation**:
1. Create `WebSocketSubscriptionManager` class
   - Tracks active client connections
   - Registers/unregisters subscriptions
   - Broadcasts updates to all subscribers
2. Modify `__init__.py`:
   - Register subscription manager on setup
   - Hook into `state_changed` events
   - Call subscription manager for each change
3. Modify `websocket_api.py`:
   - Add `handle_subscribe` command
   - Add broadcast mechanism for `device_changed` event
   - Handle disconnection cleanup

**Frontend Implementation**:
1. Add connection status state management
   - Track connection state (connected, reconnecting, offline)
   - Track last update time
2. Implement reconnection logic
   - WebSocket close handler
   - Exponential backoff timer
   - Auto-retry mechanism
3. Add real-time update handlers
   - Listen for `device_changed` events
   - Update device in list
   - Trigger animation
   - Update timestamp
4. Add UI components
   - Connection badge (top-right)
   - Last updated timestamp (bottom)
5. Implement animation
   - CSS transition for progress bar (300ms ease-out)
   - No jank on 60fps devices

**Testing**:
- Unit tests: Subscription manager, reconnection logic, event filtering
- Integration tests: Real HA instance, simulate state changes, verify latency
- E2E tests: Panel open, watch updates, simulate disconnect/reconnect
- Performance tests: 100+ devices, 100 updates/sec, no jank
- Mobile tests: iOS/Android Companion app, verify smooth updates

**QA Acceptance**:
- Real-time update latency < 500ms (from HA change to UI update)
- Connection badge accurately reflects state
- Reconnection happens automatically
- No updates lost during brief disconnects
- No console errors or warnings

**Risk**: WebSocket stability; exponential backoff implementation; mobile performance

---

## Story 2: Configurable Thresholds

**Priority**: P0 (Must Have)
**Effort**: 5 days
**Complexity**: Large (L)
**Owner**: Lead Developer

### User Story

```
As a solar installer with backup batteries,
I want to set a custom battery threshold (e.g., 50%) for critical devices,
And keep default thresholds (15%) for other devices,
So that I get alerts tailored to each device's importance.
```

### Acceptance Criteria

- [ ] Settings panel accessible via ⚙️ icon (top-right)
- [ ] Global threshold input accepts 5-100%, defaults to 15%
- [ ] Settings panel responsive: slide-out on desktop (400px), full-screen modal on mobile
- [ ] Device-specific rules show searchable list of all battery entities
- [ ] Users can add up to 10 device rules per session
- [ ] Live preview shows "X batteries below this threshold"
- [ ] Save button persists settings in HA ConfigEntry.options
- [ ] Cancel button discards changes without saving
- [ ] Settings changes immediately re-color the battery list
- [ ] Devices with new status get smooth color transition (no jarring change)
- [ ] All thresholds survive HA restart
- [ ] Threshold changes broadcast to all connected clients (multi-client sync)
- [ ] Threshold changes applied immediately to all devices in list
- [ ] Keyboard accessible: Tab through fields, Enter to save
- [ ] Escape key closes settings panel
- [ ] Mobile touch targets ≥ 44px

### Technical Notes

**Backend Implementation**:
1. Create options flow in `config_flow.py`
   - Validate threshold inputs (5-100)
   - Validate device rules (check entities exist)
   - Limit to 10 device rules
2. Modify `BatteryMonitor`:
   - Add threshold cache (loaded from config entry)
   - Add `get_threshold_for_device()` method
   - Add `get_status_for_device()` method (returns critical/warning/healthy/unavailable)
3. Add WebSocket handler `handle_set_threshold`
   - Validate inputs
   - Update config entry
   - Broadcast `threshold_updated` event to all clients
4. Add event listener for config changes
   - When options updated, broadcast to all WebSocket clients

**Frontend Implementation**:
1. Create settings panel component
   - Global threshold slider (5-100)
   - Live preview count
   - Device rules list
   - "+ Add Device Rule" button
2. Create device rule modal
   - Searchable device list
   - Threshold input with slider
   - Live feedback ("X devices will be CRITICAL")
3. Add threshold application logic
   - On save, send `set_threshold` command
   - On receive `threshold_updated`, re-calculate status for all devices
   - Re-render with new colors
4. Add UI polish
   - Loading spinner during save
   - Error messages for validation failures
   - Toast notification on successful save
   - Close button (✕) and Escape key handling

**Testing**:
- Unit tests: Threshold validation, status calculation, device rule lookup
- Integration tests: Config entry persistence, multi-client sync
- E2E tests: Settings panel open, change threshold, verify colors change
- QA tests: Add 5 device rules, verify overrides apply correctly
- Regression tests: Verify Sprint 1 features still work

**QA Acceptance**:
- Set global threshold 50%, verify 8 devices change to CRITICAL
- Add device rule "Front Door Lock: 30%", verify only that device uses override
- Restart HA, verify thresholds persist
- Two clients open, one changes threshold, other sees update within 500ms
- Settings panel responsive on iPhone 12 (390px)

**Risk**: Config entry schema versioning; multi-client synchronization; mobile modal UX

---

## Story 3: Sorting & Filtering Controls

**Priority**: P0 (Must Have)
**Effort**: 3 days
**Complexity**: Medium (M)
**Owner**: Lead Developer

### User Story

```
As a user with 20 battery devices,
I want to sort by priority or battery level,
And filter to show only CRITICAL devices,
So that I can quickly find devices that need attention.
```

### Acceptance Criteria

- [ ] Sort dropdown shows 4 options: Priority (default), Alphabetical, Level (Low→High), Level (High→Low)
- [ ] Filter checkboxes toggle status groups: Critical, Warning, Healthy, Unavailable
- [ ] Sort/filter bar sticky on scroll (stays visible at top)
- [ ] Sort/filter state persists in localStorage (per session)
- [ ] Default state: Sort by Priority, Show All statuses
- [ ] Reset button clears all filters and resets sort to default
- [ ] Desktop (> 768px): Dropdowns inline, compact
- [ ] Mobile (< 768px): Full-screen modals, large touch targets (44px+)
- [ ] No horizontal scrolling on any screen size
- [ ] Sort/filter list updates instantly (< 50ms)
- [ ] Keyboard navigation: Tab through controls, Arrow keys in dropdowns
- [ ] ARIA labels on all controls for accessibility

### Technical Notes

**Frontend Implementation**:
1. Add sort/filter state to Lit component
   - `sort_method` (priority, alphabetical, level_asc, level_desc)
   - `filter_state` (critical, warning, healthy, unavailable)
2. Implement sort algorithms
   - Priority: status order, then battery level ascending
   - Alphabetical: device name A-Z
   - Level Asc: battery level low → high
   - Level Desc: battery level high → low
3. Implement filter logic
   - Apply filter to devices array
   - Show only devices matching checked statuses
4. Implement localStorage persistence
   - Load on component init
   - Save on every sort/filter change
5. Create responsive UI
   - Desktop: inline select dropdowns
   - Mobile: full-screen modals with radio/checkbox buttons
6. Add computed property: `_filtered_and_sorted_devices`
   - Returns filtered AND sorted list
   - Used by template to render

**Backend Support**:
- Response to `query_devices` includes `device_statuses` counts
- Frontend uses counts to label filter buttons ("All (13)", "Critical (2)", etc.)

**Testing**:
- Unit tests: Sort algorithms, filter logic, localStorage
- Integration tests: Sort/filter persistence across reload
- E2E tests: Select each sort option, verify list reorders
- Performance tests: Sort/filter 100+ devices, verify < 50ms
- Mobile tests: Modal open, touch targets responsive

**QA Acceptance**:
- Select "Level (High→Low)", verify Solar Backup (95%) appears first
- Uncheck "Healthy", verify list shows only 5 devices (2 critical + 3 warning)
- Refresh page, verify sort/filter still applied
- Mobile: Open sort modal, verify all options visible without scrolling
- Keyboard: Tab navigation includes all controls

**Risk**: Responsive modal implementation on mobile; performance with 100+ devices

---

## Story 4: Mobile-Responsive UX & Accessibility

**Priority**: P0 (Must Have)
**Effort**: 2 days
**Complexity**: Medium (M)
**Owner**: Lead Developer

### User Story

```
As a Home Assistant user checking batteries from my phone,
I want responsive modals and touch-friendly controls,
So that I can comfortably use Vulcan Brownout on mobile devices.
```

### Acceptance Criteria

- [ ] Settings modal full-screen on mobile (< 768px), side panel on desktop
- [ ] Sort/filter modals accessible and readable on mobile
- [ ] Touch targets: all buttons, icons, checkboxes ≥ 44px
- [ ] Font sizes: 16px+ on mobile, readable hierarchy
- [ ] Progress bars: 100% width, no overflow
- [ ] No horizontal scrolling on any viewport (390px - 1440px)
- [ ] Keyboard focus indicators: visible on all interactive elements
- [ ] ARIA labels: all icons, buttons, status indicators
- [ ] Color contrast ratios: minimum 4.5:1 for text (WCAG AA)
- [ ] Tested on: iPhone 12 (390px), iPad (768px), Desktop (1440px)
- [ ] Swipe-down-to-refresh on mobile (nice-to-have)

### Technical Notes

**Frontend Implementation**:
1. Review all CSS media queries
   - Mobile-first approach
   - Breakpoints: 768px, 1024px, 1440px
2. Adjust touch targets
   - Buttons: 44px height + padding
   - Checkboxes: 24px + 44px hover area
   - Icons: 24px within 44px target
3. Review typography
   - Base font 16px on mobile (not 14px)
   - Line heights increased for readability
   - Heading sizes scale with viewport
4. Review colors & contrast
   - Use online contrast checker (WebAIM)
   - Critical: #F44336 on white ≥ 4.5:1 ✓
   - Ensure no color-only indicators (always use icons + color)
5. Add ARIA labels
   - Settings icon: aria-label="Open settings"
   - Connection badge: aria-label="Connection status: Connected"
   - Sort dropdown: aria-label="Sort by"
   - Filter checkboxes: aria-label="Show critical devices"
6. Test keyboard navigation
   - Tab order: Settings → Connection → Sort → Filter → Reset → Battery items
   - Escape closes modals
   - Enter/Space activates buttons

**Testing**:
- Manual testing on real devices (iPhone, iPad)
- Browser DevTools device emulation (390px, 768px, 1440px)
- Lighthouse accessibility audit (target: score ≥ 90)
- Screen reader testing (VoiceOver on iOS, TalkBack on Android)
- Keyboard-only navigation (no mouse)
- Color contrast verification (WebAIM contrast checker)

**QA Acceptance**:
- Load on iPhone 12, settings modal is full-screen and readable
- Rotate device, verify layout adapts without jumpiness
- Test Tab navigation: focus moves through all controls
- Test screen reader: VoiceOver announces all elements correctly
- Lighthouse audit: accessibility score ≥ 90

**Risk**: Device fragmentation; older browsers may not support some CSS features

---

## Story 5: Deployment & Infrastructure Updates

**Priority**: P0 (Mandatory)
**Effort**: 2 days
**Complexity**: Medium (M)
**Owner**: DevOps / Lead Developer

### User Story

```
As a DevOps engineer,
I want idempotent deployment with health checks and rollback,
So that I can confidently deploy Sprint 2 features without downtime.
```

### Acceptance Criteria

- [ ] Systemd service includes restart policy (on-failure, max 3 restarts)
- [ ] Deployment script is idempotent (safe to run multiple times)
- [ ] Environment variable validation before deployment (fail fast)
- [ ] Rollback script reverts to previous version if current fails
- [ ] Health check endpoint: GET /health returns 200 + connection status
- [ ] Health check verifies WebSocket endpoint is reachable
- [ ] Deployment logs indicate success/failure clearly
- [ ] Failed health check triggers automatic rollback
- [ ] All secrets (.env) are gitignored (not in repo)
- [ ] Deployment tested: 3+ runs, verify idempotency
- [ ] Smoke test: After deploy, verify real-time updates work
- [ ] HA instance restarts cleanly with new integration

### Technical Notes

**Deployment Script Updates** (`deploy.sh`):
1. Add systemd service management
   - Restart on-failure: max 3 attempts
   - Check service status before/after
2. Add environment validation
   - Check required .env variables exist
   - Validate format (e.g., IP addresses, ports)
   - Exit with clear error if missing
3. Add rollback mechanism
   - Keep previous version in `releases/` directory
   - If health check fails, swap symlink back to previous
   - Log rollback event
4. Add health check
   - POST-deploy, call `http://ha_instance/health`
   - Verify WebSocket connectivity
   - Retry 3 times with backoff if fails
   - Timeout after 30s
5. Add smoke test
   - After health check passes
   - Simulate battery level change
   - Verify real-time update received within 5s
   - Log result

**Health Check Endpoint** (new in `websocket_api.py`):
```python
async def health_check(hass):
    """GET /health returns integration status."""
    return {
        "status": "healthy",
        "integration": "vulcan_brownout",
        "websocket_ready": True,
        "battery_entities": len(battery_monitor.entities),
        "timestamp": datetime.now().isoformat()
    }
```

**Testing**:
- Manual deploy 3+ times, verify script is idempotent
- Deploy with missing .env variable, verify early exit + clear error
- Deploy with WebSocket failure, verify health check fails + rollback triggers
- Verify previous version active after rollback
- Monitor HA logs for errors
- Verify no secrets in git history

**QA Acceptance**:
- Run deployment twice, no errors on second run
- Deploy with invalid .env, get clear error message
- Simulate WebSocket failure, health check fails, rollback executes
- Verify previous version is active after rollback
- Check git history: no .env or secrets found

**Risk**: Systemd service cross-platform compatibility (HA on Docker vs bare metal); health check endpoint security (should be authenticated)

---

## Implementation Timeline

### Week 1

| Day | Story | Tasks | Lead Dev | QA |
|-----|-------|-------|----------|-----|
| Mon (2/24) | Story 1 | Backend: Subscription manager, state_changed hook | START | Setup |
| Tue (2/25) | Story 1 | Frontend: Connection state, reconnection logic | CONTINUE | Review |
| Wed (2/26) | Story 1 | Frontend: Real-time event handlers, animation | CONTINUE | Review |
| Thu (2/27) | Story 1 | Testing, edge cases, mobile optimization | CONTINUE | QA Testing |
| Fri (2/28) | Story 2 | Backend: Config flow, threshold options | START | Story 1 QA |

### Week 2

| Day | Story | Tasks | Lead Dev | QA |
|-----|-------|-------|----------|-----|
| Mon (3/3) | Story 2 | Frontend: Settings panel, device rules | CONTINUE | Regression |
| Tue (3/4) | Story 2 | Testing, persistence, multi-client sync | CONTINUE | QA Testing |
| Wed (3/5) | Story 3 | Sort/filter algorithms, localStorage | START | Story 2 QA |
| Thu (3/6) | Story 4 | Mobile UX, accessibility, responsive design | START | QA Testing |
| Fri (3/7) | Story 5 | Deployment script, health check, rollback | START | Final Testing |

### Sprint End

- **Code Review**: All PRs approved by Architect (Thu-Fri)
- **QA Sign-Off**: All stories accepted by QA (Fri)
- **Documentation**: Updated README, API docs (Fri)
- **Retrospective**: Team review (Fri afternoon)

---

## Dependencies & Risks

### External Dependencies

- **Home Assistant API Stability**: WebSocket protocol must remain stable
- **Browser WebSocket Support**: All modern browsers supported
- **localStorage Availability**: Must work in incognito/private mode (graceful fallback)

### Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| WebSocket connection flaky | Medium | Users miss updates | Implement exponential backoff + health check |
| Config entry schema changes in HA | Low | Settings lost | Version config schema, handle migrations |
| Mobile modal UX complex | Medium | Poor mobile UX | Use standard HA modal patterns, extensive testing |
| Performance with 100+ devices | Medium | Jank on sort/filter | Optimize sort algorithms, use virtual scrolling if needed (Sprint 3) |
| Deployment rollback fails | Low | Service down | Test rollback mechanism 3+ times before release |

### Mitigation Strategies

1. **WebSocket Reliability**: Exponential backoff, health checks, clear user feedback
2. **Schema Management**: Version all stored data, handle migrations
3. **Mobile Testing**: Real device testing (iPhone + Android), Lighthouse accessibility audit
4. **Performance**: Profiling with Chrome DevTools, optimize hot paths
5. **Deployment**: Test script 3+ times, dry-run before production

---

## Success Criteria

**All Criteria Must Be Met for Sprint 2 Acceptance:**

1. **Story 1 (Real-Time)**: Real-time latency < 500ms, connection badge accurate, auto-reconnect works
2. **Story 2 (Thresholds)**: Settings persist, multi-client sync works, no broken colors
3. **Story 3 (Sort/Filter)**: All 4 sort options work, filters update instantly, localStorage persists
4. **Story 4 (Mobile UX)**: Touch targets ≥ 44px, no horizontal scroll, Lighthouse ≥ 90
5. **Story 5 (Deployment)**: Idempotent script, rollback works, health checks pass
6. **Quality**: Zero critical bugs, < 3 minor bugs, all console errors resolved
7. **Testing**: > 80% code coverage, all acceptance criteria met
8. **Documentation**: Architecture docs complete, deployment guide updated

---

## Resource Plan

**Team**:
- Lead Developer: 8 days (full-time, all 5 stories)
- QA: 6 days (testing, regression, acceptance)
- Architect: 2 days (design review, code review, ADR approval)

**Tools**:
- Home Assistant test instance (pre-provisioned)
- GitHub for version control
- GitHub Actions for CI/CD (optional for Sprint 2)
- Lighthouse for accessibility audits
- Chrome DevTools for performance profiling

**Capacity Planning**:
- Total capacity: 16 days
- Planned: 16 days (5+3+4+2+2)
- Contingency: 0 days (at full capacity)

**Risk**: No buffer time. If Story 1 (WebSocket) overruns, others will slip. Mitigation: Daily standups, escalate blockers immediately.

---

## Handoff Criteria

Before Sprint 2 ships to production:

- [ ] All 5 stories implemented and merged to `develop` branch
- [ ] All code reviewed and approved by Architect
- [ ] All tests passing (> 80% coverage)
- [ ] QA acceptance for all stories
- [ ] Zero critical bugs
- [ ] No console errors or warnings
- [ ] Deployment script tested 3+ times (idempotent)
- [ ] Documentation complete (README, API docs, ADRs)
- [ ] Performance targets met (< 500ms real-time latency, < 50ms sort/filter)
- [ ] Mobile & accessibility testing complete (Lighthouse ≥ 90)

---

## Open Questions & Notes

1. **WebSocket Concurrency**: Can HA handle 50+ WebSocket subscriptions simultaneously?
   - **Answer**: Yes, tested in Sprint 1. HA's WebSocket broker is robust.

2. **Threshold Migrations**: What if user upgrades from Sprint 1 to Sprint 2?
   - **Answer**: Default to 15% (same as Sprint 1). First save creates options entry.

3. **localStorage Security**: Should sort/filter be encrypted?
   - **Answer**: No, localStorage is client-side only. Not sensitive data.

4. **Deployment Rollback**: How far back can we rollback?
   - **Answer**: Keep 1 previous version. If needed, keep more (but adds complexity).

5. **Future Scaling**: When do we move sort/filter to server-side?
   - **Answer**: Sprint 3, if device count > 100 per user. Current plan handles < 50.

---

**Prepared by**: FiremanDecko (Architect)
**Reviewed by**: [Product Owner], [Tech Lead]
**Approved**: [Sprint 2 Kickoff]
**Last Updated**: February 2026
