# Delegation Brief: Sprint 2 Implementation

**For**: Lead Developer
**From**: FiremanDecko (Architect)
**Date**: February 2026
**Sprint Duration**: 2 weeks (10 business days)
**Capacity**: 16 days

---

## The Mission

Sprint 2 transforms Vulcan Brownout from a passive battery display into an active monitoring tool. You'll implement three major features:

1. **Real-Time WebSocket Updates** (< 500ms latency)
2. **Configurable Thresholds** (global + per-device)
3. **Sort & Filter Controls** (user-controlled list organization)

Plus mobile-responsive UX and deployment infrastructure improvements.

**Success = All 5 stories shipped, tested, and production-ready by sprint end.**

---

## What You're Building

### Overview

The system evolves from request-response to push-response hybrid:

**Sprint 1**: User clicks refresh → Backend queries → User waits for data
**Sprint 2**: User opens panel → WebSocket subscribes → Real-time updates flow automatically

Three separate systems, all interconnected:

1. **WebSocket Subscription Manager** (Backend)
   - Tracks active client connections
   - Broadcasts battery updates to all subscribers
   - Handles reconnection gracefully

2. **Threshold Configuration System** (Backend + Frontend)
   - Stores global and per-device thresholds in HA config entry
   - Calculates device status (critical/warning/healthy/unavailable) using thresholds
   - Broadcasts threshold changes to all connected clients

3. **Sort & Filter Engine** (Frontend)
   - Client-side sorting (4 algorithms)
   - Client-side filtering (4 status groups)
   - localStorage persistence for user preferences

---

## Architecture Documents to Follow

Read these in order (all in `/sprints/sprint-2/architecture/`):

1. **system-design.md** — Updated component diagram, data flows for each feature
2. **api-contracts.md** — All new WebSocket messages, commands, events
3. **ADR-006** — WebSocket subscription architecture (design decisions)
4. **ADR-007** — Threshold storage (why ConfigEntry.options)
5. **ADR-008** — Sort/filter implementation (why client-side for Sprint 2)
6. **sprint-plan.md** — 5 stories with acceptance criteria & technical notes

**CRITICAL**: Don't skip the ADRs. They contain the "why" behind decisions. If you have concerns, flag them in code review.

---

## Story-by-Story Implementation

### Story 1: Real-Time WebSocket Updates (4 days)

**What**: Battery levels update automatically as devices change in Home Assistant.

**Why**: Users want confidence their monitoring is active, not "I need to refresh."

**Key Components to Build**:

1. **Backend: `WebSocketSubscriptionManager` (NEW)**
   - Manages subscriber list: `{connection_id: ClientSubscription}`
   - Listens to HA `state_changed` events
   - For each battery change, broadcasts to all subscribers
   - Handles client disconnection cleanup

2. **Backend: Modify `__init__.py`**
   - Create subscription manager on setup
   - Register state_changed event listener
   - Call subscription manager for each battery entity change

3. **Backend: Modify `websocket_api.py`**
   - Add `handle_subscribe` command handler
   - Add broadcast mechanism for `device_changed` events
   - Return subscription_id to client

4. **Frontend: Connection State Machine**
   - Track state: connected | reconnecting | offline
   - Exponential backoff: 1s, 2s, 4s, 8s, 16s, 30s
   - Max 10 retries before showing "Offline" message
   - Auto-retry on network restore

5. **Frontend: Real-Time Update Handler**
   - Listen for `device_changed` events
   - Update local device: `battery_level`, `available`, `status`
   - Trigger Lit re-render
   - Progress bar animates 300ms (CSS transition, not JS)

6. **Frontend: UI Components**
   - Connection badge (🟢 green, 🔵 spinning blue, 🔴 red)
   - Last Updated timestamp ("Updated 3 seconds ago")
   - Toast notification on reconnect ("✓ Connection updated")

