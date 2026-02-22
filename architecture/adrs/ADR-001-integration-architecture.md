# ADR-001: Integration Architecture

## Status: Proposed

## Context

Sprint 1 requires a Home Assistant integration that can auto-discover all battery-powered devices without user configuration. The integration must:
1. Query and cache battery entities on startup
2. Listen for entity state changes in real-time
3. Expose discovered entities via WebSocket API to the frontend panel
4. Support graceful handling of entity addition/removal during runtime

The PO brief specifies "zero-config" — users install, restart HA, and see all battery devices immediately. This requires:
- Automatic discovery of entities with `device_class=battery`
- No YAML configuration required
- Quick startup time (discovery must complete within 10 seconds)
- HA restart resilience (re-query entities on every restart)

We must decide:
- When discovery runs (startup only vs. periodic polling)
- Where discovered entities are cached (memory, persistent storage, or HA state machine)
- How often battery levels are updated (polling interval vs. event-driven)
- Whether the 15% threshold is hardcoded for Sprint 1 or configurable

## Options Considered

### Option A: Discovery on Startup Only, In-Memory Cache, Event-Driven Updates
- **Discovery:** Runs once during `async_setup_entry()`, queries all entities, filters by `device_class=battery`
- **Caching:** Store filtered entity list in memory (Python dict keyed by entity_id)
- **Updates:** Listen to HA's `state_changed` events; when a battery entity state changes, notify WebSocket clients
- **Threshold:** Hardcoded to 15% in Sprint 1 (no config option)
- **Pros:**
  - Simple, fast startup (no polling loops)
  - Event-driven means real-time updates with zero latency
  - In-memory cache is fast and requires no persistence layer
  - Matches PO's "zero-config" requirement
  - Uses standard HA patterns (config entries, event listeners)
