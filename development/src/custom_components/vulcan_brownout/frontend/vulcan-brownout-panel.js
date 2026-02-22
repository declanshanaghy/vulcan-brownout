/**
 * Vulcan Brownout Battery Monitor Panel - Sprint 3
 *
 * A Lit Element web component that displays battery-powered devices
 * with real-time updates, infinite scroll pagination, dark mode support,
 * and configurable notifications.
 *
 * Sprint 3 Features:
 * - Cursor-based pagination with infinite scroll
 * - Skeleton loaders and "Back to Top" button
 * - Dark mode / theme detection with MutationObserver
 * - Notification preferences modal
 * - Binary sensor filtering
 */

import { LitElement, html, css } from "https://unpkg.com/lit@3.1.0?module";
import { customElement, property, state } from "https://unpkg.com/lit@3.1.0/decorators.js?module";

const QUERY_DEVICES_COMMAND = "vulcan-brownout/query_devices";
const SUBSCRIBE_COMMAND = "vulcan-brownout/subscribe";
const SET_THRESHOLD_COMMAND = "vulcan-brownout/set_threshold";
const GET_NOTIFICATION_PREFERENCES_COMMAND = "vulcan-brownout/get_notification_preferences";
const SET_NOTIFICATION_PREFERENCES_COMMAND = "vulcan-brownout/set_notification_preferences";
const EVENT_DEVICE_CHANGED = "vulcan-brownout/device_changed";
const EVENT_THRESHOLD_UPDATED = "vulcan-brownout/threshold_updated";
const EVENT_STATUS = "vulcan-brownout/status";
const EVENT_NOTIFICATION_SENT = "vulcan-brownout/notification_sent";

const DEFAULT_PAGE_SIZE = 50;
const SKELETON_LOADER_COUNT = 5;
const SCROLL_TO_TOP_THRESHOLD = 30;
const SCROLL_NEAR_BOTTOM_PX = 100;
const RECONNECT_BACKOFF = [1000, 2000, 4000, 8000, 16000, 30000];
const MAX_RECONNECT_ATTEMPTS = 10;

const STATUS_CRITICAL = "critical";
const STATUS_WARNING = "warning";
const STATUS_HEALTHY = "healthy";
const STATUS_UNAVAILABLE = "unavailable";

const CONNECTION_CONNECTED = "connected";
const CONNECTION_RECONNECTING = "reconnecting";
const CONNECTION_OFFLINE = "offline";

@customElement("vulcan-brownout-panel")
export class VulcanBrownoutPanel extends LitElement {
  // HA-provided property
  @property({ attribute: false }) hass = null;

  // Data state
  @state() battery_devices = [];
  @state() global_threshold = 15;
  @state() device_rules = {};
  @state() device_statuses = { critical: 0, warning: 0, healthy: 0, unavailable: 0 };

  // Pagination state (Sprint 3: cursor-based)
  @state() current_cursor = null;
  @state() has_more = false;
  @state() is_fetching = false;
  @state() show_skeleton_loaders = false;

  // UI state
  @state() isLoading = false;
  @state() error = null;
  @state() sort_method = "priority";
  @state() filter_state = {
    critical: true,
    warning: true,
    healthy: true,
    unavailable: false,
  };

  // Connection state
  @state() connection_status = CONNECTION_OFFLINE;
  @state() last_update_time = null;
  @state() subscription_id = null;

  // Modal state
  @state() show_settings_panel = false;
  @state() settings_global_threshold = 15;
  @state() settings_device_rules = {};
  @state() show_add_rule_modal = false;
  @state() selected_device_for_rule = null;
  @state() new_rule_threshold = 15;

  // Sprint 3: Notification preferences modal
  @state() show_notification_modal = false;
  @state() notification_prefs = {
    enabled: true,
    frequency_cap_hours: 6,
    severity_filter: "critical_only",
    per_device: {},
  };
  @state() notification_history = [];
  @state() notification_search = "";

  // Mobile state
  @state() show_sort_modal = false;
  @state() show_filter_modal = false;
  @state() is_mobile = window.innerWidth < 768;

  // Sprint 3: Back to top button and dark mode
  @state() show_back_to_top = false;
  @state() current_theme = "light";

  // Connection retry state
  reconnect_attempt = 0;
  reconnect_timer = null;

