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
    async def test_query_devices_sorting(self, ws_client):
        """Test sorting by battery level."""
        response = await ws_client.send_command("vulcan-brownout/query_devices", {
            "limit": 100,
            "offset": 0,
            "sort_key": "level_asc",
            "sort_order": "asc"
        })

        assert response["success"] is True
        devices = response["data"]["devices"]

        # Verify sorted ascending by battery_level
        battery_levels = []
        for device in devices:
            try:
                level = float(device["battery_level"])
                battery_levels.append(level)
            except (ValueError, TypeError):
                pass

        if battery_levels:
            assert battery_levels == sorted(battery_levels)

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
    async def test_auth_failure_injection(self, mock_ha):
        """Test authentication failure scenario."""
        # Configure mock to fail auth once
        await mock_ha.set_auth_failures(1)

        # First connection should fail
        client1 = HAWebSocketClient(TEST_HA_URL, TEST_HA_TOKEN)
        with pytest.raises(AssertionError):
            await client1.connect()
        await client1.close()

        # Second connection should succeed
        await mock_ha.set_auth_failures(0)
        client2 = HAWebSocketClient(TEST_HA_URL, TEST_HA_TOKEN)
        await client2.connect()
        await client2.close()

    @pytest.mark.asyncio
    async def test_auth_timeout_injection(self, mock_ha):
        """Test authentication timeout scenario."""
        # Set very short auth timeout
        await mock_ha.set_auth_timeout(100)  # 100ms

        client = HAWebSocketClient(TEST_HA_URL, TEST_HA_TOKEN)
        # This should timeout during auth
        with pytest.raises(Exception):
            await client.connect()
        await client.close()

    @pytest.mark.asyncio
    async def test_response_delay_injection(self, mock_ha):
        """Test response delay injection."""
        from .mock_fixtures import get_fixture_entities
        entities = get_fixture_entities()
        await mock_ha.setup_entities(entities)

        # Set 200ms delay
        await mock_ha.set_response_delay(200)

        client = HAWebSocketClient(TEST_HA_URL, TEST_HA_TOKEN)
        await client.connect()

        import time
        start = time.time()
        response = await client.send_command("vulcan-brownout/query_devices", {
            "limit": 10,
            "offset": 0
        })
        elapsed = time.time() - start

        assert response["success"] is True
        # Should take at least 200ms due to injected delay
        assert elapsed >= 0.18  # Allow 20ms variance

        await client.close()

    @pytest.mark.asyncio
    async def test_malformed_response_injection(self, mock_ha):
        """Test malformed JSON response handling."""
        from .mock_fixtures import get_fixture_entities
        entities = get_fixture_entities()
        await mock_ha.setup_entities(entities)

        # Enable malformed responses
        await mock_ha.set_malformed_response(True)

        client = HAWebSocketClient(TEST_HA_URL, TEST_HA_TOKEN)
        await client.connect()

        # Send command - should receive malformed JSON
        client.msg_id += 1
        payload = {
            "id": client.msg_id,
            "type": "vulcan-brownout/query_devices",
            "limit": 10,
            "offset": 0
        }
        await client.ws.send(json.dumps(payload))

        # Try to parse response - should fail
        with pytest.raises(json.JSONDecodeError):
            raw_response = await client.ws.recv()
            json.loads(raw_response)

        await client.close()

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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
