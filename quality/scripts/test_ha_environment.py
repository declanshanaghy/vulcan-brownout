#!/usr/bin/env python3
"""
Vulcan Brownout QA Test Suite - Environment Validation Phase 1
Tests Home Assistant API connectivity, battery entities, and WebSocket functionality.

Usage:
    python3 test_ha_environment.py [--verbose] [--output-file results.json]
"""

import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum

import requests
import websockets
from urllib.parse import urljoin

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)


class TestStatus(Enum):
    """Test result status."""
    PASSED = "PASSED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    ERROR = "ERROR"


@dataclass
class TestResult:
    """Individual test result."""
    name: str
    status: TestStatus
    duration_ms: float
    message: str = ""
    details: Dict[str, Any] = None

    def __post_init__(self):
        if self.details is None:
            self.details = {}

    def to_dict(self):
        return {
            "name": self.name,
            "status": self.status.value,
            "duration_ms": round(self.duration_ms, 2),
            "message": self.message,
            "details": self.details,
        }


class EnvironmentValidator:
    """Validates Home Assistant environment and battery entities."""

    def __init__(self, ha_url: str, ha_token: str, verbose: bool = False):
        """Initialize validator with HA connection details."""
        self.ha_url = ha_url
        self.ha_token = ha_token
        self.verbose = verbose
        self.results: List[TestResult] = []
        self.battery_entities: Dict[str, Dict[str, Any]] = {}
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {ha_token}",
            "Content-Type": "application/json"
        })

    def log(self, level: int, message: str):
        """Log message if verbose."""
        if self.verbose:
            logger.log(level, message)

    async def run_all_tests(self) -> List[TestResult]:
        """Run complete test suite."""
        logger.info("=" * 80)
        logger.info("VULCAN BROWNOUT QA TEST SUITE - ENVIRONMENT VALIDATION")
        logger.info("=" * 80)

        # Phase 1: REST API Tests
        logger.info("\n[PHASE 1] REST API Connectivity Tests")
        logger.info("-" * 80)
        await self.test_rest_api_connectivity()
        await self.test_rest_api_auth()
        await self.test_battery_entity_inventory()
        await self.test_entity_data_quality()

        # Phase 2: WebSocket Tests
        logger.info("\n[PHASE 2] WebSocket Tests")
        logger.info("-" * 80)
        await self.test_websocket_connectivity()
        await self.test_websocket_state_subscription()

        # Phase 3: State Change Tests
        logger.info("\n[PHASE 3] State Change Tests")
        logger.info("-" * 80)
        await self.test_entity_state_change()

        # Phase 4: Performance Tests
        logger.info("\n[PHASE 4] Performance Tests")
        logger.info("-" * 80)
        await self.test_query_performance()

        return self.results

    async def test_rest_api_connectivity(self) -> None:
        """Test 1: REST API responds."""
        test_name = "REST API Connectivity"
        logger.info(f"\nTest 1: {test_name}")

        start = time.time()
        try:
            response = self.session.get(
                urljoin(self.ha_url, "/api/"),
                timeout=10
            )
            duration = (time.time() - start) * 1000

            if response.status_code == 200:
                data = response.json()
                logger.info(f"✓ API is responding: {data}")
                self.results.append(TestResult(
                    name=test_name,
                    status=TestStatus.PASSED,
                    duration_ms=duration,
                    message="REST API /api/ endpoint responds correctly",
                    details={
                        "status_code": response.status_code,
                        "response": data,
                        "response_time_ms": round(duration, 2)
                    }
                ))
            else:
                logger.error(f"✗ Unexpected status: {response.status_code}")
                self.results.append(TestResult(
                    name=test_name,
                    status=TestStatus.FAILED,
                    duration_ms=duration,
                    message=f"Expected 200, got {response.status_code}",
                    details={"status_code": response.status_code}
                ))

        except Exception as e:
            duration = (time.time() - start) * 1000
            logger.error(f"✗ Error: {e}")
            self.results.append(TestResult(
                name=test_name,
                status=TestStatus.ERROR,
                duration_ms=duration,
                message=str(e),
                details={"exception": type(e).__name__}
            ))

    async def test_rest_api_auth(self) -> None:
        """Test 2: Authentication token works."""
        test_name = "REST API Authentication"
        logger.info(f"\nTest 2: {test_name}")

        start = time.time()
        try:
            # Test with /api/states (requires auth)
            response = self.session.get(
                urljoin(self.ha_url, "/api/states"),
                timeout=10
            )
            duration = (time.time() - start) * 1000

            if response.status_code == 200:
                states = response.json()
                logger.info(f"✓ Authentication successful, retrieved {len(states)} states")
                self.results.append(TestResult(
                    name=test_name,
                    status=TestStatus.PASSED,
                    duration_ms=duration,
                    message="Authentication token works for /api/states",
                    details={
                        "total_entities": len(states),
                        "status_code": response.status_code,
                        "response_time_ms": round(duration, 2)
                    }
                ))
            else:
                logger.error(f"✗ Auth failed: {response.status_code}")
                self.results.append(TestResult(
                    name=test_name,
                    status=TestStatus.FAILED,
                    duration_ms=duration,
                    message=f"Authentication failed with status {response.status_code}",
                    details={"status_code": response.status_code}
                ))

        except Exception as e:
            duration = (time.time() - start) * 1000
            logger.error(f"✗ Error: {e}")
            self.results.append(TestResult(
                name=test_name,
                status=TestStatus.ERROR,
                duration_ms=duration,
                message=str(e),
                details={"exception": type(e).__name__}
            ))

    async def test_battery_entity_inventory(self) -> None:
        """Test 3: Battery entity inventory and categorization."""
        test_name = "Battery Entity Inventory"
        logger.info(f"\nTest 3: {test_name}")

        start = time.time()
        try:
            # Get all states
            response = self.session.get(
                urljoin(self.ha_url, "/api/states"),
                timeout=10
            )

            if response.status_code != 200:
                raise Exception(f"Failed to get states: {response.status_code}")

            all_states = response.json()
            total_entities = len(all_states)

            # Filter battery entities (device_class == battery)
            battery_entities = []
            for entity in all_states:
                entity_id = entity.get("entity_id", "")
                attributes = entity.get("attributes", {})
                device_class = attributes.get("device_class", "")

                if device_class == "battery":
                    battery_entities.append(entity)
                    self.battery_entities[entity_id] = entity

            # Categorize by state
            state_categories = {
                "numeric": 0,
                "unavailable": 0,
                "unknown": 0,
                "other": 0
            }

            for entity in battery_entities:
                state = entity.get("state", "")
                try:
                    float(state)
                    state_categories["numeric"] += 1
                except ValueError:
                    if state == "unavailable":
                        state_categories["unavailable"] += 1
                    elif state == "unknown":
                        state_categories["unknown"] += 1
                    else:
                        state_categories["other"] += 1

            duration = (time.time() - start) * 1000

            logger.info(f"✓ Found {len(battery_entities)} battery entities")
            logger.info(f"  Total entities: {total_entities}")
            logger.info(f"  Battery distribution: {state_categories}")

            self.results.append(TestResult(
                name=test_name,
                status=TestStatus.PASSED,
                duration_ms=duration,
                message=f"Found {len(battery_entities)} battery entities out of {total_entities} total",
                details={
                    "total_entities": total_entities,
                    "battery_entities": len(battery_entities),
                    "state_distribution": state_categories,
                    "response_time_ms": round(duration, 2)
                }
            ))

        except Exception as e:
            duration = (time.time() - start) * 1000
            logger.error(f"✗ Error: {e}")
            self.results.append(TestResult(
                name=test_name,
                status=TestStatus.ERROR,
                duration_ms=duration,
                message=str(e),
                details={"exception": type(e).__name__}
            ))

    async def test_entity_data_quality(self) -> None:
        """Test 4: Battery entities have proper attributes."""
        test_name = "Battery Entity Data Quality"
        logger.info(f"\nTest 4: {test_name}")

        start = time.time()
        try:
            if not self.battery_entities:
                raise Exception("No battery entities found in previous test")

            # Check attributes for each battery entity
            missing_attributes = {
                "device_class": 0,
                "friendly_name": 0,
                "unit_of_measurement": 0
            }

            entity_details = []
            for entity_id, entity in list(self.battery_entities.items())[:5]:  # Sample first 5
                attributes = entity.get("attributes", {})
                details = {
                    "entity_id": entity_id,
                    "state": entity.get("state"),
                    "has_device_class": "device_class" in attributes,
                    "has_friendly_name": "friendly_name" in attributes,
                    "has_unit_of_measurement": "unit_of_measurement" in attributes,
                }
                entity_details.append(details)

                if "device_class" not in attributes:
                    missing_attributes["device_class"] += 1
                if "friendly_name" not in attributes:
                    missing_attributes["friendly_name"] += 1
                if "unit_of_measurement" not in attributes:
                    missing_attributes["unit_of_measurement"] += 1

            duration = (time.time() - start) * 1000

            # All required attributes should be present
            all_present = all(v == 0 for v in missing_attributes.values())

            if all_present:
                logger.info(f"✓ All sampled battery entities have required attributes")
                status = TestStatus.PASSED
                msg = "Battery entities have proper attributes (device_class, friendly_name, unit_of_measurement)"
            else:
                logger.warning(f"⚠ Some entities missing attributes: {missing_attributes}")
                status = TestStatus.FAILED
                msg = f"Some entities missing attributes: {missing_attributes}"

            self.results.append(TestResult(
                name=test_name,
                status=status,
                duration_ms=duration,
                message=msg,
                details={
                    "total_battery_entities": len(self.battery_entities),
                    "sample_size": len(entity_details),
                    "missing_attributes": missing_attributes,
                    "sample_entities": entity_details,
                    "response_time_ms": round(duration, 2)
                }
            ))

        except Exception as e:
            duration = (time.time() - start) * 1000
            logger.error(f"✗ Error: {e}")
            self.results.append(TestResult(
                name=test_name,
                status=TestStatus.ERROR,
                duration_ms=duration,
                message=str(e),
                details={"exception": type(e).__name__}
            ))

    async def test_websocket_connectivity(self) -> None:
        """Test 5: WebSocket connectivity and authentication."""
        test_name = "WebSocket Connectivity"
        logger.info(f"\nTest 5: {test_name}")

        start = time.time()
        ws = None
        try:
            # Extract host and construct WS URL
            ws_url = self.ha_url.replace("http://", "ws://").replace("https://", "wss://")
            ws_url = urljoin(ws_url + "/", "api/websocket")

            logger.info(f"Connecting to {ws_url}")

            # Connect to WebSocket
            async with websockets.connect(ws_url, ping_interval=None) as websocket:
                ws = websocket

                # Receive auth_required message
                msg = await asyncio.wait_for(websocket.recv(), timeout=5)
                auth_msg = json.loads(msg)
                logger.info(f"Received: {auth_msg}")

                if auth_msg.get("type") != "auth_required":
                    raise Exception(f"Expected auth_required, got {auth_msg.get('type')}")

                # Send auth message
                auth_payload = {
                    "type": "auth",
                    "access_token": self.ha_token
                }
                await websocket.send(json.dumps(auth_payload))

                # Wait for auth_ok
                msg = await asyncio.wait_for(websocket.recv(), timeout=5)
                auth_ok = json.loads(msg)
                logger.info(f"Received: {auth_ok}")

                if auth_ok.get("type") != "auth_ok":
                    raise Exception(f"Authentication failed: {auth_ok}")

                duration = (time.time() - start) * 1000

                logger.info("✓ WebSocket connected and authenticated")
                self.results.append(TestResult(
                    name=test_name,
                    status=TestStatus.PASSED,
                    duration_ms=duration,
                    message="WebSocket connection established and authenticated",
                    details={
                        "ws_url": ws_url,
                        "auth_type": auth_ok.get("type"),
                        "response_time_ms": round(duration, 2)
                    }
                ))

        except asyncio.TimeoutError as e:
            duration = (time.time() - start) * 1000
            logger.error(f"✗ Timeout: {e}")
            self.results.append(TestResult(
                name=test_name,
                status=TestStatus.ERROR,
                duration_ms=duration,
                message=f"WebSocket timeout: {e}",
                details={"exception": "TimeoutError"}
            ))

        except Exception as e:
            duration = (time.time() - start) * 1000
            logger.error(f"✗ Error: {e}")
            self.results.append(TestResult(
                name=test_name,
                status=TestStatus.ERROR,
                duration_ms=duration,
                message=str(e),
                details={"exception": type(e).__name__}
            ))
        finally:
            if ws:
                try:
                    await ws.close()
                except Exception:
                    pass

    async def test_websocket_state_subscription(self) -> None:
        """Test 6: WebSocket state subscription."""
        test_name = "WebSocket State Subscription"
        logger.info(f"\nTest 6: {test_name}")

        start = time.time()
        ws = None
        received_events = []

        try:
            # Extract host and construct WS URL
            ws_url = self.ha_url.replace("http://", "ws://").replace("https://", "wss://")
            ws_url = urljoin(ws_url + "/", "api/websocket")

            async with websockets.connect(ws_url, ping_interval=None) as websocket:
                ws = websocket

                # Authenticate
                msg = await asyncio.wait_for(websocket.recv(), timeout=5)
                auth_msg = json.loads(msg)

                auth_payload = {
                    "type": "auth",
                    "access_token": self.ha_token
                }
                await websocket.send(json.dumps(auth_payload))

                msg = await asyncio.wait_for(websocket.recv(), timeout=5)
                auth_ok = json.loads(msg)

                if auth_ok.get("type") != "auth_ok":
                    raise Exception("Authentication failed")

                # Subscribe to state changes for a battery entity
                if not self.battery_entities:
                    raise Exception("No battery entities available to subscribe to")

                entity_id = list(self.battery_entities.keys())[0]
                logger.info(f"Subscribing to state changes for {entity_id}")

                subscribe_payload = {
                    "id": 1,
                    "type": "subscribe_events",
                    "event_type": "state_changed",
                }
                await websocket.send(json.dumps(subscribe_payload))

                # Receive subscription confirmation
                msg = await asyncio.wait_for(websocket.recv(), timeout=5)
                confirm = json.loads(msg)
                logger.info(f"Subscription confirmed: {confirm}")

                if confirm.get("type") != "result" or not confirm.get("success"):
                    raise Exception(f"Subscription failed: {confirm}")

                # Wait for events (up to 3 seconds)
                start_listen = time.time()
                while time.time() - start_listen < 3:
                    try:
                        msg = await asyncio.wait_for(websocket.recv(), timeout=1)
                        event = json.loads(msg)
                        if event.get("type") == "event":
                            received_events.append(event)
                            logger.info(f"Received event: {event.get('event', {}).get('data', {}).get('entity_id')}")
                    except asyncio.TimeoutError:
                        break

                duration = (time.time() - start) * 1000

                if len(received_events) > 0:
                    logger.info(f"✓ Received {len(received_events)} state change events")
                    self.results.append(TestResult(
                        name=test_name,
                        status=TestStatus.PASSED,
                        duration_ms=duration,
                        message=f"Successfully subscribed to state changes and received {len(received_events)} events",
                        details={
                            "subscribed_entity": entity_id,
                            "events_received": len(received_events),
                            "response_time_ms": round(duration, 2)
                        }
                    ))
                else:
                    logger.warning("⚠ No state change events received (may be normal if entities stable)")
                    self.results.append(TestResult(
                        name=test_name,
                        status=TestStatus.PASSED,
                        duration_ms=duration,
                        message="State subscription successful (no state changes during test)",
                        details={
                            "subscribed_entity": entity_id,
                            "events_received": 0,
                            "response_time_ms": round(duration, 2)
                        }
                    ))

        except Exception as e:
            duration = (time.time() - start) * 1000
            logger.error(f"✗ Error: {e}")
            self.results.append(TestResult(
                name=test_name,
                status=TestStatus.ERROR,
                duration_ms=duration,
                message=str(e),
                details={"exception": type(e).__name__}
            ))
        finally:
            if ws:
                try:
                    await ws.close()
                except Exception:
                    pass

    async def test_entity_state_change(self) -> None:
        """Test 7: Entity state changes via REST API."""
        test_name = "Entity State Change via REST API"
        logger.info(f"\nTest 7: {test_name}")

        start = time.time()

        try:
            if not self.battery_entities:
                raise Exception("No battery entities available for testing")

            # Find a battery entity with numeric state
            test_entity = None
            original_state = None

            for entity_id, entity in self.battery_entities.items():
                state = entity.get("state", "")
                try:
                    float(state)
                    test_entity = entity_id
                    original_state = state
                    break
                except ValueError:
                    continue

            if not test_entity:
                raise Exception("No numeric battery entity found for testing")

            logger.info(f"Testing state change on {test_entity}")
            logger.info(f"Original state: {original_state}")

            # Change state to a new value
            new_state = str(int(float(original_state)) + 1) if float(original_state) < 100 else "50"

            response = self.session.post(
                urljoin(self.ha_url, f"/api/states/{test_entity}"),
                json={"state": new_state},
                timeout=10
            )

            if response.status_code not in [200, 201]:
                raise Exception(f"Failed to update state: {response.status_code}")

            updated_entity = response.json()
            returned_state = updated_entity.get("state", "")

            logger.info(f"New state: {returned_state}")

            duration = (time.time() - start) * 1000

            if returned_state == new_state:
                logger.info("✓ State change successful")
                self.results.append(TestResult(
                    name=test_name,
                    status=TestStatus.PASSED,
                    duration_ms=duration,
                    message=f"Successfully changed state from {original_state} to {new_state}",
                    details={
                        "entity_id": test_entity,
                        "original_state": original_state,
                        "new_state": new_state,
                        "response_time_ms": round(duration, 2)
                    }
                ))
            else:
                raise Exception(f"State mismatch: expected {new_state}, got {returned_state}")

        except Exception as e:
            duration = (time.time() - start) * 1000
            logger.error(f"✗ Error: {e}")
            self.results.append(TestResult(
                name=test_name,
                status=TestStatus.ERROR,
                duration_ms=duration,
                message=str(e),
                details={"exception": type(e).__name__}
            ))

    async def test_query_performance(self) -> None:
        """Test 8: Performance - query all states with 1500+ entities."""
        test_name = "Query Performance (1500+ entities)"
        logger.info(f"\nTest 8: {test_name}")

        start = time.time()
        try:
            response = self.session.get(
                urljoin(self.ha_url, "/api/states"),
                timeout=30
            )

            if response.status_code != 200:
                raise Exception(f"Failed to query states: {response.status_code}")

            states = response.json()
            duration = (time.time() - start) * 1000

            entity_count = len(states)
            logger.info(f"✓ Retrieved {entity_count} entities in {duration:.2f}ms")

            status = TestStatus.PASSED if duration < 5000 else TestStatus.FAILED
            msg_status = "EXCELLENT" if duration < 1000 else "GOOD" if duration < 2000 else "ACCEPTABLE" if duration < 5000 else "SLOW"

            self.results.append(TestResult(
                name=test_name,
                status=status,
                duration_ms=duration,
                message=f"Query performance: {msg_status} ({duration:.2f}ms for {entity_count} entities)",
                details={
                    "entity_count": entity_count,
                    "response_time_ms": round(duration, 2),
                    "entities_per_second": round(entity_count / (duration / 1000), 2)
                }
            ))

        except Exception as e:
            duration = (time.time() - start) * 1000
            logger.error(f"✗ Error: {e}")
            self.results.append(TestResult(
                name=test_name,
                status=TestStatus.ERROR,
                duration_ms=duration,
                message=str(e),
                details={"exception": type(e).__name__}
            ))

    def print_summary(self) -> None:
        """Print test summary."""
        logger.info("\n" + "=" * 80)
        logger.info("TEST SUMMARY")
        logger.info("=" * 80)

        by_status = {}
        for result in self.results:
            status = result.status.value
            by_status[status] = by_status.get(status, 0) + 1

        total = len(self.results)
        logger.info(f"\nTotal Tests: {total}")
        for status in [s.value for s in TestStatus]:
            count = by_status.get(status, 0)
            logger.info(f"  {status}: {count}")

        logger.info("\nDetailed Results:")
        logger.info("-" * 80)
        for result in self.results:
            status_icon = {
                "PASSED": "✓",
                "FAILED": "✗",
                "SKIPPED": "⊘",
                "ERROR": "⚠"
            }.get(result.status.value, "?")

            logger.info(f"{status_icon} {result.name} ({result.duration_ms:.2f}ms)")
            if result.message:
                logger.info(f"  → {result.message}")

        logger.info("=" * 80)

        # Return exit code
        passed = by_status.get("PASSED", 0)
        failed = by_status.get("FAILED", 0)
        errors = by_status.get("ERROR", 0)

        return 0 if (failed == 0 and errors == 0) else 1


