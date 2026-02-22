# Sprint 1 Architecture — Complete Technical Specification

## What's Here

This directory contains the complete technical specification for Sprint 1 of the Vulcan Brownout project. Everything the Lead Developer needs to implement the MVP is documented here.

## Document Guide

Read these in order:

### 1. Start Here
- **`README.md`** (this file) — Overview and reading guide

### 2. Architecture Decisions
Read all 5 ADRs to understand the trade-offs and rationale:
- **`adrs/ADR-001-integration-architecture.md`** — Backend service design, auto-discovery strategy, event-driven updates
- **`adrs/ADR-002-frontend-panel-technology.md`** — Lit Element choice, WebSocket communication
- **`adrs/ADR-003-deployment-architecture.md`** — SSH + rsync deployment, idempotent scripts
- **`adrs/ADR-004-secrets-management.md`** — .env structure, .gitignore, security
- **`adrs/ADR-005-test-environment-setup.md`** — Mock entity provisioning, test HA configuration

### 3. Technical Design
- **`system-design.md`** — Component diagram, data flows, lifecycle, performance, scaling
- **`api-contracts.md`** — WebSocket message schemas, command/response formats, error handling

### 4. Implementation Plan
- **`sprint-plan.md`** — 5 stories with acceptance criteria, technical notes, estimation
- **`delegation-brief.md`** — Handoff to Lead Developer with implementation guidance, best practices, code review criteria

## Key Decisions (TL;DR)

| Decision | Rationale |
|----------|-----------|
| **Auto-discovery on startup only** | Fast, simple, aligns with Sprint 1 scope |
| **In-memory entity caching** | No persistence layer needed, sufficient for MVP |
| **Event-driven updates** | Real-time responsiveness, zero polling overhead |
| **Hardcoded 15% threshold** | Defers config UI to Sprint 2 |
| **Lit Element for panel** | HA-native, zero bundle size, reactive rendering |
| **SSH + rsync deployment** | Efficient, idempotent, secure |
| **`.env` secrets** | Industry standard, CI/CD compatible |
| **Real HA test instance** | Realistic testing, catches edge cases |

## Sprint Scope

**5 Stories, ~30 story points, 1 week:**

1. **Integration Scaffolding & Auto-Discovery** (8 pts) — Backend service setup, entity discovery
2. **Sidebar Panel Rendering** (6 pts) — Lit component, basic UI
3. **Visual Status Indicators** (4 pts) — Colors, icons, progress bars
4. **Empty State & Error Handling** (6 pts) — Helpful messages, retry logic
5. **Deployment Pipeline** (6 pts) — SSH deployment script, idempotent

## File Structure

```
custom_components/vulcan_brownout/
├── __init__.py                          # Integration entry point
├── const.py                             # Constants
├── battery_monitor.py                   # Core service
├── websocket_api.py                     # WebSocket handlers
├── config_flow.py                       # Configuration (minimal)
├── manifest.json                        # Integration metadata
├── translations/en.json                 # i18n
└── frontend/
    ├── vulcan-brownout-panel.js         # Lit component
    └── styles.css                       # Scoped styles
```

Also in repo root:
- `deploy.sh` — Deployment script
- `.env.example` — Secrets template
- `TESTING.md` — QA setup instructions
- `.gitignore` — Prevent secret commits

## Quick Reference

### Backend Architecture
- **Service:** `BatteryMonitor` maintains in-memory cache of discovered entities
- **Discovery:** On startup, queries HA entity registry for `device_class=battery`
- **Updates:** Listens to HA's `state_changed` events, notifies WebSocket clients
- **API:** WebSocket command `vulcan-brownout/query_devices` with sorting/pagination

### Frontend Architecture
- **Component:** Lit Element custom element `<vulcan-brownout-panel>`
- **Communication:** WebSocket (HA native, uses existing session auth)
- **State:** `battery_devices[]`, `isLoading`, `error`, pagination state
- **Rendering:** Conditional templates for loading/error/empty/list states
- **Styling:** Shadow DOM scoped, uses HA CSS variables for theme support

### Deployment
- **Transfer:** `rsync -avz --delete` (only changed files)
- **Restart:** `docker-compose restart homeassistant`
- **Health Check:** Poll `/api/` endpoint until 200 response
- **Secrets:** Loaded from `.env` (gitignored, never committed)

## Open Questions Resolved

The Product Design Brief asked the Architect to clarify:

