"""Mock Home Assistant WebSocket + REST server for component testing.

Simplified for v6: only query_entities (no params) and subscribe commands.
Returns entities below fixed 15% threshold.
"""

import asyncio
import json
import logging
import uuid
from typing import Any, Dict, Set
from datetime import datetime

from aiohttp import web
import aiohttp_cors

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] mock_ha: %(message)s'
)
logger = logging.getLogger(__name__)

THRESHOLD = 15


class MockHAServer:
    """Mock Home Assistant server."""

    def __init__(self, token: str = "test-token-constant") -> None:
        self.token = token
        self.app = web.Application()
        self.entity_data: Dict[str, Dict[str, Any]] = {}
        self.subscriptions: Dict[str, Set[str]] = {}
        self.control_config: Dict[str, Any] = {}
        self.message_id_counter = 0
        self._setup_routes()

    def _setup_routes(self) -> None:
        self.app.router.add_get("/api/websocket", self._websocket_handler)
        self.app.router.add_get("/api/states", self._get_states)
        self.app.router.add_post("/api/states/{entity_id}", self._set_state)
        self.app.router.add_get("/api/config", self._get_config)
        self.app.router.add_post("/mock/control", self._mock_control)
        self.app.router.add_get("/mock/entities", self._get_mock_entities)

        cors = aiohttp_cors.setup(
            self.app,
            defaults={
                "*": aiohttp_cors.ResourceOptions(
                    allow_credentials=True,
                    expose_headers="*",
                    allow_headers="*",
                    allow_methods="*",
                )
            },
        )

        for route in list(self.app.router.routes()):
            if isinstance(route.resource, web.Resource):
                cors.add(route)

    async def _websocket_handler(self, request: web.Request) -> web.WebSocketResponse:
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        try:
            if not await self._authenticate(ws):
                return ws
            await self._process_messages(ws)
        except Exception as e:
            logger.error("WebSocket error: %s", e)
        finally:
            await ws.close()

        return ws

    async def _authenticate(self, ws: web.WebSocketResponse) -> bool:
        """Handle WebSocket auth handshake. Returns True if auth succeeded."""
        await ws.send_json({
            "type": "auth_required",
            "ha_version": "2024.1.0",
        })

        auth_timeout = self.control_config.get("auth_timeout_ms", 5000) / 1000.0
        try:
            msg = await asyncio.wait_for(ws.receive_json(), timeout=auth_timeout)
        except asyncio.TimeoutError:
            await ws.send_json({"type": "auth_invalid", "message": "Timeout"})
            await ws.close()
            return False

        if msg.get("type") != "auth":
            await ws.send_json({"type": "auth_invalid", "message": "Bad type"})
            await ws.close()
            return False

        auth_failures = self.control_config.get("auth_failures", 0)
        if auth_failures > 0:
            self.control_config["auth_failures"] -= 1
            await ws.send_json({"type": "auth_invalid", "message": "Simulated"})
            await ws.close()
            return False

        if msg.get("access_token") != self.token:
            await ws.send_json({"type": "auth_invalid", "message": "Bad token"})
            await ws.close()
            return False

        await ws.send_json({"type": "auth_ok", "ha_version": "2024.1.0"})
        return True

    async def _process_messages(self, ws: web.WebSocketResponse) -> None:
        """Process WebSocket messages after auth."""
        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                try:
                    command = json.loads(msg.data)
                    await self._handle_command(ws, command)
                except json.JSONDecodeError:
                    await ws.send_json({
                        "type": "result", "success": False,
                        "error": {"code": "invalid_json", "message": "Invalid JSON"},
                    })
            elif msg.type in (web.WSMsgType.CLOSE, web.WSMsgType.ERROR):
                break

    async def _handle_command(
        self, ws: web.WebSocketResponse, command: Dict[str, Any]
    ) -> None:
        cmd_type = command.get("type")
        msg_id = command.get("id")

        delay_ms = self.control_config.get("response_delay_ms", 0)
        if delay_ms > 0:
            await asyncio.sleep(delay_ms / 1000.0)

        if cmd_type == "vulcan-brownout/query_entities":
            await self._handle_query_entities(ws, command)
        elif cmd_type == "vulcan-brownout/subscribe":
            await self._handle_subscribe(ws, command)
        else:
            if msg_id:
                await ws.send_json({
                    "type": "result", "id": msg_id, "success": False,
                    "error": {"code": "unknown_command", "message": f"Unknown: {cmd_type}"},
                })

    async def _handle_query_entities(
        self, ws: web.WebSocketResponse, command: Dict[str, Any]
    ) -> None:
        """Return entities below the fixed 15% threshold, sorted by level asc."""
        msg_id = command.get("id")

        if self.control_config.get("malformed_response", False):
            await ws.send(b"{invalid json")
            return

        entities = []
        for entity_id, entity in sorted(self.entity_data.items()):
            try:
                battery_level = float(entity.get("state", 0))
                available = entity.get("available", True)
                if not available:
                    continue
                if battery_level >= THRESHOLD:
                    continue

                entities.append({
                    "entity_id": entity_id,
                    "state": str(battery_level),
                    "battery_level": battery_level,
                    "device_name": entity.get("friendly_name", entity_id),
                    "status": "critical",
                    "attributes": entity.get("attributes", {}),
                    "last_changed": entity.get("last_changed"),
                    "last_updated": entity.get("last_updated"),
                    "manufacturer": entity.get("manufacturer"),
                    "model": entity.get("model"),
                    "area_name": entity.get("area_name"),
                })
            except (ValueError, TypeError):
                continue

        entities.sort(key=lambda d: d["battery_level"])

        await ws.send_json({
            "type": "result",
            "id": msg_id,
            "success": True,
            "data": {
                "entities": entities,
                "total": len(entities),
            },
        })

    async def _handle_subscribe(
        self, ws: web.WebSocketResponse, command: Dict[str, Any]
    ) -> None:
        msg_id = command.get("id")
        subscription_id = f"sub_{uuid.uuid4().hex[:12]}"
        self.subscriptions[subscription_id] = set(self.entity_data.keys())

        await ws.send_json({
            "type": "result",
            "id": msg_id,
            "success": True,
            "data": {
                "subscription_id": subscription_id,
                "status": "subscribed",
            },
        })

    async def _get_states(self, request: web.Request) -> web.Response:
        states = []
        for entity_id, entity in self.entity_data.items():
            states.append({
                "entity_id": entity_id,
                "state": entity.get("state", "unknown"),
                "attributes": entity.get("attributes", {}),
                "last_changed": entity.get("last_changed"),
                "last_updated": entity.get("last_updated"),
            })
        return web.json_response(states)

    async def _set_state(self, request: web.Request) -> web.Response:
        entity_id = request.match_info["entity_id"]
        data = await request.json()
        state = data.get("state", "unknown")
        attributes = data.get("attributes", {})

        self.entity_data[entity_id] = {
            "state": state,
            "attributes": attributes,
            "available": True,
            "friendly_name": attributes.get("friendly_name", entity_id),
            "last_changed": datetime.utcnow().isoformat() + "Z",
            "last_updated": datetime.utcnow().isoformat() + "Z",
        }

        return web.json_response({
            "entity_id": entity_id, "state": state, "attributes": attributes,
        })

    async def _get_config(self, request: web.Request) -> web.Response:
        return web.json_response({
            "latitude": 0.0, "longitude": 0.0, "elevation": 0,
            "unit_system": {"length": "km", "mass": "kg", "temperature": "C", "volume": "L"},
            "time_zone": "UTC",
            "components": ["frontend", "websocket_api"],
            "version": "2024.1.0",
        })

    async def _mock_control(self, request: web.Request) -> web.Response:
        data = await request.json()

        for key in ("response_delay_ms", "malformed_response", "auth_failures", "auth_timeout_ms"):
            if key in data:
                self.control_config[key] = data[key]

        if "entities" in data:
            self.entity_data.clear()
            for entity in data["entities"]:
                entity_id = entity.get("entity_id", "sensor.unknown")
                self.entity_data[entity_id] = {
                    "state": entity.get("state", "unknown"),
                    "friendly_name": entity.get("friendly_name", entity_id),
                    "attributes": entity.get("attributes", {}),
                    "available": entity.get("available", True),
                    "manufacturer": entity.get("manufacturer"),
                    "model": entity.get("model"),
                    "area_name": entity.get("area_name"),
                    "last_changed": datetime.utcnow().isoformat() + "Z",
                    "last_updated": datetime.utcnow().isoformat() + "Z",
                }
            logger.info("Loaded %d mock entities", len(self.entity_data))

        return web.json_response({
            "status": "configured",
            "entities_count": len(self.entity_data),
        })

    async def _get_mock_entities(self, request: web.Request) -> web.Response:
        entities = [
            {"entity_id": eid, "state": d.get("state"), "friendly_name": d.get("friendly_name")}
            for eid, d in self.entity_data.items()
        ]
        return web.json_response(entities)

    def _next_message_id(self) -> int:
        self.message_id_counter += 1
        return self.message_id_counter

    def run(self, host: str = "0.0.0.0", port: int = 8123) -> None:
        logger.info("Starting mock HA server on %s:%d", host, port)
        web.run_app(self.app, host=host, port=port)


if __name__ == "__main__":
    server = MockHAServer()
    server.run()
