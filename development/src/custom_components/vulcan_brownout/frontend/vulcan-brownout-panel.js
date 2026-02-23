/**
 * Vulcan Brownout Battery Monitor Panel v6.1.0
 *
 * Tabbed panel: "Low Battery" (entities below 15%) and
 * "Unavailable Devices" (state=unavailable|unknown).
 * Real-time updates apply to the Low Battery tab only.
 * Unavailable tab is a point-in-time snapshot loaded lazily on first visit.
 * Theme follows HA user preference (Auto/Light/Dark) via CSS custom properties.
 */

import { LitElement, html, css } from "https://unpkg.com/lit@3.1.0?module";

const QUERY_ENTITIES_COMMAND = "vulcan-brownout/query_entities";
const QUERY_UNAVAILABLE_COMMAND = "vulcan-brownout/query_unavailable";
const SUBSCRIBE_COMMAND = "vulcan-brownout/subscribe";

const SESSION_STORAGE_KEY = "vulcan_brownout_active_tab";

const TAB_LOW_BATTERY = "low-battery";
const TAB_UNAVAILABLE = "unavailable";

const RECONNECT_BACKOFF = [1000, 2000, 4000, 8000, 16000, 30000];
const MAX_RECONNECT_ATTEMPTS = 10;

const CONNECTION_CONNECTED = "connected";
const CONNECTION_RECONNECTING = "reconnecting";
const CONNECTION_OFFLINE = "offline";

class VulcanBrownoutPanel extends LitElement {
  static properties = {
    hass: { attribute: false },
    battery_devices: { state: true },
    isLoading: { state: true },
    error: { state: true },
    connection_status: { state: true },
    subscription_id: { state: true },
    current_theme: { state: true },
    _activeTab: { state: true },
    _unavailableEntities: { state: true },
    _unavailableTotal: { state: true },
    _unavailableLoading: { state: true },
    _unavailableError: { state: true },
  };

  constructor() {
    super();
    this.hass = null;
    this.battery_devices = [];
    this.isLoading = false;
    this.error = null;
    this.connection_status = CONNECTION_OFFLINE;
    this.subscription_id = null;
    this.current_theme = "light";
    this._activeTab = TAB_LOW_BATTERY;
    this._unavailableEntities = null; // null = not yet loaded (lazy-load guard)
    this._unavailableTotal = 0;
    this._unavailableLoading = false;
    this._unavailableError = null;
  }

  reconnect_attempt = 0;
  reconnect_timer = null;
  _themeListener = null;

  updated(changedProperties) {
    super.updated(changedProperties);
    if (changedProperties.has("hass") && this.hass && !this._themeListener) {
      this._setup_theme_listener();
      this._apply_theme(this._detect_theme());
    }
  }

  connectedCallback() {
    super.connectedCallback();
    this._apply_theme(this._detect_theme());

    // Restore tab from session storage before first data fetch
    const savedTab = sessionStorage.getItem(SESSION_STORAGE_KEY);
    if (savedTab === TAB_LOW_BATTERY || savedTab === TAB_UNAVAILABLE) {
      this._activeTab = savedTab;
    }

    this._load_devices();
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    this._clear_reconnect_timer();
    if (this._themeListener && this.hass?.connection) {
      this.hass.connection.removeEventListener(
        "hass_themes_updated",
        this._themeListener
      );
      this._themeListener = null;
    }
  }