**Acceptance Criteria** (from sprint-plan.md):
- Real-time latency < 500ms (HA change to UI update)
- Connection badge accurately reflects state
- Exponential backoff works (1s, 2s, 4s, 8s, ...)
- No lost updates during brief disconnects
- No jank or stutter during animations
- Works on mobile (scrolling smooth despite updates)
- Keyboard & screen reader accessible

**Testing You Must Do**:
- Unit: Subscription manager, reconnection logic
- Integration: Real HA instance, simulate battery changes, measure latency
- E2E: Panel open, watch updates, simulate disconnect/reconnect
- Performance: 100+ batteries, 100 updates/sec, no jank
- Mobile: iPhone/Android, verify smooth scrolling

**Code Review Will Check**:
- Subscription memory leak prevention (cleanup on disconnect)
- Exponential backoff correctness (no missing edge cases)
- Error handling (disconnects, auth failures, max retries)
- Animation performance (60 FPS on low-end devices)

---

### Story 2: Configurable Thresholds (5 days)

**What**: Users set custom thresholds: global (all devices) or per-device (override).

**Why**: Solar backup needs 50% alert, sensors need 15%. One-size-fits-all is broken.

**Key Components to Build**:

1. **Backend: Config Flow (NEW `config_flow.py`)**
   - OptionsFlow for threshold configuration
   - Validate inputs: threshold 5-100, device_rules ≤ 10
   - Store in `ConfigEntry.options`

2. **Backend: Modify `battery_monitor.py`**
   - Add threshold cache: `self.global_threshold`, `self.device_rules`
   - Add `get_threshold_for_device(entity_id)` method
   - Add `get_status_for_device(device)` method
   - Update status calculation to use thresholds

3. **Backend: WebSocket Handler**
   - Add `handle_set_threshold` command
   - Validate threshold inputs
   - Update config entry
   - Broadcast `threshold_updated` event to ALL clients (not just requester)

4. **Backend: Event Listener**
   - Hook to config entry changes
   - Call `battery_monitor.on_options_updated()`
   - Broadcast update to all WebSocket subscribers

5. **Frontend: Settings Panel (NEW)**
   - Slide-out from right on desktop (400px wide, 300ms animation)
   - Full-screen modal on mobile (100vh, 90% height)
   - Global threshold section:
     - Slider 5-100%
     - Text input (optional)
     - Live preview: "8 batteries below this threshold"
   - Device-specific rules section:
     - "+ Add Device Rule" button
     - List of rules (show 5, "SHOW MORE" if > 5)
     - Delete button (✕) for each rule
   - Buttons: "SAVE" (blue), "CANCEL" (gray)
   - Close button (✕) and Escape key close without saving

6. **Frontend: Add Device Rule Modal (NEW)**
   - Step 1: Select device
     - Searchable list of all battery entities
     - Filter as user types
     - Show device name + current battery level + status
   - Step 2: Set threshold
     - Slider 5-100%
     - Text input
     - Help text: "Show CRITICAL when battery < X%"
     - Live feedback: "After save: 3 devices will be CRITICAL"
   - Buttons: "SAVE RULE" (blue), "CANCEL" (gray)

7. **Frontend: Threshold Application**
   - On page load: Request query_devices, get device_statuses
   - On threshold_updated event: Re-calculate status for all devices
   - Re-render with new colors (red for CRITICAL, orange for WARNING, green for HEALTHY)
   - Smooth color transition (no jarring change)

**Acceptance Criteria**:
- Settings icon (⚙️) opens settings panel
- Global threshold 5-100%, defaults to 15%
- Can add up to 10 device rules per session
- Live preview shows affected device count
- Save persists in HA ConfigEntry.options
- Changes survive HA restart
- Changes broadcast to all connected clients
- Threshold changes immediately re-color list
- Mobile: full-screen modal, touch targets ≥ 44px
- Keyboard: Tab through fields, Enter to save, Escape to cancel

