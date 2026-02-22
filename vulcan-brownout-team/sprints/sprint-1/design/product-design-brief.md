# Product Design Brief: Sprint 1 — Vulcan Brownout MVP

## Problem Statement

**PO:** Home Assistant users with battery-powered devices (door sensors, motion detectors, smart locks, etc.) today discover dead batteries reactively — when a device stops responding. There is no centralized, real-time view of battery health across their installation. Users must either:
1. Check each device individually in the HA UI
2. Build and maintain custom Lovelace cards with manual YAML configuration
3. Use third-party integrations like Battery Notes, which track replacement dates but not real-time levels

This creates friction, increases support burden, and reduces user satisfaction with their HA setup.

**UX Designer:** From a user experience perspective, the problem is information scattering. When a user opens Home Assistant, there's no single place to see "which of my devices have weak batteries right now?" The cognitive load falls on the user to remember or hunt for the answer.

**PO:** Sprint 1 focuses on solving the core user problem: **Zero-config battery monitoring with a dedicated sidebar panel.** We want users to install Vulcan Brownout, and immediately see all their battery-powered devices ranked by urgency — lowest battery first, unavailable devices highlighted.

---

## Target User

**Primary:** Home Assistant power users with:
- 10+ battery-powered devices (typical smart home with multiple sensors)
- Multiple device types (door locks, motion detectors, window sensors, remotes, etc.)
- Desire for a clean, native HA experience (not custom Lovelace hacks)

**Secondary:** System integrators and HA enthusiasts who maintain instances for others

**Context:**
- Users typically check their HA dashboard multiple times daily
- Battery monitoring is a "background" need — not urgent until something breaks
- Users appreciate integrations that "just work" with zero config

---

## Desired Outcome

After Sprint 1 ships, the user should be able to:

1. Install Vulcan Brownout from HACS
2. Restart Home Assistant (auto-discovery runs in background)
3. Open the Vulcan Brownout sidebar panel
4. See **all battery-powered entities ranked by urgency**:
   - Critical devices (≤15% battery) at top, visually prominent
   - Unavailable/offline devices clearly separated
   - Healthy devices (>15% battery) below
5. Understand at a glance which devices need immediate attention
6. Click a refresh button to manually pull latest data
7. See helpful guidance if no battery entities exist ("Configure devices to appear here")

This is the **MVP**. Sorting controls, pagination, threshold configuration, and infinite scroll are deferred to Sprint 2+.

---

## Interactions & User Flow

### First-Run Experience

**UX Designer:** We focus on a frictionless onboarding flow:

**Step 1: Install**
- User adds Vulcan Brownout via HACS (not in scope for Sprint 1, but assumed)
- Restart Home Assistant
- Integration auto-discovers all `device_class=battery` entities (zero config)

**Step 2: Open Panel**
- User opens sidebar in HA
- Vulcan Brownout appears as a new panel with battery icon
- Panel loads immediately; skeleton loading states appear while fetching data

**Step 3: View Battery List**
- List renders in default sort: **critical first** (implicit, no UX to change sort in Sprint 1)
- Devices ordered by battery level ascending within each status group:
  - Critical (≤15%)
  - Unavailable (offline/error)
  - Healthy (>15%)
- Each device card shows:
  - Device name and icon (inherited from HA device_class)
  - Battery percentage with visual progress bar
  - Color-coded status (red=critical, gray=unavailable, green=healthy)

**Step 4: Take Action**
- User sees a critical device (e.g., "Front Door Lock: 12%")
- User recognizes it needs attention (red background, warning icon)
- User may click to view details (optional, implementation detail for Dev)
- User manually refreshes list via refresh button if needed

**Step 5: Empty State (Alternative)**
- If user has zero battery-powered devices:
  - Friendly message with battery icon
  - CTA button: "Browse Home Assistant Devices"
  - Guides user to configure entities with `device_class=battery`

### User Flow Diagram

```
User opens Vulcan Brownout panel
         ↓
[Auto-discovery complete?]
         ├→ YES
         │   ↓
         │   Load battery entities from HA
         │   ↓
         │   [Any entities found?]
         │   ├→ YES
         │   │   ↓
         │   │   Sort: Critical → Unavailable → Healthy
         │   │   Display list with status colors
         │   │   (show refresh button in header)
         │   │   ↓
         │   │   User sees battery status at a glance
         │   │
         │   └→ NO
         │       ↓
         │       Show empty state ("No devices found")
         │       Provide guidance: "Configure devices with device_class=battery"
         │
         └→ NO (connection error)
             ↓
             Show error state with "Retry" button
             Show last-successful-update timestamp
```

---

## Look & Feel Direction

