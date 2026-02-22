# Delegation Brief: Sprint 3 Implementation

**For**: ArsonWells (Lead Developer)
**From**: FiremanDecko (Architect)
**Date**: February 22, 2026
**Sprint Duration**: 2 weeks (10 business days)
**Capacity**: 16 days
**Planned Work**: 12 days (1+3+4+2+2)
**Buffer**: 4 days contingency

---

## The Mission

Sprint 3 makes Vulcan Brownout a truly proactive monitoring system. You'll implement:

1. **Binary Sensor Filtering** (1 day - DO THIS FIRST - quick win)
2. **Infinite Scroll with Cursor Pagination** (3 days)
3. **Notification System** (4 days - most complex)
4. **Dark Mode / Theme Support** (2 days)
5. **Deployment & Infrastructure** (2 days)

**Success = All 5 stories shipped, tested, and production-ready by Friday sprint end.**

---

## Architecture Documents to Read (In Order)

1. **SKILL.md** — Your role as architect liaison
2. **system-design.md** (Sprint 3 updated) — Component diagram, data flows, entity filtering, pagination algorithm
3. **api-contracts.md** (Sprint 3 updated) — All new WebSocket commands/events (cursor-based pagination, notifications, theme)
4. **sprint-plan.md** (Sprint 3) — 5 stories with acceptance criteria
5. **ADR-009, 010, 011, 012** — Design decisions for cursor pagination, notifications, dark mode, entity filtering
6. **Existing code**: `/development/src/custom_components/vulcan_brownout/*.py` and frontend JS

**CRITICAL**: These docs contain the architecture. Read them before coding. If anything is unclear, ask now.

---

## Quick Start: Do This First

### Binary Sensor Filtering (1 Day - QUICK WIN)

This is a **quick win** that unblocks other stories and fixes data quality.

**What**: Remove binary sensors from battery list (they report on/off, not %)

**Files to Change**:

1. `/development/src/custom_components/vulcan_brownout/battery_monitor.py`
   - Modify method `get_battery_entities()` (or similar entity discovery method)
   - Add filter: `battery_level` attribute must exist AND be numeric (0-100)
   - Add filter: Exclude domain == 'binary_sensor'
   - Example:
     ```python
     def is_battery_entity(entity_id: str) -> bool:
         domain = entity_id.split('.')[0]
         if domain == 'binary_sensor':
             return False
         entity = hass.states.get(entity_id)
         battery_level = entity.attributes.get('battery_level')
         if battery_level is None:
             return False
         try:
             level = float(battery_level)
             if not (0 <= level <= 100):
                 return False
         except (TypeError, ValueError):
             return False
         return True
     ```

2. `/development/src/custom_components/vulcan_brownout/frontend/vulcan-brownout-panel.js`
   - Add empty state UI (show if `devices.length === 0`)
   - Template: Friendly message, "No battery devices found"
   - Include buttons: Docs link, Refresh, Settings
   - Example Mermaid from design doc for reference

**Testing**:
- Unit: Test `is_battery_entity()` with various inputs (binary sensor, missing battery_level, etc.)
- Integration: Query HA instance, count filtered devices
- QA will verify 45 binary sensors are removed from test HA