  // Sprint 3: Infinite scroll state
  scroll_observer = null;
  scroll_container = null;
  scroll_debounce_timer = null;

  // Sprint 3: Theme observer
  theme_observer = null;

  connectedCallback() {
    super.connectedCallback();
    this._load_ui_state_from_storage();
    this._detect_theme();
    this._setup_theme_observer();
    this._load_devices();
    window.addEventListener("resize", () => {
      this.is_mobile = window.innerWidth < 768;
    });
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    this._clear_reconnect_timer();
    if (this.scroll_observer) {
      this.scroll_observer.disconnect();
    }
    if (this.theme_observer) {
      this.theme_observer.disconnect();
    }
    window.removeEventListener("resize", this._on_window_resize.bind(this));
  }

  static styles = css`
    :host {
      --vb-bg-primary: #ffffff;
      --vb-bg-card: #f5f5f5;
      --vb-bg-divider: #e0e0e0;
      --vb-text-primary: #212121;
      --vb-text-secondary: #757575;
      --vb-text-disabled: #bdbdbd;
      --vb-color-critical: #f44336;
      --vb-color-warning: #ff9800;
      --vb-color-healthy: #4caf50;
      --vb-color-unavailable: #9e9e9e;
      --vb-color-primary-action: #03a9f4;
      --vb-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
      --vb-skeleton-bg: #e0e0e0;
      --vb-skeleton-shimmer: #f5f5f5;
    }

    [data-theme="dark"],
    [data-theme="dark-theme"] {
      --vb-bg-primary: #1c1c1c;
      --vb-bg-card: #2c2c2c;
      --vb-bg-divider: #444444;
      --vb-text-primary: #ffffff;
      --vb-text-secondary: #b0b0b0;
      --vb-text-disabled: #666666;
      --vb-color-critical: #ff5252;
      --vb-color-warning: #ffb74d;
      --vb-color-healthy: #66bb6a;
      --vb-color-unavailable: #bdbdbd;
      --vb-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
      --vb-skeleton-bg: #444444;
      --vb-skeleton-shimmer: #555555;
    }

    .battery-panel {
      display: flex;
      flex-direction: column;
      height: 100%;
      background-color: var(--vb-bg-primary);
      color: var(--vb-text-primary);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      padding: 16px;
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

    .header-controls {
      display: flex;
      gap: 8px;
      align-items: center;
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

    .battery-unavailable {
      color: var(--vb-color-unavailable);
      opacity: 0.6;
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
      transition: all 0.2s;
    }

    .button:hover {
      opacity: 0.9;
    }

    .skeleton-loader {
      background: linear-gradient(
        90deg,
        var(--vb-skeleton-bg) 25%,
        var(--vb-skeleton-shimmer) 50%,
        var(--vb-skeleton-bg) 75%
      );
      background-size: 1000px 100%;
      animation: shimmer 2s infinite;
      border-radius: 4px;
      height: 16px;
      margin-bottom: 8px;
      margin-top: 8px;
    }

    @keyframes shimmer {
      0% {
        background-position: -1000px 0;
      }
      100% {
        background-position: 1000px 0;
      }
    }

    .back-to-top {
      position: fixed;
      bottom: 16px;
      right: 16px;
      background-color: var(--vb-color-primary-action);
      color: white;
      border: none;
      border-radius: 50%;
      width: 48px;
      height: 48px;
      font-size: 20px;
      cursor: pointer;
      opacity: 0;
      transition: opacity 0.3s;
      z-index: 1000;
    }

    .back-to-top.visible {
      opacity: 1;
    }

    .modal-overlay {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background-color: rgba(0, 0, 0, 0.5);
      display: flex;
      align-items: flex-end;
      z-index: 999;
    }

    .modal {
      background-color: var(--vb-bg-primary);
      width: 100%;
      max-width: 600px;
      max-height: 80vh;
      overflow-y: auto;
      border-radius: 8px 8px 0 0;
      padding: 16px;
      animation: slideUp 0.3s ease-out;
    }

    @keyframes slideUp {
      from {
        transform: translateY(100%);
      }
      to {
        transform: translateY(0);
      }
    }

    .modal-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 16px;
      padding-bottom: 12px;
      border-bottom: 1px solid var(--vb-bg-divider);
    }

    .modal-header h2 {
      margin: 0;
      font-size: 18px;
      font-weight: 600;
    }

    .modal-close {
      background: none;
      border: none;
      font-size: 20px;
      cursor: pointer;
      color: var(--vb-text-secondary);
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
  `;

