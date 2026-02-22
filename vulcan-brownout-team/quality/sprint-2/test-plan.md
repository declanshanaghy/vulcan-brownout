# Sprint 2 QA Test Plan

**Project:** Vulcan Brownout Battery Monitoring
**Sprint:** 2
**QA Lead:** Loki (QA Tester)
**Date:** February 2026
**Version:** 1.0

---

## Executive Summary

Sprint 2 implementation adds real-time WebSocket updates, configurable thresholds, sort/filter controls, mobile responsiveness, and deployment infrastructure. This test plan covers all 5 user stories with comprehensive functional, integration, edge case, and regression testing.

**Scope:** All 5 Sprint 2 stories are in scope. Sprint 1 features are regression tested.

**Test Environment Requirements:**
- Home Assistant 2023.12.0+ instance (test/staging)
- Modern browser (Chrome/Firefox/Safari, within 1 year)
- Mobile device emulator (iPhone 12 / Android)
- Network simulation tools (optional: throttle, disconnect)
- Bash shell for deployment scripts
- Python 3.11+ for running pytest tests

---

## Test Categories

### 1. Functional Testing
Verify each feature works as specified in acceptance criteria.

**Coverage:**
- Real-time WebSocket updates (Story 1)
- Threshold configuration UI (Story 2)
- Sort and filter controls (Story 3)
- Mobile-responsive UI (Story 4)
- Deployment script (Story 5)

**Scope:** All user-facing features plus backend validation.

### 2. Integration Testing
Verify components interact correctly across layers.

**Coverage:**
- WebSocket subscription management
- Backend-to-frontend event broadcasting
- Configuration persistence (config entry options)
- Multi-client synchronization
- Entity registry discovery and updates

**Scope:** Backend + frontend interactions.

### 3. Edge Case Testing
Verify unusual but plausible scenarios are handled gracefully.

**Coverage:**
- Zero battery entities
- 100+ battery entities
- Rapid state changes (10+ updates/second)
- Multiple tabs/browsers open
- WebSocket disconnect during panel interaction
- Entity deletion while viewing list
- Threshold values at boundaries (5%, 100%)
- Device names > 100 characters
- localStorage full or disabled

**Scope:** Unusual but valid scenarios.

### 4. Regression Testing
Verify Sprint 1 features still work.

**Coverage:**
- Panel appears in sidebar
- Device list displays all battery entities
- Status colors work (critical/warning/healthy)
- Progress bar displays correctly
- Device cards show battery level
- Devices grouped/sorted correctly

**Scope:** Sprint 1 features only.

### 5. Performance Testing
Verify acceptable performance under load.

**Coverage:**
- Panel load time (< 3 seconds with 50 devices)
- Sort/filter time (< 50ms with 100 devices)
- WebSocket latency (< 500ms update latency)
- Memory usage (no growth over 1 hour)
- Mobile performance (smooth 60fps)

**Scope:** Performance and scalability.

### 6. Accessibility Testing
Verify WCAG 2.1 AA compliance.

**Coverage:**
- Keyboard navigation (Tab, Enter, Escape)
- Screen reader compatibility (ARIA labels)
- Color contrast ratios (≥ 4.5:1 for normal text)
- Focus management in modals
- Touch target sizes (≥ 44px)
- No color-alone indicators

**Scope:** Accessibility standards.

### 7. Deployment Testing
Verify deployment script is idempotent and safe.

**Coverage:**
- Script runs without errors
- Script is idempotent (run 3+ times)
- Environment validation (fail on missing files)
- Health check success
- Rollback mechanism (if available)
- Integration loaded in HA

**Scope:** Deployment process.

---

## Entry Criteria

Before testing begins:
- [ ] All 5 stories merged to develop branch
- [ ] Code reviewed and approved by Architect
- [ ] All Python files pass syntax checking
- [ ] manifest.json is valid JSON
- [ ] Frontend code loads without console errors
- [ ] Test environment provisioned (HA 2023.12.0+)
- [ ] At least 5 battery test entities created
- [ ] QA has access to test HA instance

---

## Exit Criteria

Before Sprint 2 ships:
- [ ] All test cases passing (100%)
- [ ] Zero critical bugs found
- [ ] < 3 major bugs found (and fixed)
- [ ] No console errors or warnings
- [ ] Performance targets met (real-time < 500ms, sort/filter < 50ms)
- [ ] Deployment script idempotent
- [ ] Mobile responsive (no horizontal scroll, 44px touch targets)
- [ ] Accessibility audit passing (Lighthouse ≥ 90)
- [ ] Regression tests all passing

---

## Risk Assessment

### High Risk Areas
1. **WebSocket Connection Stability** (Story 1)
   - Risk: Connection drops, updates missed
   - Mitigation: Test with network simulation, verify reconnection works
   - Test Focus: Connection state machine, reconnect backoff, dead subscription cleanup

