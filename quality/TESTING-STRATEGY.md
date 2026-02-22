# QA Testing Strategy (Summary)

## Approach
3 phases: Environment validation → Integration testing (WebSocket API) → E2E testing (Playwright)

## Tools
- Python websocket-client for API integration tests
- Playwright for E2E (Shadow DOM piercing, chromium only)
- Real HA staging instance (not mocked)
- HA long-lived access token auth
- Pre-provisioned test entities in HA config

## Test Categories
Integration: WebSocket commands, entity discovery, pagination, notifications, thresholds
E2E: Panel load, infinite scroll, settings modal, notification modal, dark mode, empty state
Performance: Load times, scroll FPS, notification latency

## Current Status
- Integration test suite: 28 tests (Sprint 3), 19 tests (Sprint 2 live)
- E2E framework: Implemented (68 test cases, 6 suites), not yet run against staging
- See SPRINT3-INDEX.md for latest results
