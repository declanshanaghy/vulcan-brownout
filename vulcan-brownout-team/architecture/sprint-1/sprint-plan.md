# Sprint 1 Plan: Vulcan Brownout MVP

## Overview

Sprint 1 delivers the minimum viable product (MVP) for battery device monitoring in Home Assistant. The sprint consists of 5 stories, aligned with the Product Design Brief and architectural decisions (ADRs 001-005).

**Duration:** 1 week (5 business days)
**Max Stories:** 5
**Estimated Velocity:** 20 story points

---

## Story 1: Integration Scaffolding & Auto-Discovery

### User Story

As a Home Assistant user,
I want the Vulcan Brownout integration to automatically discover all my battery-powered devices when I install it,
So that I don't have to manually configure anything and can immediately see my battery status.

### Acceptance Criteria

- [ ] Integration loads without errors on HA startup
- [ ] Integration queries HA entity registry for all entities with `device_class=battery`
- [ ] Discovered entities are cached in memory (dict keyed by entity_id)
- [ ] Battery level is parsed correctly (handles numeric strings, "unavailable" state)
- [ ] Integration handles HA restart gracefully (re-discovers entities on each restart)
- [ ] No configuration required from user (zero-config, no YAML setup)
- [ ] Integration logs INFO level messages: "Discovered N battery entities" on startup
- [ ] Integration logs ERROR level messages on discovery failures (with reason)
- [ ] QA can SSH into test HA server, install integration, and see "Discovered N entities" in logs within 10 seconds

### Technical Notes

**Implementation:**

1. **File: `__init__.py`** (Integration entry point)
   - Implement `async_setup_entry(hass, entry)` to:
     - Create `BatteryMonitor` service
     - Call `await battery_monitor.discover_entities()`
     - Register event listener for `state_changed` events
     - Register WebSocket command `vulcan-brownout/query_devices`
     - Register sidebar panel
   - Implement `async_unload_entry(hass, entry)` for cleanup
   - Complexity: ~150 lines

2. **File: `const.py`** (Constants)
   - `DOMAIN = "vulcan_brownout"`
   - `BATTERY_THRESHOLD = 15`
   - `EVENT_STATE_CHANGED = "state_changed"`
   - Complexity: ~20 lines

3. **File: `battery_monitor.py`** (Core service)
   - Implement class `BatteryMonitor`:
     - `async def discover_entities()` — Query HA state machine, filter by device_class=battery, parse levels, cache in memory
     - `def _is_battery_entity(entity_id)` — Check if entity has device_class=battery attribute
     - `def _parse_entity(entity_id, state)` — Extract battery level, availability, friendly name, device name
     - `async def on_state_changed(event)` — Listen for HA state changes, update cache
   - Use HA's entity registry API (not string parsing)
   - Handle edge cases:
     - Entity state is non-numeric → `battery_level = 0, available = False`
     - Entity state is "unavailable" → `battery_level = 0, available = False`
     - Entity has no friendly_name → Use entity_id as fallback
   - Complexity: ~200 lines

4. **File: `manifest.json`** (Integration metadata)
   - `domain`, `name`, `version`, `documentation`, `codeowners`, `homeassistant` (min version)
   - `panel_custom` entry for sidebar panel registration
   - Complexity: ~15 lines

5. **File: `config_flow.py`** (Configuration UI, empty for Sprint 1)
   - Minimal implementation: Return empty config entry
   - No user-facing options yet
   - Complexity: ~30 lines

**Testing:**

- Unit test: `test_battery_monitor.py::test_discover_entities()` — Verify discovery queries HA correctly
- Unit test: `test_battery_monitor.py::test_parse_battery_level()` — Edge cases (non-numeric, unavailable)
- Unit test: `test_battery_monitor.py::test_on_state_changed()` — Verify cache updates on state change
- Integration test: Deploy to test HA, verify logs show "Discovered N entities"

**Definition of Done:**