  render() {
    return html`
      <div class="battery-panel">
        <div class="header">
          <h1>🔋 Battery Monitoring</h1>
          <div class="header-controls">
            <div class="connection-badge">
              <span class="connection-dot ${this.connection_status}"></span>
              ${this.connection_status === CONNECTION_CONNECTED ? "Connected" :
                this.connection_status === CONNECTION_RECONNECTING ? "Reconnecting..." : "Offline"}
            </div>
            <button class="button" @click=${this._open_settings_modal}>⚙️ Settings</button>
            <button class="button" @click=${this._open_notification_modal}>🔔 Notifications</button>
          </div>
        </div>

        ${this.error
          ? html`<div style="color: var(--vb-color-critical); padding: 8px; border-radius: 4px;">
              ⚠️ ${this.error}
            </div>`
          : ""}

        ${this.battery_devices.length === 0 && !this.isLoading
          ? html`<div class="empty-state">
              <div class="empty-state-icon">🔋</div>
              <div class="empty-state-text">No battery devices found</div>
              <small style="color: var(--vb-text-disabled);">Check your Home Assistant configuration</small>
              <button class="button" @click=${this._load_devices} style="margin-top: 12px;">
                🔄 Refresh
              </button>
            </div>`
          : html`<div class="battery-list" id="battery-list">
              ${this.battery_devices.map(
                (device) => html`
                  <div class="battery-card">
                    <div class="device-info">
                      <div class="device-name">${device.device_name || device.entity_id}</div>
                      <div class="device-status">${device.status}</div>
                    </div>
                    <div
                      class="battery-level battery-${device.status}"
                    >
                      ${device.available ? `${Math.round(device.battery_level)}%` : "N/A"}
                    </div>
                  </div>
                `
              )}
              ${this.show_skeleton_loaders
                ? html`${Array.from({ length: SKELETON_LOADER_COUNT }).map(
                    () => html`<div class="skeleton-loader" style="height: 60px; margin-top: 8px;"></div>`
                  )}`
                : ""}
              ${this.has_more
                ? html`<div style="text-align: center; padding: 12px; color: var(--vb-text-secondary); font-size: 12px;">
                    Scroll for more...
                  </div>`
                : ""}
            </div>`}

        <button
          class="back-to-top ${this.show_back_to_top ? "visible" : ""}"
          @click=${this._scroll_to_top}
          aria-label="Back to top"
          title="Back to top"
        >
          ↑
        </button>

        ${this.show_settings_panel ? this._render_settings_modal() : ""}
        ${this.show_notification_modal ? this._render_notification_modal() : ""}
      </div>
    `;
  }

  _render_settings_modal() {
    return html`
      <div class="modal-overlay" @click=${this._close_settings_modal}>
        <div class="modal" @click=${(e) => e.stopPropagation()}>
          <div class="modal-header">
            <h2>⚙️ Threshold Settings</h2>
            <button class="modal-close" @click=${this._close_settings_modal}>✕</button>
          </div>
          <div style="margin-bottom: 12px;">
            <label>Global Threshold (%)</label>
            <input
              type="number"
              .value=${this.settings_global_threshold}
              @change=${(e) => (this.settings_global_threshold = parseInt(e.target.value))}
              min="5"
              max="100"
              style="width: 100%; padding: 8px; border: 1px solid var(--vb-bg-divider); border-radius: 4px;"
            />
          </div>
          <div style="display: flex; gap: 8px; margin-top: 16px;">
            <button class="button" @click=${this._save_settings} style="flex: 1;">
              💾 Save
            </button>
            <button class="button" @click=${this._close_settings_modal} style="flex: 1; background-color: var(--vb-text-disabled);">
              Cancel
            </button>
          </div>
        </div>
      </div>
    `;
  }

