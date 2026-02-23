"""Constants for the Vulcan Brownout integration."""

DOMAIN: str = "vulcan_brownout"
VERSION: str = "6.0.0"

# Fixed battery threshold — entities below this level are shown
BATTERY_THRESHOLD: int = 15

# Device class to filter by
BATTERY_DEVICE_CLASS: str = "battery"

# WebSocket command types
COMMAND_QUERY_ENTITIES: str = "vulcan-brownout/query_entities"
COMMAND_QUERY_UNAVAILABLE: str = "vulcan-brownout/query_unavailable"
COMMAND_SUBSCRIBE: str = "vulcan-brownout/subscribe"

# WebSocket event types
EVENT_ENTITY_CHANGED: str = "vulcan-brownout/entity_changed"
EVENT_STATUS: str = "vulcan-brownout/status"

# HA core events
HA_EVENT_STATE_CHANGED: str = "state_changed"

# Panel configuration
PANEL_NAME: str = "vulcan-brownout"
PANEL_TITLE: str = "Battery Monitoring"
PANEL_ICON: str = "mdi:battery-alert"

# WebSocket subscription limits
MAX_SUBSCRIPTIONS: int = 100

# Status — only "critical" exists now (all shown entities are below threshold)
STATUS_CRITICAL: str = "critical"
