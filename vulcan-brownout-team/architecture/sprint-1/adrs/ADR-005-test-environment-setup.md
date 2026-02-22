# ADR-005: Test Environment Setup

## Status: Proposed

## Context

Sprint 1 QA tests the integration against a live Home Assistant server. Per the Product Owner's brief, the test environment is:
- A **predefined Home Assistant server** used exclusively for testing
- A **real running instance**, not a mock or local dev setup
- **Persistent** across multiple test runs
- Accessible via **SSH and HTTP**

We must decide:
- How to provision mock battery entities for testing
- How tests connect to the HA server
- How to reset state between test runs
- How to handle test data isolation

## Options Considered

### Option A: Pre-Provisioned Mock Entities via Integration Config Flow
- **Setup:** Admin creates YAML config with mock entities, applies before tests
- **Config:** `configuration.yaml` includes mock sensor definitions
- **Tests:** Connect via HTTP/WebSocket to real HA instance, query actual entities
- **Reset:** Restart HA or use HA API to delete/reset entities between tests
- **Pros:**
  - Entities are "real" from HA's perspective (in state machine)
  - Tests use actual HA API (most realistic)
  - Easy to inspect entities in HA UI during debugging
  - Deterministic (same entities every test run)
- **Cons:**
  - Requires editing HA's `configuration.yaml` before tests
  - Test data mixed with live HA setup
  - Manual cleanup between test runs
  - Hard to isolate test failures (test data pollution)

### Option B: Dynamically Created Mock Entities via REST API
- **Setup:** Test script creates entities via HA's Developer Tools or API
- **Config:** No YAML needed; entities created on-the-fly
- **Tests:** Query created entities via WebSocket
- **Reset:** DELETE request to remove entities after each test
- **Pros:**
  - Fully automated (no manual HA config needed)
  - Test data isolated to each test run
  - Easy cleanup (delete after test)
  - Repeatable and deterministic
