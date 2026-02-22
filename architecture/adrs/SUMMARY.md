# ADR Summary

All architecture decisions for Vulcan Brownout. Full ADR docs in this directory.

| ADR | Decision | Sprint |
|-----|----------|--------|
| 001 | Event-driven updates + in-memory cache for battery entity discovery | 1 |
| 002 | Lit Element for frontend panel (HA native, Shadow DOM) | 1 |
| 003 | Bash + rsync SSH deployment with health checks and rollback via symlinks | 1 |
| 004 | .env file for secrets, .env.example committed, never log tokens | 1 |
| 005 | Pre-provisioned mock entities in test HA configuration.yaml | 1 |
| 006 | WebSocket push events for real-time battery updates (subscribe pattern) | 2 |
| 007 | HA ConfigEntry.options for threshold storage (global + per-device rules, max 10) | 2 |
| 008 | Client-side sort/filter with localStorage persistence | 2 |
| 009 | Cursor-based pagination (base64 last_changed\|entity_id), replaces offset | 3 |
| 010 | HA persistent_notification service for battery alerts + frequency caps | 3 |
| 011 | CSS custom properties + MutationObserver for auto dark mode (3-level detection) | 3 |
| 012 | Server-side filter: exclude binary_sensor domain + require numeric battery_level 0-100 | 3 |
| 013 | Playwright for E2E testing (Shadow DOM piercing, WebSocket mocking, HA auth fixtures) | 3 |
| 014 | hass.themes.darkMode as primary theme source + hass_themes_updated event listener | 4 |
| 015 | Server-side filtering via query_devices filter params + get_filter_options command | 5 |

## ADR-013 Key Decisions (E2E Framework)
- Real HA staging instance (not mocked) for integration tests
- Playwright with chromium only (not cross-browser initially)
- HA long-lived access token auth (not UI login flow)
- Shadow DOM: use `page.locator()` with `>>` piercing
- WebSocket: test via UI observation (not direct WS interception)
- Test data: pre-provisioned entities in test HA config
- CI: GitHub Actions with Playwright container
- Coverage: Critical paths first (panel load, pagination, notifications, theme)