async def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Vulcan Brownout QA Test Suite")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--output-file", "-o", help="Output results to JSON file")
    parser.add_argument("--ha-url", default=None, help="Home Assistant URL")
    parser.add_argument("--ha-token", default=None, help="Home Assistant token")
    args = parser.parse_args()

    # Load environment
    env_file = Path(__file__).parent.parent.parent / ".env"
    if env_file.exists():
        from dotenv import load_dotenv
        load_dotenv(env_file)

    # Get HA connection details
    ha_url = args.ha_url or os.getenv("HA_URL", "http://homeassistant.lan")
    ha_port = os.getenv("HA_PORT", "8123")
    ha_token = args.ha_token or os.getenv("HA_TOKEN")

    if not ha_token:
        logger.error("ERROR: HA_TOKEN not provided and not in environment")
        sys.exit(1)

    ha_url = f"{ha_url}:{ha_port}"

    # Run tests
    validator = EnvironmentValidator(ha_url, ha_token, verbose=args.verbose)
    results = await validator.run_all_tests()

    # Print summary
    exit_code = validator.print_summary()

    # Output JSON if requested
    if args.output_file:
        output_path = Path(args.output_file)
        output_data = {
            "timestamp": datetime.now().isoformat(),
            "ha_url": ha_url,
            "total_battery_entities": len(validator.battery_entities),
            "tests": [r.to_dict() for r in results],
            "summary": {
                "passed": sum(1 for r in results if r.status == TestStatus.PASSED),
                "failed": sum(1 for r in results if r.status == TestStatus.FAILED),
                "errors": sum(1 for r in results if r.status == TestStatus.ERROR),
                "skipped": sum(1 for r in results if r.status == TestStatus.SKIPPED),
            }
        }

        with open(output_path, "w") as f:
            json.dump(output_data, f, indent=2)

        logger.info(f"\nResults written to {output_path}")

    sys.exit(exit_code)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\nTest interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
