# Vulcan Brownout

HA custom integration: real-time battery monitoring panel with notifications, infinite scroll, dark mode.

**Status**: Sprint 3 on HOLD (24/28 tests pass, bugs triaged). Sprint 4 architecture ready.

> ⚠️ **Git push is disabled in this environment.** Agents must commit locally only. The repo owner (Dek) handles all pushes to GitHub manually.

## Team

| Role | Agent | Model | Skill |
|------|-------|-------|-------|
| Product Owner | Freya | Opus | [SKILL](vulcan-brownout-team/product-owner/SKILL.md) |
| UX Designer | Luna | Sonnet | [SKILL](vulcan-brownout-team/ux-designer/SKILL.md) |
| Architect | FiremanDecko | Opus | [SKILL](vulcan-brownout-team/architect/SKILL.md) |
| Lead Developer | ArsonWells | Sonnet | [SKILL](vulcan-brownout-team/lead-dev/SKILL.md) |
| QA Tester | Loki | Sonnet | [SKILL](vulcan-brownout-team/qa-tester/SKILL.md) |

## Workflow

PO + UX Designer -> Design Brief -> Architect -> System Design + API Contracts -> Lead Dev -> Implementation -> QA Tester -> Acceptance. Kanban method. Max 5 stories/sprint. Deployment story mandatory every sprint.

## Key Docs

- [Product Brief](product-brief.md) — What we're building + Sprint 4 backlog
- [System Design](architecture/system-design.md) — How it works (Sprint 3 + Sprint 4)
- [API Contracts](architecture/api-contracts.md) — WebSocket protocol (Sprint 3, no changes Sprint 4)
- [Sprint Plan](architecture/sprint-plan.md) — Current sprint stories
- [Design Brief](design/product-design-brief.md) — UX specs
- [Implementation Status](development/implementation-plan.md) — What's built
- [QA Status](quality/SPRINT3-INDEX.md) — Test results
- [ADR Summary](architecture/adrs/SUMMARY.md) — All architecture decisions
- [Source Code](development/src/custom_components/vulcan_brownout/)
- [Pipeline](vulcan-brownout-team/pipeline/SKILL.md) | [Git Convention](vulcan-brownout-team/git-commit/SKILL.md)

## FiremanDecko — Architect

**Sprint 3 → Sprint 4 Transition**:

- [Sprint 3 Bug Triage](architecture/sprint3-bug-triage.md) — Analysis of 3 QA bugs (all code-complete)
- [Sprint 4 System Design](architecture/system-design.md) — Theme detection via hass.themes.darkMode + UX polish
- [Sprint 4 API Contracts](architecture/api-contracts.md) — No API changes (frontend-only sprint)
- [Sprint 4 Sprint Plan](architecture/sprint-plan.md) — 5 stories: theme detection, empty state, scroll perf, notification UX, deployment
- [Sprint 4 Delegation Brief](architecture/delegation-brief.md) — Full implementation guide for ArsonWells
- [ADR-014: Theme Detection Strategy](architecture/adrs/ADR-014-theme-detection-strategy.md) — hass.themes.darkMode vs DOM sniffing decision
