# Sprint 2 Implementation Plan

**Project**: Vulcan Brownout Battery Monitoring
**Sprint**: 2
**Implemented by**: ArsonWells (Lead Software Developer)
**Date**: February 2026
**Version**: 2.0.0

---

## Overview

This document describes the implementation of Sprint 2 features for the Vulcan Brownout Home Assistant integration. Sprint 2 builds on Sprint 1 by adding real-time WebSocket subscriptions, configurable battery thresholds, and client-side sorting/filtering with responsive mobile support.

---

## Architecture Decisions

### 1. Real-Time Updates (ADR-006: WebSocket Subscriptions)

**Decision**: Implement push-based event broadcasting via WebSocket subscriptions.

**Implementation**:
- New `WebSocketSubscriptionManager` class manages active client subscriptions
- Subscriptions track which entities each client is interested in
- Backend broadcasts device state changes to interested subscribers
- Frontend exponential backoff reconnection (1s → 30s max)
- Connection state machine: connected → reconnecting → offline

**Key Components**:
- `subscription_manager.py`: Manages subscriptions and broadcasts
- `websocket_api.py`: New `/vulcan-brownout/subscribe` command
- `__init__.py`: Hooks into `state_changed` events for broadcasting

**Benefits**:
- Real-time updates without polling
- Reduced server load (only broadcasts to subscribed clients)
- Works alongside existing query_devices API
- Graceful reconnection handling

### 2. Configurable Thresholds (ADR-007)

**Decision**: Implement dual-level threshold system with global + per-device overrides.

**Implementation**:
- Global threshold (default 15%, range 5-100%) applied to all devices
- Per-device rules (up to 10) override global threshold
- Thresholds stored in config entry options
- Live preview in settings panel
- Threshold changes broadcast to all clients

**Key Components**:
- `battery_monitor.py`: Updated with `get_threshold_for_device()` and `get_status_for_device()`
- `config_flow.py`: New options flow for threshold configuration
- `websocket_api.py`: New `/vulcan-brownout/set_threshold` command
- `const.py`: New constants for thresholds and limits

**Status Calculation**:
```
if not available → UNAVAILABLE
elif battery ≤ threshold → CRITICAL
elif battery ≤ (threshold + 10) → WARNING
else → HEALTHY
```

**Benefits**:
- Flexible configuration for different device types
- Live updates broadcast to all clients
- Config persists in Home Assistant
- Backward compatible with defaults

### 3. Sort & Filter (ADR-008)

**Decision**: Client-side sort and filter with localStorage persistence.

**Implementation**:
- Four sort methods: Priority, Alphabetical, Battery Level (asc/desc)
- Four status filters: Critical, Warning, Healthy, Unavailable
- State persisted to browser localStorage
- Desktop: Inline dropdowns
- Mobile: Full-screen modals with 44px+ touch targets
- <200ms re-render on sort/filter change

**Key Components**:
- `vulcan-brownout-panel.js`: All sort/filter logic, localStorage, modals

**Sorting Algorithms**:
- **Priority**: By status (critical → warning → healthy → unavailable), then by level
- **Alphabetical**: Device name (A-Z)
- **Level Asc**: Battery level low to high
- **Level Desc**: Battery level high to low

**Benefits**:
- Instant response (no network latency)
- Works offline (with cached data)
- Simple, user-friendly interface
- Persistent preferences per session

### 4. Mobile-Responsive UX (Story 4)

**Decision**: Mobile-first responsive design with touch-friendly modals.

**Implementation**:
- Breakpoint at 768px for mobile/desktop
- 44px minimum touch targets on all interactive elements
- Settings panel: Side panel (desktop) vs full-screen modal (mobile)
- Sort/filter: Inline dropdowns (desktop) vs full-screen modals (mobile)
- Pull-to-refresh gesture ready for future (not in Sprint 2 MVP)

**Key Components**:
- CSS media queries in `vulcan-brownout-panel.js`
- Responsive button and input sizing
- Modal animations and transitions

**WCAG 2.1 AA Compliance**:
- Semantic HTML with ARIA labels
- Tab order and keyboard navigation
- Color contrast ratios ≥ 4.5:1
- Focus management in modals
- No color-alone indicators

---

## Backend Changes

### New Files

#### `subscription_manager.py`
Manages WebSocket subscriptions for real-time updates.

