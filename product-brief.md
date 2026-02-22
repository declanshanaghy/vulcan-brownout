# Product Brief: Vulcan Brownout

HA custom integration: dedicated sidebar panel for battery monitoring.

## Core Features
- Real-time WebSocket monitoring of battery levels and entity availability
- Configurable low-battery threshold (default 15%, per-device overrides)
- Server-side cursor-based pagination with infinite scroll (200+ devices)
- Proactive HA notifications when batteries drop below threshold
- Auto-detecting dark mode / theme support
- Sort/filter by priority, alphabetical, battery level

## Technical Constraints
- Max 5 stories/sprint, deployment story mandatory
- QA tests against predefined HA server (not local dev), SSH access required
- Secrets in `.env` (gitignored), `.env.example` committed
- All diagrams use Mermaid syntax

## Target Users
HA users with battery-powered devices (sensors, locks, etc.) needing centralized monitoring.

## Sprint 4+ Backlog
- Battery degradation graphs / historical trends
- Notification scheduling (quiet hours, do-not-disturb)
- Bulk operations (apply threshold to multiple devices)
- Multi-language support (i18n framework ready)
- Advanced filtering (manufacturer, device_class, last_seen)
- CSV/JSON export
- Mobile app deep linking