- Code passes unit tests
- Code passes linting (black, flake8)
- Code review approved
- QA verifies auto-discovery works on test HA server
- Integration loads without errors
- No console errors in HA logs

**Estimated Complexity:** **M** (Medium, ~8 story points)

**UX Reference:** Product Design Brief section "First-Run Experience" → "Step 1: Install"

---

## Story 2: Sidebar Panel Rendering

### User Story

As a Home Assistant user,
I want to see a "Vulcan Brownout" panel in my sidebar with a battery icon,
So that I can open it and see my battery devices at a glance.

### Acceptance Criteria

- [ ] Sidebar panel appears in HA UI immediately after installation
- [ ] Panel title is "Vulcan Brownout" with battery icon (`mdi:battery-alert`)
- [ ] Panel renders correctly on desktop (340-400px width)
- [ ] Panel renders correctly on tablet (100% width, single column)
- [ ] Panel renders correctly on mobile (<600px, 16px padding)
- [ ] No layout shifts or visual glitches during load
- [ ] Panel is closeable (standard HA sidebar behavior)
- [ ] Settings icon (⚙️) appears in header (clickable but disabled for Sprint 1)
- [ ] Refresh icon (↻) appears in header and is clickable
- [ ] Panel background uses HA's `--card-background-color` CSS variable
- [ ] Responsive behavior works: resizing browser doesn't break layout
- [ ] Panel loads within 2 seconds (or shows skeleton to indicate progress)

### Technical Notes

**Implementation:**

1. **File: `frontend/vulcan-brownout-panel.js`** (Lit Element component)
   - Extend `LitElement` + `LocalizeMixin` (for i18n support)
   - Declare properties:
     - `@property({ attribute: false }) hass` — Provided by HA
     - `@state() battery_devices = []`
     - `@state() isLoading = false`
     - `@state() error = null`
   - Implement lifecycle:
     - `connectedCallback()` — Call `_load_devices()`, set up WebSocket
     - `disconnectedCallback()` — Cleanup listeners
   - Implement methods:
     - `async _load_devices()` — Send WebSocket query, populate state
     - `async _on_refresh()` — User clicked refresh button
     - `_on_device_changed(event)` — Real-time update (from backend)
     - `render()` — Return template (conditional: loading/error/empty/list)
   - CSS:
     - Use `--card-background-color`, `--primary-color`, etc.
     - Responsive media queries (desktop, tablet, mobile)
     - Shadow DOM scoping
   - Complexity: ~300 lines

2. **File: `frontend/styles.css`** (Scoped styles)
   - `.header` — Title + icons (fixed top)
   - `.device-list` — Scrollable container
   - `.device-card` — Individual device card (72px height)
   - `.device-card.critical` — Red background for critical devices
   - `.progress-bar` — Battery fill indicator (4px height)
   - `.loading`, `.error`, `.empty` — State-specific layouts
   - Media queries for mobile/tablet/desktop
   - Complexity: ~100 lines

3. **Update: `manifest.json`**
   - Add `panel_custom` entry:
     ```json
     "panel_custom": [
       {
         "name": "vulcan-brownout",
         "sidebar_title": "Vulcan Brownout",
         "sidebar_icon": "mdi:battery-alert",
         "js_url": "/local/vulcan-brownout-panel.js",
         "require_admin": false
       }
     ]
     ```

**Testing:**

- Unit test: `test_panel.js::test_render_list()` — Verify template renders correctly
- Unit test: `test_panel.js::test_responsive_layout()` — Media queries applied
- Integration test: Open panel in HA UI, verify sidebar entry appears
- E2E test: Test on mobile (Chrome DevTools mobile emulation)
- E2E test: Test on tablet and desktop viewports
- Manual test: Verify dark/light theme CSS variables work

**Definition of Done:**

- Component renders without console errors
- Sidebar entry visible and clickable
- Panel opens and closes smoothly
- Responsive across all breakpoints
- CSS uses HA variables (no hardcoded colors)
- Code review approved