2. **Multi-Client Synchronization** (Story 2)
   - Risk: Threshold changes not broadcast to all clients
   - Mitigation: Test with 2+ tabs open, verify all update simultaneously
   - Test Focus: Broadcast mechanism, config entry listener, multi-client events

3. **localStorage Corruption** (Story 3)
   - Risk: Sort/filter state lost or malformed
   - Mitigation: Test localStorage full, localStorage disabled, corrupted JSON
   - Test Focus: localStorage fallback, error handling, persistence logic

4. **Mobile Modal UX** (Story 4)
   - Risk: Modals don't fit on screen, text overflow, touch targets too small
   - Mitigation: Test on real devices (iPhone, Android), various screen sizes
   - Test Focus: Responsive breakpoints, touch targets, modal sizing

5. **Deployment Rollback** (Story 5)
   - Risk: Rollback fails, service stays down
   - Mitigation: Test rollback mechanism, verify health checks work
   - Test Focus: Symlink swap, previous release availability, health checks

### Medium Risk Areas
- Entity discovery with 100+ devices (performance)
- Threshold boundary values (off-by-one errors)
- Rapid sort/filter toggles (race conditions)
- HA restart during active subscription (reconnection)

### Low Risk Areas
- Basic panel rendering
- Settings form validation
- Color coding logic
- Last updated timestamp formatting

---

## Test Data Strategy

### Battery Test Entities
Create 5 test battery entities with various states:

```yaml
sensor.test_battery_critical:      5%  (CRITICAL)
sensor.test_battery_warning:       18% (WARNING)
sensor.test_battery_healthy:       87% (HEALTHY)
sensor.test_battery_unavailable:   unavailable (UNAVAILABLE)
sensor.test_battery_edge:          0%  (CRITICAL edge case)
```

### Dynamic Testing
During testing, change battery levels via:
```bash
hass-cli entity set_state sensor.test_battery_critical 12
```

---

## Test Timeline

| Phase | Duration | Activities |
|-------|----------|------------|
| Setup | 1 day | Environment provisioning, test entity creation |
| Smoke Test | 0.5 day | Basic functionality verification |
| Feature Testing | 3 days | Each story functionally tested |
| Integration Testing | 1 day | Multi-story interactions, multi-client |
| Edge Cases | 1 day | Unusual scenarios, performance testing |
| Mobile Testing | 1 day | Responsive design, touch, accessibility |
| Regression Testing | 0.5 day | Sprint 1 features still work |
| Deployment Testing | 0.5 day | Script idempotency, rollback |
| **Total** | **7.5 days** | |

---

## Testing Tools & Resources

| Tool | Purpose | Version |
|------|---------|---------|
| Home Assistant | Test environment | 2023.12.0+ |
| Chrome DevTools | Browser testing, network simulation | Latest |
| Lighthouse | Accessibility audit | Built-in to Chrome |
| Playwright | UI automation (optional) | 1.40+ |
| pytest | Backend unit tests | 7.0+ |
| curl | Health checks, API testing | Standard |
| Network Link Conditioner | Network simulation | Optional |

---

## Acceptance Criteria Summary

**All of the following must be true to SHIP:**

1. **Story 1 (Real-Time):** Real-time latency < 500ms, connection badge accurate, auto-reconnect works, no missed updates
2. **Story 2 (Thresholds):** Settings persist, multi-client sync, threshold applied correctly, device status colors update
3. **Story 3 (Sort/Filter):** All 4 sort methods work, all filter combinations work, localStorage persists across reload
4. **Story 4 (Mobile UX):** Touch targets ≥ 44px, no horizontal scroll, modals fit screen, keyboard navigation works
5. **Story 5 (Deployment):** Script runs idempotent (3+ times), environment validation works, rollback available
6. **Quality:** Zero critical bugs, < 3 major bugs, no console errors
7. **Performance:** Panel loads < 3s, sort/filter < 50ms, real-time < 500ms
8. **Accessibility:** Lighthouse ≥ 90, WCAG AA compliance, keyboard accessible
9. **Regression:** Sprint 1 features all working, no broken functionality

---

## Defect Tracking

Use this format for reporting defects:

```
DEF-{ID}: {Title}
Severity: Critical | Major | Minor | Cosmetic
Status: Open | In Progress | Fixed | Verified
Description: [What is broken]
Reproduction: [Steps to reproduce]
Expected: [What should happen]
Actual: [What actually happens]
Evidence: [Screenshot/console output]
Root Cause: [Why it happened, if known]
Fix: [How it was fixed, if resolved]
```

---

## Sign-Off

**QA Test Plan Prepared By:** Loki
**Date:** February 2026
**Next Step:** Begin testing per test cases (test-cases.md)

---

**Test Plan Status:** ✅ APPROVED

This plan is comprehensive and covers all Sprint 2 features. Testing will be thorough, methodical, and focused on finding defects before they reach production.