**Testing You Must Do**:
- Unit: Threshold validation, status calculation
- Integration: Config entry persistence, multi-client sync
- E2E: Open settings, change threshold, verify colors update
- QA: Add 5 device rules, verify overrides apply correctly
- Regression: Ensure Sprint 1 features still work

**Code Review Will Check**:
- Config entry schema versioning
- Threshold validation (edge cases)
- Multi-client broadcast mechanism
- localStorage handling (if implemented)
- Performance of device status re-calculation (< 100ms for 50 devices)

---

### Story 3: Sorting & Filtering (3 days)

**What**: Users can sort by priority/alphabetical/battery level and filter by status.

**Why**: With 20+ devices, finding "critical" devices is hard. Give users control.

**Key Components to Build**:

1. **Frontend: Sort/Filter Bar (NEW)**
   - Desktop (> 768px): Inline dropdowns
     - Sort dropdown: Priority (default), Alphabetical, Level (Low→High), Level (High→Low)
     - Filter dropdown: Critical, Warning, Healthy, Unavailable (checkboxes)
     - Reset button (✕): Clears all filters, resets sort to default
   - Mobile (< 768px): Button bar
     - "SORT" button → Opens full-screen modal
     - "FILTER" button → Opens full-screen modal
     - "✕ RESET" button

2. **Frontend: Sort Algorithms**
   ```javascript
   // Priority (DEFAULT): critical < warning < healthy < unavailable, then by battery level asc
   // Alphabetical: device name A-Z
   // Level Ascending: battery level low → high
   // Level Descending: battery level high → low
   ```
   Implement in `_apply_sort(devices, method)` function.

3. **Frontend: Filter Logic**
   ```javascript
   function _apply_filter(devices, filter_state) {
     return devices.filter(d => {
       const status = this._get_status(d);
       return filter_state[status] === true;
     });
   }
   ```

4. **Frontend: State Management**
   - `@state() sort_method = 'priority'`
   - `@state() filter_state = { critical: true, warning: true, healthy: true, unavailable: false }`
   - Computed property: `get _filtered_and_sorted_devices()` returns final list

5. **Frontend: localStorage Persistence**
   - Save to `localStorage['vulcan_brownout_ui_state']` as JSON
   - Load on component init
   - Persist on every sort/filter change
   - Handle localStorage full/unavailable gracefully

6. **Frontend: Mobile Modals (Responsive)**
   - Sort modal: Radio buttons (44px touch targets)
   - Filter modal: Checkboxes (44px touch targets)
   - Both modals: Full-screen on mobile, close on "Apply"
   - Desktop: Dropdowns, stay open

**Acceptance Criteria**:
- Sort dropdown: 4 options work correctly
- Filter checkboxes: Toggle status groups, update list instantly
- Sort/filter bar sticky on scroll
- Default: Priority sort, Show All filters
- localStorage persists per session
- Reset button clears all
- Desktop (dropdowns) and mobile (modals) both work
- No horizontal scrolling any screen size
- Keyboard accessible: Tab, Arrow keys, Enter
- Performance: Sort/filter 100+ devices in < 50ms

**Testing You Must Do**:
- Unit: Sort algorithms, filter logic, localStorage
- Integration: Persistence across reload
- E2E: Select each sort, verify order; toggle filters, verify visibility
- Performance: Measure sort/filter time with 100+ devices
- Mobile: Modals responsive, touch targets clickable
- Keyboard: Tab through all controls

**Code Review Will Check**:
- Sort algorithm correctness
- Filter logic efficiency
- localStorage error handling
- Responsive design (no horizontal scroll)
- Performance (< 50ms)

---

### Story 4: Mobile-Responsive UX & Accessibility (2 days)

**What**: Settings modals, sort/filter modals, and all controls responsive & accessible.

**Why**: Many HA users check batteries from phones. Must be native-feeling, not desktop-squeezed.

**Key Components to Build**:

