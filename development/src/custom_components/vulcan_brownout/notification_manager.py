"""Notification system for Vulcan Brownout integration - Sprint 3."""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from collections import deque

from homeassistant.core import HomeAssistant

from .const import (
    DOMAIN,
    STATUS_CRITICAL,
    STATUS_WARNING,
    NOTIFICATION_FREQUENCY_CAP_OPTIONS,
    NOTIFICATION_SEVERITY_FILTER_OPTIONS,
    NOTIFICATION_HISTORY_MAX_SIZE,
)

_LOGGER = logging.getLogger(__name__)


class NotificationManager:
    """Manages battery notifications with preferences and frequency caps.

    Features:
    - Global enable/disable for all notifications
    - Per-device enable/disable
    - Severity filtering (critical_only or critical_and_warning)
    - Frequency caps (1h, 6h, 24h) to prevent notification spam
    - Per-device frequency cap override
    - Notification history tracking
    - Integration with HA's persistent_notification service
    """

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize notification manager.

        Args:
            hass: Home Assistant instance
        """
        self.hass = hass
        self.preferences: Dict[str, Any] = {}
        self.notification_history: deque = deque(maxlen=NOTIFICATION_HISTORY_MAX_SIZE)
        self.last_notification_time: Dict[str, datetime] = {}

    async def async_setup(self, config_entry: Any) -> None:
        """Load notification preferences from config entry.

        Args:
            config_entry: HA config entry with notification preferences
        """
        try:
            options = config_entry.options if config_entry else {}
            self.preferences = options.get(
                "notification_preferences",
                {
                    "enabled": True,
                    "frequency_cap_hours": 6,
                    "severity_filter": "critical_only",
                    "per_device": {},
                },
            )
            _LOGGER.debug(f"Notification preferences loaded: {self.preferences}")
        except Exception as e:
            _LOGGER.error(f"Error loading notification preferences: {e}")
            self.preferences = {
                "enabled": True,
                "frequency_cap_hours": 6,
                "severity_filter": "critical_only",
                "per_device": {},
            }

    async def check_and_send_notification(
        self,
        entity_id: str,
        status: str,
        battery_level: float,
        device_name: str,
    ) -> bool:
        """Check if notification should be sent, then queue it to HA.

        Checks:
        1. Notifications globally enabled
        2. Device notifications enabled
        3. Status passes severity filter
        4. Not within frequency cap window

        Args:
            entity_id: Battery entity identifier
            status: Device status (critical or warning)
            battery_level: Battery level (0-100)
            device_name: Friendly device name

        Returns:
            True if notification was sent, False if skipped
        """
        try:
            # Step 1: Check if notifications are globally enabled
            if not self.preferences.get("enabled", True):
                _LOGGER.debug(f"Notifications globally disabled, skipping {entity_id}")
                return False

            # Step 2: Check if notifications enabled for this device
            device_pref = self.preferences.get("per_device", {}).get(entity_id, {})
            if not device_pref.get("enabled", True):
                _LOGGER.debug(f"Notifications disabled for device {entity_id}")
                return False

            # Step 3: Check severity filter
            severity_filter = self.preferences.get("severity_filter", "critical_only")
            if severity_filter == "critical_only" and status == STATUS_WARNING:
                _LOGGER.debug(f"Warning status filtered for {entity_id}")
                return False

            # Step 4: Check frequency cap
            frequency_cap_hours = device_pref.get(
                "frequency_cap_hours",
                self.preferences.get("frequency_cap_hours", 6),
            )
            if not self._check_frequency_cap(entity_id, frequency_cap_hours):
                _LOGGER.debug(
                    f"Frequency cap active for {entity_id}, skipping notification"
                )
                return False

            # All checks passed - send notification
            await self._send_notification(
                entity_id, status, battery_level, device_name
            )
            self.last_notification_time[entity_id] = datetime.now()
            return True

        except Exception as e:
            _LOGGER.error(f"Error checking notification for {entity_id}: {e}")
            return False

    def _check_frequency_cap(self, entity_id: str, cap_hours: int) -> bool:
        """Check if device is within frequency cap window.

        Args:
            entity_id: Battery entity identifier
            cap_hours: Frequency cap in hours (1, 6, or 24)

        Returns:
            True if notification can be sent (not within cap), False if within cap
        """
        last_notif_time = self.last_notification_time.get(entity_id)
        if not last_notif_time:
            return True  # No previous notification

        time_since = datetime.now() - last_notif_time
        cap_duration = timedelta(hours=cap_hours)

        if time_since < cap_duration:
            _LOGGER.debug(
                f"Device {entity_id} within {cap_hours}h frequency cap "
                f"({time_since.total_seconds():.0f}s / {cap_duration.total_seconds():.0f}s)"
            )
            return False

        return True

    async def _send_notification(
        self,
        entity_id: str,
        status: str,
        battery_level: float,
        device_name: str,
    ) -> None:
        """Send notification via HA persistent_notification service.

        Args:
            entity_id: Battery entity identifier
            status: Device status (critical or warning)
            battery_level: Battery level (0-100)
            device_name: Friendly device name
        """
        try:
            status_label = "critical" if status == STATUS_CRITICAL else "warning"
            message = f"{device_name} battery {status_label} ({battery_level:.0f}%) — action needed soon"

            notification_id = f"vulcan_brownout.{entity_id}.{status}"

            # Call HA service
            await self.hass.services.async_call(
                "persistent_notification",
                "create",
                {
                    "title": "🔋 Battery Low",
                    "message": message,
                    "notification_id": notification_id,
                },
            )

            # Record in history
            notification_record = {
                "timestamp": datetime.now().isoformat(),
                "entity_id": entity_id,
                "device_name": device_name,
                "battery_level": battery_level,
                "status": status,
                "message": message,
                "notification_id": notification_id,
            }
            self.notification_history.append(notification_record)

            _LOGGER.info(f"Notification sent for {device_name}: {message}")

        except Exception as e:
            _LOGGER.error(f"Error sending notification for {entity_id}: {e}")

    async def broadcast_notification_sent(
        self,
        entity_id: str,
        device_name: str,
        status: str,
        battery_level: float,
        message: str,
        subscription_manager: Any,
    ) -> None:
        """Broadcast notification_sent event to all WebSocket subscribers.

        Args:
            entity_id: Battery entity identifier
            device_name: Friendly device name
            status: Device status (critical or warning)
            battery_level: Battery level (0-100)
            message: Notification message
            subscription_manager: WebSocket subscription manager to broadcast through
        """
        try:
            subscription_manager.broadcast_notification_sent(
                timestamp=datetime.now().isoformat(),
                entity_id=entity_id,
                device_name=device_name,
                battery_level=battery_level,
                status=status,
                message=message,
                notification_id=f"vulcan_brownout.{entity_id}.{status}",
            )
        except Exception as e:
            _LOGGER.warning(f"Error broadcasting notification event: {e}")

    def get_notification_preferences(self) -> Dict[str, Any]:
        """Get current notification preferences and history.

        Returns:
            Dict with preferences and notification history
        """
        return {
            "enabled": self.preferences.get("enabled", True),
            "frequency_cap_hours": self.preferences.get("frequency_cap_hours", 6),
            "severity_filter": self.preferences.get("severity_filter", "critical_only"),
            "per_device": self.preferences.get("per_device", {}),
            "notification_history": list(self.notification_history),
        }

    async def set_notification_preferences(
        self,
        enabled: bool,
        frequency_cap_hours: int,
        severity_filter: str,
        per_device: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> None:
        """Update notification preferences.

        Args:
            enabled: Global enable/disable
            frequency_cap_hours: Frequency cap in hours (1, 6, or 24)
            severity_filter: Severity filter (critical_only or critical_and_warning)
            per_device: Per-device settings dict

        Raises:
            ValueError: If parameters are invalid
        """
        # Validate inputs
        if frequency_cap_hours not in NOTIFICATION_FREQUENCY_CAP_OPTIONS:
            raise ValueError(
                f"Invalid frequency_cap_hours: {frequency_cap_hours}. "
                f"Must be one of {NOTIFICATION_FREQUENCY_CAP_OPTIONS}"
            )

        if severity_filter not in NOTIFICATION_SEVERITY_FILTER_OPTIONS:
            raise ValueError(
                f"Invalid severity_filter: {severity_filter}. "
                f"Must be one of {NOTIFICATION_SEVERITY_FILTER_OPTIONS}"
            )

        # Update preferences
        self.preferences = {
            "enabled": enabled,
            "frequency_cap_hours": frequency_cap_hours,
            "severity_filter": severity_filter,
            "per_device": per_device or {},
        }

        _LOGGER.info(
            f"Notification preferences updated: "
            f"enabled={enabled}, "
            f"frequency_cap={frequency_cap_hours}h, "
            f"severity={severity_filter}"
        )

    def reset_frequency_caps(self) -> None:
        """Reset all frequency cap timers.

        Called when preferences are updated or on integration reload.
        """
        self.last_notification_time.clear()
        _LOGGER.debug("Notification frequency caps reset")
