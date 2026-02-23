#!/usr/bin/env python3
"""
Vulcan Brownout Component Test Suite v6.0.0 — Simplified

Tests query_entities (no params) and subscribe commands against the
mock Home Assistant server. Fixed 15% threshold, no filters/sorting.

Usage:
    pytest quality/scripts/test_component_integration.py -v
"""

import json
import logging
import os
from typing import Any, Dict, Optional
import urllib.parse

import pytest
import pytest_asyncio
import websockets
import aiohttp


TEST_HA_URL = os.getenv("HA_URL", "http://localhost:8123")
TEST_HA_TOKEN = os.getenv("HA_TOKEN", "test-token-constant")
MOCK_CONTROL_URL = f"{TEST_HA_URL}/mock/control"

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
        self.ws: Optional[Any] = None
        self.msg_id = 0

    async def connect(self) -> None:
        ws_url = self.ha_url.replace("http://", "ws://").replace("https://", "wss://")
        if not ws_url.endswith("/"):
            ws_url += "/"
        ws_url = urllib.parse.urljoin(ws_url, "api/websocket")

        self.ws = await websockets.connect(ws_url, ping_interval=None)

        msg = json.loads(await self.ws.recv())
        assert msg["type"] == "auth_required"

        await self.ws.send(json.dumps({
            "type": "auth",
            "access_token": self.ha_token
        }))

        msg = json.loads(await self.ws.recv())
        assert msg["type"] == "auth_ok"

    async def send_command(self, command_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        assert self.ws is not None, "Not connected"
        self.msg_id += 1
        payload = {"id": self.msg_id, "type": command_type, **data}
        await self.ws.send(json.dumps(payload))
        response = json.loads(await self.ws.recv())
        return response

    async def close(self) -> None:
        if self.ws:
            await self.ws.close()


class MockHAController:
    """Control mock HA behavior via HTTP."""

    def __init__(self, mock_control_url: str = MOCK_CONTROL_URL):
        self.mock_control_url = mock_control_url
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, *args):
        if self.session:
            await self.session.close()

    async def setup_entities(self, entities: list) -> None:
        assert self.session is not None, "Not initialized"
        async with self.session.post(
            self.mock_control_url,
            json={"entities": entities}
        ) as resp:
            assert resp.status == 200


@pytest_asyncio.fixture
async def mock_ha():
    async with MockHAController() as controller:
        yield controller


@pytest_asyncio.fixture
async def ws_client(mock_ha):
    from .mock_fixtures import get_fixture_entities
    entities = get_fixture_entities()
    await mock_ha.setup_entities(entities)

    client = HAWebSocketClient(TEST_HA_URL, TEST_HA_TOKEN)
    await client.connect()
    yield client
    await client.close()


class TestQueryEntities:
    """Test vulcan-brownout/query_entities — no params, returns low-battery entities."""

    @pytest.mark.asyncio
    async def test_query_entities_basic(self, ws_client):
        response = await ws_client.send_command("vulcan-brownout/query_entities", {})

        assert response["type"] == "result"
        assert response["success"] is True
        assert "data" in response

        data = response["data"]
        assert "entities" in data
        assert "total" in data
        assert isinstance(data["entities"], list)
        assert isinstance(data["total"], int)

    @pytest.mark.asyncio
    async def test_query_entities_only_below_threshold(self, ws_client):
        """All returned entities should have battery_level < 15."""
        response = await ws_client.send_command("vulcan-brownout/query_entities", {})
        assert response["success"] is True

        for device in response["data"]["entities"]:
            assert device["battery_level"] < 15, (
                f"{device['entity_id']} has level {device['battery_level']}"
            )

    @pytest.mark.asyncio
    async def test_query_entities_sorted_by_level(self, ws_client):
        """Entities should be sorted by battery level ascending."""
        response = await ws_client.send_command("vulcan-brownout/query_entities", {})
        assert response["success"] is True

        devices = response["data"]["entities"]
        levels = [d["battery_level"] for d in devices]
        assert levels == sorted(levels)

    @pytest.mark.asyncio
    async def test_query_entities_entity_structure(self, ws_client):
        response = await ws_client.send_command("vulcan-brownout/query_entities", {})
        assert response["success"] is True

        devices = response["data"]["entities"]
        if devices:
            device = devices[0]
            assert "entity_id" in device
            assert "battery_level" in device
            assert "status" in device
            assert "device_name" in device
            assert device["status"] == "critical"

    @pytest.mark.asyncio
    async def test_query_entities_all_critical(self, ws_client):
        """All returned entities should have status=critical."""
        response = await ws_client.send_command("vulcan-brownout/query_entities", {})
        assert response["success"] is True

        for device in response["data"]["entities"]:
            assert device["status"] == "critical"


class TestSubscribe:
    """Test vulcan-brownout/subscribe."""

    @pytest.mark.asyncio
    async def test_subscribe_basic(self, ws_client):
        response = await ws_client.send_command("vulcan-brownout/subscribe", {})

        assert response["type"] == "result"
        assert response["success"] is True
        assert "data" in response

        data = response["data"]
        assert "subscription_id" in data
        assert data["status"] == "subscribed"
        assert data["subscription_id"].startswith("sub_")

    @pytest.mark.asyncio
    async def test_subscribe_multiple(self, ws_client):
        r1 = await ws_client.send_command("vulcan-brownout/subscribe", {})
        r2 = await ws_client.send_command("vulcan-brownout/subscribe", {})

        assert r1["success"] is True
        assert r2["success"] is True
        assert r1["data"]["subscription_id"] != r2["data"]["subscription_id"]


class TestErrorHandling:
    """Test error handling."""

    @pytest.mark.asyncio
    async def test_empty_entity_list(self, mock_ha):
        await mock_ha.setup_entities([])

        client = HAWebSocketClient(TEST_HA_URL, TEST_HA_TOKEN)
        await client.connect()

        response = await client.send_command("vulcan-brownout/query_entities", {})

        assert response["success"] is True
        assert response["data"]["total"] == 0
        assert response["data"]["entities"] == []

        await client.close()

    @pytest.mark.asyncio
    async def test_unknown_command(self, ws_client):
        """Unknown commands should return an error."""
        response = await ws_client.send_command("vulcan-brownout/nonexistent", {})
        assert response["success"] is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
