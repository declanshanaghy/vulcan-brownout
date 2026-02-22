# Vulcan Brownout

Custom Home Assistant integration for real-time monitoring of low-battery devices and unavailable entities.

[Product Brief](product-brief.md) · [Pipeline](vulcan-brownout-team/pipeline/SKILL.md) · [Git Convention](vulcan-brownout-team/git-commit/SKILL.md)

## Team

| Role | Name | Skill | Output |
|------|------|-------|--------|
| Product Owner | Freya | [SKILL.md](vulcan-brownout-team/product-owner/SKILL.md) | [design/](design/) |
| UX Designer | Luna | [SKILL.md](vulcan-brownout-team/ux-designer/SKILL.md) | [design/](design/) |
| Architect | FiremanDecko | [SKILL.md](vulcan-brownout-team/architect/SKILL.md) | [architecture/](architecture/) |
| Lead Developer | ArsonWells | [SKILL.md](vulcan-brownout-team/lead-dev/SKILL.md) | [development/](development/) |
| QA Tester | Loki | [SKILL.md](vulcan-brownout-team/qa-tester/SKILL.md) | [quality/](quality/) |

---

## Freya + Luna — Design

Freya (PO) and Luna (UX) collaborate to produce the product design brief, wireframes, and interaction specs.

- [Product Design Brief](design/product-design-brief.md)
- [Wireframes](design/wireframes.md)
- [Interactions](design/interactions.md)
- [Mermaid Style Guide](vulcan-brownout-team/ux-designer/ux-assets/mermaid-style-guide.md)

---

## FiremanDecko — Architecture

Translates product vision into technical solutions.

- [System Design](architecture/system-design.md)
- [API Contracts](architecture/api-contracts.md)
- [Sprint Plan](architecture/sprint-plan.md)
- [Delegation Brief](architecture/delegation-brief.md)
- ADRs: [Integration](architecture/adrs/ADR-001-integration-architecture.md) · [Frontend](architecture/adrs/ADR-002-frontend-panel-technology.md) · [Deployment](architecture/adrs/ADR-003-deployment-architecture.md) · [Secrets](architecture/adrs/ADR-004-secrets-management.md) · [Test Env](architecture/adrs/ADR-005-test-environment-setup.md) · [WebSocket](architecture/adrs/ADR-006-websocket-subscriptions.md) · [Thresholds](architecture/adrs/ADR-007-threshold-configuration.md) · [Sort/Filter](architecture/adrs/ADR-008-sort-filter-implementation.md)

---

## ArsonWells — Development

Implements the architecture using latest best practices.

- [Source Code](development/src/custom_components/vulcan_brownout/)
- [Implementation Plan](development/implementation-plan.md)
- [QA Handoff](development/qa-handoff.md)
- [Deploy Script](development/scripts/deploy.sh)

---

## Loki — Quality

Validates everything as devil's advocate with idempotent scripts.

- [Test Plan](quality/test-plan.md)
- [Test Cases](quality/test-cases.md)
- [Quality Report](quality/quality-report.md)
- [Executive Summary](quality/EXECUTIVE-SUMMARY.md)
- [Deploy Script](quality/scripts/deploy.sh)
- [Test Env Setup](quality/scripts/setup-test-env.sh)

---

## Shared Resources

- [Product Brief](product-brief.md)
- [Git Commit Convention](vulcan-brownout-team/git-commit/SKILL.md)
- [Mermaid Style Guide](vulcan-brownout-team/ux-designer/ux-assets/mermaid-style-guide.md)
- [Kanban Pipeline](vulcan-brownout-team/pipeline/SKILL.md)