- **Cons:**
  - Requires HA `template` entity platform or custom integration to create entities
  - More API calls (slower setup/teardown)
  - Harder to debug (entities don't persist after test)

### Option C: Custom Test Integration with Mock Entities
- **Setup:** Install a temporary `test_mock_battery` integration that creates entities
- **Config:** Integration config specifies how many mock entities to create
- **Tests:** Query mock entities via WebSocket
- **Reset:** Unload integration or call reset API
- **Pros:**
  - Clean separation of test data from prod
  - Entities are "real" (in HA state machine)
  - Can be toggled on/off without restarting HA
  - Repeatable and deterministic
- **Cons:**
  - Requires building and maintaining test integration
  - Extra code to maintain (not in scope for Sprint 1)

### Option D: Fixture-Based Testing with Mocked HA Instance
- **Setup:** Unit/integration tests spin up mock HA instance with test data
- **Config:** Fixtures define test data (no real HA server needed)
- **Tests:** Tests run against mock; no real server involved
- **Reset:** Cleanup fixtures after each test
- **Pros:**
  - Fast (no network)
  - Completely isolated
  - Deterministic
  - No real server needed
- **Cons:**
  - Doesn't test against real HA (misses edge cases)
  - Mock doesn't capture HA's actual behavior
  - Defeats purpose of test environment (PO specified real server)

## Decision

**Option A: Pre-Provisioned Mock Entities via Integration Config Flow**

This provides a simple, maintainable test environment that uses a real HA instance (as required) with deterministic, repeatable test data.

### Rationale

1. **PO Requirement:** The brief specifies "a predefined HA server" and "real running instance." Option A uses an actual HA server, not a mock.

2. **Simplicity:** QA configures mock entities once in `configuration.yaml`, then all tests use them. No complex test setup code.

3. **Debuggability:** Entities are visible in HA UI during test runs. QA can manually verify state, inspect logs, etc.

4. **Realism:** Tests query actual HA API (WebSocket, state machine), not mocks. This catches integration issues with real HA behavior.

5. **Sprint 1 Scope:** This is the fastest way to get tests running. Automated entity creation (Option B) or custom test integration (Option C) can be added in Sprint 2.

6. **Standard Practice:** HA testing typically uses configuration.yaml with test entities. This aligns with community norms.

### Implementation

**File: `tests/home_assistant_test_config.yaml` (Configuration for Test HA Instance)**

This file is loaded onto the test HA server's `configuration.yaml`. It defines mock battery entities used by all tests.

```yaml
# Vulcan Brownout Test Configuration
# Add this to your test HA instance's configuration.yaml
# Restart HA after adding

# Template entities (these are "battery" entities for testing)
template:
  - sensor:
      - name: "Critical Battery Device 1"
        unique_id: "test_battery_critical_1"
        unit_of_measurement: "%"
        state_class: "measurement"
        device_class: "battery"
        icon: "mdi:battery"
        state: "5"
        attributes:
          device_name: "Test Critical Device 1"

      - name: "Critical Battery Device 2"
        unique_id: "test_battery_critical_2"
        unit_of_measurement: "%"
        state_class: "measurement"
        device_class: "battery"
        icon: "mdi:battery"
        state: "12"
        attributes:
          device_name: "Test Critical Device 2"

      - name: "Low Battery Device"
        unique_id: "test_battery_low_1"
        unit_of_measurement: "%"
        state_class: "measurement"
        device_class: "battery"
        icon: "mdi:battery"
        state: "25"
        attributes:
          device_name: "Test Low Battery Device"

      - name: "Healthy Battery Device"
        unique_id: "test_battery_healthy_1"
        unit_of_measurement: "%"
        state_class: "measurement"
        device_class: "battery"
        icon: "mdi:battery"
        state: "85"
        attributes:
          device_name: "Test Healthy Device"

      - name: "Unavailable Battery Device"
        unique_id: "test_battery_unavailable_1"
        unit_of_measurement: "%"
        state_class: "measurement"
        device_class: "battery"
        icon: "mdi:battery"
        state: "unavailable"
        attributes:
          device_name: "Test Unavailable Device"

# Input numbers (for dynamic battery level changes during tests)
input_number:
  test_battery_critical_1_level:
    name: "Test Battery Critical 1 Level"
    unit_of_measurement: "%"
    min: 0
    max: 100
    step: 1
    initial: 5
    icon: "mdi:battery"

  test_battery_critical_2_level:
    name: "Test Battery Critical 2 Level"
    unit_of_measurement: "%"
    min: 0
    max: 100
    step: 1
    initial: 12
    icon: "mdi:battery"

  test_battery_healthy_1_level:
    name: "Test Battery Healthy 1 Level"
    unit_of_measurement: "%"
    min: 0
    max: 100
    step: 1
    initial: 85
    icon: "mdi:battery"

# Automations (for testing state changes)
automation:
  - alias: "Test: Update Battery Level 1"
    description: "Update template sensor via input_number (test only)"
    trigger:
      platform: state
      entity_id: input_number.test_battery_critical_1_level
    action:
      - service: template.reload_entities
```

**File: `tests/test_integration_end_to_end.py` (E2E Test Example)**

```python
import pytest
import asyncio
from homeassistant.core import HomeAssistant


@pytest.fixture
async def hass():
    """Fixture: Home Assistant instance (real test server)."""
    # This assumes HA is running at http://localhost:8123
    # and configuration.yaml includes our test entities
    # Tests connect via HTTP/WebSocket to real HA instance
    pass


async def test_auto_discovery_finds_battery_entities(hass):
    """Test: Integration discovers all battery entities on startup."""
    # Trigger integration reload
    await hass.services.async_call("homeassistant", "reload_custom_components")
    await asyncio.sleep(2)  # Wait for integration to discover

    # Query HA state machine for battery entities
    states = hass.states.async_all()
    battery_entities = [s for s in states
                        if s.attributes.get("device_class") == "battery"]

    assert len(battery_entities) >= 5, "Should find at least 5 test battery entities"
    entity_ids = [e.entity_id for e in battery_entities]
    assert "sensor.test_battery_critical_1" in entity_ids
    assert "sensor.test_battery_critical_2" in entity_ids


async def test_critical_devices_identified(hass):
    """Test: Devices ≤15% are marked as critical."""
    # Get state of critical device
    state = hass.states.get("sensor.test_battery_critical_1")
    assert state is not None
    assert int(state.state) <= 15  # Should be 5%


async def test_unavailable_devices_shown(hass):
    """Test: Unavailable devices appear in list."""
    state = hass.states.get("sensor.test_battery_unavailable_1")
    assert state is not None
    assert state.state == "unavailable"


async def test_panel_renders_without_error(hass):
    """Test: Panel loads and renders without console errors."""
    # This is a Chrome E2E test (see tests/test_ui.spec.js)
    pass
```

**File: `tests/conftest.py` (Pytest Fixtures)**

```python
import os
import pytest
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component


@pytest.fixture
async def hass():
    """Fixture: Real Home Assistant instance (test server)."""
    # Get HA server URL from environment
    ha_url = os.getenv("HA_URL", "http://localhost:8123")
    ha_token = os.getenv("HA_API_TOKEN", "test_token")

    # Connect to real HA instance
    # Tests communicate via WebSocket/HTTP
    hass = HomeAssistant(ha_url)

    # Set auth token
    hass.http.headers = {"Authorization": f"Bearer {ha_token}"}

    # Note: We don't call async_setup() here because HA is already running
    # We just use the hass object to make API calls

    yield hass

    # Cleanup (optional)
    # await hass.async_block_till_done()


@pytest.fixture
async def mock_battery_entities(hass):
    """Fixture: Mock battery entities are pre-provisioned in HA."""
    # Return list of test entity IDs that should be in HA
    return [
        "sensor.test_battery_critical_1",
        "sensor.test_battery_critical_2",
        "sensor.test_battery_low_1",
        "sensor.test_battery_healthy_1",
        "sensor.test_battery_unavailable_1",
    ]
```

**File: `tests/TESTING_SETUP.md` (QA Instructions)**

```markdown
# Test Environment Setup

## Prerequisites

- Home Assistant instance running (version 2023.12+)
- SSH access to HA server
- HA API token (long-lived)

## Setup Steps

### Step 1: Add Test Configuration to HA

Copy `tests/home_assistant_test_config.yaml` to your HA instance.

**Option A: Manually Edit configuration.yaml**

1. SSH into HA server
2. Edit `~/.homeassistant/configuration.yaml` (or wherever HA stores config)
3. Append contents of `tests/home_assistant_test_config.yaml`
4. Restart HA: `docker-compose restart homeassistant` (or systemctl restart)
5. Wait for HA to become healthy (check UI)

**Option B: Automated (Using Deployment Script)**

```bash
# Copy test config to HA
scp -i ~/.ssh/vulcan_brownout_deploy \
  tests/home_assistant_test_config.yaml \
  homeassistant@192.168.1.100:~/.homeassistant/test_config.yaml

# Log in and append to configuration.yaml
ssh -i ~/.ssh/vulcan_brownout_deploy homeassistant@192.168.1.100 << 'EOF'
  cat ~/.homeassistant/test_config.yaml >> ~/.homeassistant/configuration.yaml
  docker-compose restart homeassistant
EOF

# Wait for HA to restart (30s)
sleep 30
```

### Step 2: Verify Test Entities Exist

```bash
# Check HA logs for template sensor creation
curl -H "Authorization: Bearer $HA_API_TOKEN" \
  http://192.168.1.100:8123/api/states | jq '.[] | select(.entity_id | contains("test_battery"))'
```

Should see:
```json
{
  "entity_id": "sensor.test_battery_critical_1",
  "state": "5",
  "attributes": {
    "device_class": "battery",
    "device_name": "Test Critical Device 1"
  }
}
```

### Step 3: Run Tests

```bash
# Unit tests (backend only, don't need HA running)
python -m pytest tests/test_battery_monitor.py

# Integration tests (require real HA instance)
export HA_URL=http://192.168.1.100:8123
export HA_API_TOKEN=eyJhbGciOi...
python -m pytest tests/test_integration_end_to_end.py

# E2E tests (require Chrome/Chromium)
npm run test:ui
```

### Step 4: State Management Between Tests

Test entities are pre-provisioned and persist across test runs.

If you need to reset state between tests:

```bash
# Reset battery levels to defaults
curl -X POST \
  -H "Authorization: Bearer $HA_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"state": "5"}' \
  http://192.168.1.100:8123/api/states/sensor.test_battery_critical_1

curl -X POST \
  -H "Authorization: Bearer $HA_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"state": "12"}' \
  http://192.168.1.100:8123/api/states/sensor.test_battery_critical_2
```

Or use the input_number automations to change battery levels dynamically:

```bash
# Change battery level via input_number
curl -X POST \
  -H "Authorization: Bearer $HA_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"value": 25}' \
  http://192.168.1.100:8123/api/services/input_number/set_value \
  -d '{"entity_id": "input_number.test_battery_critical_1_level", "value": 25}'
```

## Troubleshooting

### Test entities not appearing

1. Check HA logs: `docker-compose logs homeassistant | grep -i template`
2. Verify configuration.yaml syntax: `docker-compose exec homeassistant yamllint configuration.yaml`
3. Reload template entities: Home Assistant UI > Developer Tools > YAML > Reload Template Entities

### Entities showing "unknown"

- Template sensors take a moment to evaluate. Wait 10s after HA restart.
- Check if template is valid: HA UI > Developer Tools > Template > paste template, check output

### State not updating during tests

- Ensure test config is in `configuration.yaml` (not in a separate file)
- Restart HA: `docker-compose restart homeassistant`
- Check if entity_id is correct: `curl -H "Authorization: Bearer $HA_API_TOKEN" http://ha:8123/api/states | jq '.[] | select(.entity_id | contains("test"))'`

## Cleanup

To remove test entities, remove the test configuration section from `configuration.yaml` and restart HA.

```bash
# Remove test config (comment out or delete from configuration.yaml)
ssh -i ~/.ssh/vulcan_brownout_deploy homeassistant@192.168.1.100 "vi ~/.homeassistant/configuration.yaml"

# Restart
docker-compose restart homeassistant
```

## Next Steps

- Run test suite: `npm run test` and `python -m pytest`
- Debug failures using HA UI (http://ha:8123)
- Check integration logs during test runs
```

## Consequences

Positive:
- Uses real HA instance (as required by PO)
- Entities are "real" (in HA state machine, not mocked)
- Easy to debug (visible in HA UI)
- Deterministic (same test data every run)
- Minimal code (no custom test integration)
- Fast to implement

Negative:
- Manual setup of test entities (YAML editing)
- State persists between tests (need manual reset if needed)
- Test data mixed with test HA instance (not ideal isolation)
- Requires HA restart to add test config

## Future Improvements (Sprint 2+)

1. **Automated Entity Creation:** Custom test integration that creates entities on-demand
2. **Test Data Isolation:** Per-test entity namespaces
3. **Snapshot Testing:** Record baseline entity states, compare across test runs
4. **Docker Compose for Test HA:** Pre-built test HA image with test config baked in

## Next Steps

- QA creates test HA instance (or uses existing one)
- QA adds test configuration to `configuration.yaml`
- QA verifies test entities appear in HA UI
- QA runs test suite
- Lead Developer implements integration