**Why First?**: Clean data quality, unblocks pagination (don't want to paginate bad entities), small scope, high impact.

---

## Story 1: Binary Sensor Filtering

See "Quick Start" section above. Do this immediately.

---

## Story 2: Infinite Scroll with Cursor Pagination

### 2.1 Backend: Cursor-Based Pagination API

**Files to Change**:

1. **`websocket_api.py`**
   - Modify `handle_query_devices()` command handler
   - **OLD** (Sprint 2): `offset` + `limit` pagination
   - **NEW** (Sprint 3): `cursor` + `limit` pagination
   - Old request: `{offset: 0, limit: 50}`
   - New request: `{cursor: null, limit: 50}`
   - Next page: `{cursor: "base64(...)", limit: 50}`

2. **`battery_monitor.py`**
   - Add method: `get_devices_paginated(cursor: str | None, limit: int, sort_key: str) -> dict`
   - Cursor format: base64-encoded `{last_changed}|{entity_id}`
   - Logic:
     a. Decode cursor (if provided) to find starting position
     b. Get all battery entities (already filtered by Story 1)
     c. Apply sort (priority, alphabetical, level_asc, level_desc)
     d. Find cursor position in sorted list
     e. Return items from position+1 to position+limit
     f. Generate next_cursor from last item in response
     g. Return: `{devices: [...], total: N, has_more: bool, next_cursor: "base64(...)"}`

**Implementation Detail - Cursor Decoding**:
```python
import base64

def decode_cursor(cursor_str: str) -> tuple[str, str]:
    """Decode cursor to (last_changed, entity_id)."""
    decoded = base64.b64decode(cursor_str).decode('utf-8')
    parts = decoded.split('|')
    return parts[0], parts[1]  # last_changed, entity_id

def encode_cursor(last_changed: str, entity_id: str) -> str:
    """Encode (last_changed, entity_id) to cursor string."""
    data = f"{last_changed}|{entity_id}"
    return base64.b64encode(data.encode('utf-8')).decode('utf-8')
```

**Response Format**:
```json
{
  "devices": [...50 items...],
  "total": 200,
  "has_more": true,
  "next_cursor": "eyIyMDI2LTAyLTIyVDEwOjE1OjMwWiIsInNlbnNvci5raXRjaGVuIn0="
}
```

### 2.2 Frontend: Infinite Scroll UI

**Files to Change**:

1. **`vulcan-brownout-panel.js`**
   - Add Intersection Observer to detect scroll near bottom (100px)
   - Debounce scroll events (max 1 fetch per 500ms)
   - Track state: `this.current_cursor`, `this.has_more`, `this.is_fetching`
   - When near bottom:
     a. Set `is_fetching = true`
     b. Show skeleton loaders (5 placeholders)
     c. Fetch next batch with `current_cursor`
     d. Append new devices to `this.battery_devices` array
     e. Update `current_cursor` to `next_cursor`
     f. Set `is_fetching = false`
     f. Hide skeleton loaders

2. **Create Skeleton Loader Component**
   - CSS class: `.skeleton-loader`
   - Animation: Shimmer gradient, 2s infinite
   - Colors: Dark mode #444444, light mode #E0E0E0
   - Sizing: Match real card heights (vary heights)
   - Example CSS:
     ```css
     @keyframes shimmer {
       0% { background-position: -1000px 0; }
       100% { background-position: 1000px 0; }
     }
     .skeleton-loader {
       background: linear-gradient(90deg, var(--vb-skeleton-bg) 25%, var(--vb-skeleton-shimmer) 50%, var(--vb-skeleton-bg) 75%);
       background-size: 1000px 100%;
       animation: shimmer 2s infinite;
       border-radius: 4px;
       height: 16px;
       margin-bottom: 8px;
     }
     ```

3. **Add Back to Top Button**
   - Element: Fixed position, bottom-right (16px from edges)
   - Trigger show: scrolled past 30 items (or ~1000px)
   - Trigger hide: scroll back to top
   - Click: Smooth scroll to top (500ms)
   - Animation: Fade in/out (300ms CSS)
   - ARIA: `aria-label="Back to top"`
   - Example handler:
     ```javascript
     backToTopButton.addEventListener('click', () => {
       this.shadowRoot.querySelector('.battery-list').scrollTo({
         top: 0,
         behavior: 'smooth'
       });
     });
     ```

4. **Add Scroll Position Restoration**
   - On scroll events, save position: `sessionStorage.setItem('vulcanScrollPos', scrollTop)`
   - On component init, restore: `sessionStorage.getItem('vulcanScrollPos')`
   - Edge case: If device count changed, validate scroll position doesn't exceed maxScrollHeight

**Testing You Must Do**:
- Load panel, scroll to bottom 3x, verify no duplicate items
- Load with 200 device HA instance, paginate through all pages
- Scroll rapidly, verify debounce prevents duplicate fetches
- Refresh page mid-scroll, verify position restored
- Mobile: Scroll on iPhone 12, verify 60 FPS (no jank)

---

## Story 3: Notification System with Preferences UI

### 3.1 Backend: NotificationManager

**New File to Create**: `/development/src/custom_components/vulcan_brownout/notification_manager.py`

**Class: NotificationManager**

```python
class NotificationManager:
    def __init__(self, hass, battery_monitor):
        self.hass = hass
        self.battery_monitor = battery_monitor
        self.preferences = {}  # Loaded from config entry
        self.notification_history = {}  # Track last_notification_time per device

    async def async_setup(self):
        """Load preferences from config entry."""
        config_entry = ...  # Get from hass.config_entries
        self.preferences = config_entry.options.get('notification_preferences', {
            'enabled': True,
            'frequency_cap_hours': 6,
            'severity_filter': 'critical_only',
            'per_device': {}
        })

    async def check_and_send_notification(self, entity_id: str, status: str, battery_level: int, device_name: str):
        """Check if notification should be sent, then queue it to HA."""
        # Step 1: Check global enabled
        if not self.preferences['enabled']:
            return

        # Step 2: Check device enabled
        device_pref = self.preferences['per_device'].get(entity_id, {})
        if not device_pref.get('enabled', True):
            return

        # Step 3: Check severity filter
        severity = self.preferences['severity_filter']
        if severity == 'critical_only' and status == 'warning':
            return

        # Step 4: Check frequency cap
        frequency_cap_hours = device_pref.get('frequency_cap_hours', self.preferences['frequency_cap_hours'])
        last_notif_time = self.notification_history.get(entity_id)
        if last_notif_time:
            time_since = datetime.now() - last_notif_time
            if time_since < timedelta(hours=frequency_cap_hours):
                return  # Within cap window, don't send

        # Step 5: Send notification via HA service
        await self._send_notification(entity_id, status, battery_level, device_name)
        self.notification_history[entity_id] = datetime.now()

    async def _send_notification(self, entity_id: str, status: str, battery_level: int, device_name: str):
        """POST to persistent_notification service."""
        status_label = "critical" if status == 'critical' else "warning"
        message = f"{device_name} battery {status_label} ({battery_level}%) — action needed soon"

        await self.hass.services.async_call(
            'persistent_notification',
            'create',
            {
                'title': '🔋 Battery Low',
                'message': message,
                'notification_id': f'vulcan_brownout.{entity_id}.{status}'
            }
        )

        # Broadcast event to WebSocket subscribers
        await self.broadcast_notification_sent(entity_id, device_name, status, battery_level, message)
```

### 3.2 Backend: Integrate with Battery Monitor

**Modify**: `/development/src/custom_components/vulcan_brownout/battery_monitor.py`

- Add hook in `on_state_changed()` to call NotificationManager
- Example:
  ```python
  async def on_state_changed(self, entity_id, new_state):
      if not self.is_battery_entity(entity_id):
          return

      # ... existing logic to broadcast device_changed ...

      # NEW: Check notifications
      status = self.get_status(entity_id, new_state)
      battery_level = float(new_state.state)
      device_name = new_state.attributes.get('friendly_name', entity_id)
      await self.notification_manager.check_and_send_notification(
          entity_id, status, battery_level, device_name
      )
  ```

### 3.3 Backend: WebSocket Commands for Notifications

**Modify**: `/development/src/custom_components/vulcan_brownout/websocket_api.py`

Add two new command handlers:

1. **`handle_get_notification_preferences(hass, connection, msg)`**
   - Retrieve current preferences
   - Return: `{enabled, frequency_cap_hours, severity_filter, per_device, notification_history}`
   - notification_history: Last 10-20 notifications (timestamp, entity_id, device_name, battery_level, status, message)

2. **`handle_set_notification_preferences(hass, connection, msg)`**
   - Validate input:
     - `enabled`: bool
     - `frequency_cap_hours`: int in [1, 6, 24]
     - `severity_filter`: str in ['critical_only', 'critical_and_warning']
     - `per_device`: dict of {entity_id: {enabled: bool, frequency_cap_hours: int}}
   - Update config entry options
   - Broadcast `status` event to all clients
   - Return success response

### 3.4 Frontend: Notification Preferences Modal

**Modify**: `/development/src/custom_components/vulcan_brownout/frontend/vulcan-brownout-panel.js`

1. **Add Notification Preferences Modal Component**
   - Trigger: "[⚙️ CONFIGURE NOTIFICATIONS]" button in settings panel
   - Modal opens: Slide from right (desktop) or bottom (mobile)
   - Sections:
     a. **Global Enable**: Toggle switch (44px touch target)
     b. **Frequency Cap**: Dropdown (1 hour, 6 hours, 24 hours)
     c. **Severity Filter**: Radio buttons (Critical only, Critical+Warning)
     d. **Per-Device List**: Checkboxes with search
     e. **Notification History**: Last 5 notifications
   - Buttons: Save (blue), Cancel (gray)

2. **Add Search Functionality**
   - Searchable device list (real-time filter as user types)
   - Show only matching devices

3. **Add Notification History Display**
   - Subscribe to `notification_sent` events
   - Append to history list (max 10 items in UI)
   - Format: "2026-02-22 10:15 — Device Name (8% critical)"

4. **Form Handling**
   - On Save: Send `set_notification_preferences` command
   - On Cancel: Close modal without saving (confirm if changes made)
   - Keyboard: Tab through fields, Enter to save, Escape to cancel

**Testing You Must Do**:
- Unit: Frequency cap logic (mock time, test window expiration)
- Integration: Create device at critical, set notifications ON, verify notification sent
- Integration: Change frequency cap to 1 hour, trigger 2 notifications within 1 hour, verify only 1 sent
- Integration: Disable device notifications, device goes critical, verify no notification
- QA: Multi-device scenario (5 devices critical at same time, frequency caps enforced per device)

---

## Story 4: Dark Mode / Theme Support

### 4.1 Frontend: CSS Custom Properties

**Create or Modify**: `/development/src/custom_components/vulcan_brownout/frontend/styles.css`

Define CSS custom properties for all colors:

```css
/* Light Mode (Default) */
:root,
[data-theme="light"] {
  --vb-bg-primary: #FFFFFF;
  --vb-bg-card: #F5F5F5;
  --vb-bg-divider: #E0E0E0;
  --vb-text-primary: #212121;
  --vb-text-secondary: #757575;
  --vb-text-disabled: #BDBDBD;
  --vb-color-critical: #F44336;
  --vb-color-warning: #FF9800;
  --vb-color-healthy: #4CAF50;
  --vb-color-unavailable: #9E9E9E;
  --vb-color-primary-action: #03A9F4;
  --vb-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  --vb-skeleton-bg: #E0E0E0;
  --vb-skeleton-shimmer: #F5F5F5;
}

/* Dark Mode */
[data-theme="dark"],
[data-theme="dark-theme"] {
  --vb-bg-primary: #1C1C1C;
  --vb-bg-card: #2C2C2C;
  --vb-bg-divider: #444444;
  --vb-text-primary: #FFFFFF;
  --vb-text-secondary: #B0B0B0;
  --vb-text-disabled: #666666;
  --vb-color-critical: #FF5252;       /* Brightened red */
  --vb-color-warning: #FFB74D;        /* Lightened amber */
  --vb-color-healthy: #66BB6A;        /* Lightened green */
  --vb-color-unavailable: #BDBDBD;
  --vb-color-primary-action: #03A9F4;
  --vb-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
  --vb-skeleton-bg: #444444;
  --vb-skeleton-shimmer: #555555;
}

/* Apply to all components */
.battery-panel {
  background-color: var(--vb-bg-primary);
  color: var(--vb-text-primary);
  border-color: var(--vb-bg-divider);
}

.battery-card {
  background-color: var(--vb-bg-card);
  color: var(--vb-text-primary);
  box-shadow: var(--vb-shadow);
}

.battery-critical {
  color: var(--vb-color-critical);
}

.battery-warning {
  color: var(--vb-color-warning);
}

.battery-healthy {
  color: var(--vb-color-healthy);
}
```

**IMPORTANT**: Remove all hardcoded colors from CSS. Use `var(--vb-*)` everywhere.

### 4.2 Frontend: Theme Detection

**Modify**: `/development/src/custom_components/vulcan_brownout/frontend/vulcan-brownout-panel.js`

Add theme detection method:

```javascript
detectTheme() {
  // Method 1: HA's data-theme attribute (most reliable)
  const haTheme = document.documentElement.getAttribute('data-theme');
  if (haTheme === 'dark') return 'dark';
  if (haTheme === 'light') return 'light';

  // Method 2: CSS Media Query (OS preference)
  if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
    return 'dark';
  }

  // Method 3: HA localStorage (fallback)
  const stored = localStorage.getItem('ha_theme');
  if (stored === 'dark' || stored === 'light') return stored;

  // Default to light
  return 'light';
}
```

### 4.3 Frontend: Theme Listener

Add MutationObserver to watch for theme changes:

```javascript
observeThemeChanges() {
  const observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
      if (mutation.attributeName === 'data-theme') {
        const newTheme = document.documentElement.getAttribute('data-theme');
        this.applyTheme(newTheme);
      }
    });
  });

  observer.observe(document.documentElement, {
    attributes: true,
    attributeFilter: ['data-theme']
  });
}

applyTheme(theme) {
  // CSS custom properties already defined in styles.css
  // Just ensure data-theme attribute is set on root
  document.documentElement.setAttribute('data-theme', theme || 'light');
  // Optionally force re-render if needed
  this.requestUpdate();
}
```

### 4.4 Frontend: Responsive Dark Mode Colors

Ensure all status colors are readable on dark background:

- Critical: #FF5252 (lightened red) — contrast 5.5:1 on #1C1C1C ✓
- Warning: #FFB74D (lightened amber) — contrast 6.8:1 on #1C1C1C ✓
- Healthy: #66BB6A (lightened green) — contrast 4.8:1 on #1C1C1C ✓ (AA)
- Text: #FFFFFF (white) — contrast 19:1 on #1C1C1C ✓ (AAA)

Use [WebAIM contrast checker](https://webaim.org/resources/contrastchecker/) to verify.

**Testing You Must Do**:
- Load panel in light mode, verify light colors
- Load panel in dark mode, verify dark colors
- Toggle HA theme while panel is open, verify smooth transition (no flashing)
- Use contrast checker, verify all colors meet WCAG AA (4.5:1)
- Mobile: Load on iPhone 12 in dark mode, verify readable

---

## Story 5: Deployment & Infrastructure

### 5.1 Idempotent Deployment Script

**Update**: `deploy.sh` (or similar)

Make script safe to run multiple times:

```bash
#!/bin/bash
set -e

# Step 1: Validate .env variables
if [ -z "$HASS_URL" ] || [ -z "$HASS_TOKEN" ]; then
  echo "ERROR: Missing required .env variables"
  echo "Required: HASS_URL, HASS_TOKEN"
  exit 1
fi

# Step 2: Copy files (idempotent)
mkdir -p releases/$(date +%s)
rsync -av --delete ./src/ releases/$(date +%s)/

# Step 3: Create symlink (safe to re-run)
ln -sfn releases/$(date +%s) current

# Step 4: Health check
curl -f http://$HASS_URL/api/vulcan_brownout/health || exit 1

# Step 5: Rollback if needed
if [ $? -ne 0 ]; then
  ln -sfn releases/previous current
  echo "Rollback completed"
  exit 1
fi

echo "Deployment successful"
```

### 5.2 Health Check Endpoint

**Create New File**: `/development/src/custom_components/vulcan_brownout/health.py`

Or add to `websocket_api.py`:

```python
async def health_check(hass):
    """Health check for deployment validation."""
    return {
        'status': 'healthy',
        'integration': 'vulcan_brownout',
        'websocket_ready': True,
        'battery_entities': len(battery_monitor.get_battery_entities()),
        'notifications_ready': notification_manager is not None,
        'timestamp': datetime.now().isoformat()
    }
```

Register as HTTP GET endpoint:
```python
app.router.get('/api/vulcan_brownout/health', health_check)
```

### 5.3 Testing Deployment

Test script 3+ times:

```bash
# Run 1
./deploy.sh
# Verify success

# Run 2 (same version)
./deploy.sh
# Verify idempotent (no errors)

# Run 3
./deploy.sh
# Verify idempotent (no errors)

# Simulate failure
# Modify health check to fail
./deploy.sh
# Verify rollback triggered
# Verify previous version active
```

**Testing You Must Do**:
- Run deploy script 3x in a row, verify all succeed with no errors
- Deploy with missing .env variable, verify clear error message
- Simulate health check failure, verify rollback triggered
- Check git history: `git log -p -- .env` — should show nothing
- Monitor HA logs post-deploy, check for errors

---

## Common Patterns in the Codebase

### WebSocket Command Handler Pattern

```python
async def handle_command_name(hass, connection, msg):
    """Handle vulcan-brownout/command_name command."""
    try:
        # Validate input
        data = msg['data']
        if 'required_field' not in data:
            raise ValueError("Missing required_field")

        # Process
        result = await do_something(data)

        # Send response
        connection.send_message(
            websocket_api.result_message(msg['id'], {
                'status': 'success',
                'data': result
            })
        )
    except Exception as e:
        _LOGGER.error(f"Error: {e}")
        connection.send_message(
            websocket_api.error_message(msg['id'], 'invalid_request', str(e))
        )
```

### Lit Component Pattern (Frontend)

```javascript
class VulcanBrownoutPanel extends LitElement {
  @property() hass;
  @state() battery_devices = [];
  @state() is_loading = false;

  async connectedCallback() {
    super.connectedCallback();
    await this.load_devices();
    this.subscribe_to_updates();
  }

  async load_devices() {
    this.is_loading = true;
    const response = await this.hass.callWS({
      type: 'vulcan-brownout/query_devices',
      data: { limit: 50, cursor: null }
    });
    this.battery_devices = response.devices;
    this.is_loading = false;
  }

  render() {
    return html`
      <div class="battery-panel">
        ${this.is_loading ? html`<div class="loading">Loading...</div>` : ''}
        ${this.battery_devices.map(device => html`
          <div class="battery-card">
            ${device.device_name}: ${device.battery_level}%
          </div>
        `)}
      </div>
    `;
  }
}

customElements.define('vulcan-brownout-panel', VulcanBrownoutPanel);
```

---

## Code Review Criteria (for you to self-check before submitting PR)

### Python (Backend)
- [ ] Type hints on all functions
- [ ] Docstrings (what, args, returns, raises)
- [ ] Error handling (try/except, log errors)
- [ ] No blocking calls (all async)
- [ ] HA logging: `_LOGGER.info()`, `.error()`, `.debug()`
- [ ] Edge cases handled (None values, empty lists, invalid cursors)
- [ ] Performance considered (no N+1 queries, efficient filtering)

### JavaScript (Frontend)
- [ ] Lit conventions (properties, @state, render, styles)
- [ ] No manual DOM manipulation (let Lit handle it)
- [ ] Error handling (try/catch on promises)
- [ ] Clean up subscriptions (disconnectedCallback)
- [ ] CSS custom properties (for theming, no hardcoded colors)
- [ ] Performance (no re-renders on every keystroke, debounce events)
- [ ] Accessibility (ARIA labels, semantic HTML)

### Testing
- [ ] Unit tests: > 80% code coverage
- [ ] Integration tests: Real HA instance
- [ ] E2E tests: Full user flows
- [ ] No console errors/warnings
- [ ] Performance targets met

### Git
- [ ] Commits are atomic (one logical change per commit)
- [ ] Commit messages descriptive (use story number + what changed)
- [ ] No secrets in git history (`git log -p | grep -i password` returns nothing)
- [ ] PR description includes acceptance criteria checklist

---

## Tools & Resources

### Home Assistant Development
- **Dev Docs**: https://developers.home-assistant.io/
- **WebSocket API**: https://developers.home-assistant.io/docs/api/websocket/
- **Test HA Instance**: Pre-provisioned at `ha.test.local:8123`

### Frontend (Lit)
- **Lit Docs**: https://lit.dev/
- **HA Components**: https://github.com/home-assistant/frontend

### Debugging
- **Chrome DevTools**: F12 (Network, Console, Performance tabs)
- **HA Dev Tools**: /dev-tools in HA UI
- **Logging**: `_LOGGER.debug()` (Python), console.log() (JS, remove before merge)

---

## Critical Success Factors

1. **Read the Architecture Docs First** — Don't just code. Understand the design.
2. **Test Thoroughly** — Don't skip tests. QA will find bugs you missed.
3. **Performance Matters** — Real-time updates must feel real (< 500ms latency).
4. **Accessibility is Non-Negotiable** — Dark mode, WCAG AA contrast, keyboard navigation.
5. **No Secrets in Git** — Review git history before pushing.
6. **Ask Early** — Blockers are your problem to solve, not Architect's.

---

## Timeline

- **Mon-Wed Week 1**: Stories 1-2 (filtering + pagination)
- **Wed-Fri Week 1**: Stories 2-3 start (pagination ends, notifications begin)
- **Mon-Tue Week 2**: Story 3 finishes (notifications complete)
- **Wed-Fri Week 2**: Stories 4-5 (dark mode + deployment)
- **Friday EOD**: All stories shipped, tested, merged to `develop`

If you get stuck on any story:
1. Try for 30 minutes
2. Ask for help (don't waste time struggling alone)
3. Unblock others while architect helps you

---

## Final Thoughts

Sprint 3 is **ambitious but achievable**. You've done 2 sprints. You know the patterns. Trust the process.

**The architecture is solid. The design is clear. You've got support.**

Ship it well. Code it clean. Test it thoroughly.

I'm cheering you on.

—FiremanDecko (Architect)

---

**Prepared by**: FiremanDecko (Architect)
**Date**: February 22, 2026
**Status**: Ready for Implementation
