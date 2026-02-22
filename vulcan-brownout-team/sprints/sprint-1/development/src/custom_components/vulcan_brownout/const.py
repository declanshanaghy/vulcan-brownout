"""Constants for the Vulcan Brownout integration."""

DOMAIN = "vulcan_brownout"
VERSION = "1.0.0"

# Battery monitoring thresholds and defaults
BATTERY_THRESHOLD = 15  # Hardcoded for Sprint 1; configurable in Sprint 2

# WebSocket command and event types
COMMAND_QUERY_DEVICES = "vulcan-brownout/query_devices"
EVENT_DEVICE_CHANGED = "vulcan-brownout/device_changed"
EVENT_DEVICE_REMOVED = "vulcan-brownout/device_removed"
EVENT_STATUS = "vulcan-brownout/status"

# Device class to filter by
BATTERY_DEVICE_CLASS = "battery"

# Pagination and sorting
MAX_PAGE_SIZE = 100
DEFAULT_PAGE_SIZE = 20

# Supported sort keys
SORT_KEY_BATTERY_LEVEL = "battery_level"
SORT_KEY_AVAILABLE = "available"
SORT_KEY_DEVICE_NAME = "device_name"
SUPPORTED_SORT_KEYS = [SORT_KEY_BATTERY_LEVEL, SORT_KEY_AVAILABLE, SORT_KEY_DEVICE_NAME]

# Sort orders
SORT_ORDER_ASC = "asc"
SORT_ORDER_DESC = "desc"
SUPPORTED_SORT_ORDERS = [SORT_ORDER_ASC, SORT_ORDER_DESC]

# HA core events
HA_EVENT_STATE_CHANGED = "state_changed"

# Panel configuration
PANEL_NAME = "vulcan-brownout"
PANEL_TITLE = "Vulcan Brownout"
PANEL_ICON = "mdi:battery-alert"
