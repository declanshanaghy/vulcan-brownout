/**
 * Vulcan Brownout Battery Monitor Panel
 *
 * A Lit Element web component that displays battery-powered devices
 * in a Home Assistant sidebar panel. Communicates with the backend
 * via WebSocket API.
 */

import { LitElement, html, css } from "https://unpkg.com/lit@3.1.0?module";
import { customElement, property, state } from "https://unpkg.com/lit@3.1.0/decorators.js?module";

const QUERY_DEVICES_COMMAND = "vulcan-brownout/query_devices";
const DEFAULT_PAGE_SIZE = 20;

@customElement("vulcan-brownout-panel")
export class VulcanBrownoutPanel extends LitElement {
  // HA-provided property
  @property({ attribute: false }) hass = null;

  // Component state
  @state() battery_devices = [];
  @state() isLoading = false;
  @state() error = null;
  @state() hasMore = false;
  @state() currentOffset = 0;
  @state() total = 0;
  @state() lastUpdateTime = null;

  connectedCallback() {
    super.connectedCallback();
    this._load_devices();
  }

  /**
   * Load battery devices from backend via WebSocket.
   */
  async _load_devices() {
    this.isLoading = true;
    this.error = null;

    try {
      const result = await this._call_websocket({
        type: QUERY_DEVICES_COMMAND,
        data: {
          limit: DEFAULT_PAGE_SIZE,
          offset: 0,
          sort_key: "battery_level",
          sort_order: "asc",
        },
      });

      if (!result || !result.data) {
        throw new Error("Invalid response from server");
      }

      this.battery_devices = result.data.devices || [];
      this.total = result.data.total || 0;
      this.hasMore = result.data.has_more || false;
      this.currentOffset = 0;
      this.lastUpdateTime = new Date();
      this.error = null;
    } catch (err) {
      console.error("Failed to load battery devices:", err);
      this.error = err.message || "Failed to load battery devices";
      this.battery_devices = [];
    } finally {
      this.isLoading = false;
    }
  }

  /**
   * Refresh battery device list.
   */
  async _on_refresh() {
    await this._load_devices();
  }

