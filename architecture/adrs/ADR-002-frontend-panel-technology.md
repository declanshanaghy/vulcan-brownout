# ADR-002: Frontend Panel Technology

## Status: Proposed

## Context

Sprint 1 requires a custom sidebar panel component that renders a battery device list. The panel must:
1. Register as a native HA sidebar panel (not iframe, not popup)
2. Communicate with the backend via WebSocket
3. Be responsive across desktop/tablet/mobile
4. Use HA's theme tokens (dark/light mode)
5. Render efficiently with no jank during scroll or updates

We must choose:
- Component framework (vanilla JS, Preact, Lit Element, or web components)
- How the panel registers with HA
- How styles are scoped (shadow DOM vs. global CSS)
- Dependency footprint

## Options Considered

### Option A: Vanilla JavaScript + Shadow DOM
- **Implementation:** Plain ES6 class extending HTMLElement, Shadow DOM for style scoping
- **Registration:** Via `panel_custom` manifest entry in `manifest.json`
- **Styling:** Shadow DOM + HA CSS custom properties (--primary-color, --card-background-color, etc.)
- **Dependencies:** None (uses native Web APIs)
- **Pros:**
  - Zero dependencies, smallest bundle
  - Full control over rendering logic
  - Shadow DOM provides style isolation
  - Works in all modern browsers
  - Can still access HA's `hass` object for auth and API calls
- **Cons:**
  - More boilerplate code (lifecycle, property observation, re-renders)
  - Manual DOM manipulation (potentially error-prone)
  - Requires knowledge of Web Component APIs
  - No built-in reactivity (manual re-render on state change)

### Option B: Lit Element (Web Component library)
- **Implementation:** Extend `LitElement` base class, use decorators for properties and rendering
- **Registration:** Via `panel_custom` (same as Option A)
- **Styling:** Lit's scoped styles + HA CSS custom properties
- **Dependencies:** `lit@2.x` (already bundled in HA, no extra bundle size)
- **Pros:**
  - Reactive property system (auto-re-renders on property change)
  - Minimal boilerplate vs. vanilla JS
  - Excellent TypeScript support (optional)
  - Follows HA's own frontend patterns (HA uses Lit internally)
  - Less error-prone than manual DOM updates
  - Still zero external dependencies (Lit is bundled)
  - Great for complex state management (infinite scroll, pagination)
- **Cons:**
  - Slightly more abstraction than vanilla JS (learning curve for new devs)
  - Decorator syntax requires some familiarity with class-based components

### Option C: Preact (Lightweight React alternative)
- **Implementation:** Functional components with hooks, JSX syntax
- **Registration:** Via `panel_custom`
- **Styling:** CSS Modules or Tailwind (would need bundler setup)
- **Dependencies:** `preact`, `preact/hooks` (not bundled in HA, would increase bundle)
- **Pros:**
  - Familiar to React developers
  - Hooks are powerful for state management
  - Smaller than React
- **Cons:**
  - Adds external dependencies (increases bundle size)
  - Requires bundler (webpack/Rollup) for JSX compilation
  - HA doesn't provide Preact pre-bundled
  - More complex deployment (build step required)
  - Overkill for this use case (single panel component)

### Option D: Vue.js
- **Implementation:** Single-file components (.vue)
- **Registration:** Via `panel_custom` with build output
- **Styling:** Vue's scoped CSS
- **Dependencies:** `vue@3` (not bundled in HA)
- **Pros:**
  - Excellent developer experience
  - Scoped CSS is intuitive
- **Cons:**
  - Requires build step
  - Adds external dependency (not bundled in HA)
  - Over-engineered for this scope
  - CI/CD complexity (GitHub Actions for build)

## Decision

**Option B: Lit Element**

This balances simplicity, maintainability, and alignment with HA's own architecture.

### Rationale

1. **HA Native Alignment:** HA's frontend is built with Lit. By using Lit, we align with HA's patterns and conventions. Future HA developers joining the team will recognize the structure.

2. **Zero External Dependencies:** Lit is already bundled in HA. No additional bundle size, no build step required. Just write the component and drop it in the `frontend/` directory.

3. **Reactivity Without Complexity:** Lit's `@property` decorator + reactive rendering eliminates the boilerplate of vanilla JS's manual property observation and DOM updates. This is critical for Sprint 1's timeline.

4. **Perfect Scope Fit:** Lit excels at single components with complex state (battery list, infinite scroll, sorting, pagination). We don't need a full framework (Vue/React), but vanilla JS would be too verbose.

5. **Developer Experience:** Lit + TypeScript (optional) provides excellent IDE support and type safety. The template syntax is readable and concise.

