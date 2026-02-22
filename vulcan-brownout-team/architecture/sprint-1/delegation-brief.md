# Delegation Brief: Sprint 1 Implementation

## For: Lead Developer

This brief summarizes everything you need to begin implementing Sprint 1. Architecture decisions have been made; technical trade-offs have been resolved. Your job is to implement the design per best practices and deliver code that passes code review and QA testing.

---

## The Problem (Context)

Home Assistant users with battery-powered devices (sensors, locks, remotes, etc.) have no centralized way to see which devices have low batteries. They discover dead batteries reactively, when devices stop working.

**Sprint 1 solves this:** A lightweight integration that auto-discovers battery devices and renders them in a dedicated sidebar panel, ranked by urgency (critical first). **Zero configuration required.**

---

## What You're Building

### Backend (Python)
A Home Assistant integration that:
1. **Auto-discovers** all entities with `device_class=battery` on startup
2. **Caches** them in memory
3. **Listens** for state changes in real-time
4. **Serves** the list via WebSocket API (query + paginated results)

### Frontend (JavaScript)
A Lit-based sidebar panel that:
1. **Connects** to backend via WebSocket
2. **Renders** battery devices in a scrollable list
3. **Shows** status visually (color-coded: red=critical, green=healthy, gray=unavailable)
4. **Handles** empty and error states gracefully
5. **Refreshes** on manual request

### Deployment
An idempotent Bash script that:
1. Transfers integration files via rsync
2. Restarts HA via Docker
3. Health-checks the API
4. Logs all steps

---

## Architecture Overview

See these documents in order:

1. **`system-design.md`** — Component structure, data flows, error handling
2. **`api-contracts.md`** — WebSocket message schemas (the contract between backend/frontend)
3. **ADRs (001-005)** — Technical decisions and rationale:
   - ADR-001: Integration architecture (event-driven, in-memory cache, hardcoded 15% threshold)
   - ADR-002: Frontend technology (Lit Element, no external deps)
   - ADR-003: Deployment (SSH + rsync, idempotent)
   - ADR-004: Secrets management (.env, gitignore)
   - ADR-005: Test environment (pre-provisioned mock entities)

**Key Decisions You Must Honor:**
- Auto-discovery happens **once** on startup (no periodic polling)
- Battery entities are cached **in memory** (no persistent storage)
- Updates are **event-driven** (listening to HA state_changed events)
- Threshold is **hardcoded to 15%** (no config UI in Sprint 1)
- Sorting is **implicit** (critical → unavailable → healthy; no UI controls)
- Frontend is **Lit-based** (HA native, zero bundle overhead)
- Deployment is **via SSH + rsync** (not HACS in Sprint 1)

Don't fight these decisions; implement them as specified. If you have concerns, flag them in code review.

---

## File Structure

Create this structure in the integration directory:

```
custom_components/vulcan_brownout/
├── __init__.py                          # Integration setup, panel/WebSocket registration
├── const.py                             # DOMAIN, BATTERY_THRESHOLD, etc.
├── battery_monitor.py                   # Core service: discovery, caching, event handling
├── websocket_api.py                     # WebSocket command handlers
├── config_flow.py                       # Configuration UI (minimal for Sprint 1)
├── manifest.json                        # Integration metadata
├── translations/
│   └── en.json                          # i18n strings (minimal for Sprint 1)
└── frontend/
    ├── vulcan-brownout-panel.js         # Lit component
    └── styles.css                       # Shadow DOM scoped styles
```

Also create (in repo root):
```
deploy.sh                                # Deployment script
.env.example                             # Secrets template
.gitignore                               # Add .env, *.pem, id_rsa*
TESTING.md                               # QA instructions
```

---

## Implementation Guidance

### Backend: Key Classes & Methods

**`battery_monitor.py` (Core Service)**

