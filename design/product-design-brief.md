> **Note: The design briefs below (Sprints 4, 5, 6) document features that were **removed in v6.0.0** as part of the architecture simplification. They are preserved here for historical context and to understand past design decisions, but they do **not** represent the current product.
>
> **v6.0.0 Architecture (Current)**: Fixed 15% battery threshold, battery entities only (`device_class=battery`), no filtering, sorting, pagination, configurable thresholds, notifications, or tab navigation. Two WebSocket commands: `query_entities` (no params) and `subscribe`.
>
> The features below (theme detection, filtering, unavailable devices tab) are **NOT IMPLEMENTED** in v6.0.0.

---

# Historical Design Briefs (Archived)

## ADR: Why These Features Were Removed

See `architecture/adrs/` for ADRs explaining the simplification decisions that led to v6.0.0. Sprint 4-6 designs represent a more complex feature set that was later consolidated into the current minimal, focused implementation.

---

# Product Design Brief — v6.0.0 (Current)

**By**: Freya (PO) + Luna (UX) | **Status**: CURRENT | **Date**: 2026-02-23

## Problem Statement

**Simple Battery Monitoring for Home Assistant**: Users with 10-100+ battery-powered devices (sensors, locks, remotes) need a quick way to see which devices have low batteries without complex filtering, sorting, or configuration.

## Design Principles

1. **Fixed 15% threshold** — No user configuration. Devices below 15% are flagged as critical.
2. **Battery entities only** — `device_class=battery` entities only. Binary sensors and other entity types are excluded.
3. **No filtering, sorting, pagination** — Display all critical devices in a simple list. Minimal mental model.
4. **Minimal UI** — A single sidebar panel with a table and optional real-time updates via WebSocket subscription.
5. **No notifications, no modals, no settings** — Out of scope for v6.0.0. Add in future sprints if needed.

## Target User

HA users who:
- Have 10-100+ battery-powered devices
- Need a at-a-glance view of critical low batteries
- Don't need complex filtering or sorting
- Want a minimal, native-feeling HA integration

## UI Layout

Simple table with columns:
- **Last Seen**: Time since last update
- **Entity**: Device friendly name (clickable to entity detail)
- **Area**: Physical location from HA area registry
- **Manufacturer / Model**: From device registry
- **% Remaining**: Battery level percentage, red color for critical

Empty state when no devices below threshold:
> ✓ **All batteries above 15%**
> No low battery devices found.

## WebSocket API (v6.0.0)

Two commands only:
1. **`query_entities`** (no params) → returns `{ entities: [...], total: N }`
2. **`subscribe`** → opens real-time stream, emits `entity_changed` events

No filtering, sorting, or pagination parameters.
