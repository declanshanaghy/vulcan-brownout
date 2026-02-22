# Vulcan Brownout QA Testing Strategy

**Project**: Vulcan Brownout Battery Monitoring
**Sprint**: 2 (Integration Deployment)
**QA Lead**: Loki
**Last Updated**: February 22, 2026

---

## Testing Phases Overview

```
┌─────────────────────────────────────────────────────────────┐
│ Phase 1: Environment Validation ✅ COMPLETE               │
│ - REST API, WebSocket, Battery entities                    │
│ - Performance baseline, Data quality                        │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ Phase 2: Deployment 🔴 BLOCKED (SSH Key)                   │
│ - SSH-based rsync deployment                                │
│ - Integration validation on server                          │
│ - Rollback capability                                        │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ Phase 3: API Integration Testing (READY)                    │
│ - Query Devices (pagination, sorting, filtering)            │
│ - Subscribe (real-time updates)                             │
│ - Set Threshold (persistence, broadcast)                    │
│ - Error handling                                             │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ Phase 4: UI/UX Testing (Manual)                             │
│ - Real-time updates visible                                 │
│ - Sort/Filter working                                        │
│ - Mobile responsiveness                                      │
│ - Accessibility compliance                                   │
└─────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Environment Validation ✅

**Status**: COMPLETE
**Execution Time**: ~10 seconds
**Results**: 7/8 passed (87.5%)

### Objectives
- Verify HA infrastructure is operational
- Validate battery entity inventory
- Establish performance baseline
- Identify data quality issues

### Test Coverage

| Area | Tests | Status |
|------|-------|--------|
| REST API | 2 | ✅ |
| Battery Entities | 2 | ⚠️ (1 warning) |
| WebSocket | 2 | ✅ |
| Performance | 1 | ✅ |
| **TOTAL** | **8** | **7/8 passed** |

### Deliverables
- ✅ `test_ha_environment.py` - Python test suite
- ✅ `test-results.json` - Machine-readable results
- ✅ `ENVIRONMENT-VALIDATION.md` - Detailed report

---

## Phase 2: Deployment

**Status**: 🔴 BLOCKED - SSH key authorization required
**Blocker**: `SSH_KEY_PATH` not yet authorized on HA server
**Est. Time**: 2 minutes (after SSH fix)

### Objectives
- Deploy integration to HA server
- Verify integration loads correctly
- Enable Phase 3 testing

### Prerequisites
1. SSH key authorized on HA server
   ```bash
   ssh-copy-id -i ~/.ssh/vulcan_deploy.pub -p 2222 root@homeassistant.lan
   ```

2. Integration files present locally
   - All source files in `development/src/custom_components/vulcan_brownout/`

3. .env file configured
   - `SSH_HOST`, `SSH_PORT`, `SSH_USER`, `SSH_KEY_PATH`, `HA_CONFIG_PATH`

### Deployment Process

**Script**: `quality/scripts/deploy.sh`

**Steps**:
1. Load .env configuration ✅ (Ready)
2. Validate SSH connectivity 🔴 (BLOCKED)
3. Verify HA config path on server
4. Deploy files via rsync
5. Restart Home Assistant
6. Verify integration loads

**Dry Run**:
```bash
./quality/scripts/deploy.sh --dry-run --verbose
```

**Execute**:
```bash
./quality/scripts/deploy.sh
```

### Expected Outcome
- Integration appears in HA sidebar
- "Battery Monitoring" panel accessible
- No errors in HA logs

---

## Phase 3: API Integration Testing

**Status**: READY (after Phase 2)
**Test Framework**: pytest + pytest-asyncio
**Coverage**: All WebSocket commands

### Test Structure

```
quality/scripts/test_api_integration.py
├── TestQueryDevices
│   ├── test_query_devices_basic
│   ├── test_query_devices_pagination
│   ├── test_query_devices_sorting_battery_level
│   ├── test_query_devices_sorting_device_name
│   ├── test_query_devices_device_statuses
│   ├── test_query_devices_invalid_limit
│   ├── test_query_devices_invalid_sort_key
│   └── test_query_devices_device_structure
├── TestSubscribe
│   ├── test_subscribe_basic
│   ├── test_subscribe_multiple
│   └── test_subscribe_receives_events
├── TestSetThreshold
│   ├── test_set_threshold_global
│   ├── test_set_threshold_device_rules
│   ├── test_set_threshold_global_and_device_rules
│   ├── test_set_threshold_invalid_value
│   ├── test_set_threshold_invalid_device_rule
│   ├── test_set_threshold_too_many_rules
│   └── test_set_threshold_persistence
├── TestErrorHandling
│   ├── test_invalid_command_type
│   ├── test_malformed_data
│   └── test_missing_required_fields
├── TestPerformance
│   ├── test_query_many_devices
│   └── test_set_threshold_broadcast
└── TestIntegrationLoaded
    ├── test_integration_responds_to_commands
    └── test_version_check
