"""Constants for the Vulcan Brownout integration."""

DOMAIN = "vulcan_brownout"
VERSION = "2.0.0"

# Battery monitoring thresholds and defaults
BATTERY_THRESHOLD_DEFAULT = 15
BATTERY_THRESHOLD_MIN = 5
BATTERY_THRESHOLD_MAX = 100

# WebSocket command and event types
COMMAND_QUERY_DEVICES = "vulcan-brownout/query_devices"
COMMAND_SUBSCRIBE = "vulcan-brownout/subscribe"
COMMAND_SET_THRESHOLD = "vulcan-brownout/set_threshold"
EVENT_DEVICE_CHANGED = "vulcan-brownout/device_changed"
EVENT_DEVICE_REMOVED = "vulcan-brownout/device_removed"
EVENT_STATUS = "vulcan-brownout/status"
EVENT_THRESHOLD_UPDATED = "vulcan-brownout/threshold_updated"

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

# Device status classifications
STATUS_CRITICAL = "critical"
STATUS_WARNING = "warning"
STATUS_HEALTHY = "healthy"
STATUS_UNAVAILABLE = "unavailable"
SUPPORTED_STATUSES = [STATUS_CRITICAL, STATUS_WARNING, STATUS_HEALTHY, STATUS_UNAVAILABLE]

# Status thresholds (relative to configured threshold)
WARNING_BUFFER = 10  # Show WARNING for levels threshold to threshold+10

# HA core events
HA_EVENT_STATE_CHANGED = "state_changed"

# Panel configuration
PANEL_NAME = "vulcan-brownout"
PANEL_TITLE = "Battery Monitoring"
PANEL_ICON = "mdi:battery-alert"

# WebSocket subscription limits
MAX_SUBSCRIPTIONS = 100
SUBSCRIPTION_KEEPALIVE_INTERVAL = 30  # seconds

# Device rule limits
MAX_DEVICE_RULES = 10

# API endpoints
HEALTH_CHECK_ENDPOINT = "/api/vulcan_brownout/health"