### Visual Language: Native Home Assistant

**UX Designer:** The panel must feel like a native HA component, not a third-party addon. We use:
- HA's card-based layout (12px spacing between items)
- HA's CSS custom properties for colors (no hardcoded hex)
- HA's `ha-icon` component for device icons
- Sidebar panel dimensions (340-400px on desktop)
- Material Design principles consistent with HA 2.x

### Information Hierarchy

1. **Critical** (≤15% battery): Maximum visual emphasis
   - Red/orange background (`--error-color-background`)
   - Large red status icon
   - Progress bar (red fill)
   - Appears at top of list
   - Used to: Alert user of urgent action needed

2. **Unavailable/Offline**: Clear but not alarming
   - Gray background (`--divider-color`)
   - Gray X or error icon
   - Grouped separately (below critical, above healthy)
   - Used to: Show user which devices are offline

3. **Healthy** (>15% battery): Calm, informative
   - Default card background (`--card-background-color`)
   - Green checkmark icon
   - Subtle progress bar (green)
   - Used to: Provide peace of mind, show device is functioning

### Battery Level Color Coding

- **Critical** (≤15%): Red/orange, warning triangle (`--error-color`)
- **Low** (15-30%): Amber/yellow (`--warning-color`) — *deferred to Sprint 2*
- **Healthy** (>30%): Green (`--success-color`)
- **Unavailable**: Gray (`--disabled-text-color`)

### Density & Readability

- **Card height**: 72px (touch-friendly, not cramped)
- **Font sizes**: 14px device name, 12px battery level (readable on mobile)
- **Icon size**: 24px (consistent with HA)
- **Progress bar**: 4px height (visible, not distracting)

### Responsive Behavior

- **Desktop (>1024px)**: Full 340-400px sidebar, full spacing
- **Tablet (600-1024px)**: Single column, comfortable touch targets
- **Mobile (<600px)**: 100% width, 16px padding, compact but readable

---

## Market Fit & Differentiation

### Why Vulcan Brownout Beats Alternatives

**PO:** Here's how we stack up:

| Feature | Built-in HA | Battery Notes | Custom Lovelace | Vulcan Brownout |
|---------|-------------|---|---|---|
| Real-time battery monitoring | ❌ | ❌ (dates only) | ✅ | ✅ |
| Zero-config auto-discovery | ❌ | ❌ | ❌ | ✅ |
| Dedicated sidebar panel | ❌ | ❌ | ❌ | ✅ |
| Native HA look & feel | N/A | ✅ | Varies | ✅ |
| Installation friction | N/A | Medium (needs config) | High (YAML config) | **Low (HACS + restart)** |
| Works out of the box | N/A | ❌ | ❌ | ✅ |
| Sortable by level/status | ❌ | ❌ | Sometimes | ✅ (Sprint 2) |
| Threshold alerts | ❌ | ❌ | Requires YAML | ✅ (Sprint 2) |

**Key advantages:**
1. **Zero-config**: Users don't touch YAML. Just install and go.
2. **Server-side performance**: Sorting and filtering run on the HA server, not the browser. Scales to 100+ devices.
3. **Native to HA**: Feels like part of the platform. No custom Lovelace skill needed.
4. **Actionable**: Ranked by urgency. Users see what matters immediately.

**UX Designer (complementing PO):** From a UX standpoint, Vulcan Brownout solves the "where is this information?" problem that custom Lovelace cards create. Users know exactly where to look — the dedicated panel. They don't have to remember which dashboard contains the battery card. This reduces cognitive load and increases engagement.

---

## Acceptance Criteria

This section defines what "done" means for Sprint 1. Each criterion is testable by QA against the live HA server.

### Story 1: Integration Scaffolding & Auto-Discovery

- [ ] Integration loads without errors on HA startup
- [ ] Integration auto-discovers all entities with `device_class=battery` from HA
- [ ] Discovered entities are cached in memory (or persistent storage) after first run
- [ ] Integration handles HA restart gracefully (re-queries entities on restart)
- [ ] No configuration required from user (zero-config)
- [ ] Integration logs activity for debugging (INFO level: entities found, errors)
- [ ] QA can SSH into test HA server, install integration, and see entities discovered in logs within 10 seconds

### Story 2: Sidebar Panel Rendering

- [ ] Sidebar panel appears in HA UI immediately after installation
- [ ] Panel title: "Vulcan Brownout" with battery icon
- [ ] Panel renders correctly on desktop (340-400px width), tablet, and mobile viewports
- [ ] No layout shifts or visual glitches during initial load
- [ ] Panel is dismissible/closeable (standard HA sidebar behavior)
- [ ] Settings icon (⚙️) appears in header (for Sprint 2 config, but button must exist)
- [ ] Refresh button (↻) appears in header and is clickable
- [ ] Panel background uses HA's `--card-background-color` token