  static styles = css`
    :host {
      --vb-bg-primary: var(--primary-background-color, #fafafa);
      --vb-bg-card: var(--card-background-color, #ffffff);
      --vb-bg-divider: var(--divider-color, #e0e0e0);
      --vb-border-color: var(--divider-color, #e0e0e0);
      --vb-text-primary: var(--primary-text-color, #212121);
      --vb-text-secondary: var(--secondary-text-color, #727272);
      --vb-text-disabled: var(--disabled-text-color, #bdbdbd);
      --vb-color-critical: var(--error-color, #db4437);
      --vb-color-primary-action: var(--primary-color, #03a9f4);
      --vb-shadow: var(--ha-card-box-shadow, 0 2px 8px rgba(0, 0, 0, 0.1));
    }

    .battery-panel {
      display: flex;
      flex-direction: column;
      height: 100%;
      background-color: var(--vb-bg-primary);
      color: var(--vb-text-primary);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
        sans-serif;
      padding: 16px;
      transition: background-color 300ms ease-out, color 300ms ease-out;
    }

    .header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 16px;
      padding-bottom: 12px;
      border-bottom: 1px solid var(--vb-bg-divider);
    }

    .header h1 {
      margin: 0;
      font-size: 20px;
      font-weight: 600;
    }

    .connection-badge {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 4px 8px;
      border-radius: 4px;
      background-color: var(--vb-bg-card);
      color: var(--vb-text-secondary);
      font-size: 12px;
    }

    .connection-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      display: inline-block;
    }

    .connection-dot.connected {
      background-color: #4caf50;
    }
    .connection-dot.reconnecting {
      background-color: #ff9800;
      animation: pulse 1s infinite;
    }
    .connection-dot.offline {
      background-color: #f44336;
    }

    @keyframes pulse {
      0%,
      100% {
        opacity: 1;
      }
      50% {
        opacity: 0.5;
      }
    }

    /* Tab bar */
    .tab-bar {
      display: flex;
      align-items: center;
      gap: 24px;
      padding: 0 0 0 0;
      height: 40px;
      border-bottom: 1px solid var(--vb-border-color);
      margin-bottom: 0;
    }

    .tab {
      background: none;
      border: none;
      border-bottom: 2px solid transparent;
      padding: 0 0 2px 0;
      height: 40px;
      min-width: 80px;
      cursor: pointer;
      font-size: 14px;
      font-weight: 400;
      color: var(--vb-text-secondary);
      display: inline-flex;
      align-items: center;
    }

    .tab.active {
      color: var(--vb-color-primary-action);
      font-weight: 600;
      border-bottom: 2px solid var(--vb-color-primary-action);
    }

    .tab:hover:not(.active) {
      color: var(--vb-text-primary);
    }

    .tab:focus-visible {
      outline: 2px solid var(--vb-color-primary-action);
      outline-offset: 2px;
    }

    .tab-panel {
      flex: 1;
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }

    .table-container {
      flex: 1;
      overflow-y: auto;
    }

    .battery-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
    }

    .battery-table thead th {
      position: sticky;
      top: 0;
      background-color: var(--vb-bg-primary);
      text-align: left;
      padding: 8px 10px;
      font-size: 11px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      color: var(--vb-text-secondary);
      border-bottom: 2px solid var(--vb-bg-divider);
      white-space: nowrap;
    }

    .battery-table thead th:last-child {
      text-align: right;
    }

    .battery-table tbody td {
      padding: 6px 10px;
      border-bottom: 1px solid var(--vb-bg-divider);
      color: var(--vb-text-primary);
      vertical-align: middle;
    }

    .battery-table tbody tr:hover {
      background-color: var(--vb-bg-card);
    }

    .battery-table .level-cell {
      text-align: right;
      font-weight: 600;
      color: var(--vb-color-critical);
      white-space: nowrap;
    }

    .battery-table .status-cell {
      text-align: right;
      white-space: nowrap;
    }

    .battery-table .time-cell {
      color: var(--vb-text-secondary);
      white-space: nowrap;
      font-size: 12px;
    }

    .battery-table .secondary-cell {
      color: var(--vb-text-secondary);
      font-size: 12px;
    }

    .entity-link {
      color: var(--vb-color-primary-action);
      text-decoration: none;
    }

    .entity-link:hover {
      text-decoration: underline;
    }

    /* Status badge for unavailable/unknown */
    .status-badge {
      display: inline-block;
      background: rgba(158, 158, 158, 0.12);
      border: 1px solid #9e9e9e;
      border-radius: 12px;
      padding: 2px 8px;
      font-size: 12px;
      font-weight: 400;
      color: var(--vb-text-secondary);
    }

    .empty-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 40px 20px;
      text-align: center;
      color: var(--vb-text-secondary);
    }

    .empty-state-icon {
      font-size: 48px;
      margin-bottom: 16px;
    }

    .empty-state-text {
      font-size: 14px;
      margin-bottom: 12px;
    }

    .button {
      background-color: var(--vb-color-primary-action);
      color: white;
      border: none;
      border-radius: 4px;
      padding: 8px 16px;
      font-size: 12px;
      cursor: pointer;
      min-height: 44px;
      min-width: 44px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
    }

    .button:hover {
      opacity: 0.9;
    }
  `;