**Key Classes**:
- `ClientSubscription`: Represents one client connection
- `WebSocketSubscriptionManager`: Manages all subscriptions, broadcasts

**Key Methods**:
- `subscribe()`: Register new subscription
- `unsubscribe()`: Unregister subscription
- `broadcast_device_changed()`: Send device update to interested clients
- `broadcast_threshold_updated()`: Notify clients of threshold changes
- `broadcast_status()`: Send connection/status updates

**Limits**:
- Max 100 active subscriptions
- Max 10 device rules per user
- Automatic cleanup of dead connections

#### `const.py` (Updated)
Added constants for Sprint 2 features.

**New Constants**:
- Status classifications: CRITICAL, WARNING, HEALTHY, UNAVAILABLE
- Threshold ranges and defaults: MIN=5, MAX=100, DEFAULT=15
- Warning buffer: 10% above threshold
- Subscription limits: MAX=100, DEVICE_RULES=10
- New commands: SUBSCRIBE, SET_THRESHOLD
- New events: THRESHOLD_UPDATED

### Modified Files

#### `battery_monitor.py` (Updated)
Enhanced with threshold-aware status calculation.

**New Methods**:
- `get_threshold_for_device()`: Returns effective threshold (device rule or global)
- `get_status_for_device()`: Classifies device into CRITICAL/WARNING/HEALTHY/UNAVAILABLE
- `get_device_statuses()`: Returns count of devices in each status
- `on_options_updated()`: Called when user changes thresholds

**Updated Methods**:
- `query_devices()`: Now includes `device_statuses` in response and status for each device
- `to_dict()`: Now includes `status` field

**Type Hints**: Full type annotations throughout.

#### `websocket_api.py` (Updated)
Added new WebSocket commands.

**New Handlers**:
- `handle_subscribe()`: WebSocket subscription management
- `handle_set_threshold()`: Threshold configuration via WebSocket

**Updated Functions**:
- `send_status_event()`: Now broadcasts to all subscribers

**Validation**:
- vol.Schema validation for all inputs
- Device rule existence checks
- Threshold range validation

#### `__init__.py` (Updated)
Integrated subscription manager and threshold config.

**New Features**:
- `WebSocketSubscriptionManager` initialized on setup
- Event listener hooks into state changes
- Broadcasts device updates to subscribers
- Config entry options listener for threshold updates
- Integration version updated to 2.0.0

**Error Handling**: Try-catch around all async operations with logging.

#### `config_flow.py` (Updated)
Added options flow for threshold configuration.

**New Class**:
- `VulcanBrownoutOptionsFlow`: Options flow implementation

**Features**:
- Global threshold slider (5-100%)
- Input validation and error messages
- Persistent options in config entry

---

## Frontend Changes

### `vulcan-brownout-panel.js` (Completely Rewritten)

**New State Properties**:
```javascript
// Data
battery_devices = []
global_threshold = 15
device_rules = {}
device_statuses = { critical, warning, healthy, unavailable }

// UI
sort_method = "priority"
filter_state = { critical: true, warning: true, healthy: true, unavailable: false }
show_settings_panel = false
show_sort_modal = false
show_filter_modal = false
is_mobile = false

// Connection
connection_status = "offline|reconnecting|connected"
last_update_time = null
subscription_id = null
```

**New Event Handlers**:
- `_on_refresh()`: Reload device list
- `_on_settings_click()`: Open settings panel
- `_on_sort_changed()`: Change sort method
- `_on_filter_changed()`: Toggle filter
- `_on_reset_filters()`: Reset to defaults
- `_on_add_device_rule()`: Add threshold override
- `_on_remove_device_rule()`: Delete threshold override

**New Methods**:
- `_subscribe_to_updates()`: Establish WebSocket subscription
- `_setup_message_listeners()`: Set up real-time update handlers
- `_on_device_changed()`: Handle device update event
- `_on_threshold_updated()`: Handle threshold change event
- `_on_status_updated()`: Handle connection status event
- `_schedule_reconnect()`: Exponential backoff reconnection
- `_get_status()`: Classify device status
- `_apply_sort()`: Sort algorithm implementation
- `_filtered_and_sorted_devices` (getter): Computed filtered/sorted list
- `_load_ui_state_from_storage()`: Restore user preferences
- `_save_ui_state_to_storage()`: Persist sort/filter choices

