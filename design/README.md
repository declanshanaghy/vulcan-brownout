# Design Documentation — Vulcan Brownout

UX design artifacts, interaction specifications, wireframes, and style guides for the Vulcan Brownout Home Assistant integration.

## Current (v6.0.0)

- [**product-design-brief.md**](product-design-brief.md) — Current v6.0.0 design brief: fixed 15% threshold, battery entities only, no filtering/sorting/pagination. Also contains archived briefs from Sprints 4, 5, 6 for historical context.

- [**wireframes.md**](wireframes.md) — Current v6.0.0 wireframes showing the simple main panel layout and empty state. Wireframes 17-19 (Sprint 6 tabs) are archived.

- [**interactions.md**](interactions.md) — Interaction specifications for Interactions 2-3, 6-8, and 10 describing current v6.0.0 behaviors: infinite scroll, back-to-top, empty/error states, scroll persistence, mobile responsiveness. Archived interactions 1, 9, 11-13 are preserved for historical context.

- [**mermaid-style-guide.md**](mermaid-style-guide.md) — Conventions for creating Mermaid diagrams: color palette, node shapes, edge styles, and pattern examples. **Evergreen reference for all team members creating diagrams.**

## Archived (Not in v6.0.0)

The following features were planned in Sprints 4-6 but were **not implemented** in v6.0.0:

- **Sprint 4**: Theme detection via `hass_themes_updated` event, theme switching, notifications modal, settings modal
- **Sprint 5**: Server-side filtering by manufacturer/device class/status/area, filter dropdowns, chip row, mobile bottom sheet filter UI, dynamic filter population
- **Sprint 6**: Unavailable devices tab, tab navigation, real-time unavailable entity streaming

These archived designs are preserved in `product-design-brief.md` (Sprints 4-6 sections marked as archived) for understanding past decisions and future reference.

## v6.0.0 Architecture

See [CLAUDE.md](../CLAUDE.md) in the repository root for the authoritative description of v6.0.0 architecture:
- Fixed 15% battery threshold (not configurable)
- Battery entities only (`device_class=battery`)
- No filtering, sorting, pagination
- Two WebSocket commands: `query_entities` (query) and `subscribe` (real-time updates)
- Minimal UI: single panel, no modals, no settings

---

**Last updated**: 2026-02-24 | **Status**: Current with archived historical content (interactions.md reorganized for clarity)
