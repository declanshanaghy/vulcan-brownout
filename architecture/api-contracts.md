# API Contracts — Sprint 4 (v3.0.0)

**Updated**: 2026-02-22 | **Status**: No API changes from Sprint 3

**Note**: Sprint 4 focuses on frontend theme detection (hass.themes.darkMode) and UX polish. No new WebSocket commands or backend API changes are required. The contracts below are carried forward from Sprint 3 unchanged.

## Commands (Frontend → Backend)

### query_devices
```json
→ { "type": "vulcan-brownout/query_devices", "data": { "limit": 50, "cursor": null|"base64", "sort_key": "priority|alphabetical|level_asc|level_desc", "sort_order": "asc|desc" } }
← { "devices": [...], "total": N, "has_more": bool, "next_cursor": "base64"|null, "device_statuses": { "critical": N, "warning": N, "healthy": N, "unavailable": N } }
```
Cursor format: `base64("{last_changed}|{entity_id}")`. Auto-filters to device_class=battery + battery_level IS NOT NULL. Binary sensors excluded.

### subscribe (unchanged from S2)
```json
→ { "type": "vulcan-brownout/subscribe" }
← { "subscription_id": "sub_abc", "status": "subscribed" }
```

### set_threshold (unchanged from S2)
```json
→ { "type": "vulcan-brownout/set_threshold", "data": { "global_threshold": 20, "device_rules": { "entity_id": threshold } } }
```

### get_notification_preferences (NEW S3)
```json
→ { "type": "vulcan-brownout/get_notification_preferences" }
← { "enabled": bool, "frequency_cap_hours": 1|6|24, "severity_filter": "critical_only|critical_and_warning", "per_device": { "entity_id": { "enabled": bool, "frequency_cap_hours": N } }, "notification_history": [...last 10-20...] }
```

### set_notification_preferences (NEW S3)
```json
→ { "type": "vulcan-brownout/set_notification_preferences", "data": { "enabled": bool, "frequency_cap_hours": 1|6|24, "severity_filter": "critical_only|critical_and_warning", "per_device": { "entity_id": { "enabled": bool, "frequency_cap_hours": N } } } }
```

## Events (Backend → Frontend)

### status (on connect + config changes)
```json
← { "type": "vulcan-brownout/status", "data": { "status": "connected", "version": "3.0.0", "threshold": N, "theme": "dark|light", "notifications_enabled": bool, "notification_preferences": {...}, "device_statuses": {...} } }
```

### device_changed
```json
← { "type": "vulcan-brownout/device_changed", "data": { "entity_id": "...", "battery_level": N, "status": "critical|warning|healthy", "available": bool, ... } }
```

### threshold_updated
```json
← { "type": "vulcan-brownout/threshold_updated", "data": { "global_threshold": N, "device_rules": {...}, "affected_devices": [...] } }
```

### notification_sent (NEW S3)
```json
← { "type": "vulcan-brownout/notification_sent", "data": { "entity_id": "...", "device_name": "...", "battery_level": N, "status": "critical|warning", "message": "...", "notification_id": "..." } }
```

## Error Codes
invalid_request, invalid_limit (1-100), invalid_cursor, invalid_sort_key, invalid_threshold (5-100), invalid_notification_preferences, invalid_device_entity, too_many_rules (>10), permission_denied, integration_not_loaded, subscription_limit_exceeded, internal_error

## Breaking Changes S2→S3
- query_devices uses cursor instead of offset (offset removed)
- Status event now includes theme + notification fields (non-breaking additions)