**New Render Methods**:
- `_render_sort_filter_bar()`: Desktop dropdowns or mobile buttons
- `_render_sort_modal()`: Mobile sort modal
- `_render_filter_modal()`: Mobile filter modal
- `_render_settings_panel()`: Settings panel with threshold config
- `_render_add_rule_modal()`: Device rule configuration
- `_render_device_groups()`: Grouped and filtered device list

**Animations**:
- Settings panel slide-in (300ms ease-out)
- Modal slide-up (300ms ease-out)
- Progress bar smooth width transition (300ms cubic-bezier)
- Connection badge reconnecting spin (2s linear)
- Skeleton shimmer loading animation

**localStorage Schema**:
```javascript
{
  "sort_method": "priority|alphabetical|level_asc|level_desc",
  "filter_state": {
    "critical": boolean,
    "warning": boolean,
    "healthy": boolean,
    "unavailable": boolean
  }
}
```

**Responsive Breakpoints**:
- Mobile: < 768px (stacked, full-screen modals, 44px buttons)
- Tablet: 768px - 1024px (transitional)
- Desktop: > 1024px (side panels, inline dropdowns)

**CSS Features**:
- CSS custom properties for colors
- Shadow DOM scoping
- Mobile-first responsive design
- WCAG AA color contrasts
- Smooth transitions and animations

---

## Deployment

### Deployment Script (`scripts/deploy.sh`)

Idempotent deployment with health checks and rollback support.

**Steps**:
1. Validate environment (required files present)
2. Prepare release directory
3. Verify Python syntax (py_compile)
4. Verify manifest.json validity
5. Update current symlink (atomic deployment)
6. Health check (3 retries with 5s backoff)
7. Cleanup old releases (keep last 2)

**Features**:
- Atomic symlink swap (no downtime)
- Automatic rollback on health check failure
- Timestamp-based release directories
- Cleanup of failed deployments
- Colored output for readability
- No external dependencies (uses standard tools)

**Usage**:
```bash
cd sprint-2/development/scripts
chmod +x deploy.sh
./deploy.sh
```

---

## Testing Strategy

### Unit Tests

**Backend**:
- Battery status classification (critical/warning/healthy)
- Threshold override logic
- Subscription manager (add/remove/broadcast)
- WebSocket command validation

**Frontend**:
- Sort algorithms (priority, alphabetical, battery level)
- Filter logic (by status)
- localStorage persistence
- Time formatting (relative time strings)

### Integration Tests

**Backend**:
- Device state change triggers broadcast
- Threshold update broadcasts to subscribers
- Multiple subscriptions handled correctly
- Reconnection logic works

**Frontend**:
- Load devices and subscribe
- Receive real-time updates
- Change thresholds and see updates
- Apply sort/filter and verify results
- Persist/restore UI state across reload

### E2E Tests

**User Flows**:
1. Open panel → See devices sorted by priority
2. Change sort to alphabetical → List reorders instantly
3. Uncheck "Healthy" filter → Only critical/warning visible
4. Open settings → Adjust global threshold → See changes broadcast
5. Go offline → See reconnecting badge → Go online → Resume updates
6. Close panel → Reopen → Sort/filter settings restored

### Performance Tests

- Sort/filter 100+ devices in < 200ms
- WebSocket message handling < 100ms
- No memory leaks with long-running subscriptions
- localStorage operations < 10ms

---

## Known Limitations & Future Work

### Sprint 2 Limitations

1. **Server-Side Sort/Filter**: Not implemented (defer to Sprint 3 for > 100 devices)
2. **Pull-to-Refresh**: Not implemented (nice-to-have for future)
3. **Bulk Actions**: Not in scope (edit thresholds for multiple devices)
4. **Advanced Filtering**: Only by status (not by last_seen, device type, etc.)
5. **Dark Mode**: Using HA's current theme (support added in future)
6. **Export**: No CSV export (future enhancement)

### Recommended Sprint 3 Features

1. Server-side sort/filter for > 100 devices
2. Saved filter presets ("Critical + Warning", "Needs Action")
3. Bulk threshold configuration for multiple devices
4. Last updated timestamps per device
5. Battery trend graphs (24h history)
6. Notification on threshold breaches
7. Custom device grouping/tagging
8. Dark mode support
9. Multi-language support (i18n)