  /**
   * Call WebSocket command.
   */
  async _call_websocket(command) {
    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        reject(new Error("WebSocket command timeout"));
      }, 10000);

      try {
        this.hass
          .callWS(command)
          .then((result) => {
            clearTimeout(timeout);
            resolve(result);
          })
          .catch((err) => {
            clearTimeout(timeout);
            reject(err);
          });
      } catch (err) {
        clearTimeout(timeout);
        reject(err);
      }
    });
  }

  /**
   * Get status classification for a device.
   */
  _get_status(device) {
    if (!device.available) return "unavailable";
    if (device.battery_level <= 15) return "critical";
    return "healthy";
  }

  /**
   * Get icon name based on device status.
   */
  _get_icon(device) {
    const status = this._get_status(device);
    if (status === "critical") return "mdi:battery-alert";
    if (status === "unavailable") return "mdi:help-circle";
    return "mdi:battery";
  }

  /**
   * Format time difference (e.g., "2 minutes ago").
   */
  _format_time_ago(date) {
    if (!date) return "";

    const now = new Date();
    const diffMs = now - date;
    const diffSecs = Math.floor(diffMs / 1000);
    const diffMins = Math.floor(diffSecs / 60);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffSecs < 60) return "just now";
    if (diffMins < 60) return `${diffMins} minute${diffMins > 1 ? "s" : ""} ago`;
    if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? "s" : ""} ago`;
    return `${diffDays} day${diffDays > 1 ? "s" : ""} ago`;
  }

  render() {
    // Loading state
    if (this.isLoading && this.battery_devices.length === 0) {
      return html`
        <div class="panel-container">
          <div class="header">
            <h1>Vulcan Brownout</h1>
            <div class="header-buttons">
              <button class="icon-button" @click=${this._on_refresh}>
                <ha-icon icon="mdi:refresh"></ha-icon>
              </button>
            </div>
          </div>
          <div class="loading-state">
            <div class="skeleton skeleton-card"></div>
            <div class="skeleton skeleton-card"></div>
            <div class="skeleton skeleton-card"></div>
            <div class="loading-text">Loading battery devices...</div>
          </div>
        </div>
      `;
    }

    // Error state
    if (this.error) {
      return html`
        <div class="panel-container">
          <div class="header">
            <h1>Vulcan Brownout</h1>
            <div class="header-buttons">
              <button class="icon-button" @click=${this._on_refresh}>
                <ha-icon icon="mdi:refresh"></ha-icon>
              </button>
            </div>
          </div>
          <div class="error-state">
            <div class="error-icon">
              <ha-icon icon="mdi:alert-circle"></ha-icon>
            </div>
            <div class="error-title">Unable to load battery devices</div>
            <div class="error-message">
              The Home Assistant server is unreachable. Check your connection and try again.
            </div>
            <button class="cta-button" @click=${this._on_refresh}>
              Retry
            </button>
            ${this.lastUpdateTime
              ? html`
                  <div class="last-update">
                    Last successful update: ${this._format_time_ago(this.lastUpdateTime)}
                  </div>
                `
              : ""}
          </div>
        </div>
      `;
    }

    // Empty state
    if (this.battery_devices.length === 0) {
      return html`
        <div class="panel-container">
          <div class="header">
            <h1>Vulcan Brownout</h1>
            <div class="header-buttons">
              <button class="icon-button" @click=${this._on_refresh}>
                <ha-icon icon="mdi:refresh"></ha-icon>
              </button>
            </div>
          </div>
          <div class="empty-state">
            <div class="empty-icon">
              <ha-icon icon="mdi:battery-unknown"></ha-icon>
            </div>
            <div class="empty-title">No battery devices found</div>
            <div class="empty-message">
              Configure entities with device_class=battery in Home Assistant to appear here.
            </div>
            <a
              href="/config/devices"
              class="cta-button"
              target="_blank"
              rel="noopener"
            >
              Browse Home Assistant Devices
            </a>
          </div>
        </div>
      `;
    }

    // Normal list state
    return html`
      <div class="panel-container">
        <div class="header">
          <h1>Vulcan Brownout</h1>
          <div class="header-buttons">
            <button
              class="icon-button settings-button"
              title="Settings (Coming in Sprint 2)"
              disabled
            >
              <ha-icon icon="mdi:cog"></ha-icon>
            </button>
            <button
              class="icon-button refresh-button ${this.isLoading ? "loading" : ""}"
              @click=${this._on_refresh}
              title="Refresh"
            >
              <ha-icon icon="mdi:refresh"></ha-icon>
            </button>
          </div>
        </div>

        <div class="device-list-container">
          ${this._render_device_groups()}
        </div>

        ${this.lastUpdateTime
          ? html`
              <div class="footer">
                Last updated: ${this._format_time_ago(this.lastUpdateTime)}
              </div>
            `
          : ""}
      </div>
    `;
  }

  /**
   * Render devices grouped by status.
   */
  _render_device_groups() {
    const critical = this.battery_devices.filter((d) => this._get_status(d) === "critical");
    const unavailable = this.battery_devices.filter((d) => this._get_status(d) === "unavailable");
    const healthy = this.battery_devices.filter((d) => this._get_status(d) === "healthy");

    return html`
      ${critical.length > 0
        ? html`
            <div class="device-group">
              <div class="group-header">CRITICAL (${critical.length})</div>
              ${critical.map((device) => this._render_device_card(device))}
            </div>
          `
        : ""}
      ${unavailable.length > 0
        ? html`
            <div class="device-group">
              <div class="group-header">UNAVAILABLE (${unavailable.length})</div>
              ${unavailable.map((device) => this._render_device_card(device))}
            </div>
          `
        : ""}
      ${healthy.length > 0
        ? html`
            <div class="device-group">
              <div class="group-header">HEALTHY (${healthy.length})</div>
              ${healthy.map((device) => this._render_device_card(device))}
            </div>
          `
        : ""}
    `;
  }

  /**
   * Render a single device card.
   */
  _render_device_card(device) {
    const status = this._get_status(device);
    const icon = this._get_icon(device);

    return html`
      <div class="device-card ${status}">
        <div class="device-content">
          <ha-icon icon="${icon}" class="device-icon ${status}"></ha-icon>
          <div class="device-info">
            <div class="device-name">${device.device_name}</div>
            <div class="battery-level">${device.battery_level}%</div>
          </div>
        </div>
        <div class="progress-bar">
          <div
            class="progress-bar-fill ${status}"
            style="width: ${device.battery_level}%"
            aria-label="Battery level: ${device.battery_level}%"
          ></div>
        </div>
      </div>
    `;
  }

  static get styles() {
    return css`
      :host {
        display: block;
        background-color: var(--card-background-color);
        --primary-color: var(--primary-color, #1976d2);
        --error-color: var(--error-color, #f44336);
        --success-color: var(--success-color, #4caf50);
        --text-primary-color: var(--text-primary-color, #212121);
        --text-secondary-color: var(--text-secondary-color, #757575);
        --text-tertiary-color: var(--text-tertiary-color, #bdbdbd);
        --divider-color: var(--divider-color, #e0e0e0);
        --error-color-background: var(--error-color-background, #ffebee);
        --disabled-text-color: var(--disabled-text-color, #9e9e9e);
      }

      .panel-container {
        display: flex;
        flex-direction: column;
        height: 100vh;
        max-height: 100vh;
      }

      .header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 12px 16px;
        border-bottom: 1px solid var(--divider-color);
        background-color: var(--card-background-color);
        flex-shrink: 0;
      }

      .header h1 {
        margin: 0;
        font-size: 20px;
        font-weight: 500;
        color: var(--text-primary-color);
      }

      .header-buttons {
        display: flex;
        gap: 8px;
      }

      .icon-button {
        background: none;
        border: none;
        cursor: pointer;
        padding: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        color: var(--text-secondary-color);
        transition: color 0.2s;
        border-radius: 4px;
      }

      .icon-button:hover:not(:disabled) {
        color: var(--primary-color);
      }

      .icon-button:disabled {
        cursor: not-allowed;
        opacity: 0.5;
      }

      .refresh-button.loading ha-icon {
        animation: spin 1s linear infinite;
      }

      @keyframes spin {
        from {
          transform: rotate(0deg);
        }
        to {
          transform: rotate(360deg);
        }
      }

      .device-list-container {
        flex: 1;
        overflow-y: auto;
        padding: 12px;
      }

      .device-group {
        margin-bottom: 20px;
      }

      .group-header {
        font-size: 12px;
        font-weight: 600;
        color: var(--text-secondary-color);
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 8px;
        padding: 0 12px;
      }

      .device-card {
        background-color: var(--card-background-color);
        border-radius: 4px;
        padding: 12px;
        margin-bottom: 12px;
        border: 1px solid var(--divider-color);
        transition: background-color 0.2s;
      }

      .device-card:hover {
        background-color: var(--divider-color);
      }

      .device-card.critical {
        background-color: var(--error-color-background);
        border-color: var(--error-color);
      }

      .device-card.unavailable {
        background-color: rgba(0, 0, 0, 0.02);
        border-color: var(--divider-color);
        opacity: 0.7;
      }

      .device-card.healthy {
        background-color: var(--card-background-color);
      }

      .device-content {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 8px;
      }

      .device-icon {
        font-size: 24px;
        flex-shrink: 0;
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

      .device-info {
        flex: 1;
        min-width: 0;
      }

      .device-name {
        font-size: 14px;
        font-weight: 500;
        color: var(--text-primary-color);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }

      .battery-level {
        font-size: 12px;
        color: var(--text-secondary-color);
      }

      .progress-bar {
        height: 4px;
        background-color: var(--divider-color);
        border-radius: 2px;
        overflow: hidden;
      }

      .progress-bar-fill {
        height: 100%;
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

      /* Loading state */
      .loading-state {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 16px;
        padding: 24px;
        flex: 1;
      }

      .skeleton {
        background: linear-gradient(90deg, #f0f0f0 0%, #e0e0e0 50%, #f0f0f0 100%);
        background-size: 200% 100%;
        animation: shimmer 1.5s infinite;
      }

      @keyframes shimmer {
        0% {
          background-position: 200% 0;
        }
        100% {
          background-position: -200% 0;
        }
      }

      .skeleton-card {
        width: 100%;
        height: 72px;
        border-radius: 4px;
      }

      .loading-text {
        font-size: 14px;
        color: var(--text-secondary-color);
      }

      /* Empty state */
      .empty-state {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 12px;
        padding: 48px 24px;
        text-align: center;
        flex: 1;
      }

      .empty-icon {
        font-size: 64px;
        color: var(--text-tertiary-color);
      }

      .empty-title {
        font-size: 20px;
        font-weight: 500;
        color: var(--text-primary-color);
      }

      .empty-message {
        font-size: 13px;
        color: var(--text-secondary-color);
        max-width: 300px;
      }

      /* Error state */
      .error-state {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 12px;
        padding: 48px 24px;
        text-align: center;
        flex: 1;
      }

      .error-icon {
        font-size: 64px;
        color: var(--error-color);
      }

      .error-title {
        font-size: 20px;
        font-weight: 500;
        color: var(--text-primary-color);
      }

      .error-message {
        font-size: 13px;
        color: var(--text-secondary-color);
        max-width: 300px;
      }

      .cta-button {
        background-color: var(--primary-color);
        color: white;
        padding: 12px 24px;
        border: none;
        border-radius: 4px;
        cursor: pointer;
        font-size: 14px;
        font-weight: 500;
        text-decoration: none;
        display: inline-block;
        transition: opacity 0.2s;
        margin-top: 12px;
      }

      .cta-button:hover {
        opacity: 0.8;
      }

      .last-update {
        font-size: 12px;
        color: var(--text-tertiary-color);
        margin-top: 12px;
      }

      .footer {
        font-size: 11px;
        color: var(--text-tertiary-color);
        text-align: center;
        padding: 8px;
        border-top: 1px solid var(--divider-color);
        flex-shrink: 0;
      }

      /* Responsive design */
      @media (max-width: 600px) {
        .header {
          padding: 8px 12px;
        }

        .header h1 {
          font-size: 16px;
        }

        .device-list-container {
          padding: 8px;
        }

        .device-card {
          padding: 10px;
          margin-bottom: 8px;
        }

        .device-icon {
          font-size: 20px;
        }

        .device-name {
          font-size: 13px;
        }

        .battery-level {
          font-size: 11px;
        }

        .group-header {
          padding: 0 8px;
        }
      }

      /* Tablet layout */
      @media (min-width: 600px) and (max-width: 1024px) {
        .device-list-container {
          padding: 12px;
        }

        .device-card {
          padding: 12px;
        }
      }
    `;
  }
}
