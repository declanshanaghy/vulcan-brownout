"""Fixture data for mock Home Assistant server.

Generates realistic battery entity data for component testing, including:
- 150+ battery entities spanning all battery states
- Binary sensors that should be filtered out
- Unavailable entities
- Varying battery levels to test sorting and filtering
"""

from typing import Any, Dict, List


def generate_test_entities(count: int = 150) -> List[Dict[str, Any]]:
    """Generate test battery entities.

    Args:
        count: Number of test entities to generate (default 150)

    Returns:
        List of entity dictionaries suitable for mock HA /mock/control endpoint
    """
    entities: List[Dict[str, Any]] = []

    # Critical state entities (0-15% battery)
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
                "icon": "mdi:battery-alert",
                "battery_level": battery_level,
            },
            "available": True,
        })

    # Warning state entities (15-25% battery)
    warning_count = max(3, count // 10)
    for i in range(warning_count):
        entity_id = f"sensor.battery_warning_{i:03d}"
        battery_level = 15 + (i % 10)  # 15-24%
        entities.append({
            "entity_id": entity_id,
            "state": str(battery_level),
            "friendly_name": f"Warning Battery Device {i}",
            "attributes": {
                "device_class": "battery",
                "unit_of_measurement": "%",
                "icon": "mdi:battery-medium",
                "battery_level": battery_level,
            },
            "available": True,
        })

    # Healthy state entities (>25% battery)
    healthy_count = count - critical_count - warning_count - 10  # Reserve 10 for special cases
    for i in range(healthy_count):
        entity_id = f"sensor.battery_healthy_{i:03d}"
        battery_level = 25 + (i % 75)  # 25-99%
        entities.append({
            "entity_id": entity_id,
            "state": str(battery_level),
            "friendly_name": f"Healthy Battery Device {i}",
            "attributes": {
                "device_class": "battery",
                "unit_of_measurement": "%",
                "icon": "mdi:battery-high",
                "battery_level": battery_level,
            },
            "available": True,
        })

    # Unavailable entities
    for i in range(5):
        entity_id = f"sensor.battery_unavailable_{i:03d}"
        entities.append({
            "entity_id": entity_id,
            "state": "unavailable",
            "friendly_name": f"Unavailable Battery Device {i}",
            "attributes": {
                "device_class": "battery",
                "unit_of_measurement": "%",
                "icon": "mdi:battery-unknown",
            },
            "available": False,
        })

    # Binary sensors that should be filtered out (they don't have numeric battery_level)
    for i in range(5):
        entity_id = f"binary_sensor.battery_low_{i:03d}"
        entities.append({
            "entity_id": entity_id,
            "state": "off",
            "friendly_name": f"Battery Low Alert {i}",
            "attributes": {
                "device_class": "battery_low",
                "icon": "mdi:alert-circle",
            },
            "available": True,
        })

    # Edge case: entities with invalid battery_level (should be filtered)
    for i in range(2):
        entity_id = f"sensor.battery_invalid_{i:03d}"
        entities.append({
            "entity_id": entity_id,
            "state": "unknown",
            "friendly_name": f"Invalid Battery Device {i}",
            "attributes": {
                "device_class": "battery",
                "unit_of_measurement": "%",
                "icon": "mdi:battery-unknown",
                "battery_level": "not_a_number",  # Invalid!
            },
            "available": True,
        })

    # Exactly 100% battery (max edge case)
    entities.append({
        "entity_id": "sensor.battery_max",
        "state": "100",
        "friendly_name": "Fully Charged Battery",
        "attributes": {
            "device_class": "battery",
            "unit_of_measurement": "%",
            "icon": "mdi:battery",
            "battery_level": 100,
        },
        "available": True,
    })

    return entities


def get_fixture_entities() -> List[Dict[str, Any]]:
    """Get default fixture entities for tests.

    Returns:
        List of 150+ test entities
    """
    return generate_test_entities(150)


def get_empty_fixture() -> List[Dict[str, Any]]:
    """Get empty fixture (no entities).

    Returns:
        Empty list
    """
    return []


def get_small_fixture() -> List[Dict[str, Any]]:
    """Get small fixture for quick tests.

    Returns:
        List of 10 test entities
    """
    return generate_test_entities(10)


def get_large_fixture() -> List[Dict[str, Any]]:
    """Get large fixture for pagination tests.

    Returns:
        List of 500 test entities
    """
    return generate_test_entities(500)