- **Cons:**
  - Cache lost on HA restart (requires re-discovery, but that's acceptable)
  - No periodic sync; if entity registry changes outside HA (unlikely), won't detect it
  - New entities added to HA won't appear until user manually refreshes panel

### Option B: Discovery on Startup + Periodic Polling, Persistent Storage, Mixed Updates
- **Discovery:** On startup AND every 15 minutes
- **Caching:** Store in SQLite or JSON file; survives HA restarts
- **Updates:** Event-driven + polling fallback
- **Threshold:** Configurable via config flow
- **Pros:**
  - Detects new entities without user refresh (better UX)
  - Persistent cache survives HA restart
  - Threshold can be configured per-user preference (roadmap for Sprint 2, but architecture ready)
  - Handles edge cases (entity registry changes, etc.)
- **Cons:**
  - More complex (persistence layer adds ~50 lines of code)
  - Polling adds system load (negligible for 1 polling task)
  - Still requires manual refresh to see new entities immediately (polling is on 15-min interval)
  - HA state machine not designed for persistent domain-specific data

### Option C: Hybrid — Event-Driven Updates + Manual Refresh, Config Entry Storage
- **Discovery:** On startup + on-demand when user clicks refresh
- **Caching:** In-memory (cleared on HA restart, but that's fine)
- **Updates:** Event-driven for battery level changes; refresh button re-queries entities
- **Threshold:** Hardcoded 15% for Sprint 1
- **Pros:**
  - User can manually refresh if they add a new device (explicit control)
  - No polling overhead
  - Very simple to implement
  - Aligns with Sprint 1 UX (manual refresh button already in design)
- **Cons:**
  - User must manually refresh to see newly added devices
  - Slightly more UX friction than Option B

## Decision

**Option A: Discovery on Startup Only, In-Memory Cache, Event-Driven Updates**

This aligns with Sprint 1's MVP scope and the PO's emphasis on simplicity and quick ship-ability.

### Rationale

1. **Zero-Config Requirement:** Option A requires no persistent storage, no config flow UI for threshold (hardcoded 15%), no periodic polling — just startup discovery. This is the simplest path to "install and go."

2. **Real-Time Updates:** Event-driven updates mean users see battery level changes instantly without polling overhead. This is superior UX for Sprint 1's core use case (seeing which devices need attention).

3. **Sprint 1 Scope:** The PO brief explicitly defers threshold configuration to Sprint 2. Option A is the minimum viable implementation that ships value immediately. Option B's persistent storage and threshold config can be added in Sprint 2 if needed.

4. **HA Integration Patterns:** HA's config entry and event listener patterns are mature and well-tested. We avoid inventing new persistence mechanisms when in-memory caching is sufficient for Sprint 1.

5. **User Expectation:** The PO brief says users expect battery entities to appear after restart. We honor this with startup discovery. Users adding new entities later expect to refresh (which they can do via the refresh button). This is reasonable for MVP.

### Implementation Details

**File: `__init__.py` (Integration Entry Point)**
```python
async def async_setup_entry(hass, entry):
    # 1. Initialize BatteryMonitor service
    battery_monitor = BatteryMonitor(hass, threshold=15)  # Hardcoded 15% for Sprint 1

    # 2. Trigger auto-discovery
    await battery_monitor.discover_entities()

    # 3. Store service in hass.data for later access
    hass.data[DOMAIN] = battery_monitor

    # 4. Register WebSocket command
    websocket_api.async_register_command(hass, handle_query_devices)

    # 5. Register event listener for state changes
    hass.bus.async_listen(EVENT_STATE_CHANGED, battery_monitor.on_state_changed)

    # 6. Register sidebar panel
    hass.components.frontend.async_register_panel(
        hass,
        frontend_url_path="vulcan-brownout",
        webcomponent_path="local/vulcan-brownout/vulcan-brownout-panel.js",
        title="Vulcan Brownout",
        icon="mdi:battery-alert"
    )
```

**File: `battery_monitor.py` (Core Service)**
```python
class BatteryMonitor:
    def __init__(self, hass, threshold=15):
        self.hass = hass
        self.threshold = threshold
        self.entities = {}  # In-memory cache: {entity_id: EntityData}

    async def discover_entities(self):
        """Query HA for all entities with device_class=battery."""
        for entity_id, entity_state in self.hass.states.items():
            if self._is_battery_entity(entity_id):
                self.entities[entity_id] = self._parse_entity(entity_id, entity_state)

        logger.info(f"Discovered {len(self.entities)} battery entities")

    async def on_state_changed(self, event):
        """Listen for HA state changes; update cache and notify clients."""
        entity_id = event.data.get("entity_id")

        if not self._is_battery_entity(entity_id):
            return

        new_state = event.data.get("new_state")

        if new_state is None:
            # Entity deleted
            self.entities.pop(entity_id, None)
        else:
            # Entity updated
            self.entities[entity_id] = self._parse_entity(entity_id, new_state)
```

**Consequences:**

Positive:
- Minimal code, fast startup, zero persistence complexity
- Event-driven = real-time battery level updates
- Aligns with HA conventions
- Users see newly added entities after clicking refresh button

Negative:
- New entities don't auto-appear (must click refresh)
- Cache lost on HA restart (re-discovery takes ~100ms, negligible)
- Threshold not configurable in Sprint 1 (fine; deferred to Sprint 2)
- No periodic sync (acceptable; HA registry changes are rare)

## Open Questions Resolved by This ADR

From Product Design Brief:

1. **Auto-discovery mechanism: Should discovery run on startup only, or periodically?**
   - **Answer:** Startup only. Users can click refresh to pick up new entities.

2. **Entity caching: Where should discovered entities be stored?**
   - **Answer:** In-memory dict. Fast, simple, sufficient for Sprint 1.

3. **Update polling: How frequently should battery levels be fetched?**
   - **Answer:** No polling. Event-driven (HA's state_changed events).

4. **Threshold default: Is 15% hardcoded for Sprint 1, or configurable?**
   - **Answer:** Hardcoded 15% for Sprint 1. Configurable in Sprint 2.

## Next Steps

- Lead Developer implements `battery_monitor.py` with discovery and event listening
- QA verifies entities appear in logs after startup
- QA tests that battery level changes trigger WebSocket updates