1. **CSS Media Queries**
   - Mobile-first approach
   - Breakpoints: 768px, 1024px, 1440px
   - Responsive font sizes, padding, touch targets

2. **Touch Targets**
   - All buttons, checkboxes, icons: ≥ 44px
   - No overlapping targets
   - Visual feedback on tap (highlight)

3. **Typography**
   - Base font: 16px (not 14px) on mobile
   - Headings: 18px+
   - Line heights: 1.5+ for readability
   - High contrast text

4. **Modals**
   - Full-screen on mobile (100vw, 90vh)
   - Fixed header/footer
   - Scrollable content area
   - Close button (✕) visible

5. **Accessibility (WCAG 2.1 AA)**
   - ARIA labels: all icons, buttons, status indicators
   - Color + icon: never color alone for status
   - Keyboard navigation: Tab through all controls
   - Focus indicators: visible outline on all focusable elements
   - Color contrast: min 4.5:1 for text, 3:1 for graphics
   - Semantic HTML: use `<button>`, `<input>`, etc.

6. **Testing Tools**
   - Lighthouse accessibility audit (target: ≥ 90)
   - Chrome DevTools: Device emulation (390px, 768px, 1440px)
   - Screen reader: VoiceOver (iOS), TalkBack (Android)
   - Keyboard-only navigation: no mouse
   - Color contrast checker: WebAIM

**Acceptance Criteria**:
- Settings modal full-screen on mobile, side panel on desktop
- Sort/filter modals full-screen on mobile, dropdowns on desktop
- All touch targets ≥ 44px
- Font sizes readable on 390px screen
- No horizontal scrolling any viewport
- Keyboard focus indicators visible
- ARIA labels on all controls
- Color contrast ≥ 4.5:1
- Lighthouse accessibility ≥ 90
- Tested on iPhone 12, iPad, Desktop

**Testing You Must Do**:
- Real device testing: iPhone, iPad
- Browser emulation: 390px, 768px, 1440px
- Lighthouse: Run accessibility audit
- Screen reader: Navigate with VoiceOver/TalkBack
- Keyboard: Tab through all controls, Escape closes
- Color contrast: Use WebAIM tool

**Code Review Will Check**:
- Media query correctness
- Touch target sizing
- ARIA labels completeness
- Color contrast compliance
- Keyboard navigation flow
- Lighthouse score ≥ 90

---

### Story 5: Deployment & Infrastructure (2 days)

**What**: Idempotent deployment with systemd, health checks, and rollback.

**Why**: Zero-downtime updates, automatic recovery from failures.

**Key Components to Build**:

1. **Systemd Service Management**
   - Service file: `vulcan-brownout.service`
   - Restart policy: `on-failure`, max 3 restarts
   - HA integration: Works with HA's Docker + bare metal

2. **Deployment Script (`deploy.sh` UPDATED)**
   - Environment validation: Check required .env vars exist
   - Idempotent: Safe to run multiple times
   - Rollback: Keep previous version, swap symlink if health check fails
   - Health check: POST-deploy, call `/health` endpoint
   - Smoke test: Verify real-time updates work
   - Logging: Clear success/failure messages

3. **Health Check Endpoint** (NEW)
   - Endpoint: GET `/api/vulcan_brownout/health`
   - Response: `{ status: "healthy", websocket_ready: true, battery_entities: N, timestamp: "..." }`
   - Validates: WebSocket functional, battery entities loaded
   - Retry logic: 3 attempts with backoff if fails
   - Timeout: 30 seconds max

4. **Rollback Mechanism**
   - Keep directory: `releases/{version}/` for last 2 versions
   - Symlink: `current/ -> releases/{version}/`
   - On failure: Swap symlink to previous version
   - Verify: Check service status after rollback

