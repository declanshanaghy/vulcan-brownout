"""WebSocket subscription manager for real-time battery updates."""

import logging
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime

from homeassistant.core import HomeAssistant

from .const import MAX_SUBSCRIPTIONS, VERSION

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
        self.hass = hass
        self.subscribers: Dict[str, ClientSubscription] = {}
        self.entity_subscribers: Dict[str, Set[str]] = {}

    def subscribe(
        self,
        subscription_id: str,
        connection: Any,
        entity_ids: Optional[List[str]] = None,
    ) -> bool:
        if len(self.subscribers) >= MAX_SUBSCRIPTIONS:
            return False

        entity_set = set(entity_ids) if entity_ids else set()
        subscription = ClientSubscription(
            subscription_id=subscription_id,
            connection=connection,
            entity_ids=entity_set,
        )
        self.subscribers[subscription_id] = subscription

        if entity_ids:
            for entity_id in entity_ids:
                if entity_id not in self.entity_subscribers:
                    self.entity_subscribers[entity_id] = set()
                self.entity_subscribers[entity_id].add(subscription_id)

        return True

    def unsubscribe(self, subscription_id: str) -> None:
        subscription = self.subscribers.pop(subscription_id, None)
        if not subscription:
            return
        for entity_id in subscription.entity_ids:
            if entity_id in self.entity_subscribers:
                self.entity_subscribers[entity_id].discard(subscription_id)
                if not self.entity_subscribers[entity_id]:
                    del self.entity_subscribers[entity_id]

    def broadcast_entity_changed(
        self,
        entity_id: str,
        battery_level: float,
        status: str,
        last_changed: Optional[str] = None,
        last_updated: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Broadcast entity change to interested subscribers."""
        subscription_ids = self.entity_subscribers.get(entity_id, set())
        if not subscription_ids:
            return

        message = {
            "type": "vulcan-brownout/entity_changed",
            "data": {
                "entity_id": entity_id,
                "battery_level": battery_level,
                "status": status,
                "last_changed": last_changed,
                "last_updated": last_updated,
                "attributes": attributes or {},
            },
        }

        dead = []
        for sid in subscription_ids:
            sub = self.subscribers.get(sid)
            if sub:
                try:
                    sub.connection.send_message(message)
                except Exception:
                    dead.append(sid)

        for sid in dead:
            self.unsubscribe(sid)

    def broadcast_status(self, status: str) -> None:
        """Broadcast status update to all subscribers."""
        message = {
            "type": "vulcan-brownout/status",
            "data": {
                "status": status,
                "version": VERSION,
            },
        }

        dead = []
        for sid, sub in self.subscribers.items():
            try:
                sub.connection.send_message(message)
            except Exception:
                dead.append(sid)

        for sid in dead:
            self.unsubscribe(sid)

    def get_subscription_count(self) -> int:
        return len(self.subscribers)

    def cleanup(self) -> None:
        self.subscribers.clear()
        self.entity_subscribers.clear()
