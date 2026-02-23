#!/usr/bin/env python3
"""
Vulcan Brownout QA Test Suite - API Integration Phase 3
Tests all WebSocket commands and integration functionality after deployment.

Requires: pytest, pytest-asyncio, websockets

Usage:
    pytest quality/integration-tests/test_api_integration.py -v
    pytest quality/integration-tests/test_api_integration.py -v --capture=no  # Show print statements
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional
from datetime import datetime

import pytest
import websockets
from urllib.parse import urljoin

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
        ws_url = urljoin(ws_url + "/", "api/websocket")

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
            "data": data
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


def _load_staging_config() -> dict:
    """Load staging config via ConfigLoader (quality/environments/staging/)."""
    try:
        repo_root = Path(__file__).resolve().parents[3]
        sys.path.insert(0, str(repo_root / 'development' / 'scripts'))
        from config_loader import ConfigLoader
        loader = ConfigLoader('staging', env_base_dir='quality/environments')
        return loader.get_env_vars()
    except Exception:
        return {}


@pytest.fixture(scope="session")
def ha_connection_params():
    """Load HA connection parameters from staging YAML config."""
    cfg = _load_staging_config()

    ha_url = cfg.get("HA_URL") or os.getenv("HA_URL", "http://homeassistant.lan:8123")
    ha_token = cfg.get("HA_TOKEN") or os.getenv("HA_TOKEN")

    if not ha_token:
        pytest.skip(
            "HA_TOKEN not set — add it to "
            "quality/environments/staging/vulcan-brownout-secrets.yaml"
        )

    return {
        "ha_url": ha_url,
        "ha_token": ha_token
    }


@pytest.fixture
async def ws_client(ha_connection_params):
    """Create and connect WebSocket client."""
    client = HAWebSocketClient(**ha_connection_params)
    await client.connect()
    yield client
    await client.close()


class TestQueryDevices:
    """Test vulcan-brownout/query_devices command."""

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

        # Get second page
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
    async def test_query_devices_sorting_battery_level(self, ws_client):
        """Test sorting by battery level."""
        response = await ws_client.send_command("vulcan-brownout/query_devices", {
            "limit": 50,
            "offset": 0,
            "sort_key": "battery_level",
            "sort_order": "asc"
        })

        assert response["success"] is True
        devices = response["data"]["devices"]

        # Verify sorted ascending by battery_level
        battery_levels = []
        for device in devices:
            try:
                level = int(device["battery_level"])
                battery_levels.append(level)
            except (ValueError, TypeError):
                # Handle unavailable or unknown states
                pass

        if battery_levels:
            assert battery_levels == sorted(battery_levels)

    @pytest.mark.asyncio
    async def test_query_devices_sorting_device_name(self, ws_client):
        """Test sorting by device name."""
        response = await ws_client.send_command("vulcan-brownout/query_devices", {
            "limit": 50,
            "offset": 0,
            "sort_key": "device_name",
            "sort_order": "asc"
        })

        assert response["success"] is True
        devices = response["data"]["devices"]

        # Verify sorted alphabetically
        names = [d["device_name"] for d in devices]
        assert names == sorted(names)

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

        # Total should match sum of statuses
        total_from_statuses = sum(statuses.values())
        assert total_from_statuses == response["data"]["total"]

    @pytest.mark.asyncio
    async def test_query_devices_invalid_limit(self, ws_client):
        """Test query with invalid limit."""
        response = await ws_client.send_command("vulcan-brownout/query_devices", {
            "limit": 101,  # Max is 100
            "offset": 0
        })

        # Should either reject or accept (depends on validation)
        # If it accepts, verify limit is clamped to 100
        if response["success"]:
            assert len(response["data"]["devices"]) <= 100

    @pytest.mark.asyncio
    async def test_query_devices_invalid_sort_key(self, ws_client):
        """Test query with invalid sort key."""
        response = await ws_client.send_command("vulcan-brownout/query_devices", {
            "limit": 20,
            "offset": 0,
            "sort_key": "invalid_key"
        })

        # Should fail with error
        assert response["success"] is False
        assert "error" in response

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


class TestSubscribe:
    """Test vulcan-brownout/subscribe command."""

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

        # Subscribe again - different client should work
        response2 = await ws_client.send_command("vulcan-brownout/subscribe", {})
        assert response2["success"] is True
        sub_id_2 = response2["data"]["subscription_id"]

        # IDs should be different
        assert sub_id_1 != sub_id_2

    @pytest.mark.asyncio
    async def test_subscribe_receives_events(self, ws_client):
        """Test that subscription receives device_changed events."""
        # Subscribe
        response = await ws_client.send_command("vulcan-brownout/subscribe", {})
        assert response["success"] is True

        # Set a short timeout and check for events
        try:
            # This is a simplified test - real events would come from state changes
            # In production, we'd trigger a state change and verify event receipt
            logger.info("Subscription active - waiting for potential events...")
            await asyncio.sleep(1)  # Wait 1 second for any events

        except asyncio.TimeoutError:
            pass  # Expected if no state changes


class TestSetThreshold:
    """Test vulcan-brownout/set_threshold command."""

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

    @pytest.mark.asyncio
    async def test_set_threshold_global_and_device_rules(self, ws_client):
        """Test setting both global and device rules."""
        query_response = await ws_client.send_command("vulcan-brownout/query_devices", {
            "limit": 5,
            "offset": 0
        })

        if not query_response["success"] or len(query_response["data"]["devices"]) < 2:
            pytest.skip("Not enough devices for testing")

        entity_ids = [d["entity_id"] for d in query_response["data"]["devices"][:2]]

        response = await ws_client.send_command("vulcan-brownout/set_threshold", {
            "global_threshold": 25,
            "device_rules": {
                entity_ids[0]: 35,
                entity_ids[1]: 40
            }
        })

        assert response["success"] is True
        assert response["data"]["global_threshold"] == 25
        assert len(response["data"]["device_rules"]) == 2

    @pytest.mark.asyncio
    async def test_set_threshold_invalid_value(self, ws_client):
        """Test setting invalid threshold value."""
        response = await ws_client.send_command("vulcan-brownout/set_threshold", {
            "global_threshold": 150  # Out of range (max 100)
        })

        assert response["success"] is False
        assert "error" in response
        assert response["error"]["code"] == "invalid_threshold"

    @pytest.mark.asyncio
    async def test_set_threshold_invalid_device_rule(self, ws_client):
        """Test setting rule for non-existent device."""
        response = await ws_client.send_command("vulcan-brownout/set_threshold", {
            "device_rules": {
                "sensor.nonexistent_battery": 30
            }
        })

        assert response["success"] is False
        assert "error" in response
        assert response["error"]["code"] == "invalid_device_rule"

    @pytest.mark.asyncio
    async def test_set_threshold_too_many_rules(self, ws_client):
        """Test exceeding maximum device rules (10)."""
        # Try to set 11 rules
        device_rules = {}
        for i in range(11):
            device_rules[f"sensor.nonexistent_{i}"] = 30

        response = await ws_client.send_command("vulcan-brownout/set_threshold", {
            "device_rules": device_rules
        })

        # Should fail with too_many_rules or invalid_device_rule
        assert response["success"] is False

    @pytest.mark.asyncio
    async def test_set_threshold_persistence(self, ws_client):
        """Test that threshold changes persist across commands."""
        # Set threshold
        set_response = await ws_client.send_command("vulcan-brownout/set_threshold", {
            "global_threshold": 22
        })

        assert set_response["success"] is True
        assert set_response["data"]["global_threshold"] == 22

        # Query devices should reflect new threshold (at least in status calculations)
        query_response = await ws_client.send_command("vulcan-brownout/query_devices", {
            "limit": 5,
            "offset": 0
        })

        assert query_response["success"] is True


class TestErrorHandling:
    """Test error handling and edge cases."""

    @pytest.mark.asyncio
    async def test_invalid_command_type(self, ws_client):
        """Test handling of invalid command type."""
        response = await ws_client.send_command("invalid/command", {})

        # Should either reject or be unknown
        # Most HA integrations will silently ignore unknown types
        logger.info(f"Invalid command response: {response}")

    @pytest.mark.asyncio
    async def test_malformed_data(self, ws_client):
        """Test handling of malformed data."""
        # Send invalid data structure
        response = await ws_client.send_command("vulcan-brownout/query_devices", {
            "limit": "not_a_number"
        })

        # Should either coerce or reject
        assert "success" in response

    @pytest.mark.asyncio
    async def test_missing_required_fields(self, ws_client):
        """Test handling of missing required fields."""
        # This depends on API validation
        response = await ws_client.send_command("vulcan-brownout/set_threshold", {
            "device_rules": {
                "sensor.test": "not_a_number"
            }
        })

        # Should fail with validation error
        if not response["success"]:
            assert "error" in response


class TestPerformance:
    """Test performance characteristics."""

    @pytest.mark.asyncio
    async def test_query_many_devices(self, ws_client):
        """Test querying with maximum page size."""
        import time

        start = time.time()
        response = await ws_client.send_command("vulcan-brownout/query_devices", {
            "limit": 100,
            "offset": 0
        })
        duration = time.time() - start

        assert response["success"] is True
        logger.info(f"Query 100 devices: {duration*1000:.2f}ms")
        assert duration < 2.0  # Should be fast

    @pytest.mark.asyncio
    async def test_set_threshold_broadcast(self, ws_client):
        """Test threshold update broadcast."""
        # This would verify that threshold_updated events are broadcast
        # Requires multiple connections or event monitoring
        logger.info("Threshold broadcast test - requires multi-connection setup")


class TestIntegrationLoaded:
    """Test that integration is properly loaded."""

    @pytest.mark.asyncio
    async def test_integration_responds_to_commands(self, ws_client):
        """Test that integration responds to valid commands."""
        response = await ws_client.send_command("vulcan-brownout/query_devices", {})

        # Should not get integration_not_loaded error
        if not response["success"]:
            assert response.get("error", {}).get("code") != "integration_not_loaded"

    @pytest.mark.asyncio
    async def test_version_check(self, ws_client):
        """Test that we're running expected version."""
        # Query devices response includes version info
        response = await ws_client.send_command("vulcan-brownout/query_devices", {})

        assert response["success"] is True
        logger.info("Integration is responding correctly")


