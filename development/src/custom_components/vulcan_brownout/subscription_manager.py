"""WebSocket subscription manager for real-time battery updates."""

import logging
from typing import Any, Callable, Dict, List, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime

from homeassistant.core import HomeAssistant, State

from .const import (
    MAX_SUBSCRIPTIONS,
    STATUS_CRITICAL,
    STATUS_WARNING,
    STATUS_HEALTHY,
    STATUS_UNAVAILABLE,
    WARNING_BUFFER,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class ClientSubscription:
    """Represents a client WebSocket subscription."""

    subscription_id: str
    connection: Any
    entity_ids: Set[str] = field(default_factory=set)
    created_at: datetime = field(default_factory=datetime.now)


class WebSocketSubscriptionManager:
    """Manages WebSocket subscriptions for real-time battery updates."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize subscription manager."""
        self.hass = hass
        self.subscribers: Dict[str, ClientSubscription] = {}
        self.entity_subscribers: Dict[str, Set[str]] = {}  # Maps entity_id to subscription_ids

    def subscribe(
        self,
        subscription_id: str,
        connection: Any,
        entity_ids: Optional[List[str]] = None,
    ) -> bool:
        """Register a client subscription.

        Args:
            subscription_id: Unique subscription identifier
            connection: WebSocket connection object
            entity_ids: List of entity IDs to monitor (or all if None)

        Returns:
            True if subscription created, False if limit exceeded
        """
        if len(self.subscribers) >= MAX_SUBSCRIPTIONS:
            _LOGGER.warning(f"Subscription limit ({MAX_SUBSCRIPTIONS}) exceeded")
            return False

        entity_set = set(entity_ids) if entity_ids else set()
        subscription = ClientSubscription(
            subscription_id=subscription_id,
            connection=connection,
            entity_ids=entity_set,
        )
        self.subscribers[subscription_id] = subscription

        # Register this subscription for each entity
        if entity_ids:
            for entity_id in entity_ids:
                if entity_id not in self.entity_subscribers:
                    self.entity_subscribers[entity_id] = set()
                self.entity_subscribers[entity_id].add(subscription_id)

        _LOGGER.debug(
            f"Subscription {subscription_id} created for {len(entity_set)} entities"
        )
        return True

    def unsubscribe(self, subscription_id: str) -> None:
        """Unregister a client subscription.

        Args:
            subscription_id: Subscription identifier to remove
        """
        subscription = self.subscribers.pop(subscription_id, None)
        if not subscription:
            return

        # Unregister from entity subscriptions
        for entity_id in subscription.entity_ids:
            if entity_id in self.entity_subscribers:
                self.entity_subscribers[entity_id].discard(subscription_id)
                if not self.entity_subscribers[entity_id]:
                    del self.entity_subscribers[entity_id]

        _LOGGER.debug(f"Subscription {subscription_id} removed")

    def broadcast_device_changed(
        self,
        entity_id: str,
        battery_level: float,
        available: bool,
        status: str,
        last_changed: Optional[str] = None,
        last_updated: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Broadcast device change to all interested subscribers.

        Args:
            entity_id: Entity that changed
            battery_level: New battery level
            available: Whether device is available
            status: Device status (critical/warning/healthy/unavailable)
            last_changed: ISO8601 timestamp of last state change
            last_updated: ISO8601 timestamp of last update
            attributes: Entity attributes
        """
        subscription_ids = self.entity_subscribers.get(entity_id, set())
        if not subscription_ids:
            return

        message = {
            "type": "vulcan-brownout/device_changed",
            "data": {
                "entity_id": entity_id,
                "battery_level": battery_level,
                "available": available,
                "status": status,
                "last_changed": last_changed,
                "last_updated": last_updated,
                "attributes": attributes or {},
            },
        }

        dead_subscriptions = []
        for subscription_id in subscription_ids:
            subscription = self.subscribers.get(subscription_id)
            if subscription:
                try:
                    subscription.connection.send_json_message(message)
                except Exception as e:
                    _LOGGER.warning(
                        f"Failed to send update to subscription {subscription_id}: {e}"
                    )
                    dead_subscriptions.append(subscription_id)

        # Clean up dead subscriptions
        for subscription_id in dead_subscriptions:
            self.unsubscribe(subscription_id)

    def broadcast_threshold_updated(
        self,
        global_threshold: int,
        device_rules: Dict[str, int],
        affected_devices: Optional[List[Dict[str, str]]] = None,
    ) -> None:
        """Broadcast threshold update to all subscribers.

        Args:
            global_threshold: New global threshold
            device_rules: New device-specific rules
            affected_devices: Devices whose status changed (optional optimization)
        """
        message = {
            "type": "vulcan-brownout/threshold_updated",
            "data": {
                "global_threshold": global_threshold,
                "device_rules": device_rules,
                "affected_devices": affected_devices or [],
            },
        }

        dead_subscriptions = []
        for subscription_id, subscription in self.subscribers.items():
            try:
                subscription.connection.send_json_message(message)
            except Exception as e:
                _LOGGER.warning(
                    f"Failed to send threshold update to subscription {subscription_id}: {e}"
                )
                dead_subscriptions.append(subscription_id)

        # Clean up dead subscriptions
        for subscription_id in dead_subscriptions:
            self.unsubscribe(subscription_id)

    def broadcast_status(
        self,
        status: str,
        threshold: int,
        device_rules: Dict[str, int],
        device_statuses: Optional[Dict[str, int]] = None,
    ) -> None:
        """Broadcast status update to all subscribers.

        Args:
            status: Connection status (connected/disconnected/error)
            threshold: Global threshold
            device_rules: Device-specific rules
            device_statuses: Count of devices in each status (optional)
        """
        message = {
            "type": "vulcan-brownout/status",
            "data": {
                "status": status,
                "version": "2.0.0",
                "threshold": threshold,
                "threshold_rules": device_rules,
                "device_statuses": device_statuses or {},
            },
        }

        dead_subscriptions = []
        for subscription_id, subscription in self.subscribers.items():
            try:
                subscription.connection.send_json_message(message)
            except Exception as e:
                _LOGGER.warning(
                    f"Failed to send status to subscription {subscription_id}: {e}"
                )
                dead_subscriptions.append(subscription_id)

        # Clean up dead subscriptions
        for subscription_id in dead_subscriptions:
            self.unsubscribe(subscription_id)

    def get_subscription_count(self) -> int:
        """Get current subscription count."""
        return len(self.subscribers)

    def cleanup(self) -> None:
        """Clean up all subscriptions (called on integration unload)."""
        self.subscribers.clear()
        self.entity_subscribers.clear()
        _LOGGER.debug("Subscription manager cleaned up")
