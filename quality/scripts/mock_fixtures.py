"""Mock fixture data for component tests.

Provides test entity data that can be loaded into the mock HA server.
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
            "manufacturer": "IKEA",
            "area_name": "Living Room",
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
            "manufacturer": "Aqara",
            "area_name": "Kitchen",
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
    manufacturers = ["Philips", "IKEA", "Aqara", "Sonoff"]
    areas = ["Bedroom", "Living Room", "Kitchen", "Office"]
    for i in range(healthy_count):
        entity_id = f"sensor.battery_healthy_{i:03d}"
        battery_level = 25 + (i % 75)  # 25-99%
        entities.append({
            "entity_id": entity_id,
            "state": str(battery_level),
            "friendly_name": f"Healthy Battery Device {i}",
            "manufacturer": manufacturers[i % len(manufacturers)],
            "area_name": areas[i % len(areas)],
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
            "manufacturer": "Aqara",
            "area_name": "Bedroom",
            "attributes": {
                "device_class": "battery",
                "unit_of_measurement": "%",
                "icon": "mdi:battery-unknown",
            },
            "available": False,
        })

    # Exactly 100% battery (max edge case)
    entities.append({
        "entity_id": "sensor.battery_max",
        "state": "100",
        "friendly_name": "Fully Charged Battery",
        "manufacturer": "Philips",
        "area_name": "Office",
        "attributes": {
            "device_class": "battery",
            "unit_of_measurement": "%",
            "icon": "mdi:battery",
            "battery_level": 100,
        },
        "available": True,
    })

    return entities


def generate_filter_test_entities(count: int = 50) -> List[Dict[str, Any]]:
    """Generate test entities with diverse manufacturers, areas, and statuses for filter testing.

    Args:
        count: Number of test entities to generate (default 50)

    Returns:
        List of entity dictionaries with manufacturer and area_name fields
    """
    entities: List[Dict[str, Any]] = []

    manufacturers = ["Aqara", "Philips", "IKEA", "Sonoff"]
    areas = ["Living Room", "Kitchen", "Bedroom", "Office"]

    # Generate entities with diverse manufacturer/area/status combinations
    for i in range(count):
        manufacturer = manufacturers[i % len(manufacturers)]
        area = areas[i % len(areas)]

        # Vary battery levels to get different statuses
        if i % 5 == 0:
            battery_level = 5 + (i % 10)  # 5-15% -> critical
            status = "critical"
        elif i % 5 == 1:
            battery_level = 15 + (i % 10)  # 15-25% -> warning
            status = "warning"
        elif i % 5 == 2:
            battery_level = 30 + (i % 70)  # 30-99% -> healthy
            status = "healthy"
        elif i % 5 == 3:
            battery_level = 50 + (i % 50)  # 50-99% -> healthy
            status = "healthy"
        else:
            battery_level = 0  # unavailable
            status = "unavailable"

        entity_id = f"sensor.filter_test_{i:03d}_battery"
        entities.append({
            "entity_id": entity_id,
            "state": str(battery_level) if battery_level > 0 else "unavailable",
            "friendly_name": f"Filter Test Device {i} ({manufacturer})",
            "manufacturer": manufacturer,
            "area_name": area,
            "attributes": {
                "device_class": "battery",
                "unit_of_measurement": "%",
                "icon": "mdi:battery",
                "battery_level": battery_level if battery_level > 0 else None,
            },
            "available": battery_level > 0,
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