```

### Running Tests

**All tests**:
```bash
pytest quality/scripts/test_api_integration.py -v
```

**Specific test**:
```bash
pytest quality/scripts/test_api_integration.py::TestQueryDevices::test_query_devices_basic -v
```

**With output**:
```bash
pytest quality/scripts/test_api_integration.py -v --capture=no
```

**Coverage report**:
```bash
pytest quality/scripts/test_api_integration.py -v --cov=custom_components.vulcan_brownout
```

### Expected Results

| Test Category | Count | Expected Result |
|---|---|---|
| Query Devices | 8 | ✅ 8 passed |
| Subscribe | 3 | ✅ 3 passed |
| Set Threshold | 7 | ✅ 7 passed |
| Error Handling | 3 | ✅ 3 passed |
| Performance | 2 | ✅ 2 passed |
| Integration | 2 | ✅ 2 passed |
| **TOTAL** | **25** | **25 passed** |

---

## Phase 4: Test Environment Setup

**Status**: READY
**Purpose**: Create test battery entities
**Script**: `quality/scripts/setup-test-env.sh`

### Create Test Entities

```bash
./quality/scripts/setup-test-env.sh --create --count 20
```

Creates 20 test entities:
- `sensor.test_battery_1` to `sensor.test_battery_20`
- Varying battery levels (10-95%)
- All with proper attributes (device_class, unit_of_measurement, etc.)

### Cleanup After Testing

```bash
./quality/scripts/setup-test-env.sh --cleanup
```

Removes all test entities.

---

## High-Priority Test Cases (From QA Handoff)

### 1. Real-Time Updates (Critical)

**Purpose**: Verify battery state changes appear instantly
**Steps**:
1. Open Battery Monitoring panel
2. Subscribe to state changes
3. Manually change a battery entity state
4. Verify update within 1 second

**Expected**: Progress bar updates, timestamp changes to "just now"
**Failure Criteria**: Update takes > 2 seconds or doesn't appear

### 2. Connection Resilience (Critical)

**Purpose**: Panel recovers from network interruption
**Steps**:
1. Open panel (verify connected)
2. Simulate network outage
3. Observe badge changes (blue → red)
4. Restore network
5. Verify automatic reconnection

**Expected**: Green badge, panel resumes receiving updates
**Failure Criteria**: Manual refresh required, crashes

### 3. Threshold Configuration (Critical)

**Purpose**: Threshold changes update device statuses
**Steps**:
1. Open settings
2. Change global threshold to 50%
3. Observe status colors change
4. Add device rule
5. Save and reload

**Expected**: Changes persist, all clients notified
**Failure Criteria**: Settings lost on reload, no broadcast

### 4. Sort & Filter (High)

**Purpose**: All sort/filter combinations work
**Steps**:
1. Test each sort method (4 total)
2. Test filters (4 categories)
3. Test combinations
4. Verify persistence across reload

**Expected**: Correct sort order, filters apply correctly
**Failure Criteria**: Wrong order, filters ignored, state lost

### 5. Mobile Responsiveness (High)

**Purpose**: Touch-friendly on mobile (< 768px)
**Steps**:
1. Open in mobile browser
2. Verify modals for settings/sort/filter
3. Test touch targets (≥ 44px)
4. Verify 3-step add rule wizard

**Expected**: All features accessible, readable
**Failure Criteria**: Overflow, small targets, text truncation

---

## Testing Approach: Devil's Advocate

As QA lead, I will:

1. **Test Beyond Requirements**
   - Not just happy path, but edge cases
   - Boundary conditions (0%, 100%, 101%, -1%)
   - Performance under load

2. **Verify Integration Points**
   - HA ↔ WebSocket
   - Frontend ↔ Backend state consistency
   - Thresholds persist across restarts

3. **Break Things Intentionally**
   - Network failures
   - Invalid inputs
   - Race conditions
   - Resource limits

4. **Document Everything**
   - Every failure with reproduction steps
   - Screenshots of issues
   - Performance metrics
   - Logs from HA

---

## Test Data

### Battery Level Ranges

| Level | Classification | Test Cases |
|-------|---|---|
| 0-15% | Critical | 0%, 5%, 15% |
| 15-25% | Warning | 16%, 20%, 25% |
| 25%+ | Healthy | 26%, 50%, 75%, 100% |
| >100% | Invalid | 101%, 200% |
| Unknown | Unavailable | "unavailable", "unknown", "error" |

### Device Quantities

| Scenario | Devices | Purpose |
|---|---|---|
| Baseline | 50-100 | Normal operation |
| Stress | 150-200 | Performance limits |
| Edge | 1-5 | Minimal data |

---

## Regression Testing

### Sprint 1 Features (Must Not Break)

- [ ] Panel appears in sidebar
- [ ] Device list displays
- [ ] Status colors render correctly
- [ ] Last updated timestamp shows
- [ ] Refresh button works
- [ ] Progress bars display
- [ ] Devices grouped by status

### Sprint 2 New Features (Must Work)

- [ ] WebSocket real-time updates
- [ ] Threshold configuration UI
- [ ] Sort/filter functionality
- [ ] Mobile responsiveness
- [ ] Accessibility compliance

---

## Metrics & Success Criteria

### Performance Targets

| Metric | Target | Actual |
|---|---|---|
| Initial load | < 3s | TBD |
| Sort/filter | < 200ms | TBD |
| WebSocket latency | < 100ms | TBD |
| Reconnect time | < 5s | TBD |

### Reliability Targets

| Metric | Target |
|---|---|
| Test pass rate | ≥ 95% |
| Critical issues | 0 |
| High issues | ≤ 2 |
| Medium issues | ≤ 5 |

### Accessibility Targets

| Standard | Target |
|---|---|
| WCAG 2.1 AA | Pass all checks |
| Keyboard nav | 100% of controls |
| Color contrast | ≥ 4.5:1 |

---

## Issue Tracking

### Severity Levels

**Critical** (Blocks deployment)
- Crashes
- Data loss
- Security issues
- API failures

**High** (Should fix before release)
- Wrong calculations
- Missing features
- Performance issues
- Accessibility failures

**Medium** (Can defer)
- UI polish
- Edge cases
- Performance optimizations
- Documentation

**Low** (Nice to have)
- Copy changes
- Minor UI tweaks
- Future enhancements

---

## Sign-Off Requirements

**Before Deploying to Staging**:
- [ ] Phase 1 complete (✅ Done)
- [ ] SSH key authorized
- [ ] Phase 2 deployment successful

**Before Deploying to Production**:
- [ ] Phase 3 API tests all pass
- [ ] Phase 4 UI tests all pass
- [ ] No critical/high issues
- [ ] Performance benchmarks met
- [ ] Accessibility verified

---

## Timeline

| Phase | Duration | Status | Blocker |
|---|---|---|---|
| Phase 1 | ~10s | ✅ Complete | None |
| Phase 2 | ~2m | 🔴 Blocked | SSH key |
| Phase 3 | ~5m | Ready | Phase 2 |
| Phase 4 | ~30m | Ready | Phase 2 |
| **Total** | **~40m** | | **SSH key** |

---

## Tools & Setup

### Required Packages

```bash
pip install pytest pytest-asyncio websockets python-dotenv
```

### Environment Variables

```bash
HA_URL=http://homeassistant.lan
HA_PORT=8123
HA_TOKEN=<your-long-lived-token>
SSH_HOST=homeassistant.lan
SSH_PORT=2222
SSH_USER=root
SSH_KEY_PATH=~/.ssh/vulcan_deploy
HA_CONFIG_PATH=/root/homeassistant
```

### Running Full Test Suite

```bash
# Phase 1 (already done)
python3 quality/scripts/test_ha_environment.py

# Phase 2 (when ready)
./quality/scripts/deploy.sh

# Phase 3
pytest quality/scripts/test_api_integration.py -v

# Phase 4
./quality/scripts/setup-test-env.sh --create --count 20
# ... run manual UI tests ...
./quality/scripts/setup-test-env.sh --cleanup
```

---

## Documentation

- [Environment Validation Report](./ENVIRONMENT-VALIDATION.md)
- [API Contracts](../architecture/api-contracts.md)
- [QA Handoff](../development/qa-handoff.md)
- [Test Cases](./test-cases.md) (in progress)
- [Test Plan](./test-plan.md) (original)

---

**Prepared by**: Loki (QA Tester)
**Date**: February 22, 2026