```python
class BatteryMonitor:
    def __init__(self, hass, threshold=15):
        self.hass = hass
        self.threshold = threshold
        self.entities = {}  # In-memory cache: {entity_id: EntityData}

    async def discover_entities(self):
        """Query HA entity registry, filter by device_class=battery, cache."""
        # Use hass.data[entity_registry.DATA_ENTITY_REGISTRY] to access registry
        # For each entity:
        #   1. Check if device_class == "battery"
        #   2. Parse battery_level (handle non-numeric, "unavailable")
        #   3. Get friendly_name, device_name from registry
        #   4. Store in self.entities[entity_id]
        # Log: INFO "Discovered N battery entities"

    async def on_state_changed(self, event):
        """HA state_changed event listener. Update cache, notify clients."""
        # Extract entity_id from event
        # Check if it's a battery entity
        # If yes: Update cache, send device_changed event to WebSocket clients
        # If no: Ignore

    async def query_devices(self, limit=20, offset=0, sort_key='battery_level', sort_order='asc'):
        """Return paginated, sorted list of devices."""
        # Apply sorting to self.entities
        # Apply pagination (limit, offset)
        # Return: {devices: [...], total: int, offset: int, limit: int, has_more: bool}
        # Validate inputs; raise if invalid sort_key, limit, offset
```

**`__init__.py` (Entry Point)**

```python
async def async_setup_entry(hass, entry):
    """Called when config entry is setup."""
    # 1. Create BatteryMonitor service
    # 2. Call await battery_monitor.discover_entities()
    # 3. Store in hass.data[DOMAIN]
    # 4. Register WebSocket command via websocket_api.async_register_command()
    # 5. Register event listener via hass.bus.async_listen(EVENT_STATE_CHANGED, ...)
    # 6. Register sidebar panel via hass.components.frontend.async_register_panel()
    # Return True
```

**`websocket_api.py` (WebSocket Handler)**

```python
async def handle_query_devices(hass, connection, msg):
    """WebSocket command: vulcan-brownout/query_devices"""
    # 1. Parse msg['data']: extract limit, offset, sort_key, sort_order
    # 2. Validate parameters (see api-contracts.md)
    # 3. Call battery_monitor = hass.data[DOMAIN]
    # 4. Call result = await battery_monitor.query_devices(...)
    # 5. Send response via connection.send_json_message()
    # 6. On error: send error response with code and message
```

### Frontend: Key Methods

**`vulcan-brownout-panel.js` (Lit Component)**

```javascript
@customElement('vulcan-brownout-panel')
export class VulcanBrownoutPanel extends LocalizeMixin(LitElement) {
  @property({ attribute: false }) hass;
  @state() battery_devices = [];
  @state() isLoading = false;
  @state() error = null;
  @state() hasMore = false;
  @state() currentOffset = 0;

  async connectedCallback() {
    super.connectedCallback();
    await this._load_devices();
    // Optional: Set up WebSocket listeners for real-time updates
  }

  async _load_devices() {
    this.isLoading = true;
    try {
      const result = await this.hass.callWS({
        type: 'vulcan-brownout/query_devices',
        id: this._generate_message_id(),
        data: { limit: 20, offset: 0, sort_key: 'battery_level', sort_order: 'asc' }
      });
      this.battery_devices = result.data.devices;
      this.hasMore = result.data.has_more;
      this.error = null;
    } catch (e) {
      this.error = e;
      console.error('Failed to load devices:', e);
    } finally {
      this.isLoading = false;
    }
  }

  async _on_refresh() {
    await this._load_devices();
  }

  _get_status(device) {
    // Return "critical" | "unavailable" | "healthy"
    if (!device.available) return "unavailable";
    if (device.battery_level <= 15) return "critical";
    return "healthy";
  }

  render() {
    if (this.error) {
      return html`<div class="error-state">...</div>`;
    }
    if (this.battery_devices.length === 0) {
      return html`<div class="empty-state">...</div>`;
    }
    return html`<ul class="device-list">
      ${this.battery_devices.map(device => html`
        <li class="device-card ${this._get_status(device)}">
          <div class="device-content">
            <ha-icon .icon="${this._get_icon(device)}"></ha-icon>
            <div class="device-info">
              <div class="device-name">${device.device_name}</div>
              <div class="battery-level">${device.battery_level}%</div>
            </div>
          </div>
          <div class="progress-bar">
            <div class="progress-bar-fill" style="width: ${device.battery_level}%"></div>
          </div>
        </li>
      `)}
    </ul>`;
  }

  static get styles() {
    return css`
      :host {
        display: block;
        background-color: var(--card-background-color);
      }
      .device-list {
        list-style: none;
        padding: 0;
        margin: 0;
      }
      .device-card {
        padding: 12px;
        margin: 12px;
        border-radius: 4px;
        background-color: var(--card-background-color);
      }
      .device-card.critical {
        background-color: var(--error-color-background);
      }
      /* ... more styles ... */
    `;
  }
}
```

### Key Best Practices

