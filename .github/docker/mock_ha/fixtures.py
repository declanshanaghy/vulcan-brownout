"""Fixture data for mock Home Assistant server.

Generates battery entities with varying levels for component testing.
Only entities below 15% will be returned by query_devices.
"""

from typing import Any, Dict, List


def generate_test_entities(count: int = 150) -> List[Dict[str, Any]]:
    """Generate test battery entities with varying levels.

    Args:
        count: Number of test entities to generate

    Returns:
        List of entity dictionaries for mock HA /mock/control endpoint
    """
    entities: List[Dict[str, Any]] = []

    # Critical entities (below 15% — these will be shown)
    critical_count = max(3, count // 15)
    for i in range(critical_count):
        entity_id = f"sensor.battery_critical_{i:03d}"
        battery_level = (10 + i) % 15  # 10-14%
        entities.append({
            "entity_id": entity_id,
            "state": str(battery_level),
            "friendly_name": f"Critical Battery Device {i}",
            "attributes": {
                "device_class": "battery",
                "unit_of_measurement": "%",
                "battery_level": battery_level,
            },
            "available": True,
        })

    # Above-threshold entities (>= 15% — these will NOT be shown)
    above_count = count - critical_count - 5
    for i in range(above_count):
        entity_id = f"sensor.battery_above_{i:03d}"
        battery_level = 15 + (i % 85)  # 15-99%
        entities.append({
            "entity_id": entity_id,
            "state": str(battery_level),
            "friendly_name": f"Above Threshold Device {i}",
            "attributes": {
                "device_class": "battery",
                "unit_of_measurement": "%",
                "battery_level": battery_level,
            },
            "available": True,
        })

    # Binary sensors (should be filtered out)
    for i in range(3):
        entities.append({
            "entity_id": f"binary_sensor.battery_low_{i:03d}",
            "state": "off",
            "friendly_name": f"Battery Low Alert {i}",
            "attributes": {"device_class": "battery_low"},
            "available": True,
        })

    # Unavailable entities (should be skipped)
    for i in range(2):
        entities.append({
            "entity_id": f"sensor.battery_unavailable_{i:03d}",
            "state": "unavailable",
            "friendly_name": f"Unavailable Device {i}",
            "attributes": {"device_class": "battery"},
            "available": False,
        })

    return entities


def get_fixture_entities() -> List[Dict[str, Any]]:
    """Get default fixture entities (150)."""
    return generate_test_entities(150)


def get_empty_fixture() -> List[Dict[str, Any]]:
    """Get empty fixture."""
    return []


def get_small_fixture() -> List[Dict[str, Any]]:
    """Get small fixture (10 entities)."""
    return generate_test_entities(10)
