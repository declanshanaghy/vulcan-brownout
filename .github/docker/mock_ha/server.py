"""Mock Home Assistant WebSocket + REST server for component testing.

This server simulates Home Assistant's API endpoints and WebSocket protocol,
allowing the vulcan_brownout integration to be tested without a real HA instance.

It implements:
- WebSocket endpoint at /api/websocket with HA auth handshake
- REST endpoints at /api/states and /api/config
- Mock control endpoint at /mock/control for error injection

The mock is fully configurable via control requests to allow testing of error
scenarios, timeouts, malformed responses, etc.
"""

import asyncio
import json
import logging
import uuid
from typing import Any, Dict, Optional, Set
from datetime import datetime

from aiohttp import web
import aiohttp_cors

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] mock_ha: %(message)s'
)
logger = logging.getLogger(__name__)


class MockHAServer:
    """Mock Home Assistant server."""

    def __init__(self, token: str = "test-token-constant") -> None:
        """Initialize mock HA server.

        Args:
            token: Authentication token required for WebSocket connection
        """
        self.token = token
        self.app = web.Application()
        self.entity_data: Dict[str, Dict[str, Any]] = {}
        self.subscriptions: Dict[str, Set[str]] = {}
        self.control_config: Dict[str, Any] = {}
        self.message_id_counter = 0

        # Setup routes
        self._setup_routes()

    def _setup_routes(self) -> None:
        """Setup HTTP and WebSocket routes."""
        # WebSocket endpoint
        self.app.router.add_get("/api/websocket", self._websocket_handler)

        # REST endpoints
        self.app.router.add_get("/api/states", self._get_states)
        self.app.router.add_post("/api/states/{entity_id}", self._set_state)
        self.app.router.add_get("/api/config", self._get_config)

        # Mock control endpoint (test-only)
        self.app.router.add_post("/mock/control", self._mock_control)
        self.app.router.add_get("/mock/entities", self._get_mock_entities)

        # CORS support
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

        # Configure CORS on all routes
        for route in list(self.app.router.routes()):
            if isinstance(route.resource, web.Resource):
                cors.add(route)

    async def _websocket_handler(self, request: web.Request) -> web.WebSocketResponse:
        """Handle WebSocket connections with HA protocol."""
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        try:
            # Send auth_required message
            msg_id = self._next_message_id()
            await ws.send_json({
                "type": "auth_required",
                "ha_version": "2024.1.0",
            })

            # Wait for auth message
            auth_timeout = self.control_config.get("auth_timeout_ms", 5000) / 1000.0
            try:
                msg = await asyncio.wait_for(ws.receive_json(), timeout=auth_timeout)
            except asyncio.TimeoutError:
                logger.warning("Auth timeout")
                await ws.send_json({
                    "type": "auth_invalid",
                    "message": "Authentication timeout",
                })
                await ws.close()
                return ws

            # Check auth
            if msg.get("type") != "auth":
                logger.warning(f"Invalid auth message type: {msg.get('type')}")
                await ws.send_json({
                    "type": "auth_invalid",
                    "message": "Invalid auth message type",
                })
                await ws.close()
                return ws

            token = msg.get("access_token")

            # Check if we should simulate auth failure
            auth_failures_remaining = self.control_config.get("auth_failures", 0)
            if auth_failures_remaining > 0:
                self.control_config["auth_failures"] -= 1
                logger.info("Simulating auth failure")
                await ws.send_json({
                    "type": "auth_invalid",
                    "message": "Invalid authentication token",
                })
                await ws.close()
                return ws

            # Verify token
            if token != self.token:
                logger.warning(f"Invalid token: {token}")
                await ws.send_json({
                    "type": "auth_invalid",
                    "message": "Invalid authentication token",
                })
                await ws.close()
                return ws

            # Send auth_ok
            await ws.send_json({
                "type": "auth_ok",
                "ha_version": "2024.1.0",
            })

            logger.info("WebSocket authenticated")

            # Handle commands
            async for msg in ws:
                if msg.type == web.WSMsgType.TEXT:
                    try:
                        command = json.loads(msg.data)
                        await self._handle_websocket_command(ws, command)
                    except json.JSONDecodeError:
                        logger.warning("Invalid JSON in WebSocket message")
                        await ws.send_json({
                            "type": "result",
                            "success": False,
                            "error": {"code": "invalid_json", "message": "Invalid JSON"},
                        })
                    except Exception as e:
                        logger.error(f"Error handling command: {e}")

                elif msg.type in (web.WSMsgType.CLOSE, web.WSMsgType.ERROR):
                    break

        except Exception as e:
            logger.error(f"WebSocket error: {e}")
        finally:
            await ws.close()

        return ws

    async def _handle_websocket_command(
        self, ws: web.WebSocketResponse, command: Dict[str, Any]
    ) -> None:
        """Handle WebSocket command from client.

        Args:
            ws: WebSocket connection
            command: Command dictionary with type and parameters
        """
        command_type = command.get("type")
        msg_id = command.get("id")

        logger.debug(f"Received command: {command_type} (id={msg_id})")

        # Check for simulated connection drops
        connection_drops = self.control_config.get("connection_drops", [])
        if msg_id in connection_drops:
            logger.info(f"Simulating connection drop for message {msg_id}")
            await ws.close()
            return

        # Check for simulated response delays
        delay_ms = self.control_config.get("response_delay_ms", 0)
        if delay_ms > 0:
            await asyncio.sleep(delay_ms / 1000.0)

        if command_type == "vulcan-brownout/query_devices":
            await self._handle_query_devices(ws, command)
        elif command_type == "vulcan-brownout/subscribe":
            await self._handle_subscribe(ws, command)
        elif command_type == "vulcan-brownout/set_threshold":
            await self._handle_set_threshold(ws, command)
        else:
            logger.warning(f"Unknown command type: {command_type}")
            if msg_id:
                await ws.send_json({
                    "type": "result",
                    "id": msg_id,
                    "success": False,
                    "error": {"code": "unknown_command", "message": f"Unknown command: {command_type}"},
                })

    async def _handle_query_devices(
        self, ws: web.WebSocketResponse, command: Dict[str, Any]
    ) -> None:
        """Handle vulcan-brownout/query_devices command.

        Args:
            ws: WebSocket connection
            command: Command with limit, offset, sort parameters
        """
        msg_id = command.get("id")
        limit = min(command.get("limit", 50), 100)
        offset = command.get("offset", 0)

        # Check for malformed response simulation
        if self.control_config.get("malformed_response", False):
            logger.info("Sending malformed JSON response")
            await ws.send(b"{invalid json")
            return

        # Build device list from entity data
        devices = []
        for entity_id, entity in sorted(self.entity_data.items()):
            try:
                battery_level = float(entity.get("state", 0))
                available = entity.get("available", True)

                # Determine status
                threshold = 15  # default
                if battery_level < threshold:
                    status = "critical"
                elif battery_level < (threshold + 10):
                    status = "warning"
                else:
                    status = "healthy"

                if not available:
                    status = "unavailable"

                devices.append({
                    "entity_id": entity_id,
                    "state": str(battery_level),
                    "battery_level": battery_level,
                    "device_name": entity.get("friendly_name", entity_id),
                    "available": available,
                    "status": status,
                    "attributes": entity.get("attributes", {}),
                    "last_changed": entity.get("last_changed"),
                    "last_updated": entity.get("last_updated"),
                })
            except (ValueError, TypeError):
                logger.warning(f"Could not parse device {entity_id}")
                continue

        # Apply pagination
        total = len(devices)
        paginated = devices[offset : offset + limit]

        # Send response
        await ws.send_json({
            "type": "result",
            "id": msg_id,
            "success": True,
            "data": {
                "devices": paginated,
                "total": total,
                "offset": offset,
                "limit": limit,
                "has_more": (offset + limit) < total,
                "next_cursor": None,
                "device_statuses": self._calculate_statuses(devices),
            },
        })

    async def _handle_subscribe(
        self, ws: web.WebSocketResponse, command: Dict[str, Any]
    ) -> None:
        """Handle vulcan-brownout/subscribe command.

        Args:
            ws: WebSocket connection
            command: Subscribe command
        """
        msg_id = command.get("id")
        subscription_id = f"sub_{uuid.uuid4().hex[:12]}"

        # Track subscription
        entity_ids = list(self.entity_data.keys())
        self.subscriptions[subscription_id] = set(entity_ids)

        await ws.send_json({
            "type": "result",
            "id": msg_id,
            "success": True,
            "data": {
                "subscription_id": subscription_id,
                "status": "subscribed",
            },
        })

        logger.info(f"New subscription: {subscription_id}")

    async def _handle_set_threshold(
        self, ws: web.WebSocketResponse, command: Dict[str, Any]
    ) -> None:
        """Handle vulcan-brownout/set_threshold command.

        Args:
            ws: WebSocket connection
            command: Set threshold command with global_threshold and device_rules
        """
        msg_id = command.get("id")
        global_threshold = command.get("global_threshold")
        device_rules = command.get("device_rules", {})

        # Validate
        if global_threshold is not None:
            if not (5 <= global_threshold <= 100):
                await ws.send_json({
                    "type": "result",
                    "id": msg_id,
                    "success": False,
                    "error": {"code": "invalid_threshold", "message": "Threshold out of range"},
                })
                return

        # Validate device rules
        for entity_id in device_rules.keys():
            if entity_id not in self.entity_data:
                await ws.send_json({
                    "type": "result",
                    "id": msg_id,
                    "success": False,
                    "error": {"code": "invalid_device_rule", "message": f"Device {entity_id} not found"},
                })
                return

        await ws.send_json({
            "type": "result",
            "id": msg_id,
            "success": True,
            "data": {
                "message": "Thresholds updated",
                "global_threshold": global_threshold or 15,
                "device_rules": device_rules,
            },
        })

        logger.info(f"Threshold updated: global={global_threshold}, rules={len(device_rules)}")

    async def _get_states(self, request: web.Request) -> web.Response:
        """GET /api/states - return all entities."""
        try:
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
        except Exception as e:
            logger.error(f"Error in GET /api/states: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def _set_state(self, request: web.Request) -> web.Response:
        """POST /api/states/{entity_id} - create or update entity."""
        try:
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

            logger.info(f"Created/updated entity: {entity_id} = {state}")

            return web.json_response({
                "entity_id": entity_id,
                "state": state,
                "attributes": attributes,
            })
        except Exception as e:
            logger.error(f"Error in POST /api/states: {e}")
            return web.json_response({"error": str(e)}, status=400)

    async def _get_config(self, request: web.Request) -> web.Response:
        """GET /api/config - return mock HA config."""
        try:
            return web.json_response({
                "latitude": 0.0,
                "longitude": 0.0,
                "elevation": 0,
                "unit_system": {"length": "km", "mass": "kg", "temperature": "°C", "volume": "L"},
                "time_zone": "UTC",
                "components": ["frontend", "websocket_api"],
                "config_dir": "/config",
                "state_dir": None,
                "recovery_mode": False,
                "allowlist_external_dirs": [],
                "allowlist_external_urls": [],
                "version": "2024.1.0",
                "debug": False,
                "skip_pip": False,
                "pip_freeze": [],
            })
        except Exception as e:
            logger.error(f"Error in GET /api/config: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def _mock_control(self, request: web.Request) -> web.Response:
        """POST /mock/control - configure mock behavior.

        Allows tests to inject errors, set delays, simulate connection drops, etc.

        Example request body:
        {
            "response_delay_ms": 100,
            "malformed_response": false,
            "auth_failures": 0,
            "connection_drops": [],
            "entities": [
                {"entity_id": "sensor.test_battery_1", "state": "95", "friendly_name": "Test Battery 1"}
            ]
        }
        """
        try:
            data = await request.json()

            # Update control config
            if "response_delay_ms" in data:
                self.control_config["response_delay_ms"] = data["response_delay_ms"]
            if "malformed_response" in data:
                self.control_config["malformed_response"] = data["malformed_response"]
            if "auth_failures" in data:
                self.control_config["auth_failures"] = data["auth_failures"]
            if "connection_drops" in data:
                self.control_config["connection_drops"] = data["connection_drops"]
            if "auth_timeout_ms" in data:
                self.control_config["auth_timeout_ms"] = data["auth_timeout_ms"]

            # Load entities if provided
            if "entities" in data:
                self.entity_data.clear()
                for entity in data["entities"]:
                    entity_id = entity.get("entity_id", "sensor.unknown")
                    self.entity_data[entity_id] = {
                        "state": entity.get("state", "unknown"),
                        "friendly_name": entity.get("friendly_name", entity_id),
                        "attributes": entity.get("attributes", {}),
                        "available": entity.get("available", True),
                        "last_changed": datetime.utcnow().isoformat() + "Z",
                        "last_updated": datetime.utcnow().isoformat() + "Z",
                    }
                logger.info(f"Loaded {len(self.entity_data)} mock entities")

            return web.json_response({
                "status": "configured",
                "config": self.control_config,
                "entities_count": len(self.entity_data),
            })
        except Exception as e:
            logger.error(f"Error in POST /mock/control: {e}")
            return web.json_response({"error": str(e)}, status=400)

    async def _get_mock_entities(self, request: web.Request) -> web.Response:
        """GET /mock/entities - return current mock entities."""
        try:
            entities = []
            for entity_id, data in self.entity_data.items():
                entities.append({
                    "entity_id": entity_id,
                    "state": data.get("state"),
                    "friendly_name": data.get("friendly_name"),
                    "available": data.get("available"),
                })
            return web.json_response(entities)
        except Exception as e:
            logger.error(f"Error in GET /mock/entities: {e}")
            return web.json_response({"error": str(e)}, status=500)

    def _next_message_id(self) -> int:
        """Get next unique message ID."""
        self.message_id_counter += 1
        return self.message_id_counter

    def _calculate_statuses(self, devices: list) -> Dict[str, int]:
        """Calculate device status counts."""
        statuses = {
            "critical": 0,
            "warning": 0,
            "healthy": 0,
            "unavailable": 0,
        }

        for device in devices:
            statuses[device.get("status", "healthy")] += 1

        return statuses

    def run(self, host: str = "0.0.0.0", port: int = 8123) -> None:
        """Run the mock server.

        Args:
            host: Host to bind to
            port: Port to listen on
        """
        logger.info(f"Starting mock HA server on {host}:{port}")
        web.run_app(self.app, host=host, port=port)


if __name__ == "__main__":
    server = MockHAServer()
    server.run()