5. **Testing Deployment**
   - Run deploy script 3+ times: Verify idempotent (no errors on repeat runs)
   - Deploy with missing .env: Verify early exit + clear error
   - Simulate health check failure: Verify rollback triggers + previous version active
   - Monitor HA logs: No errors or warnings
   - Verify real-time updates post-deploy: Simulate battery change, verify update received

**Acceptance Criteria**:
- Deployment script idempotent (3+ successful runs)
- Environment validation works (fails cleanly on missing vars)
- Health check endpoint responds 200 with correct JSON
- Rollback triggered on health check failure
- Previous version active after rollback
- Deployment logs clear (success/failure obvious)
- All secrets in .env (not in git)
- No secrets in commit history
- Deployment < 5 minutes total

**Testing You Must Do**:
- Manual deployment: 3+ runs, verify idempotent
- Missing .env: Verify validation catches it
- Health check: Call endpoint, verify response
- Rollback: Simulate failure, verify rollback works
- Git history: Verify no secrets committed
- HA logs: Check for errors

**Code Review Will Check**:
- Script robustness (error handling)
- Health check correctness
- Rollback mechanism
- Secret management (no hardcodes)
- Idempotency (no side effects on repeat)
- Performance (deploy time)

---

## Development Workflow

### Daily Routine

1. **Morning Standup** (15 min)
   - What you did yesterday
   - What you're doing today
   - Any blockers

2. **Code Review Loop** (Throughout day)
   - Submit PRs daily (not all at sprint end)
   - Architect reviews within 24 hours
   - Address feedback, iterate
   - Merge when approved

3. **Testing** (Continuous)
   - Unit tests as you code
   - Integration tests after features complete
   - QA testing in parallel

### Branch Strategy

- Work on `feature/sprint-2-*` branches
- Open PRs early (mark as draft if not ready)
- Code review approval required before merge
- Merge to `develop` branch
- No direct commits to `develop` or `main`

### Commit Messages

```
Story 1: Real-time updates - implement WebSocket subscription manager

- Add WebSocketSubscriptionManager class to track subscribers
- Register state_changed event listener
- Broadcast device_changed events to all connected clients
- Handle client disconnection cleanup

Fixes: https://github.com/vulcan-brownout/issues/...
```

Use story number, clear description, bullet points for details.

---

## Code Quality Expectations

### Python (Backend)

- [ ] Type hints on all functions
- [ ] Docstrings (what, args, returns, raises)
- [ ] Error handling (try/except, log errors)
- [ ] No blocking calls (all async)
- [ ] HA logging: `_LOGGER.info()`, `.error()`, `.debug()`
- [ ] Avoid print() statements (use logging)
- [ ] Edge cases handled (None values, empty lists, etc.)
- [ ] Performance considered (no N+1, no unnecessary loops)

### JavaScript (Frontend)

- [ ] Lit conventions (properties, state, render, styles)
- [ ] No manual DOM manipulation (let Lit handle it)
- [ ] Error handling (try/catch on promises)
- [ ] Clean up subscriptions (disconnectedCallback)
- [ ] CSS custom properties (for theming)
- [ ] Performance considered (no re-renders on every keystroke)
- [ ] Accessibility (ARIA labels, semantic HTML)
- [ ] No console.log() in production code (use hass.notification)

### Testing

- [ ] Unit tests: > 80% code coverage
- [ ] Integration tests: Real HA instance
- [ ] E2E tests: Full user flows
- [ ] No skipped tests (x, skip, pending)
- [ ] Tests are readable (good names, comments)
- [ ] Tests pass locally and in CI

### Git

- [ ] Commits are atomic (one logical change per commit)
- [ ] Commit messages are descriptive
- [ ] No merge commits (rebase before merge)
- [ ] No large binary files
- [ ] No secrets (API keys, tokens) committed

---

## Tools & Resources

### Home Assistant Development