**Estimated Complexity:** **M** (Medium, ~6 story points)

**UX Reference:** Wireframes section "Main Panel View (Desktop/Tablet/Mobile)", Interactions section "Interaction 1: Panel Opens"

---

## Story 3: Visual Status Indicators

### User Story

As a Home Assistant user viewing the battery panel,
I want to see each device's battery level visually (color, icon, percentage, progress bar),
So that I can quickly identify which devices need attention.

### Acceptance Criteria

- [ ] Critical devices (≤15%) display with red/orange background (`--error-color-background`)
- [ ] Critical devices show red circular icon and "Battery Critical" text/badge
- [ ] Healthy devices (>15%) display with default card background
- [ ] Healthy devices show green checkmark icon
- [ ] Unavailable devices display with gray background (`--divider-color`)
- [ ] Unavailable devices show gray X/error icon
- [ ] Battery percentage displayed numerically (e.g., "45%") for each device
- [ ] Progress bar shows visual fill level (width = battery_level %)
- [ ] Progress bar color matches device status (red for critical, green for healthy, gray for unavailable)
- [ ] Progress bar height is 4px (visible, not distracting)
- [ ] Icon size is 24px (consistent with Material Design)
- [ ] Color contrast meets WCAG AA (4.5:1 for normal text)
- [ ] Status is not conveyed by color alone (icons and text back up meaning)
- [ ] All icons use HA's `ha-icon` component (not custom SVGs)
- [ ] Icons animate smoothly when device status changes (100ms transition)

### Technical Notes

**Implementation:**

1. **Update: `frontend/vulcan-brownout-panel.js`**
   - Add helper methods:
     - `_get_status_class(device)` → "critical" | "unavailable" | "healthy"
     - `_get_icon_name(device)` → "mdi:battery-alert" | "mdi:battery-minus" | "mdi:check" | "mdi:close"
     - `_get_icon_color(status)` → CSS color var
   - Update template to apply classes and icons based on status
   - Add icon component: `<ha-icon icon="${icon_name}"></ha-icon>`

2. **Update: `frontend/styles.css`**
   - Add state-specific background colors:
     ```css
     .device-card.critical {
       background-color: var(--error-color-background);
     }
     .device-card.unavailable {
       background-color: var(--divider-color);
     }
     .device-card.healthy {
       background-color: var(--card-background-color);
     }
     ```
   - Add icon styling:
     ```css
     .device-icon {
       width: 24px;
       height: 24px;
       margin-right: 12px;
     }
     .device-icon.critical {
       color: var(--error-color);
     }
     .device-icon.healthy {
       color: var(--success-color);
     }
     .device-icon.unavailable {
       color: var(--disabled-text-color);
     }
     ```
   - Progress bar styling:
     ```css
     .progress-bar {
       height: 4px;
       background-color: var(--divider-color);
       border-radius: 2px;
       overflow: hidden;
       margin-top: 8px;
     }
     .progress-bar-fill {
       height: 100%;
       width: var(--battery-level, 0%);
       transition: width 300ms cubic-bezier(0.4, 0, 0.2, 1);
     }
     .progress-bar-fill.critical {
       background-color: var(--error-color);
     }
     .progress-bar-fill.healthy {
       background-color: var(--success-color);
     }
     .progress-bar-fill.unavailable {
       background-color: var(--disabled-text-color);
     }
     ```