6. **HA Components Integration:** Lit components easily consume HA's provided components (`ha-icon`, `ha-card`, etc.) and CSS tokens via CSS custom properties.

### Implementation Details

**File: `frontend/vulcan-brownout-panel.js`**

```javascript
import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { LocalizeMixin } from '/frontend/common/translations/localization.js';

@customElement('vulcan-brownout-panel')
export class VulcanBrownoutPanel extends LocalizeMixin(LitElement) {
  @property({ attribute: false }) hass; // Provided by HA
  @state() battery_devices = [];
  @state() isLoading = false;
  @state() hasMore = false;
  @state() error = null;

  async connectedCallback() {
    super.connectedCallback();
    await this._load_devices();
    this._setup_websocket();
  }

  async _load_devices() {
    this.isLoading = true;
    try {
      // Call WebSocket command: vulcan-brownout/query_devices
      const result = await this.hass.callWS({
        type: 'vulcan-brownout/query_devices',
        data: { limit: 20, offset: 0, sort_key: 'battery_level', sort_order: 'asc' }
      });
      this.battery_devices = result.data.devices;
      this.hasMore = result.data.has_more;
    } catch (e) {
      this.error = 'Failed to load battery devices';
      console.error(e);
    } finally {
      this.isLoading = false;
    }
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
      .progress-bar {
        height: 4px;
        background-color: var(--divider-color);
        border-radius: 2px;
        margin-top: 8px;
      }
    `;
  }

  render() {
    if (this.isLoading) {
      return html`<div class="loading">Loading battery devices...</div>`;
    }

    if (this.error) {
      return html`<div class="error">${this.error}</div>`;
    }

    if (this.battery_devices.length === 0) {
      return html`<div class="empty">No battery devices found</div>`;
    }

    return html`
      <div class="header">
        <h1>Vulcan Brownout</h1>
        <button @click=${this._on_refresh}><ha-icon icon="mdi:refresh"></ha-icon></button>
      </div>
      <ul class="device-list">
        ${this.battery_devices.map(device => html`
          <li class="device-card ${device.battery_level <= 15 ? 'critical' : ''}">
            <div class="device-name">${device.device_name}</div>
            <div class="battery-level">${device.battery_level}%</div>
            <div class="progress-bar" style="width: ${device.battery_level}%"></div>
          </li>
        `)}
      </ul>
    `;
  }

  async _on_refresh() {
    await this._load_devices();
  }
}
```

**File: `manifest.json`**

```json
{
  "domain": "vulcan_brownout",
  "name": "Vulcan Brownout",
  "version": "1.0.0",
  "documentation": "https://github.com/...",
  "requirements": [],
  "codeowners": ["@username"],
  "config_flow": true,
  "homeassistant": "2023.12.0",
  "panel_custom": [
    {
      "name": "vulcan-brownout",
      "sidebar_title": "Vulcan Brownout",
      "sidebar_icon": "mdi:battery-alert",
      "js_url": "/local/vulcan-brownout-panel.js",
      "require_admin": false
    }
  ]
}
```

### Panel Registration

The `panel_custom` manifest entry tells HA:
- Load `vulcan-brownout-panel.js` from the frontend directory
- Register the panel with title "Vulcan Brownout" and icon
- Add it to the sidebar
- Don't require admin role (users can see their own devices)

The component receives the `hass` object (providing auth, API access, theme tokens) automatically from HA.

### Styling Strategy

- **CSS Custom Properties:** Use HA's theme tokens (`--primary-color`, `--error-color`, `--card-background-color`, etc.) for colors, so dark/light mode works automatically
- **Shadow DOM:** Lit automatically scopes styles to the component, preventing global CSS conflicts
- **Responsive:** Use CSS media queries for mobile/tablet/desktop layouts
- **Accessibility:** Ensure focus indicators, semantic HTML, aria-labels

## Consequences

Positive:
- No external dependencies (Lit is bundled)
- Zero build step (drop the .js file in and it works)
- Reactive rendering (property changes trigger re-renders automatically)
- Great IDE support and type safety
- Aligns with HA's architecture (easier onboarding for future devs)
- Shadow DOM provides style isolation

Negative:
- Developers unfamiliar with Web Components or Lit will need to learn
- Slightly more abstraction than vanilla JS
- No JSX syntax (template literals are similar but different)

## Testing Implications

- Unit tests can mock the `hass` object and test component rendering
- Integration tests can mount the component in a real HA instance
- E2E tests can open the panel in a browser and verify UI

## Next Steps

- Lead Developer creates `vulcan-brownout-panel.js` using Lit
- Implement WebSocket communication to backend
- Implement infinite scroll with IntersectionObserver
- QA tests panel rendering and responsiveness across viewport sizes
