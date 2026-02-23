/**
 * Vulcan Brownout Battery Monitor Panel v6.0.0
 *
 * Simple panel: shows battery entities below 15% threshold.
 * Real-time updates via WebSocket subscription.
 * Theme follows HA user preference (Auto/Light/Dark) via CSS custom properties.
 */

import { LitElement, html, css } from "https://unpkg.com/lit@3.1.0?module";

const QUERY_ENTITIES_COMMAND = "vulcan-brownout/query_entities";
const SUBSCRIBE_COMMAND = "vulcan-brownout/subscribe";

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

    .battery-list {
      flex: 1;
      overflow-y: auto;
      padding-right: 8px;
    }

    .battery-card {
      background-color: var(--vb-bg-card);
      border-radius: 8px;
      padding: 12px;
      margin-bottom: 8px;
      box-shadow: var(--vb-shadow);
      display: flex;
      justify-content: space-between;
      align-items: center;
      transition: background-color 300ms ease-out, box-shadow 300ms ease-out;
    }

    .device-info {
      flex: 1;
    }

    .device-name {
      font-weight: 600;
      margin-bottom: 4px;
      color: var(--vb-text-primary);
    }

    .device-status {
      font-size: 12px;
      color: var(--vb-text-secondary);
    }

    .battery-level {
      font-size: 14px;
      font-weight: 600;
      min-width: 50px;
      text-align: right;
      color: var(--vb-color-critical);
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

        ${this.error
          ? html`<div
              style="color: var(--vb-color-critical); padding: 8px; border-radius: 4px;"
            >
              ${this.error}
            </div>`
          : ""}
        ${this.battery_devices.length === 0 && !this.isLoading
          ? html`<div class="empty-state">
              <div class="empty-state-icon">✅</div>
              <div class="empty-state-text">All batteries above 15%</div>
              <button class="button" @click=${this._load_devices}>
                Refresh
              </button>
            </div>`
          : html`<div class="battery-list">
              ${this.battery_devices.map(
                (device) => html`
                  <div class="battery-card">
                    <div class="device-info">
                      <div class="device-name">
                        ${device.device_name || device.entity_id}
                      </div>
                      <div class="device-status">${device.status}</div>
                    </div>
                    <div class="battery-level">
                      ${Math.round(device.battery_level)}%
                    </div>
                  </div>
                `
              )}
            </div>`}
      </div>
    `;
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
    // Re-query to get the updated list (entities may appear/disappear
    // as they cross the 15% threshold)
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

  async _call_ws(message) {
    if (!this.hass?.callWS) {
      throw new Error("Home Assistant WebSocket not available");
    }
    return this.hass.callWS(message);
  }
}

customElements.define("vulcan-brownout-panel", VulcanBrownoutPanel);