1. **Auto-discovery mechanism:** ✅ Startup only (no periodic polling)
2. **Entity caching:** ✅ In-memory dict (no persistence)
3. **Update polling:** ✅ Event-driven (no polling, HA's state_changed events)
4. **Threshold default:** ✅ Hardcoded 15% for Sprint 1 (configurable Sprint 2)
5. **WebSocket vs HTTP:** ✅ WebSocket (real-time, efficient)
6. **Sorting implementation:** ✅ Server-side (backend logic)
7. **Component framework:** ✅ Lit Element (HA native)
8. **SSH key management:** ✅ QA generates key, adds to authorized_keys
9. **Deployment user:** ✅ `homeassistant` user (simplest setup)
10. **Health check endpoint:** ✅ `/api/` (proves HA is ready)
11. **Docker vs Bare Metal:** ✅ Docker (test HA is containerized)
12. **Partial failure handling:** ✅ Show partial list or error (graceful degradation)

## Success Criteria

Sprint 1 is successful when:

1. All 5 stories pass code review and QA testing
2. Integration auto-discovers battery entities without config
3. Panel renders correctly across desktop/tablet/mobile
4. Visual indicators match design (colors, icons, animations)
5. Error and empty states are helpful
6. Deployment script is idempotent and tested
7. No console errors or HA logs pollution
8. Documentation is complete
9. Code is ready to ship to HACS

## For the Lead Developer

Start here: **`delegation-brief.md`**

It contains:
- Implementation guidance for each story
- Code structure and best practices
- Testing requirements
- Code review checklist
- Common pitfalls to avoid
- Timeline and dependencies

## For QA

Start here: **`adrs/ADR-005-test-environment-setup.md`**

It contains:
- How to set up test HA instance with mock entities
- How to connect tests to real HA server
- How to verify integration works

Then: **`sprint-plan.md` → Manual Test Checklists**

For deployment: **`adrs/ADR-003-deployment-architecture.md` and `adrs/ADR-004-secrets-management.md`**

## Key Documents by Role

### Product Owner / UX Designer
- **Product Design Brief** (already exists)
- **Sprint Plan** (`sprint-plan.md`) — Stories, acceptance criteria
- **System Design** (`system-design.md`) — Component overview

### Architect (You Are Here)
- **All ADRs** (001-005) — Document decisions
- **System Design** (`system-design.md`) — Technical architecture
- **API Contracts** (`api-contracts.md`) — Backend/frontend interface

### Lead Developer
- **Delegation Brief** (`delegation-brief.md`) — Implementation guidance
- **API Contracts** (`api-contracts.md`) — What to build
- **ADRs** (001-005) — Why certain choices were made
- **Sprint Plan** (`sprint-plan.md`) — What to build (stories)

### QA
- **ADR-005** (`adrs/ADR-005-test-environment-setup.md`) — Test environment
- **ADR-003 & ADR-004** (Deployment) — How to deploy
- **Sprint Plan** (`sprint-plan.md`) → Manual Test Checklists

## Next Steps

1. **Lead Developer** reads `delegation-brief.md` and starts with Story 1
2. **QA** sets up test HA instance per `ADR-005` and `TESTING.md`
3. **Daily Standup** — Report progress, unblock issues
4. **Code Review** — Each story before merge
5. **Sprint Retrospective** — Lessons learned for Sprint 2

## Repository Structure

```
vulcan-brownout-team/
├── architect/
│   └── SKILL.md                         # Role definition
├── sprints/
│   ├── sprint-0/
│   │   └── architecture/
│   │       ├── system-design.md         # Sprint 0 reference
│   │       └── api-contracts.md         # Sprint 0 reference
│   └── sprint-1/
│       └── architecture/                # ← You are here
│           ├── README.md                # This file
│           ├── system-design.md         # Complete design
│           ├── api-contracts.md         # WebSocket API
│           ├── sprint-plan.md           # 5 stories
│           ├── delegation-brief.md      # For Lead Dev
│           └── adrs/
│               ├── ADR-001-integration-architecture.md
│               ├── ADR-002-frontend-panel-technology.md
│               ├── ADR-003-deployment-architecture.md
│               ├── ADR-004-secrets-management.md
│               └── ADR-005-test-environment-setup.md
└── sprints/
    └── sprint-1/
        └── design/
            ├── product-design-brief.md  # From PO/UX
            ├── wireframes.md            # From UX
            └── interactions.md          # From UX
```

## Contact & Escalation

- **Questions about architecture:** Architect (me)
- **Implementation blockers:** Lead Developer + Architect
- **Test environment issues:** QA + Architect
- **Sprint progress:** Daily standup

---

**Last Updated:** 2026-02-22
**Status:** Ready for Implementation
**Next:** Lead Developer begins Story 1