  _render_notification_modal() {
    const filtered_history = this.notification_history.filter((n) =>
      n.device_name.toLowerCase().includes(this.notification_search.toLowerCase())
    );

    return html`
      <div class="modal-overlay" @click=${this._close_notification_modal}>
        <div class="modal" @click=${(e) => e.stopPropagation()}>
          <div class="modal-header">
            <h2>🔔 Notification Preferences</h2>
            <button class="modal-close" @click=${this._close_notification_modal}>✕</button>
          </div>

          <div style="margin-bottom: 16px;">
            <label style="display: flex; align-items: center; gap: 8px;">
              <input
                type="checkbox"
                ?checked=${this.notification_prefs.enabled}
                @change=${(e) => (this.notification_prefs.enabled = e.target.checked)}
              />
              <span>Enable Notifications</span>
            </label>
          </div>

          <div style="margin-bottom: 16px;">
            <label>Frequency Cap</label>
            <select
              .value=${this.notification_prefs.frequency_cap_hours}
              @change=${(e) => (this.notification_prefs.frequency_cap_hours = parseInt(e.target.value))}
              style="width: 100%; padding: 8px; border: 1px solid var(--vb-bg-divider); border-radius: 4px;"
            >
              <option value="1">1 hour</option>
              <option value="6">6 hours</option>
              <option value="24">24 hours</option>
            </select>
          </div>

          <div style="margin-bottom: 16px;">
            <label>Severity Filter</label>
            <div style="display: flex; gap: 8px;">
              <label style="display: flex; align-items: center; gap: 4px;">
                <input
                  type="radio"
                  name="severity"
                  value="critical_only"
                  ?checked=${this.notification_prefs.severity_filter === "critical_only"}
                  @change=${(e) => (this.notification_prefs.severity_filter = e.target.value)}
                />
                <span>Critical Only</span>
              </label>
              <label style="display: flex; align-items: center; gap: 4px;">
                <input
                  type="radio"
                  name="severity"
                  value="critical_and_warning"
                  ?checked=${this.notification_prefs.severity_filter === "critical_and_warning"}
                  @change=${(e) => (this.notification_prefs.severity_filter = e.target.value)}
                />
                <span>Critical & Warning</span>
              </label>
            </div>
          </div>

          <div style="margin-bottom: 16px; border-top: 1px solid var(--vb-bg-divider); padding-top: 12px;">
            <h3 style="margin-top: 0; font-size: 14px;">Notification History</h3>
            <input
              type="text"
              placeholder="Search..."
              .value=${this.notification_search}
              @input=${(e) => (this.notification_search = e.target.value)}
              style="width: 100%; padding: 8px; border: 1px solid var(--vb-bg-divider); border-radius: 4px; margin-bottom: 8px;"
            />
            ${filtered_history.length === 0
              ? html`<small style="color: var(--vb-text-disabled);">No notifications</small>`
              : html`${filtered_history.slice(0, 5).map(
                  (n) =>
                    html`<div style="font-size: 12px; padding: 8px 0; border-bottom: 1px solid var(--vb-bg-divider);">
                      <div style="font-weight: 600;">${n.device_name}</div>
                      <div style="color: var(--vb-text-secondary); font-size: 11px;">
                        ${n.battery_level}% - ${new Date(n.timestamp).toLocaleString()}
                      </div>
                    </div>`
                )}`}
          </div>

          <div style="display: flex; gap: 8px; margin-top: 16px;">
            <button class="button" @click=${this._save_notification_prefs} style="flex: 1;">
              💾 Save
            </button>
            <button class="button" @click=${this._close_notification_modal} style="flex: 1; background-color: var(--vb-text-disabled);">
              Cancel
            </button>
          </div>
        </div>
      </div>
    `;
  }

  async _load_devices() {
    this.isLoading = true;
    this.error = null;

    try {
      const result = await this._call_websocket({
        type: QUERY_DEVICES_COMMAND,
        data: {
          limit: DEFAULT_PAGE_SIZE,
          cursor: null,
          sort_key: "priority",
          sort_order: "asc",
        },
      });

      if (!result || !result.data) {
        throw new Error("Invalid response from server");
      }

      this.battery_devices = result.data.devices || [];
      this.device_statuses = result.data.device_statuses || {};
      this.current_cursor = result.data.next_cursor || null;
      this.has_more = result.data.has_more || false;
      this.last_update_time = new Date();
      this.error = null;

      // Setup infinite scroll after first load
      await this.updateComplete;
      this._setup_infinite_scroll();

      // Subscribe to real-time updates
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

  _setup_infinite_scroll() {
    const scroll_container = this.shadowRoot?.querySelector(".battery-list");
    if (!scroll_container) return;

    if (this.scroll_observer) {
      this.scroll_observer.disconnect();
    }

    // Create observer for scroll near bottom
    this.scroll_observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && this.has_more && !this.is_fetching) {
          this._load_next_page();
        }
      },
      { threshold: 0.1 }
    );