3. **Accessibility:**
   - Ensure text contrast ratio ≥ 4.5:1 (use HA color vars, they're WCAG compliant)
   - Add `aria-label` to progress bar: "Battery level: 45%"
   - Use semantic HTML: `<span class="battery-level">45%</span>`

**Testing:**

- Unit test: `test_panel.js::test_status_class_assignment()` — Verify critical/healthy/unavailable classes applied
- Unit test: `test_panel.js::test_icon_selection()` — Verify correct icons chosen
- Unit test: `test_panel.js::test_color_contrast()` — Verify WCAG AA compliance
- E2E test: Visual inspection on dark/light theme (screenshots)
- Manual test: Accessibility audit with browser extension (axe DevTools)

**Definition of Done:**

- All status classes applied correctly
- Icons render and animate smoothly
- Colors meet accessibility standards
- Code review approved

**Estimated Complexity:** **S** (Small, ~4 story points)

**UX Reference:** Wireframes section "Component Specifications by State", Interactions section "Visual Language"

---

## Story 4: Empty State & Error Handling

### User Story

As a Home Assistant user installing Vulcan Brownout,
I want helpful guidance when there are no battery devices (or if something goes wrong),
So that I understand why the panel is empty and how to fix it.

### Acceptance Criteria

**Empty State (no battery entities found):**
- [ ] User sees message: "No battery devices found"
- [ ] Large battery icon (64px, light gray, `--text-tertiary-color`)
- [ ] Helpful text: "Configure entities with device_class=battery in Home Assistant to appear here."
- [ ] CTA button: "Browse Home Assistant Devices" (links to HA device page or settings)
- [ ] Empty state message appears within 2 seconds of panel open
- [ ] No error logs or console errors when empty
- [ ] Button is clickable and functional

**Error State (connection lost or fetch failed):**
- [ ] User sees message: "Unable to load battery devices"
- [ ] Large warning icon (64px, `--error-color`)
- [ ] Error explanation: "The Home Assistant server is unreachable. Check your connection and try again."
- [ ] "Retry" button is clickable and re-attempts fetch
- [ ] Last successful update timestamp shown (optional): "Last updated: 2 minutes ago"
- [ ] Error state appears within 3 seconds
- [ ] User can still use refresh button to retry
- [ ] No hard lockup or frozen UI

**Distinction:**
- [ ] Empty state and error state are visually distinct (different icons, messages, colors)
- [ ] Empty state icon is informational (battery icon)
- [ ] Error state icon is alarming (warning/alert icon)

### Technical Notes

**Implementation:**

1. **Update: `frontend/vulcan-brownout-panel.js`**
   - Add state tracking:
     - `@state() error = null` (error object or null)
     - `@state() lastUpdateTime = null` (timestamp of last successful query)
   - Add error handling in `_load_devices()`:
     ```javascript
     try {
       const result = await this.hass.callWS(...);
       this.battery_devices = result.data.devices;
       this.lastUpdateTime = new Date();
       this.error = null;
     } catch (e) {
       this.error = { code: e.code, message: e.message };
       console.error('Load failed:', e);
     } finally {
       this.isLoading = false;
     }
     ```
   - Update `render()` to show three states:
     ```javascript
     render() {
       if (this.error) {
         return html`<div class="error-state">...</div>`;
       }
       if (this.battery_devices.length === 0) {
         return html`<div class="empty-state">...</div>`;
       }
       return html`<div class="device-list">...</div>`;
     }
     ```
   - Implement `_on_retry()` to re-call `_load_devices()`

2. **Update: `frontend/styles.css`**
   - Add empty state styling:
     ```css
     .empty-state {
       display: flex;
       flex-direction: column;
       align-items: center;
       justify-content: center;
       padding: 48px 24px;
       text-align: center;
     }
     .empty-state-icon {
       font-size: 64px;
       margin-bottom: 16px;
       color: var(--text-tertiary-color);
     }
     .empty-state-title {
       font-size: 20px;
       font-weight: 500;
       margin-bottom: 12px;
     }
     .empty-state-text {
       font-size: 13px;
       color: var(--text-secondary-color);
       margin-bottom: 24px;
     }
     ```
   - Add error state styling (similar, but icon is warning)
   - Add button styling:
     ```css
     .cta-button {
       background-color: var(--primary-color);
       color: white;
       padding: 12px 24px;
       border: none;
       border-radius: 4px;
       cursor: pointer;
       font-size: 14px;
     }
     .cta-button:hover {
       opacity: 0.8;
     }
     ```

3. **Last Updated Timestamp:**
   - Store `this.lastUpdateTime` on successful query
   - Display formatted string: "Last updated: 2 minutes ago"
   - Use `formatDistanceToNow()` helper (or manual calculation)

**Testing:**

- Unit test: `test_panel.js::test_empty_state_render()` — Verify empty state UI
- Unit test: `test_panel.js::test_error_state_render()` — Verify error state UI
- Unit test: `test_panel.js::test_retry_button()` — Verify retry action
- Integration test: Mock 0 devices response, verify empty state
- Integration test: Mock network error, verify error state
- Manual test: Verify buttons are clickable and functional

**Definition of Done:**

- Empty state renders correctly with helpful messaging
- Error state renders correctly with retry option
- Both states visually distinct
- Last updated timestamp shown
- Code review approved
- QA tests both paths on test HA server

**Estimated Complexity:** **M** (Medium, ~6 story points)

**UX Reference:** Wireframes section "Empty State" and "Error State", Interactions section "Interaction 5" and "Interaction 6"

---

## Story 5: Deployment Pipeline (Idempotent Scripts)

### User Story

As QA,
I want a simple deployment script that installs the integration on the test HA server,
So that I can quickly test changes without manual SSH commands.

### Acceptance Criteria

**SSH Deployment Script (`deploy.sh`):**
- [ ] Script is idempotent (can run multiple times without side effects)
- [ ] Script loads secrets from `.env` file
- [ ] Script validates all required `.env` variables before proceeding
- [ ] Script SSH-connects to test HA server using `$SSH_HOST`, `$SSH_USER`, `$SSH_PORT`, `$SSH_KEY_PATH`
- [ ] Script transfers integration files to HA via `rsync` (only changed files)
- [ ] Script restarts HA container: `docker-compose restart homeassistant`
- [ ] Script waits for HA to become healthy (polls `/api/` endpoint for 200 response, max 30s timeout)
- [ ] Script logs all steps (success and failure) with timestamps
- [ ] Script exits with code 0 on success, non-zero on failure
- [ ] QA can read clear error messages if something fails

**.env File Structure:**
- [ ] `.env` file exists in repo root, in `.gitignore` (never committed)
- [ ] `.env.example` template committed with placeholder values
- [ ] `.env.example` includes all required variables with comments
- [ ] Secrets are never logged to stdout/stderr
- [ ] `.gitignore` includes: `.env`, `*.pem`, `id_rsa*`, `known_hosts`

**Idempotency Verification:**
- [ ] QA can run `./deploy.sh` once, integration installs cleanly
- [ ] QA can run `./deploy.sh` again (immediately after), no errors or duplicates
- [ ] QA can edit integration code, re-run `./deploy.sh`, changes appear immediately
- [ ] Third run produces no changes (rsync skips unchanged files)

**Testing Instructions:**
- [ ] `TESTING.md` includes setup steps for QA (SSH key, HA token, `.env` creation)
- [ ] `TESTING.md` includes troubleshooting common errors
- [ ] QA can follow instructions and deploy successfully in <5 minutes

### Technical Notes

**Implementation:**

1. **File: `deploy.sh`** (Bash script)
   - Load and validate `.env`:
     ```bash
     source .env
     for var in SSH_HOST SSH_USER SSH_PORT SSH_KEY_PATH HA_API_TOKEN; do
       [ -z "${!var}" ] && echo "ERROR: $var not set" && exit 1
     done
     ```
   - Transfer files:
     ```bash
     rsync -avz --delete \
       -e "ssh -i $SSH_KEY_PATH -p $SSH_PORT" \
       custom_components/vulcan_brownout/ \
       $SSH_USER@$SSH_HOST:/home/$SSH_USER/homeassistant/custom_components/vulcan_brownout/
     ```
   - Restart HA:
     ```bash
     ssh -i $SSH_KEY_PATH -p $SSH_PORT $SSH_USER@$SSH_HOST \
       "cd /home/$SSH_USER/homeassistant && docker-compose restart homeassistant"
     ```
   - Health check:
     ```bash
     for i in {1..30}; do
       HTTP_CODE=$(curl -s -H "Authorization: Bearer $HA_API_TOKEN" \
         http://$SSH_HOST:8123/api/ 2>/dev/null | grep -q "." && echo 200 || echo 0)
       [ "$HTTP_CODE" == "200" ] && echo "HA healthy" && break
       sleep 1
     done
     ```
   - Logging: Use `echo` with timestamps, colors for status
   - Complexity: ~120 lines

2. **File: `.env.example`** (Template)
   - Include all required variables with explanatory comments
   - Use realistic placeholder values
   - Include examples for common scenarios

3. **File: `.gitignore`** (Prevent secret commits)
   - Add: `.env`, `.env.local`, `*.pem`, `id_rsa*`, `known_hosts`
   - Verify existing `.gitignore` doesn't conflict

4. **File: `TESTING.md`** (QA Instructions)
   - Step-by-step setup guide
   - SSH key generation
   - Long-lived token creation in HA
   - `.env` creation and editing
   - First deployment test
   - Troubleshooting common errors
   - Secret rotation instructions

**Testing:**

- Manual test: QA creates `.env` file with test HA details
- Manual test: QA runs `./deploy.sh` once, verifies success logs
- Manual test: QA runs `./deploy.sh` second time, verifies no changes
- Manual test: QA edits a file in integration, re-runs `./deploy.sh`, verifies changes appear
- Manual test: QA intentionally breaks `.env` (e.g., wrong host), verifies clear error message
- Manual test: QA tests SSH key permissions (should fail if not 600), tests recovery

**Definition of Done:**

- Script works end-to-end on test HA server
- Idempotency verified (3+ runs produce no errors)
- Clear error messages for all failure modes
- `.env` properly gitignored
- `.env.example` complete and documented
- TESTING.md is clear and complete
- Code review approved

**Estimated Complexity:** **M** (Medium, ~6 story points)

**UX Reference:** Not applicable (backend infrastructure)

---

## Story Dependency Graph

```
Story 1 (Integration Scaffolding)
  ├─ Prerequisite for Story 2 (panel needs backend to query)
  └─ Prerequisite for Story 3 (needs device data)
      └─ Prerequisite for Story 4 (needs data to test error states)

Story 2 (Panel Rendering) [parallelizable with Story 1]
  └─ Prerequisite for Story 3

Story 3 (Visual Indicators) [parallelizable with Story 2]
  └─ Prerequisite for Story 4

Story 4 (Empty/Error States) [parallelizable with Story 3]
  └─ Prerequisite for Story 5 (testing)

Story 5 (Deployment) [parallelizable with all, but needs working code to deploy]
```

**Recommended Sequence:**
1. Story 1 + 2 (in parallel) — Backend + frontend basic rendering
2. Story 3 + 4 (in parallel) — Visual polish + error handling
3. Story 5 — Deploy and test

**Timeline:** Each story ~1-1.5 days with code review and testing.

---

## Acceptance Testing by QA

### Manual Test Checklist (Story 1)
- [ ] Deploy integration to test HA
- [ ] Check HA logs for "Discovered N battery entities"
- [ ] Verify no errors in logs
- [ ] Restart HA, verify re-discovery happens
- [ ] Verify battery entities in HA state machine (e.g., `sensor.test_battery_critical_1`)

### Manual Test Checklist (Story 2)
- [ ] Open HA sidebar
- [ ] Verify "Vulcan Brownout" appears with battery icon
- [ ] Click to open panel
- [ ] Verify panel slides open smoothly (250ms animation)
- [ ] Check panel width (340-400px on desktop)
- [ ] Resize to tablet (600px) and mobile (375px)
- [ ] Verify responsive layout adapts correctly

### Manual Test Checklist (Story 3)
- [ ] Open panel
- [ ] Verify critical devices (≤15%) have red background
- [ ] Verify critical devices have red icons
- [ ] Verify healthy devices (>15%) have green background
- [ ] Verify unavailable devices have gray background
- [ ] Check progress bars fill correctly (visually match %)
- [ ] Verify color contrast (use axe DevTools)

### Manual Test Checklist (Story 4)
- [ ] Create test HA config with 0 battery entities
- [ ] Open panel, verify empty state message
- [ ] Click "Browse Devices" button, verify navigation works
- [ ] Disconnect HA from network (simulate error)
- [ ] Verify error state message
- [ ] Click "Retry" button, verify error clears on reconnect

### Manual Test Checklist (Story 5)
- [ ] Run `./deploy.sh` first time, verify success
- [ ] Run `./deploy.sh` second time, verify no changes
- [ ] Edit integration file, run `./deploy.sh`, verify changes appear
- [ ] Intentionally break `.env` (wrong host), run script, verify clear error

---

## Code Review Criteria

- [ ] Code follows HA integration patterns (use platform conventions)
- [ ] Code is well-commented (non-obvious logic explained)
- [ ] Error handling is comprehensive (no silent failures)
- [ ] Performance is acceptable (no blocking calls, async/await used)
- [ ] Security is sound (no secrets in code, SSH key only)
- [ ] Accessibility is met (WCAG AA, aria-labels, semantic HTML)
- [ ] Tests are comprehensive (unit + integration coverage)
- [ ] Documentation is clear (README, TESTING.md, docstrings)
- [ ] No dead code or debugging console.log() calls
- [ ] Dependencies are minimal (Lit only, no extra npm packages)

---

## Sprint Success Criteria

Sprint 1 is successful if:

1. All 5 stories pass code review and QA testing
2. Integration installs cleanly on test HA server
3. Auto-discovery works without configuration
4. Panel renders correctly across all viewports
5. Visual indicators match design (colors, icons, animations)
6. Error/empty states are helpful and clear
7. Deployment pipeline is idempotent and tested
8. No console errors or HA logs pollution
9. Documentation is complete (README, TESTING.md, ADRs)
10. Code is ready to ship to HACS

---

## Rollout Plan (After Sprint 1)

1. **Code Freeze** — Final code review and QA signoff
2. **Release Notes** — Document features, known limitations, install instructions
3. **HACS Submission** — Add integration to HACS repository
4. **Announcement** — Post on HA forums, subreddits, social media
5. **Monitoring** — Track HACS installs, user feedback, bug reports
6. **Sprint 2 Planning** — Prioritize user-requested features (threshold config, filtering, etc.)

---

## Known Limitations (Sprint 1 → Sprint 2 Backlog)

- [ ] Threshold is hardcoded 15% (configurable in Sprint 2)
- [ ] No sorting UI (implicit "critical first" sort, explicit controls in Sprint 2)
- [ ] No infinite scroll (full list loads, pagination in Sprint 2)
- [ ] No settings panel (battery threshold config in Sprint 2)
- [ ] No auto-refresh (manual refresh only, auto-refresh in Sprint 2)
- [ ] No WebSocket subscriptions (polling-based, real-time in Sprint 2)
- [ ] No historical data (graphs/trends in Sprint 2+)
- [ ] No notifications/alerts (would require config, Sprint 2+)

---

## Next Steps

1. **Architect reviews and approves** this plan
2. **Lead Developer estimates** story points (refine if needed)
3. **QA confirms** test environment is ready
4. **Sprint 1 begins** — Implement stories in recommended sequence
5. **Daily standup** — Track progress, unblock issues
6. **Code review** — Each story before merge to develop
7. **QA testing** — Acceptance criteria verified
8. **Sprint retrospective** — Lessons learned, improvements for Sprint 2