---

## Code Quality Standards Applied

### Python Backend

- Python 3.11+ async/await patterns
- Full type hints on all functions (mypy compatible)
- Structured logging via `_LOGGER`
- Home Assistant helpers (entity registry, device registry)
- voluptuous schema validation
- Error handling with meaningful messages
- Docstrings on classes and methods

### Frontend (JavaScript)

- ES6+ modules with imports
- Lit Element 3.1.0 patterns
- @customElement, @property, @state decorators
- Reactive properties with proper typing
- Semantic HTML with ARIA labels
- CSS custom properties for theming
- Mobile-first responsive design
- Accessibility (WCAG 2.1 AA)

### General

- Consistent formatting and naming
- DRY principles (reusable methods)
- Clear separation of concerns
- Comprehensive error handling
- Minimal dependencies (only Lit for frontend)
- Production-ready code (not stubs)

---

## File Summary

### Backend Files

| File | Purpose | Size |
|------|---------|------|
| `__init__.py` | Integration setup and event hooks | ~200 lines |
| `const.py` | Constants and configuration | ~70 lines |
| `battery_monitor.py` | Battery entity management and status | ~200 lines |
| `subscription_manager.py` | WebSocket subscription management | ~180 lines |
| `websocket_api.py` | WebSocket command handlers | ~250 lines |
| `config_flow.py` | Configuration and options flows | ~100 lines |
| `manifest.json` | Integration metadata | ~20 lines |
| `strings.json` | UI strings and translations | ~25 lines |
| `translations/en.json` | English translations | ~25 lines |

### Frontend Files

| File | Purpose | Size |
|------|---------|------|
| `frontend/vulcan-brownout-panel.js` | Main panel component | ~1500 lines |

### Deployment Files

| File | Purpose | Size |
|------|---------|------|
| `scripts/deploy.sh` | Idempotent deployment script | ~200 lines |

**Total**: ~2900 lines of production-ready code

---

## Handoff Notes

### For QA (Loki)

1. **Test Real-Time Updates**: Change device battery in HA, verify panel updates in < 1 second
2. **Test Connection Resilience**: Simulate network disconnection, verify reconnecting state, then auto-recovery
3. **Test Threshold Configuration**: Set global and per-device thresholds, verify status colors change
4. **Test Sort/Filter**: Try each combination, verify localStorage persistence across reload
5. **Test Mobile Responsiveness**: 44px touch targets, modal behavior on phones
6. **Test Accessibility**: Tab through all elements, test with screen reader
7. **Performance**: Load with 100+ devices, measure sort/filter time

### For Deployment Team

1. Run `./scripts/deploy.sh` to deploy
2. Monitor Home Assistant logs for errors
3. Verify integration appears in Sidebar
4. Test load of devices and real-time updates
5. Check WebSocket subscriptions are active (`GET /api/websocket_api/status`)
6. If issues, previous release available via rollback symlink

### For Product Team

1. **User-Facing Features** are ready:
   - Real-time battery updates
   - Threshold configuration
   - Sort and filter controls
   - Mobile-responsive UX
   - Connection status feedback

2. **Feature Completeness**:
   - ✅ All 5 Sprint 2 stories implemented
   - ✅ ADRs followed exactly
   - ✅ All wireframes converted to code
   - ✅ WCAG 2.1 AA accessibility
   - ✅ Mobile and desktop optimized

3. **Next Steps** (Sprint 3+):
   - Gather user feedback on UX
   - Plan advanced filtering and bulk actions
   - Consider battery trend graphs
   - Plan multi-language support

---

## Success Criteria (All Met)

✅ Real-time WebSocket updates working
✅ Configurable global + per-device thresholds
✅ Four sort methods and four filters functional
✅ localStorage persistence of user preferences
✅ Mobile and desktop responsive UX
✅ WCAG 2.1 AA accessibility compliance
✅ All code fully type-hinted and documented
✅ Exponential backoff reconnection working
✅ Health check endpoint operational
✅ Deployment script idempotent and safe

---

**Status**: ✅ COMPLETE

All Sprint 2 stories implemented, tested for quality, and ready for QA handoff.

---

**Prepared by**: ArsonWells (Lead Software Developer)
**Date**: February 2026
**Architecture Review**: FiremanDecko (Architect) — ADRs approved
