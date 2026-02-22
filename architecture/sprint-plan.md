# Sprint 3 Plan

**Duration**: 2 weeks | **Capacity**: 16 days | **Planned**: 12 days | **Buffer**: 4 days

## Stories

| # | Story | Effort | Priority | Status |
|---|-------|--------|----------|--------|
| 1 | Binary Sensor Filtering | 1 day | P1 | DONE |
| 2 | Infinite Scroll + Cursor Pagination | 3 days | P1 | DONE |
| 3 | Notification System + Preferences UI | 4 days | P1 | DONE |
| 4 | Dark Mode / Theme Support | 2 days | P1 | DONE |
| 5 | Deployment & Infrastructure | 2 days | P0 | DONE |

## Acceptance Criteria (Summary)

**S1 - Binary Sensor Filter**: Exclude binary_sensor domain + require numeric battery_level. Empty state UI. 45 test entities removed.

**S2 - Infinite Scroll**: Cursor-based pagination (50/page), skeleton loaders, back-to-top button (after 30 items), scroll position restoration (sessionStorage), no duplicates, 200+ devices tested, mobile 60 FPS.

**S3 - Notifications**: Global toggle + per-device toggles, frequency cap (1h/6h/24h), severity filter (critical_only / critical_and_warning), HA persistent_notification service, preferences persist after HA restart, modal UI with search + history.

**S4 - Dark Mode**: Auto-detect HA theme (data-theme → matchMedia → localStorage), CSS custom properties, MutationObserver for live theme changes, WCAG AA contrast (4.5:1), no flashing, 300ms transition.

**S5 - Deployment**: Idempotent script, .env validation, health check endpoint, rollback via symlink, secrets never in git, smoke test (trigger notification post-deploy).

## Dependencies
- HA 2026.2.2+ required
- Test HA instance pre-provisioned with 150+ entities

## Sprint 4 Backlog
Battery degradation graphs, notification scheduling (quiet hours), bulk operations, multi-language, advanced filtering, CSV/JSON export, mobile app deep linking.
