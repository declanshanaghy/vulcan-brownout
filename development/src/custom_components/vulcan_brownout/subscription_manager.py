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
        _LOGGER.debug(
            "WebSocketSubscriptionManager.__init__: max_subscriptions=%d",
            MAX_SUBSCRIPTIONS,
        )

    def subscribe(
        self,
        subscription_id: str,
        connection: Any,
        entity_ids: Optional[List[str]] = None,
    ) -> bool:
        current_count = len(self.subscribers)
        _LOGGER.debug(
            "subscribe: subscription_id=%s entity_count=%d "
            "current_subscribers=%d max_subscriptions=%d",
            subscription_id, len(entity_ids) if entity_ids else 0,
            current_count, MAX_SUBSCRIPTIONS,
        )

        if current_count >= MAX_SUBSCRIPTIONS:
            _LOGGER.warning(
                "subscribe: subscription_id=%s result=rejected "
                "reason=limit_exceeded current=%d max=%d",
                subscription_id, current_count, MAX_SUBSCRIPTIONS,
            )
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

        _LOGGER.info(
            "subscribe: subscription_id=%s result=accepted "
            "entity_count=%d total_subscribers=%d",
            subscription_id, len(entity_set), len(self.subscribers),
        )
        return True

    def unsubscribe(self, subscription_id: str) -> None:
        _LOGGER.debug(
            "unsubscribe: subscription_id=%s", subscription_id
        )
        subscription = self.subscribers.pop(subscription_id, None)
        if not subscription:
            _LOGGER.debug(
                "unsubscribe: subscription_id=%s result=not_found (already removed)",
                subscription_id,
            )
            return

        removed_entity_mappings = 0
        for entity_id in subscription.entity_ids:
            if entity_id in self.entity_subscribers:
                self.entity_subscribers[entity_id].discard(subscription_id)
                if not self.entity_subscribers[entity_id]:
                    del self.entity_subscribers[entity_id]
                removed_entity_mappings += 1

        _LOGGER.info(
            "unsubscribe: subscription_id=%s removed=true "
            "entity_mappings_cleaned=%d remaining_subscribers=%d",
            subscription_id, removed_entity_mappings, len(self.subscribers),
        )

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
        sub_count = len(subscription_ids)
        _LOGGER.debug(
            "broadcast_entity_changed: entity_id=%s battery_level=%.1f%% "
            "status=%s subscriber_count=%d",
            entity_id, battery_level, status, sub_count,
        )

        if not subscription_ids:
            _LOGGER.debug(
                "broadcast_entity_changed: entity_id=%s no_subscribers skipping",
                entity_id,
            )
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

        sent = 0
        dead = []
        for sid in subscription_ids:
            sub = self.subscribers.get(sid)
            if sub:
                try:
                    sub.connection.send_message(message)
                    sent += 1
                except Exception as e:
                    _LOGGER.warning(
                        "broadcast_entity_changed: entity_id=%s subscription_id=%s "
                        "send=failed error=%s marking_dead=true",
                        entity_id, sid, e,
                    )
                    dead.append(sid)

        for sid in dead:
            self.unsubscribe(sid)

        _LOGGER.debug(
            "broadcast_entity_changed: entity_id=%s sent=%d dead_cleaned=%d",
            entity_id, sent, len(dead),
        )

    def broadcast_status(self, status: str) -> None:
        """Broadcast status update to all subscribers."""
        sub_count = len(self.subscribers)
        _LOGGER.debug(
            "broadcast_status: status=%s subscriber_count=%d version=%s",
            status, sub_count, VERSION,
        )

        message = {
            "type": "vulcan-brownout/status",
            "data": {
                "status": status,
                "version": VERSION,
            },
        }

        sent = 0
        dead = []
        for sid, sub in self.subscribers.items():
            try:
                sub.connection.send_message(message)
                sent += 1
            except Exception as e:
                _LOGGER.warning(
                    "broadcast_status: subscription_id=%s send=failed error=%s marking_dead=true",
                    sid, e,
                )
                dead.append(sid)

        for sid in dead:
            self.unsubscribe(sid)

        _LOGGER.info(
            "broadcast_status: status=%s sent=%d dead_cleaned=%d",
            status, sent, len(dead),
        )

    def get_subscription_count(self) -> int:
        count = len(self.subscribers)
        _LOGGER.debug("get_subscription_count: count=%d", count)
        return count

    def cleanup(self) -> None:
        sub_count = len(self.subscribers)
        entity_sub_count = len(self.entity_subscribers)
        _LOGGER.debug(
            "cleanup: subscribers_to_clear=%d entity_mappings_to_clear=%d",
            sub_count, entity_sub_count,
        )
        self.subscribers.clear()
        self.entity_subscribers.clear()
        _LOGGER.info(
            "cleanup: complete subscribers_cleared=%d entity_mappings_cleared=%d",
            sub_count, entity_sub_count,
        )
