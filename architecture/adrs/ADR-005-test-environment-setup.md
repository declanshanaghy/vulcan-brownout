# ADR-005: Test Environment Setup

## Status: Proposed

## Decision

**Option A: Pre-Provisioned Mock Entities via Integration Config Flow**

QA configures mock battery entities once in `configuration.yaml` using template sensors. All tests use these pre-provisioned entities. No dynamic entity creation per test.

## Rationale

- **PO requirement**: Brief specifies "predefined HA server" and "real running instance"
- **Simplicity**: QA configures mock entities once in YAML; all tests use them
- **Debuggability**: Entities visible in HA UI; QA can manually verify state
- **Realism**: Tests query actual HA API (WebSocket, state machine), not mocks
- **Sprint 1 scope**: Fastest path to tests running; automated entity creation deferred to Sprint 2

## Implementation Details

**File: `tests/home_assistant_test_config.yaml`**:
- Template sensors for each test battery entity
- Device class: "battery"
- State values covering test scenarios:
  - Critical (5%, 12%) — for threshold testing
  - Low (25%) — warning state
  - Healthy (85%) — normal state
  - Unavailable — testing offline devices
- Input number entities for dynamic battery level changes during tests

**Setup steps**:
1. Copy test config to HA server's `configuration.yaml`
2. Restart HA (docker-compose restart homeassistant)
3. Wait for template entities to load (~10 seconds)
4. Run tests

**State management between tests**:
- Test entities persist across test runs
- Reset battery levels via REST API if needed: `POST /api/states/sensor.test_battery_critical_1`
- Or use input_number automations to change levels dynamically

## Test Entities

- sensor.test_battery_critical_1 (5%)
- sensor.test_battery_critical_2 (12%)
- sensor.test_battery_low_1 (25%)
- sensor.test_battery_healthy_1 (85%)
- sensor.test_battery_unavailable_1 (unavailable state)

## Consequences

**Positive**:
- Uses real HA instance (meets PO requirement)
- Entities are "real" (in HA state machine, not mocked)
- Easy to debug (visible in HA UI during test runs)
- Deterministic (same test data every run)
- Minimal code (no custom test integration)
- Fast to implement

**Negative**:
- Manual setup of test entities (YAML editing)
- State persists between tests (need manual reset if needed)
- Test data mixed with test HA instance (not ideal isolation)
- Requires HA restart to add test config

## Future Improvements (Sprint 2+)

- Automated entity creation via custom test integration
- Per-test entity namespaces for isolation
- Snapshot testing (record baseline, compare across runs)
- Docker Compose for test HA with pre-baked test config