  render() {
    return html`
      <div class="battery-panel">
        <div class="header">
          <h1>Battery Monitoring</h1>
          <div class="connection-badge">
            <span class="connection-dot ${this.connection_status}"></span>
            ${this.connection_status === CONNECTION_CONNECTED
              ? "Connected"
              : this.connection_status === CONNECTION_RECONNECTING
                ? "Reconnecting..."
                : "Offline"}
          </div>
        </div>

        <div
          class="tab-bar"
          role="tablist"
          aria-label="Battery monitoring tabs"
          @keydown=${this._onTabKeydown}
        >
          <button
            id="tab-low-battery"
            role="tab"
            aria-selected=${this._activeTab === TAB_LOW_BATTERY ? "true" : "false"}
            aria-controls="panel-low-battery"
            class="tab ${this._activeTab === TAB_LOW_BATTERY ? "active" : ""}"
            @click=${() => this._switchTab(TAB_LOW_BATTERY)}
          >
            Low Battery
          </button>
          <button
            id="tab-unavailable"
            role="tab"
            aria-selected=${this._activeTab === TAB_UNAVAILABLE ? "true" : "false"}
            aria-controls="panel-unavailable"
            class="tab ${this._activeTab === TAB_UNAVAILABLE ? "active" : ""}"
            @click=${() => this._switchTab(TAB_UNAVAILABLE)}
          >
            Unavailable Devices
          </button>
        </div>

        ${this._activeTab === TAB_LOW_BATTERY
          ? this._renderLowBatteryPanel()
          : this._renderUnavailablePanel()}
      </div>
    `;
  }

  _renderLowBatteryPanel() {
    return html`
      <div
        id="panel-low-battery"
        role="tabpanel"
        aria-labelledby="tab-low-battery"
        class="tab-panel"
      >
        ${this.error
          ? html`<div
              style="color: var(--vb-color-critical); padding: 8px; border-radius: 4px;"
            >
              ${this.error}
            </div>`
          : ""}
        ${this.battery_devices.length === 0 && !this.isLoading
          ? html`<div class="empty-state">
              <div class="empty-state-icon">🔋</div>
              <div class="empty-state-text">All batteries above 15%</div>
              <button class="button" @click=${this._load_devices}>
                Refresh
              </button>
            </div>`
          : html`<div class="table-container">
              <table class="battery-table">
                <thead>
                  <tr>
                    <th>Last Seen</th>
                    <th>Entity Name</th>
                    <th>Area</th>
                    <th>Manufacturer &amp; Model</th>
                    <th>% Remaining</th>
                  </tr>
                </thead>
                <tbody>
                  ${this.battery_devices.map(
                    (device) => html`
                      <tr>
                        <td class="time-cell">
                          ${this._formatRelativeTime(device.last_updated)}
                        </td>
                        <td>
                          <a
                            class="entity-link"
                            href="/config/entities?entity_id=${device.entity_id}"
                          >${device.device_name || device.entity_id}</a>
                        </td>
                        <td class="secondary-cell">
                          ${device.area_name || "\u2014"}
                        </td>
                        <td class="secondary-cell">
                          ${[device.manufacturer, device.model]
                            .filter(Boolean)
                            .join(" ") || "\u2014"}
                        </td>
                        <td class="level-cell">
                          ${Math.round(device.battery_level)}%
                        </td>
                      </tr>
                    `
                  )}
                </tbody>
              </table>
            </div>`}
      </div>
    `;
  }

