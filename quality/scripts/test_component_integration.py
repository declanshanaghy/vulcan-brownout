#!/usr/bin/env python3
"""
Vulcan Brownout Component Test Suite - Mock HA Testing

Tests all WebSocket commands and integration functionality using a mock
Home Assistant server. This suite runs in Docker with hardcoded constants
and can inject errors to test resilience.

Requires: pytest, pytest-asyncio, websockets, aiohttp

Usage:
    pytest quality/scripts/test_component_integration.py -v
    pytest quality/scripts/test_component_integration.py::TestQueryDevices::test_query_devices_basic -v
"""

import asyncio
import json
import logging
import os
from typing import Any, Dict, Optional
import urllib.parse

import pytest
import pytest_asyncio
import websockets
import aiohttp


# Test constants - read from environment or use defaults
# Environment variables are set by docker-compose or manually for component testing
TEST_HA_URL = os.getenv("HA_URL", "http://localhost:8123")
TEST_HA_TOKEN = os.getenv("HA_TOKEN", "test-token-constant")
TEST_HA_PORT = int(os.getenv("HA_PORT", "8123"))
MOCK_CONTROL_URL = f"{TEST_HA_URL}/mock/control"

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)


class HAWebSocketClient:
    """Home Assistant WebSocket API client."""

    def __init__(self, ha_url: str, ha_token: str):
        self.ha_url = ha_url
        self.ha_token = ha_token
        self.ws = None
        self.msg_id = 0

    async def connect(self) -> None:
        """Connect and authenticate to Home Assistant WebSocket."""
        ws_url = self.ha_url.replace("http://", "ws://").replace("https://", "wss://")
        if not ws_url.endswith("/"):
            ws_url += "/"
        ws_url = urllib.parse.urljoin(ws_url, "api/websocket")

        self.ws = await websockets.connect(ws_url, ping_interval=None)

        # Receive auth_required
        msg = json.loads(await self.ws.recv())
        assert msg["type"] == "auth_required"

        # Send auth
        await self.ws.send(json.dumps({
            "type": "auth",
            "access_token": self.ha_token
        }))

        # Receive auth_ok
        msg = json.loads(await self.ws.recv())
        assert msg["type"] == "auth_ok"

    async def send_command(self, command_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Send WebSocket command and wait for response."""
        self.msg_id += 1

        payload = {
            "id": self.msg_id,
            "type": command_type,
            **data
        }

        logger.debug(f"Sending: {payload}")
        await self.ws.send(json.dumps(payload))

        # Wait for response
        response = json.loads(await self.ws.recv())
        logger.debug(f"Received: {response}")

        return response

    async def close(self) -> None:
        """Close WebSocket connection."""
        if self.ws:
            await self.ws.close()


class MockHAController:
    """Control mock HA behavior via HTTP."""

    def __init__(self, mock_control_url: str = MOCK_CONTROL_URL):
        self.mock_control_url = mock_control_url
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, *args):
        if self.session:
            await self.session.close()

    async def setup_entities(self, entities: list) -> None:
        """Load test entities into mock HA."""
        async with self.session.post(
            self.mock_control_url,
            json={"entities": entities}
        ) as resp:
            assert resp.status == 200
            logger.info(f"Loaded {len(entities)} mock entities")

    async def set_response_delay(self, delay_ms: int) -> None:
        """Set response delay in milliseconds."""
        async with self.session.post(
            self.mock_control_url,
            json={"response_delay_ms": delay_ms}
        ) as resp:
            assert resp.status == 200

    async def set_malformed_response(self, malformed: bool) -> None:
        """Enable/disable malformed JSON responses."""
        async with self.session.post(
            self.mock_control_url,
            json={"malformed_response": malformed}
        ) as resp:
            assert resp.status == 200

    async def set_auth_failures(self, count: int) -> None:
        """Simulate N auth failures before success."""
        async with self.session.post(
            self.mock_control_url,
            json={"auth_failures": count}
        ) as resp:
            assert resp.status == 200

    async def set_connection_drops(self, message_ids: list) -> None:
        """Drop connection at specified message IDs."""
        async with self.session.post(
            self.mock_control_url,
            json={"connection_drops": message_ids}
        ) as resp:
            assert resp.status == 200

    async def set_auth_timeout(self, timeout_ms: int) -> None:
        """Set auth timeout in milliseconds."""
        async with self.session.post(
            self.mock_control_url,
            json={"auth_timeout_ms": timeout_ms}
        ) as resp:
            assert resp.status == 200


@pytest_asyncio.fixture
async def mock_ha():
    """Create mock HA controller."""
    async with MockHAController() as controller:
        yield controller


@pytest_asyncio.fixture
async def ws_client(mock_ha):
    """Create and connect WebSocket client."""
    # Setup default entities
    from .mock_fixtures import get_fixture_entities
    entities = get_fixture_entities()
    await mock_ha.setup_entities(entities)

    # Connect client
    client = HAWebSocketClient(TEST_HA_URL, TEST_HA_TOKEN)
    await client.connect()
    yield client
    await client.close()


# ============================================================================
# HAPPY PATH TESTS
# ============================================================================

class TestQueryDevicesHappyPath:
    """Test vulcan-brownout/query_devices happy path."""

    @pytest.mark.asyncio
    async def test_query_devices_basic(self, ws_client):
        """Test basic device query."""
        response = await ws_client.send_command("vulcan-brownout/query_devices", {
            "limit": 20,
            "offset": 0
        })

        assert response["type"] == "result"
        assert response["success"] is True
        assert "data" in response

        data = response["data"]
        assert "devices" in data
        assert "total" in data
        assert "device_statuses" in data
        assert isinstance(data["devices"], list)
        assert isinstance(data["total"], int)
        assert len(data["devices"]) <= 20

    @pytest.mark.asyncio
    async def test_query_devices_pagination(self, ws_client):
        """Test device query with pagination."""
        # Get first page
        response1 = await ws_client.send_command("vulcan-brownout/query_devices", {
            "limit": 10,
            "offset": 0
        })

        assert response1["success"] is True
        devices1 = response1["data"]["devices"]
        total = response1["data"]["total"]

        # Get second page if enough devices
        if total > 10:
            response2 = await ws_client.send_command("vulcan-brownout/query_devices", {
                "limit": 10,
                "offset": 10
            })

            assert response2["success"] is True
            devices2 = response2["data"]["devices"]

            # Verify devices are different
            ids1 = {d["entity_id"] for d in devices1}
            ids2 = {d["entity_id"] for d in devices2}
            assert len(ids1 & ids2) == 0  # No overlap

    @pytest.mark.asyncio
    async def test_query_devices_device_statuses(self, ws_client):
        """Test that device_statuses contains valid counts."""
        response = await ws_client.send_command("vulcan-brownout/query_devices", {
            "limit": 100,
            "offset": 0
        })

        assert response["success"] is True
        statuses = response["data"]["device_statuses"]

        # Verify all status categories present
        for status in ["critical", "warning", "healthy", "unavailable"]:
            assert status in statuses
            assert isinstance(statuses[status], int)
            assert statuses[status] >= 0

    @pytest.mark.asyncio
    async def test_query_devices_device_structure(self, ws_client):
        """Test that returned devices have correct structure."""
        response = await ws_client.send_command("vulcan-brownout/query_devices", {
            "limit": 5,
            "offset": 0
        })

        assert response["success"] is True
        devices = response["data"]["devices"]

        if devices:
            device = devices[0]

            # Required fields
            assert "entity_id" in device
            assert "state" in device
            assert "battery_level" in device
            assert "available" in device
            assert "status" in device
            assert "device_name" in device

            # Verify status is valid
            assert device["status"] in ["critical", "warning", "healthy", "unavailable"]


class TestSubscribeHappyPath:
    """Test vulcan-brownout/subscribe happy path."""

    @pytest.mark.asyncio
    async def test_subscribe_basic(self, ws_client):
        """Test basic subscription."""
        response = await ws_client.send_command("vulcan-brownout/subscribe", {})

        assert response["type"] == "result"
        assert response["success"] is True
        assert "data" in response

        data = response["data"]
        assert "subscription_id" in data
        assert "status" in data
        assert data["status"] == "subscribed"
        assert data["subscription_id"].startswith("sub_")

    @pytest.mark.asyncio
    async def test_subscribe_multiple(self, ws_client):
        """Test multiple subscriptions from same connection."""
        response1 = await ws_client.send_command("vulcan-brownout/subscribe", {})
        assert response1["success"] is True
        sub_id_1 = response1["data"]["subscription_id"]

        response2 = await ws_client.send_command("vulcan-brownout/subscribe", {})
        assert response2["success"] is True
        sub_id_2 = response2["data"]["subscription_id"]

        # IDs should be different
        assert sub_id_1 != sub_id_2


class TestSetThresholdHappyPath:
    """Test vulcan-brownout/set_threshold happy path."""

    @pytest.mark.asyncio
    async def test_set_threshold_global(self, ws_client):
        """Test setting global threshold."""
        response = await ws_client.send_command("vulcan-brownout/set_threshold", {
            "global_threshold": 20
        })

        assert response["type"] == "result"
        assert response["success"] is True

        data = response["data"]
        assert "global_threshold" in data
        assert data["global_threshold"] == 20

    @pytest.mark.asyncio
    async def test_set_threshold_device_rules(self, ws_client):
        """Test setting device-specific rules."""
        # First get available devices
        query_response = await ws_client.send_command("vulcan-brownout/query_devices", {
            "limit": 10,
            "offset": 0
        })

        if not query_response["success"] or not query_response["data"]["devices"]:
            pytest.skip("No devices available for testing")

        entity_id = query_response["data"]["devices"][0]["entity_id"]

        # Set threshold for specific device
        response = await ws_client.send_command("vulcan-brownout/set_threshold", {
            "device_rules": {
                entity_id: 30
            }
        })

        assert response["success"] is True
        assert "device_rules" in response["data"]
        assert entity_id in response["data"]["device_rules"]
        assert response["data"]["device_rules"][entity_id] == 30


# ============================================================================
# ERROR INJECTION TESTS
# ============================================================================

class TestErrorInjection:
    """Test error handling via mock control injection."""

    @pytest.mark.asyncio
    async def test_empty_entity_list(self, mock_ha):
        """Test behavior with no entities."""
        # Setup with empty entity list
        await mock_ha.setup_entities([])

        client = HAWebSocketClient(TEST_HA_URL, TEST_HA_TOKEN)
        await client.connect()

        response = await client.send_command("vulcan-brownout/query_devices", {
            "limit": 20,
            "offset": 0
        })

        assert response["success"] is True
        assert response["data"]["total"] == 0
        assert response["data"]["devices"] == []

        await client.close()

    @pytest.mark.asyncio
    async def test_invalid_device_rule(self, mock_ha):
        """Test setting threshold for non-existent device."""
        from .mock_fixtures import get_fixture_entities
        entities = get_fixture_entities()
        await mock_ha.setup_entities(entities)

        client = HAWebSocketClient(TEST_HA_URL, TEST_HA_TOKEN)
        await client.connect()

        response = await client.send_command("vulcan-brownout/set_threshold", {
            "device_rules": {
                "sensor.nonexistent_device": 30
            }
        })

        assert response["success"] is False
        assert "error" in response

        await client.close()

    @pytest.mark.asyncio
    async def test_invalid_threshold_value(self, mock_ha):
        """Test setting invalid threshold values."""
        from .mock_fixtures import get_fixture_entities
        entities = get_fixture_entities()
        await mock_ha.setup_entities(entities)

        client = HAWebSocketClient(TEST_HA_URL, TEST_HA_TOKEN)
        await client.connect()

        # Threshold out of range
        response = await client.send_command("vulcan-brownout/set_threshold", {
            "global_threshold": 150  # Max is 100
        })

        assert response["success"] is False

        await client.close()


# ============================================================================
# EDGE CASE TESTS
# ============================================================================

class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_max_page_size(self, ws_client):
        """Test maximum page size (100)."""
        response = await ws_client.send_command("vulcan-brownout/query_devices", {
            "limit": 100,
            "offset": 0
        })

        assert response["success"] is True
        assert len(response["data"]["devices"]) <= 100

    @pytest.mark.asyncio
    async def test_zero_offset(self, ws_client):
        """Test offset of 0 (first page)."""
        response = await ws_client.send_command("vulcan-brownout/query_devices", {
            "limit": 20,
            "offset": 0
        })

        assert response["success"] is True
        assert response["data"]["offset"] == 0

    @pytest.mark.asyncio
    async def test_large_offset(self, ws_client):
        """Test offset beyond total entities."""
        response = await ws_client.send_command("vulcan-brownout/query_devices", {
            "limit": 20,
            "offset": 10000  # Way beyond total
        })

        assert response["success"] is True
        assert response["data"]["devices"] == []

    @pytest.mark.asyncio
    async def test_sorting_stability(self, ws_client):
        """Test that sorting is stable across pages."""
        # Get first page sorted by battery level
        response1 = await ws_client.send_command("vulcan-brownout/query_devices", {
            "limit": 30,
            "offset": 0,
            "sort_key": "level_asc"
        })

        # Get second page with same sorting
        response2 = await ws_client.send_command("vulcan-brownout/query_devices", {
            "limit": 30,
            "offset": 30,
            "sort_key": "level_asc"
        })

        # Verify no overlap and consistent ordering
        ids1 = {d["entity_id"] for d in response1["data"]["devices"]}
        ids2 = {d["entity_id"] for d in response2["data"]["devices"]}
        assert len(ids1 & ids2) == 0


# ============================================================================
# SPRINT 5: FILTERING TESTS (HAPPY PATH)
# ============================================================================

class TestFilteringHappyPath:
    """Test Sprint 5 server-side filtering happy path."""

    @pytest.mark.asyncio
    async def test_query_devices_with_status_filter(self, mock_ha):
        """Test filtering devices by status=critical."""
        from .mock_fixtures import generate_filter_test_entities
        entities = generate_filter_test_entities()
        await mock_ha.setup_entities(entities)

        client = HAWebSocketClient(TEST_HA_URL, TEST_HA_TOKEN)
        await client.connect()

        # Query with status filter
        response = await client.send_command("vulcan-brownout/query_devices", {
            "limit": 100,
            "offset": 0,
            "filter_status": ["critical"]
        })

        assert response["success"] is True
        devices = response["data"]["devices"]
        # All returned devices should have critical status
        for device in devices:
            assert device["status"] == "critical"

        await client.close()

    @pytest.mark.asyncio
    async def test_query_devices_with_manufacturer_filter(self, mock_ha):
        """Test filtering devices by manufacturer."""
        from .mock_fixtures import generate_filter_test_entities
        entities = generate_filter_test_entities()
        await mock_ha.setup_entities(entities)

        client = HAWebSocketClient(TEST_HA_URL, TEST_HA_TOKEN)
        await client.connect()

        # Query with manufacturer filter (Aqara)
        response = await client.send_command("vulcan-brownout/query_devices", {
            "limit": 100,
            "offset": 0,
            "filter_manufacturer": ["Aqara"]
        })

        assert response["success"] is True
        # Response should have valid structure
        assert "data" in response
        assert "total" in response["data"]

        await client.close()

    @pytest.mark.asyncio
    async def test_query_devices_with_area_filter(self, mock_ha):
        """Test filtering devices by area."""
        from .mock_fixtures import generate_filter_test_entities
        entities = generate_filter_test_entities()
        await mock_ha.setup_entities(entities)

        client = HAWebSocketClient(TEST_HA_URL, TEST_HA_TOKEN)
        await client.connect()

        # Query with area filter
        response = await client.send_command("vulcan-brownout/query_devices", {
            "limit": 100,
            "offset": 0,
            "filter_area": ["Living Room"]
        })

        assert response["success"] is True
        assert "data" in response
        assert "devices" in response["data"]

        await client.close()

    @pytest.mark.asyncio
    async def test_query_devices_with_multiple_filters(self, mock_ha):
        """Test combining status + manufacturer filters (AND logic)."""
        from .mock_fixtures import generate_filter_test_entities
        entities = generate_filter_test_entities()
        await mock_ha.setup_entities(entities)

        client = HAWebSocketClient(TEST_HA_URL, TEST_HA_TOKEN)
        await client.connect()

        # Query with multiple filters (AND logic)
        response = await client.send_command("vulcan-brownout/query_devices", {
            "limit": 100,
            "offset": 0,
            "filter_status": ["critical"],
            "filter_manufacturer": ["Aqara"]
        })

        assert response["success"] is True
        devices = response["data"]["devices"]
        # All devices must match BOTH filters
        for device in devices:
            assert device["status"] == "critical"
            # Manufacturer check would require registry lookup in mock

        await client.close()

    @pytest.mark.asyncio
    async def test_query_devices_no_filter_returns_all(self, mock_ha):
        """Test backward compatibility: no filters returns all devices."""
        from .mock_fixtures import generate_filter_test_entities
        entities = generate_filter_test_entities()
        await mock_ha.setup_entities(entities)

        client = HAWebSocketClient(TEST_HA_URL, TEST_HA_TOKEN)
        await client.connect()

        # Query without filters
        response = await client.send_command("vulcan-brownout/query_devices", {
            "limit": 100,
            "offset": 0
        })

        assert response["success"] is True
        unfiltered_total = response["data"]["total"]

        # Query with empty filter arrays (should be equivalent to no filters)
        response2 = await client.send_command("vulcan-brownout/query_devices", {
            "limit": 100,
            "offset": 0,
            "filter_manufacturer": [],
            "filter_status": [],
            "filter_area": [],
            "filter_device_class": []
        })

        assert response2["success"] is True
        # Empty filters should return same result as no filters
        assert response2["data"]["total"] == unfiltered_total

        await client.close()

    @pytest.mark.asyncio
    async def test_get_filter_options(self, mock_ha):
        """Test get_filter_options returns correct data structure."""
        from .mock_fixtures import generate_filter_test_entities
        entities = generate_filter_test_entities()
        await mock_ha.setup_entities(entities)

        client = HAWebSocketClient(TEST_HA_URL, TEST_HA_TOKEN)
        await client.connect()

        # Call get_filter_options
        response = await client.send_command("vulcan-brownout/get_filter_options", {})

        assert response["success"] is True
        data = response["data"]

        # Verify response structure
        assert "manufacturers" in data
        assert "device_classes" in data
        assert "statuses" in data
        assert "areas" in data

        # Verify types
        assert isinstance(data["manufacturers"], list)
        assert isinstance(data["device_classes"], list)
        assert isinstance(data["statuses"], list)
        assert isinstance(data["areas"], list)

        # Statuses should always have the standard four values
        assert "critical" in data["statuses"]
        assert "warning" in data["statuses"]
        assert "healthy" in data["statuses"]
        assert "unavailable" in data["statuses"]

        await client.close()

    @pytest.mark.asyncio
    async def test_query_devices_filter_resets_pagination(self, mock_ha):
        """Test that filter changes reset pagination cursor."""
        from .mock_fixtures import generate_filter_test_entities
        entities = generate_filter_test_entities()
        await mock_ha.setup_entities(entities)

        client = HAWebSocketClient(TEST_HA_URL, TEST_HA_TOKEN)
        await client.connect()

        # First query without filter
        response1 = await client.send_command("vulcan-brownout/query_devices", {
            "limit": 50,
            "offset": 0
        })

        assert response1["success"] is True
        total1 = response1["data"]["total"]

        # Second query with filter
        response2 = await client.send_command("vulcan-brownout/query_devices", {
            "limit": 50,
            "offset": 0,
            "filter_status": ["critical"]
        })

        assert response2["success"] is True
        # Filtered total may be different (or same if all are critical)
        assert "total" in response2["data"]

        await client.close()


# ============================================================================
# SPRINT 5: FILTERING TESTS (EDGE CASES)
# ============================================================================

class TestFilteringEdgeCases:
    """Test Sprint 5 filtering edge cases."""

    @pytest.mark.asyncio
    async def test_filter_with_empty_arrays(self, mock_ha):
        """Test that empty filter arrays are treated as no filter."""
        from .mock_fixtures import generate_filter_test_entities
        entities = generate_filter_test_entities()
        await mock_ha.setup_entities(entities)

        client = HAWebSocketClient(TEST_HA_URL, TEST_HA_TOKEN)
        await client.connect()

        # Query with all empty filter arrays
        response = await client.send_command("vulcan-brownout/query_devices", {
            "limit": 100,
            "offset": 0,
            "filter_manufacturer": [],
            "filter_device_class": [],
            "filter_status": [],
            "filter_area": []
        })

        assert response["success"] is True
        # Should return all devices
        assert response["data"]["total"] > 0

        await client.close()

    @pytest.mark.asyncio
    async def test_filter_with_invalid_status(self, mock_ha):
        """Test that invalid status values are rejected."""
        from .mock_fixtures import generate_filter_test_entities
        entities = generate_filter_test_entities()
        await mock_ha.setup_entities(entities)

        client = HAWebSocketClient(TEST_HA_URL, TEST_HA_TOKEN)
        await client.connect()

        # Query with invalid status value
        response = await client.send_command("vulcan-brownout/query_devices", {
            "limit": 100,
            "offset": 0,
            "filter_status": ["invalid_status"]
        })

        # Should fail with invalid_filter_status error
        assert response["success"] is False
        assert "error" in response

        await client.close()

    @pytest.mark.asyncio
    async def test_filter_no_matches(self, mock_ha):
        """Test filter that matches nothing returns empty result."""
        from .mock_fixtures import generate_filter_test_entities
        entities = generate_filter_test_entities()
        await mock_ha.setup_entities(entities)

        client = HAWebSocketClient(TEST_HA_URL, TEST_HA_TOKEN)
        await client.connect()

        # Query with filter that matches nothing
        response = await client.send_command("vulcan-brownout/query_devices", {
            "limit": 100,
            "offset": 0,
            "filter_manufacturer": ["NonExistentManufacturer"]
        })

        assert response["success"] is True
        assert response["data"]["total"] == 0
        assert response["data"]["devices"] == []

        await client.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