- **Dev Docs**: https://developers.home-assistant.io/
- **Integration Template**: https://github.com/home-assistant/example_custom_component
- **WebSocket API**: https://developers.home-assistant.io/docs/api/websocket/
- **Test HA Instance**: Pre-provisioned at `ha.test.local:8123`

### Frontend

- **Lit Documentation**: https://lit.dev/
- **HA Components**: https://github.com/home-assistant/frontend
- **Lit Best Practices**: https://lit.dev/docs/composition/lifecycle/

### Debugging

- **Chrome DevTools**: F12 (WebSocket inspector, console, performance)
- **HA Dev Tools**: Services, States, Events (at `/dev-tools`)
- **Logging**: Backend: `_LOGGER.debug()`, Frontend: `console.log()` (will be removed)

---

## Critical Success Factors

1. **Communication**: Ask questions early. Flag blockers immediately.
2. **Testing**: Don't skip tests. QA will find bugs you should have caught.
3. **Performance**: Real-time must feel real. < 500ms latency is critical.
4. **Accessibility**: Test on real devices (mobile). Lighthouse ≥ 90.
5. **Code Review**: Iterate with feedback. Don't defend, improve.
6. **Documentation**: Write comments for "why", not "what". Code should be self-documenting for "what".

---

## Common Pitfalls to Avoid

1. **Polling Instead of Push**: Don't add periodic updates. Listen to events.
2. **Hardcoded Colors**: Use `var(--error-color)`. Dark/light mode will break.
3. **Blocking Calls**: No `requests.get()`. Use async/await.
4. **State Mutation**: Don't modify `hass.states` directly.
5. **Unhandled Promises**: Every promise should have .catch().
6. **No Error Handling**: Every async call needs try/catch.
7. **Skipped Tests**: Tests aren't optional. They're part of "done".
8. **localStorage Issues**: Handle full/unavailable gracefully.

---

## Questions? Ask Early

**Before you start**:
- Read all architecture docs (system-design.md, ADRs)
- Ask if anything is unclear

**During development**:
- Ask if you hit a blocker
- Ask if you disagree with an ADR decision
- Ask for code review early (don't wait until "done")

**After features**:
- Ask QA if acceptance unclear
- Ask Architect if design decision conflicts

---

## Timeline Pressure

Sprint ends Friday, March 7th. No extensions.

**Critical Path**:
- Story 1 (Real-Time): Days 1-4 (must complete, blockers Story 2)
- Story 2 (Thresholds): Days 5-9 (depends on Story 1)
- Story 3 (Sort/Filter): Days 6-8 (independent of Stories 1-2)
- Story 4 (Mobile): Days 9-10 (polish, all stories must be done)
- Story 5 (Deployment): Days 9-10 (can happen in parallel)

**If You Get Stuck**:
1. Try for 30 minutes
2. Ask for help
3. Don't waste time struggling alone

---

## Final Thoughts

Sprint 2 is ambitious. Five stories in 16 days is tight. But the architecture is solid, the design is clear, and you've got support.

**You've built this before** (Sprint 1 was similar scope). You know Home Assistant patterns, you know Lit, you know our CI/CD. Trust the process.

**Ship it well. Code it clean. Test it thoroughly.**

Good luck. I'm cheering you on.

—FiremanDecko (Architect)

---

## Handoff Checklist

Before you say "done":

- [ ] All 5 stories implemented
- [ ] All acceptance criteria met
- [ ] All code reviewed and approved
- [ ] All tests passing (> 80% coverage)
- [ ] QA sign-off for all stories
- [ ] Zero critical bugs
- [ ] No console errors/warnings
- [ ] No secrets in git history
- [ ] Documentation complete (ADRs, API docs, README)
- [ ] Deployment tested (3+ idempotent runs)
- [ ] Performance targets met (< 500ms real-time, < 50ms sort/filter)
- [ ] Mobile & accessibility tested (Lighthouse ≥ 90)
- [ ] Code on `develop` branch (not `main`)

When all boxes are checked: **You're done.** Great work.
