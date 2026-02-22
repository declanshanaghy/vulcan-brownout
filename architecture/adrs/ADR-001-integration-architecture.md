# ADR-001: Integration Architecture

## Status: Proposed

## Decision

**Option A: Discovery on Startup Only, In-Memory Cache, Event-Driven Updates**

Auto-discover battery entities (`device_class=battery`) on startup. Cache in memory. Listen for HA state changes and broadcast real-time updates via WebSocket.

## Rationale

- **Zero-config requirement**: No persistent storage, no polling, simple install-and-go
- **Real-time updates**: Event-driven means instant UI updates with zero latency
- **Sprint 1 scope**: Minimum viable implementation; threshold configuration deferred to Sprint 2
- **HA patterns**: Uses standard HA config entry and event listener APIs
- **User expectation**: Entities appear after restart; manual refresh for newly added devices is acceptable

## Implementation Details

**Startup (async_setup_entry)**:
- Initialize BatteryMonitor service with hardcoded 15% threshold
- Trigger auto-discovery (query all entities, filter by `device_class=battery`)
- Store filtered entity list in memory (Python dict keyed by entity_id)
- Register WebSocket command handler
- Register event listener for `state_changed` events
- Register sidebar panel

**Real-time updates (on_state_changed)**:
- Listen for HA state changes
- Update in-memory cache for battery entities
- Notify all WebSocket subscribers of changed device

**File: `__init__.py`**:
- BatteryMonitor initialization
- WebSocket command registration
- Event listener registration
- Panel registration

**File: `battery_monitor.py`**:
- Entity discovery logic
- In-memory caching (dict keyed by entity_id)
- State change handling

## Consequences

**Positive**:
- Minimal code, fast startup (no persistence complexity)
- Event-driven = real-time updates with zero latency
- Aligns with HA conventions
- Users see newly added entities after clicking refresh

**Negative**:
- New entities don't auto-appear (must click refresh)
- Cache lost on HA restart (acceptable; re-discovery takes ~100ms)
- Threshold not configurable in Sprint 1 (deferred to Sprint 2)
- No periodic sync (entity registry changes are rare)

## Open Items

- Implement refresh button in frontend panel for manually discovering new entities
- Document how to verify entities appear in HA logs after startup
