# Product Brief: Vulcan Brownout

## Project Overview
Vulcan Brownout is a custom Home Assistant integration that provides real-time monitoring of low-battery devices and unavailable entities. It adds a dedicated sidebar panel with server-side sorting, pagination, and infinite scroll capabilities.

## Core Value Proposition
- **Real-time monitoring**: Track battery levels and entity availability
- **Custom threshold**: Configurable low-battery alert level (default 15%)
- **Efficient UI**: Server-side processing for smooth scrolling
- **Focus**: Dedicated view for battery-related entities

## Key Features
1. Dedicated sidebar panel for battery monitoring
2. Real-time updates for battery levels and entity status
3. Configurable low-battery threshold
4. Server-side sorting and pagination
5. Infinite scroll implementation
6. Filtering by device_class=battery

## Technical Constraints
- Max stories per sprint: 5
- Code review required
- UX review optional
- QA testing optional
- Every sprint must include stories for idempotent deployment scripts
- QA tests against a predefined Home Assistant server (not local dev)
- Integration installation requires SSH access to the HA server
- All secrets (SSH keys, HA tokens, server addresses) stored in a `.env` file — loaded at runtime
- The `.env` file MUST be in `.gitignore` — never committed to the repo
- A `.env.example` template with placeholder values must be committed for reference
- All diagrams (architecture, flow, sequence, state, etc.) must use Mermaid syntax

## Target Users
Home Assistant users with:
- Battery-powered devices (sensors, locks, etc.)
- Large numbers of entities
- Need for centralized battery monitoring

## Success Metrics
- Integration installed in 100+ Home Assistant instances
- 4+ star rating on HACS
- Positive user feedback on battery monitoring experience