**Python (Backend):**
- Use async/await throughout (HA is async)
- Use HA's logging module: `_LOGGER.info()`, `_LOGGER.error()`
- Avoid blocking calls (no requests.get() without await)
- Use type hints: `async def query_devices(self, limit: int, offset: int) -> dict:`
- Handle edge cases (non-numeric state, missing attributes, deleted entities)
- Don't mutate external state (e.g., don't modify hass.states directly)

**JavaScript (Frontend):**
- Use Lit conventions (properties, state, render, styles)
- Avoid manual DOM manipulation (let Lit's render() handle it)
- Use `this.hass` for all HA API calls (never fetch() directly)
- Handle promises with try/catch
- Clean up subscriptions in `disconnectedCallback()`
- Use CSS custom properties for colors (HA theme support)
- Test across viewports (mobile, tablet, desktop)

**Deployment:**
- Use `rsync` with `--delete` (ensures clean deployment)
- Always validate `.env` before using variables
- Use `set -euo pipefail` in Bash (fail fast, no unset vars)
- Log every major step (users should see progress)
- Check exit codes, don't assume success

---

## Testing Requirements

You must write tests for both backend and frontend. QA will run these before accepting your code.

### Backend Tests (Python)

Create `tests/` directory with:

**`test_battery_monitor.py`:**
- Test auto-discovery (mock HA state machine, verify entities found)
- Test battery level parsing (numeric, non-numeric, unavailable)
- Test state change handling (update cache, trigger events)
- Test query_devices (sorting, pagination, filtering)

**`test_websocket_api.py`:**
- Test query_devices command (valid request, response schema)
- Test error responses (invalid limit, sort_key, etc.)
- Test message validation

**`test_config_flow.py`:**
- Test config entry creation (minimal, no options for Sprint 1)

Run with: `python -m pytest tests/`

### Frontend Tests (JavaScript)

Create `tests/` directory with:

**`test_panel.js`:**
- Test component renders (template syntax, conditional rendering)
- Test state management (loading, error, empty, list)
- Test WebSocket communication (mock callWS)
- Test device status classification (critical, healthy, unavailable)
- Test responsive layout (CSS applied correctly)

Use a testing library like `@testing-library/lit` or `@open-wc/testing`.

Run with: `npm test` (configure in package.json)

### QA Tests (Manual + Integration)

QA will:
- Deploy to test HA server using `deploy.sh`
- Verify auto-discovery works
- Open panel, verify rendering
- Check empty state and error state
- Test refresh button
- Test responsive design (mobile/tablet/desktop)
- Verify no console errors

You provide:
- Deployment script (`deploy.sh`)
- Setup instructions (`TESTING.md`)
- Test HA config (predefined mock entities)

---

## Code Review Checklist

Before submitting for review, verify:

- [ ] Code follows HA integration patterns (see `custom_components/` in HA core)
- [ ] All docstrings present (what function does, args, returns, exceptions)
- [ ] No hardcoded strings (use i18n strings, see `translations/en.json`)
- [ ] Error messages are user-friendly (not stack traces)
- [ ] Logging is appropriate (INFO for progress, ERROR for failures)
- [ ] No debug print() or console.log() statements
- [ ] Tests pass and have >80% code coverage
- [ ] No external dependencies (except Lit, which is bundled)
- [ ] Performance is acceptable (no N+1 queries, no blocking calls)
- [ ] Security is sound (no secrets in code, SSH only)
- [ ] Accessibility is met (WCAG AA, aria-labels, semantic HTML)
- [ ] Documentation is complete (README, TESTING.md, docstrings)
- [ ] Code formatted with black (Python) and prettier (JavaScript)

---

## Common Pitfalls to Avoid

1. **Polling Instead of Event-Driven:** Don't add periodic polling for state changes. Listen to HA's state_changed events.

2. **Hardcoding Colors:** Don't use `#FF0000` for red. Use `var(--error-color)`. Dark/light mode will break.

3. **Blocking Calls:** Don't use `requests.get()`. Use `aiohttp` or HA's methods with await.

4. **Direct State Mutation:** Don't modify `hass.states[entity_id]` directly. The state machine owns the data.

5. **Complex Frontend Logic:** Keep sorting, filtering in the backend. Frontend renders, backend processes.

6. **Missing Error Handling:** Every async call should have try/catch. Every WebSocket command should validate inputs.

7. **No Testing:** Don't skip tests. QA will find bugs you should have caught.

8. **Ignoring Accessibility:** Use semantic HTML, aria-labels, test color contrast. Users depend on it.

---

## Key Resources

- **HA Integration Dev Docs:** https://developers.home-assistant.io/docs/creating_integration/
- **WebSocket API:** https://developers.home-assistant.io/docs/api/websocket/
- **Lit Documentation:** https://lit.dev/
- **HA Frontend Components:** https://github.com/home-assistant/frontend/tree/dev/src/components/
- **HACS Developers:** https://developers.hacs.xyz/

---

## Communication & Handoff

### During Implementation

- **Daily Standup:** Report progress, blockers, help needed
- **Code Review:** Submit PRs early and often; iterate on feedback
- **Questions:** Ask the Architect (me) if:
  - An ADR decision seems wrong for your use case
  - You need clarification on system design
  - You discover a technical constraint not in the plan
  - You find a bug in the design

### After Implementation

- **Code Review Approval:** Architect reviews all code
- **QA Sign-Off:** QA tests all acceptance criteria
- **Sprint Retro:** Lessons learned, improvements for Sprint 2

---

## Success Criteria (For You)

Your implementation is successful when:

1. **All code passes code review** (no style issues, good practices)
2. **All unit tests pass** (>80% coverage)
3. **QA accepts all stories** (acceptance criteria met)
4. **No console errors or HA logs pollution** (clean logs)
5. **Documentation is complete** (README, TESTING.md, docstrings)
6. **Code is ready to merge** (PR approved, no outstanding comments)
7. **Sprint deadline met** (within week, 5 business days)

---

## Sprint Scope & Stories

You're implementing 5 stories (see `sprint-plan.md` for details):

1. **Integration Scaffolding & Auto-Discovery** (8 pts)
   - Backend: `battery_monitor.py`, `__init__.py`, `websocket_api.py`
   - Do this first; everything else depends on it

2. **Sidebar Panel Rendering** (6 pts)
   - Frontend: `vulcan-brownout-panel.js` basic render
   - Can start in parallel with Story 1
   - Depends on Story 1 for WebSocket API

3. **Visual Status Indicators** (4 pts)
   - Frontend: Colors, icons, progress bars
   - Depends on Story 2

4. **Empty State & Error Handling** (6 pts)
   - Frontend: Error/empty state UI
   - Depends on Story 2

5. **Deployment Pipeline** (6 pts)
   - Infrastructure: `deploy.sh`, `.env.example`, TESTING.md
   - Can do in parallel with other stories
   - Needed before QA can test

**Suggested Timeline:**
- Day 1-2: Story 1 (backend scaffolding)
- Day 2-3: Story 2 (panel rendering, can overlap with Story 1)
- Day 3: Story 3 (visual indicators)
- Day 4: Story 4 (error handling)
- Day 4-5: Story 5 (deployment) + code review + fixes

---

## Questions for the Architect (Me)

Before you start coding, ask if:

1. **Feasibility:** Does the auto-discovery approach work for all entity types?
2. **Performance:** Will in-memory caching scale to 1000+ devices?
3. **Limits:** Any known HA constraints on WebSocket message size, query frequency?
4. **Mobile:** Any known gotchas with HA's sidebar on mobile?
5. **CI/CD:** Should deployment script integrate with GitHub Actions, or manual-only for Sprint 1?

---

## Final Notes

- **This is an MVP.** Sprint 1 is not feature-complete. Threshold config, sorting UI, notifications all come later.
- **Simplicity over Cleverness.** A boring, straightforward implementation is better than a complex one.
- **User-First.** When in doubt, choose what's easiest for the user.
- **Test Everything.** Tests catch bugs before users do.
- **Ask for Help.** If you're stuck, ask. That's what I'm here for.

---

## Handoff Checklist

Before handing off to QA, ensure:

- [ ] All 5 stories implemented
- [ ] All code reviewed and approved
- [ ] All tests passing (unit + integration)
- [ ] Deployment script tested (3+ runs idempotent)
- [ ] TESTING.md is clear and complete
- [ ] No console errors or warnings
- [ ] No HA logs pollution
- [ ] README.md explains the integration
- [ ] Code is on `develop` branch (not main)
- [ ] Documentation is complete (ADRs, system design, API contracts)

---

## You've Got This

The architecture is solid, the design is clear, and the scope is manageable. Implement per the ADRs, follow best practices, ask questions when stuck, and deliver working code.

Good luck. I'll be reviewing your code and cheering you on.

— Your Architect