### Story 3: Visual Status Indicators

- [ ] Critical devices (≤15%) display with red/orange background (`--error-color-background`)
- [ ] Critical devices show red status icon and "Battery Critical" or similar badge
- [ ] Healthy devices (>15%) display with green progress bar and green icon
- [ ] Unavailable devices display with gray background and gray X/error icon
- [ ] Battery percentage displayed numerically for each device (e.g., "45%")
- [ ] Progress bar shows visual fill level matching battery percentage
- [ ] Icon colors change based on status (red, green, gray)
- [ ] Color contrast meets WCAG AA (4.5:1 for normal text)
- [ ] Status not conveyed by color alone — icons and text backup meaning
- [ ] All icons use HA's `ha-icon` component (Material Design Icons)

### Story 4: Empty State & Error Handling

**Empty State (no battery entities found):**
- [ ] User sees friendly message: "No battery devices found"
- [ ] Icon displayed (battery icon with question mark)
- [ ] Helpful text: "Configure entities with device_class=battery in Home Assistant"
- [ ] CTA button: "Browse Home Assistant Devices" (or similar)
- [ ] Empty state message appears within 2 seconds of panel open
- [ ] No error logs or console errors when empty

**Error State (connection lost):**
- [ ] If HA server becomes unreachable, show error message: "Unable to load battery devices"
- [ ] Error includes icon (⚠️ or error icon) and optional explanation
- [ ] "Retry" button is clickable and re-attempts fetch
- [ ] Last successful update timestamp is shown (e.g., "Last updated: 2 minutes ago")
- [ ] Error state appears within 3 seconds
- [ ] User can still refresh to retry (no hard lockup)

### Story 5: Deployment Pipeline (Idempotent Scripts)

**SSH Deployment Script:**
- [ ] Script is idempotent (can run multiple times without side effects)
- [ ] Script SSH-connects to test HA server using `$SSH_HOST`, `$SSH_USER`, `$SSH_PORT` from `.env`
- [ ] Script copies integration files to HA's custom_components directory
- [ ] Script restarts HA container or service (`docker-compose restart homeassistant` or equivalent)
- [ ] Script waits for HA to become healthy (polls `/api/` endpoint, max 30s timeout)
- [ ] Script logs all steps (success and failure) for debugging
- [ ] Script exits with code 0 on success, non-zero on failure
- [ ] Script runs in CI/CD pipeline before QA testing

**.env File Structure & Secrets Management:**
- [ ] `.env` file exists in repo root, in `.gitignore` (never committed)
- [ ] `.env.example` template committed with placeholder values:
  ```
  SSH_HOST=192.168.1.100
  SSH_USER=homeassistant
  SSH_PORT=22
  SSH_KEY_PATH=/path/to/ssh/key
  HA_API_TOKEN=<your-long-lived-token>
  ```
- [ ] Deployment script sources `.env` before connecting
- [ ] SSH key loaded from `$SSH_KEY_PATH` (not password auth)
- [ ] HA token used for health checks (API call to `/api/`)
- [ ] Secrets are never logged to stdout/stderr
- [ ] `.gitignore` includes `.env`, `*.pem`, `id_rsa*` to prevent accidental commits

**QA-Ready:**
- [ ] QA can copy `.env.example` to `.env`, fill in test server details
- [ ] QA can run deployment script once, integration installs cleanly
- [ ] QA can run deployment script again (idempotent), no errors or duplicates
- [ ] QA can edit integration code, re-run script, changes appear immediately
- [ ] QA has clear instructions in `TESTING.md` for setup

---

## Delivery Expectations

### Definition of Done (for entire Sprint 1)

A story is "done" when:
1. Code is merged to `develop` after code review
2. All acceptance criteria pass on test HA server
3. No console errors or warnings related to this feature
4. QA has tested empty state, error state, and happy path
5. Wireframes match implementation visually (may have minor polish differences)

### Constraints & Assumptions

- **Max 5 stories per sprint**: Sprint 1 has exactly 5 stories (scaffolding, panel, indicators, states, deployment)
- **One-week sprint**: Stories must fit within team velocity (assume ~20 story points)
- **Test server provided**: QA has persistent access to a real HA instance with battery entities
- **No mobile-first UX**: Design is desktop-first, but must be responsive

---

## Open Questions for Architect

The Architect must resolve these before implementation begins:

### Integration Architecture
1. **Auto-discovery mechanism**: Should discovery run on startup only, or periodically? Should it listen for HA config changes in real-time?
2. **Entity caching**: Where should discovered entities be stored? In-memory, SQLite, or HA's State Machine?
3. **Update polling**: How frequently should battery levels be fetched? Real-time listener or polling interval?
4. **Threshold default**: Is 15% hardcoded for Sprint 1, or configurable via YAML? (UX assumes hardcoded for MVP)

### Frontend Architecture
1. **Websocket vs. HTTP polling**: Should panel use HA's WebSocket API for real-time updates, or HTTP GET on manual refresh?
2. **Sorting implementation**: Should sorting happen server-side (integration logic) or client-side (JS)? (Sprint 1 is implicit "critical first," but architecture should plan for Spring 2 flexibility)
3. **Component framework**: Should panel use LitElement, Preact, or plain Web Components? (Follow HA conventions)
4. **CSS custom properties**: Can all colors be sourced from HA's CSS variables, or do we need custom tokens for battery states?

### Deployment & Infrastructure
1. **SSH key management**: How are SSH keys generated and stored for the test server? (Manual one-time setup, or GitOps secret injection?)
2. **Deployment user**: Should deployment script use a dedicated user (e.g., `deploy_user`) or `homeassistant` user?
3. **Health check polling**: What HA API endpoint should we poll to confirm server readiness after restart? (`/api/` or something more specific?)
4. **Docker vs. Bare Metal**: Is test HA instance containerized (docker-compose) or bare metal? Affects restart commands.
5. **CI/CD integration**: Will deployment script be triggered by GitHub Actions, GitLab CI, or manual `npm run deploy`?

### Error Handling & Resilience
1. **Partial failure**: If HA server returns some entities but not others (e.g., network glitch), should we show partial list or error state?
2. **Stale data**: If refresh fails, should we show last-known data (graceful degradation) or clear the list?
3. **Entity disappearance**: If user removes a device, should discovery re-run automatically, or only on manual refresh?

---

## Handoff Notes for Architect

### Key Product Decisions

1. **Zero-config is non-negotiable**: Users should NOT touch YAML to get battery monitoring. Auto-discovery must work out of the box.
2. **Critical-first sort is implicit**: Sprint 1 shows devices ranked by urgency (critical → unavailable → healthy). This is a default behavior, not a configurable setting. Spring 2 will add sorting controls.
3. **Visual status hierarchy**: The color red = urgent, gray = offline, green = safe. This language is consistent across all future HA battery-related features.
4. **Native HA aesthetic is required**: Any custom styling should use HA's CSS tokens. No hardcoded colors or non-standard components.

### UX Constraints the Technical Solution Must Respect

1. **Panel must load within 2 seconds** (or show loading skeleton to avoid perception of slowness)
2. **Refresh button must be responsive** (spinning icon while fetching, no hard freezes)
3. **Empty state and error state must be visually distinct** from each other
4. **Color contrast must meet WCAG AA** for accessibility
5. **Responsive design is mandatory**: Works on 320px mobile, 800px tablet, 1920px desktop
6. **No flickering or layout shifts**: Skeleton states prevent jank when data loads

### Non-Negotiable Requirements

- Integration must auto-discover battery entities with zero user config
- Sidebar panel must render native to HA (not iframe, not popup)
- Deployment must be idempotent (safe to run multiple times)
- All secrets must be in `.env`, never in code or git history

### Areas Where Technical Trade-offs Are Acceptable

- Polling vs. WebSocket: Choose what's easiest for Sprint 1; we can optimize in Sprint 2
- Sorting: Can start client-side; server-side optimization in Sprint 2 if needed
- Caching strategy: Any approach that avoids repeating auto-discovery is fine
- Icon customization: Sensible defaults are sufficient; per-device config is Sprint 2+

### Questions for Architect to Come Back With

1. **Feasibility of auto-discovery**: Can HA's State Machine be queried efficiently for all battery entities?
2. **Real-time update cost**: What's the performance impact of listening to HA updates vs. polling every N seconds?
3. **Sidebar panel registration**: Is there a standard HA way to register a custom panel? (Assume yes, but confirm API)
4. **Mobile responsiveness**: Any known gotchas with HA's sidebar on mobile devices?
5. **Estimated story point breakdown**: Roughly how many points for each of the 5 stories?

---

## Summary

**Sprint 1 is the battery monitoring MVP.** Users install, restart, and immediately see which devices need attention. No configuration, no friction, no custom Lovelace cards required. This is a compelling enough value proposition to ship as a standalone integration.

Future sprints add power-user features: threshold configuration, sorting/filtering controls, infinite scroll, notifications, and historical trends. But those can wait — Sprint 1 solves the core problem.

**Ship it. Make it native. Make it work out of the box.**