  _renderUnavailablePanel() {
    if (this._unavailableLoading) {
      return html`
        <div
          id="panel-unavailable"
          role="tabpanel"
          aria-labelledby="tab-unavailable"
          class="tab-panel"
        >
          <div class="empty-state">
            <div class="empty-state-text">Loading unavailable devices...</div>
          </div>
        </div>
      `;
    }

    if (this._unavailableError) {
      return html`
        <div
          id="panel-unavailable"
          role="tabpanel"
          aria-labelledby="tab-unavailable"
          class="tab-panel"
        >
          <div
            style="color: var(--vb-color-critical); padding: 8px; border-radius: 4px;"
          >
            ${this._unavailableError}
          </div>
        </div>
      `;
    }

    const entities = this._unavailableEntities || [];

    if (entities.length === 0) {
      return html`
        <div
          id="panel-unavailable"
          role="tabpanel"
          aria-labelledby="tab-unavailable"
          class="tab-panel"
        >
          <div class="empty-state">
            <div class="empty-state-icon">✅</div>
            <div class="empty-state-text">
              No unavailable devices. All monitored devices are responding.
            </div>
          </div>
        </div>
      `;
    }

    return html`
      <div
        id="panel-unavailable"
        role="tabpanel"
        aria-labelledby="tab-unavailable"
        class="tab-panel"
      >
        <div class="table-container">
          <table class="battery-table">
            <thead>
              <tr>
                <th>Last Seen</th>
                <th>Entity Name</th>
                <th>Area</th>
                <th>Manufacturer &amp; Model</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              ${entities.map(
                (device) => html`
                  <tr>
                    <td class="time-cell">
                      ${this._formatRelativeTime(device.last_updated)}
                    </td>
                    <td>
                      <a
                        class="entity-link"
                        href="/config/entities?entity_id=${device.entity_id}"
                      >${device.device_name || device.entity_id}</a>
                    </td>
                    <td class="secondary-cell">
                      ${device.area_name || "\u2014"}
                    </td>
                    <td class="secondary-cell">
                      ${[device.manufacturer, device.model]
                        .filter(Boolean)
                        .join(" ") || "\u2014"}
                    </td>
                    <td class="status-cell">
                      <span class="status-badge">${device.state}</span>
                    </td>
                  </tr>
                `
              )}
            </tbody>
          </table>
        </div>
      </div>
    `;
  }

  _switchTab(tab) {
    if (this._activeTab === tab) return;
    this._activeTab = tab;
    sessionStorage.setItem(SESSION_STORAGE_KEY, tab);

    // Lazy-load unavailable entities on first visit to that tab
    if (tab === TAB_UNAVAILABLE && this._unavailableEntities === null) {
      this._load_unavailable();
    }
  }