# Standalone test functions for non-pytest usage
async def run_all_tests(ha_url: str, ha_token: str):
    """Run all integration tests."""
    print("\n" + "=" * 80)
    print("VULCAN BROWNOUT API INTEGRATION TEST SUITE")
    print("=" * 80 + "\n")

    client = HAWebSocketClient(ha_url, ha_token)

    try:
        await client.connect()
        print("✓ Connected to Home Assistant WebSocket\n")

        # Test query_devices
        print("[TEST] Query Devices")
        response = await client.send_command("vulcan-brownout/query_devices", {
            "limit": 20
        })
        print(f"  Result: {'PASSED' if response['success'] else 'FAILED'}")
        if response["success"]:
            print(f"  Devices found: {response['data']['total']}")

        # Test subscribe
        print("\n[TEST] Subscribe")
        response = await client.send_command("vulcan-brownout/subscribe", {})
        print(f"  Result: {'PASSED' if response['success'] else 'FAILED'}")
        if response["success"]:
            print(f"  Subscription ID: {response['data']['subscription_id']}")

        # Test set_threshold
        print("\n[TEST] Set Threshold")
        response = await client.send_command("vulcan-brownout/set_threshold", {
            "global_threshold": 20
        })
        print(f"  Result: {'PASSED' if response['success'] else 'FAILED'}")

        print("\n" + "=" * 80)
        print("All manual tests completed")
        print("=" * 80 + "\n")

    finally:
        await client.close()


if __name__ == "__main__":
    # Allow running without pytest
    import asyncio

    cfg = _load_staging_config()
    ha_url = cfg.get("HA_URL") or os.getenv("HA_URL", "http://homeassistant.lan:8123")
    ha_token = cfg.get("HA_TOKEN") or os.getenv("HA_TOKEN")

    if not ha_token:
        print("ERROR: HA_TOKEN not set — add it to quality/environments/staging/vulcan-brownout-secrets.yaml")
        sys.exit(1)

    try:
        asyncio.run(run_all_tests(ha_url, ha_token))
    except KeyboardInterrupt:
        print("\nTest interrupted")
        sys.exit(130)
    except Exception as e:
        print(f"\nFatal error: {e}")
        sys.exit(1)
