> **Note: The wireframes below (Sprint 6 tab navigation) document a feature that was **not implemented** in v6.0.0. They are preserved for historical context but do **not** represent the current product design.

---

# Historical Wireframes (Archived)

The Sprint 6 wireframe set (Wireframes 17–19) proposed a tab-based interface to show unavailable devices alongside the low battery view. This feature was not included in the v6.0.0 release as part of the architecture simplification (see CLAUDE.md for current v6.0.0 scope).

---

# Wireframes — v6.0.0 (Current)

**By**: Luna (UX) | **Status**: Current | **Date**: 2026-02-23

## Wireframe 1: Main Panel — Low Battery Devices List

Simple table layout showing all battery entities below the 15% threshold, sorted by battery level (lowest first). No tabs, no filtering, no pagination controls.

```wiremd
<!-- Wireframe 1: Low Battery Devices Table — Luna | v6.0.0 | 2026-02-23 -->

# 🔋 Battery Monitoring | Connected 🟢

---

| Last Seen | Entity | Area | Mfr / Model | % |
|-----------|--------|------|-------------|---|
| 2m ago | Front Door Lock | Entrance | Schlage BE469 | **8%** |
| 5m ago | Motion Sensor Kitchen | Kitchen | Aqara MS-S02 | **12%** |
| 8m ago | Patio Door Sensor | Outside | Sonoff SNZB-04 | **14%** |
```

### Table Columns

```wiremd
| Column | Content | Notes |
|--------|---------|-------|
| Last Seen | Time since last update | Relative format: "2m ago", "1h ago" |
| Entity | Device friendly name | Clickable link to entity detail page |
| Area | Physical location | From HA area registry; "N/A" if not assigned |
| Mfr / Model | Manufacturer and model | From device registry; "Unknown" if not available |
| % | Battery percentage | Red text for critical (≤15%), larger font |
```

---

## Wireframe 2: Empty State — No Low Battery Devices

When all battery devices are above 15%, show a positive empty state message.

```wiremd
<!-- Wireframe 2: Empty State — Luna | v6.0.0 | 2026-02-23 -->

# 🔋 Battery Monitoring | Connected 🟢

---

> :battery: **All batteries above 15%**
> No low battery devices found.
```

---

## Design Consistency Rules (v6.0.0)

1. **No tabs** — Single view of low battery devices only.
2. **No filters or sorting controls** — Display all critical devices (≤15%) in battery level order.
3. **No pagination** — Show all devices on one scrollable view.
4. **Simple table layout** — Five columns (Last Seen, Entity, Area, Mfr/Model, %). No additional metadata.
5. **Fixed 15% threshold** — Not configurable by the user.
6. **Real-time updates** — Via WebSocket `subscribe` command to push `entity_changed` events.
7. **Minimal header** — Title + connection status indicator (green dot = connected).
8. **No modals or settings** — Out of scope for v6.0.0.