    // Observe the bottom sentinel
    const sentinel = document.createElement("div");
    sentinel.style.height = "1px";
    scroll_container.appendChild(sentinel);
    this.scroll_observer.observe(sentinel);

    // Track scroll for "Back to Top" button
    scroll_container.addEventListener("scroll", (e) => {
      clearTimeout(this.scroll_debounce_timer);
      this.scroll_debounce_timer = setTimeout(() => {
        const scrolled_items = Math.floor(e.target.scrollTop / 68); // Approximate card height
        this.show_back_to_top = scrolled_items > SCROLL_TO_TOP_THRESHOLD;
        this._save_scroll_position(e.target.scrollTop);
      }, 100);
    });

    // Restore scroll position
    const saved_scroll = sessionStorage.getItem("vulcan_brownout_scroll");
    if (saved_scroll) {
      scroll_container.scrollTop = parseInt(saved_scroll);
    }
  }

  async _load_next_page() {
    if (!this.current_cursor || this.is_fetching) return;

    this.is_fetching = true;
    this.show_skeleton_loaders = true;

    try {
      const result = await this._call_websocket({
        type: QUERY_DEVICES_COMMAND,
        data: {
          limit: DEFAULT_PAGE_SIZE,
          cursor: this.current_cursor,
          sort_key: "priority",
          sort_order: "asc",
        },
      });

      if (result && result.data) {
        this.battery_devices = [...this.battery_devices, ...(result.data.devices || [])];
        this.current_cursor = result.data.next_cursor || null;
        this.has_more = result.data.has_more || false;
      }
    } catch (err) {
      console.error("Failed to load next page:", err);
    } finally {
      this.is_fetching = false;
      this.show_skeleton_loaders = false;
    }
  }

  _scroll_to_top() {
    const scroll_container = this.shadowRoot?.querySelector(".battery-list");
    if (scroll_container) {
      scroll_container.scrollTo({ top: 0, behavior: "smooth" });
    }
  }

  _save_scroll_position(position) {
    sessionStorage.setItem("vulcan_brownout_scroll", position.toString());
  }

  async _subscribe_to_updates() {
    try {
      const result = await this._call_websocket({
        type: SUBSCRIBE_COMMAND,
        data: {},
      });

      if (!result || !result.data) {
        throw new Error("Invalid subscription response");
      }

      this.subscription_id = result.data.subscription_id;
      this.connection_status = CONNECTION_CONNECTED;
      this.reconnect_attempt = 0;

      // Set up message listener
      if (this.hass && this.hass.connection) {
        this._setup_message_listeners();
      }
    } catch (err) {
      console.error("Subscription failed:", err);
      this.connection_status = CONNECTION_OFFLINE;
      this._schedule_reconnect();
    }
  }

  _setup_message_listeners() {
    if (!this.hass || !this.hass.connection) return;

    const original_handleMessage = this.hass.connection._handleMessage;
    if (!original_handleMessage || original_handleMessage._patched) return;

    this.hass.connection._handleMessage = function (msg) {
      if (msg.type === EVENT_DEVICE_CHANGED) {
        this._on_device_changed(msg.data);
      } else if (msg.type === EVENT_THRESHOLD_UPDATED) {
        this._on_threshold_updated(msg.data);
      } else if (msg.type === EVENT_STATUS) {
        this._on_status_updated(msg.data);
      } else if (msg.type === EVENT_NOTIFICATION_SENT) {
        this._on_notification_sent(msg.data);
      }
      original_handleMessage.call(this, msg);
    }.bind(this);

    original_handleMessage._patched = true;
  }

  _on_device_changed(data) {
    const device = this.battery_devices.find((d) => d.entity_id === data.entity_id);
    if (device) {
      device.battery_level = data.battery_level;
      device.available = data.available;
      device.status = data.status;
      device.last_changed = data.last_changed;
      device.last_updated = data.last_updated;
      this.last_update_time = new Date();
      this.requestUpdate();
    }
  }

  _on_threshold_updated(data) {
    this.global_threshold = data.global_threshold;
    this.device_rules = data.device_rules;
    this.settings_global_threshold = data.global_threshold;
    this.settings_device_rules = { ...data.device_rules };
    this._save_ui_state_to_storage();
    this.requestUpdate();
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

  _on_notification_sent(data) {
    this.notification_history.unshift(data);
    if (this.notification_history.length > 20) {
      this.notification_history.pop();
    }
    this.requestUpdate();
  }

  _schedule_reconnect() {
    this._clear_reconnect_timer();

    if (this.reconnect_attempt >= MAX_RECONNECT_ATTEMPTS) {
      this.connection_status = CONNECTION_OFFLINE;
      return;
    }

    this.connection_status = CONNECTION_RECONNECTING;
    const backoff = RECONNECT_BACKOFF[Math.min(this.reconnect_attempt, RECONNECT_BACKOFF.length - 1)];
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
    const ha_theme = document.documentElement.getAttribute("data-theme");
    if (ha_theme === "dark" || ha_theme === "dark-theme") {
      this.current_theme = "dark";
    } else if (window.matchMedia("(prefers-color-scheme: dark)").matches) {
      this.current_theme = "dark";
    } else {
      this.current_theme = "light";
    }
  }

  _setup_theme_observer() {
    if (this.theme_observer) {
      this.theme_observer.disconnect();
    }

    this.theme_observer = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        if (mutation.attributeName === "data-theme") {
          this._detect_theme();
          this.requestUpdate();
        }
      });
    });

    this.theme_observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["data-theme"],
    });
  }

  _load_ui_state_from_storage() {
    try {
      const saved = localStorage.getItem("vulcan_brownout_ui_state");
      if (saved) {
        const state = JSON.parse(saved);
        this.sort_method = state.sort_method || "priority";
        this.filter_state = { ...this.filter_state, ...state.filter_state };
      }
    } catch (e) {
      console.warn("Failed to load UI state from localStorage", e);
    }
  }

  _save_ui_state_to_storage() {
    try {
      localStorage.setItem(
        "vulcan_brownout_ui_state",
        JSON.stringify({
          sort_method: this.sort_method,
          filter_state: this.filter_state,
        })
      );
    } catch (e) {
      console.warn("Failed to save UI state to localStorage", e);
    }
  }

  _open_settings_modal() {
    this.show_settings_panel = true;
  }

  _close_settings_modal() {
    this.show_settings_panel = false;
  }

  async _save_settings() {
    try {
      await this._call_websocket({
        type: SET_THRESHOLD_COMMAND,
        data: {
          global_threshold: this.settings_global_threshold,
          device_rules: this.settings_device_rules,
        },
      });
      this._close_settings_modal();
    } catch (err) {
      console.error("Failed to save settings:", err);
      this.error = err.message || "Failed to save settings";
    }
  }

  _open_notification_modal() {
    this._load_notification_preferences();
    this.show_notification_modal = true;
  }

  _close_notification_modal() {
    this.show_notification_modal = false;
  }

  async _load_notification_preferences() {
    try {
      const result = await this._call_websocket({
        type: GET_NOTIFICATION_PREFERENCES_COMMAND,
        data: {},
      });
      if (result && result.data) {
        this.notification_prefs = {
          enabled: result.data.enabled,
          frequency_cap_hours: result.data.frequency_cap_hours,
          severity_filter: result.data.severity_filter,
          per_device: result.data.per_device || {},
        };
        this.notification_history = result.data.notification_history || [];
      }
    } catch (err) {
      console.error("Failed to load notification preferences:", err);
    }
  }

  async _save_notification_prefs() {
    try {
      await this._call_websocket({
        type: SET_NOTIFICATION_PREFERENCES_COMMAND,
        data: this.notification_prefs,
      });
      this._close_notification_modal();
    } catch (err) {
      console.error("Failed to save notification preferences:", err);
      this.error = err.message || "Failed to save preferences";
    }
  }

  async _call_websocket(message) {
    return new Promise((resolve, reject) => {
      if (!this.hass || !this.hass.callWS) {
        reject(new Error("Home Assistant WebSocket not available"));
        return;
      }

      this.hass
        .callWS(message)
        .then((response) => {
          resolve(response);
        })
        .catch((error) => {
          reject(error);
        });
    });
  }

  _on_window_resize() {
    this.is_mobile = window.innerWidth < 768;
  }
}

customElements.define("vulcan-brownout-panel", VulcanBrownoutPanel);
