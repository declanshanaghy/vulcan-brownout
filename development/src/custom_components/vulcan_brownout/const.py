"""Constants for the Vulcan Brownout integration."""

DOMAIN = "vulcan_brownout"
VERSION = "6.0.0"

# Fixed battery threshold — entities below this level are shown
BATTERY_THRESHOLD = 15

# Device class to filter by
BATTERY_DEVICE_CLASS = "battery"

# WebSocket command types
COMMAND_QUERY_ENTITIES = "vulcan-brownout/query_entities"
COMMAND_SUBSCRIBE = "vulcan-brownout/subscribe"

# WebSocket event types
EVENT_ENTITY_CHANGED = "vulcan-brownout/entity_changed"
EVENT_STATUS = "vulcan-brownout/status"

# HA core events
HA_EVENT_STATE_CHANGED = "state_changed"

# Panel configuration
PANEL_NAME = "vulcan-brownout"
PANEL_TITLE = "Battery Monitoring"
PANEL_ICON = "mdi:battery-alert"

# WebSocket subscription limits
MAX_SUBSCRIPTIONS = 100

# Status — only "critical" exists now (all shown entities are below threshold)
STATUS_CRITICAL = "critical"