  _onTabKeydown(event) {
    const tabs = [TAB_LOW_BATTERY, TAB_UNAVAILABLE];
    const currentIndex = tabs.indexOf(this._activeTab);

    if (event.key === "ArrowRight") {
      const next = tabs[(currentIndex + 1) % tabs.length];
      this._switchTab(next);
      this.shadowRoot.getElementById(`tab-${next}`)?.focus();
    } else if (event.key === "ArrowLeft") {
      const prev = tabs[(currentIndex - 1 + tabs.length) % tabs.length];
      this._switchTab(prev);
      this.shadowRoot.getElementById(`tab-${prev}`)?.focus();
    } else if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
    }
  }

  async _load_devices() {
    this.isLoading = true;
    this.error = null;

    try {
      const result = await this._call_ws({ type: QUERY_ENTITIES_COMMAND });
      this.battery_devices = result.entities || [];
      this.error = null;

      await this._subscribe_to_updates();
    } catch (err) {
      console.error("Failed to load battery devices:", err);
      this.error = err.message || "Failed to load battery devices";
      this.battery_devices = [];
      this.connection_status = CONNECTION_OFFLINE;
    } finally {
      this.isLoading = false;
    }
  }

  async _load_unavailable() {
    this._unavailableLoading = true;
    this._unavailableError = null;

    try {
      const result = await this._call_ws({ type: QUERY_UNAVAILABLE_COMMAND });
      this._unavailableEntities = result.entities || [];
      this._unavailableTotal = result.total || 0;
    } catch (err) {
      console.error("Failed to load unavailable devices:", err);
      this._unavailableError = err.message || "Failed to load unavailable devices";
      // Keep _unavailableEntities as null so retry is possible next visit
      this._unavailableEntities = null;
    } finally {
      this._unavailableLoading = false;
    }
  }

  async _subscribe_to_updates() {
    try {
      const result = await this._call_ws({ type: SUBSCRIBE_COMMAND });
      this.subscription_id = result.subscription_id;
      this.connection_status = CONNECTION_CONNECTED;
      this.reconnect_attempt = 0;
      this._setup_message_listeners();
    } catch (err) {
      console.error("Subscription failed:", err);
      this.connection_status = CONNECTION_OFFLINE;
      this._schedule_reconnect();
    }
  }

  _setup_message_listeners() {
    if (!this.hass?.connection) return;

    const orig = this.hass.connection._handleMessage;
    if (!orig || orig._patched) return;

    const self = this;
    this.hass.connection._handleMessage = function (msg) {
      if (msg.type === "vulcan-brownout/entity_changed") {
        self._on_entity_changed(msg.data);
      } else if (msg.type === "vulcan-brownout/status") {
        self._on_status_updated(msg.data);
      }
      orig.call(this, msg);
    };

    this.hass.connection._handleMessage._patched = true;
  }

  _on_entity_changed(data) {
    // Re-query low-battery list; real-time updates apply only to Low Battery tab.
    // Unavailable tab is a point-in-time snapshot — not refreshed on events.
    this._load_devices();
  }

  _on_status_updated(data) {
    if (data.status === "connected") {
      this.connection_status = CONNECTION_CONNECTED;
      this.reconnect_attempt = 0;
      this._clear_reconnect_timer();
    } else if (data.status === "disconnected") {
      this.connection_status = CONNECTION_OFFLINE;
      this._schedule_reconnect();
    }
  }

  _schedule_reconnect() {
    this._clear_reconnect_timer();
    if (this.reconnect_attempt >= MAX_RECONNECT_ATTEMPTS) {
      this.connection_status = CONNECTION_OFFLINE;
      return;
    }

    this.connection_status = CONNECTION_RECONNECTING;
    const backoff =
      RECONNECT_BACKOFF[
        Math.min(this.reconnect_attempt, RECONNECT_BACKOFF.length - 1)
      ];
    this.reconnect_attempt++;

    this.reconnect_timer = setTimeout(() => {
      this._load_devices();
    }, backoff);
  }

  _clear_reconnect_timer() {
    if (this.reconnect_timer) {
      clearTimeout(this.reconnect_timer);
      this.reconnect_timer = null;
    }
  }

  _detect_theme() {
    if (this.hass?.themes?.darkMode !== undefined) {
      return this.hass.themes.darkMode ? "dark" : "light";
    }
    if (window.matchMedia("(prefers-color-scheme: dark)").matches) {
      return "dark";
    }
    return "light";
  }

  _apply_theme(theme) {
    this.current_theme = theme || "light";
  }

  _setup_theme_listener() {
    if (!this.hass?.connection) return;

    this._themeListener = () => {
      const newTheme = this._detect_theme();
      if (newTheme !== this.current_theme) {
        this._apply_theme(newTheme);
      }
    };

    this.hass.connection.addEventListener(
      "hass_themes_updated",
      this._themeListener
    );
  }

  _formatRelativeTime(isoString) {
    if (!isoString) return "\u2014";
    const now = Date.now();
    const then = new Date(isoString).getTime();
    const diffSec = Math.floor((now - then) / 1000);
    if (diffSec < 60) return "just now";
    const diffMin = Math.floor(diffSec / 60);
    if (diffMin < 60) return `${diffMin} min ago`;
    const diffHr = Math.floor(diffMin / 60);
    if (diffHr < 24) return `${diffHr} hr${diffHr > 1 ? "s" : ""} ago`;
    const diffDay = Math.floor(diffHr / 24);
    return `${diffDay} day${diffDay > 1 ? "s" : ""} ago`;
  }

  async _call_ws(message) {
    if (!this.hass?.callWS) {
      throw new Error("Home Assistant WebSocket not available");
    }
    return this.hass.callWS(message);
  }
}

customElements.define("vulcan-brownout-panel", VulcanBrownoutPanel);
