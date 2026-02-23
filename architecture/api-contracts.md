# API Contracts — v6.0.0 (Simplified)

**Updated**: 2026-02-22 | **Status**: v6 — ruthless simplification

**Breaking changes from v5.0.0**:
- `query_devices` renamed to `query_entities` (we work with entities, not devices)
- `query_entities` no longer accepts any parameters (no sort/filter/pagination)
- Removed commands: `set_threshold`, `get_notification_preferences`, `set_notification_preferences`, `get_filter_options`
- Fixed 15% threshold — not configurable
- Response key changed from `devices` to `entities`
- Response no longer includes `has_more`, `next_cursor`, `device_statuses`, `offset`, `limit`

## Commands (Frontend -> Backend)

### query_entities

Returns all battery entities below the fixed 15% threshold, sorted by battery level ascending.

```json
-> { "type": "vulcan-brownout/query_entities" }

<- {
    "entities": [
      {
        "entity_id": "sensor.front_door_battery",
        "state": "8",
        "attributes": { ... },
        "last_changed": "2026-02-22T10:00:00Z",
        "last_updated": "2026-02-22T10:00:00Z",
        "device_name": "Front Door Lock",
        "battery_level": 8.0,
        "status": "critical"
      }
    ],
    "total": 3
  }
```

No parameters. Backend automatically:
- Discovers all `device_class=battery` entities (excluding binary sensors)
- Filters to entities where `battery_level < 15`
- Skips unavailable/unknown entities
- Sorts by battery level ascending (lowest first)

---

### subscribe

Subscribe to real-time entity change events.

```json
-> { "type": "vulcan-brownout/subscribe" }

<- {
    "subscription_id": "sub_abc123",
    "status": "subscribed"
  }
```

### Events (Backend -> Frontend)

#### entity_changed

Pushed when a battery entity's state changes.

```json
{
  "type": "vulcan-brownout/entity_changed",
  "data": {
    "entity_id": "sensor.front_door_battery",
    "battery_level": 7.0,
    "status": "critical",
    "last_changed": "2026-02-22T10:05:00Z",
    "last_updated": "2026-02-22T10:05:00Z",
    "attributes": { ... }
  }
}
```

#### status

Connection status broadcast.

```json
{
  "type": "vulcan-brownout/status",
  "data": {
    "status": "connected",
    "version": "6.0.0"
  }
}
```

## Removed Commands (v5 -> v6)

- ~~`vulcan-brownout/query_devices`~~ — renamed to `query_entities`
- ~~`vulcan-brownout/set_threshold`~~ — threshold is fixed at 15%
- ~~`vulcan-brownout/get_notification_preferences`~~ — no notifications
- ~~`vulcan-brownout/set_notification_preferences`~~ — no notifications
- ~~`vulcan-brownout/get_filter_options`~~ — no filtering
