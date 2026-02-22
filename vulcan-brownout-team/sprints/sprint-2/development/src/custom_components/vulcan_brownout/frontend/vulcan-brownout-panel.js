/**
 * Vulcan Brownout Battery Monitor Panel - Sprint 2
 *
 * A Lit Element web component that displays battery-powered devices
 * in a Home Assistant sidebar panel with real-time updates, sorting,
 * filtering, and threshold configuration.
 */

import { LitElement, html, css } from "https://unpkg.com/lit@3.1.0?module";
import { customElement, property, state } from "https://unpkg.com/lit@3.1.0/decorators.js?module";

const QUERY_DEVICES_COMMAND = "vulcan-brownout/query_devices";
const SUBSCRIBE_COMMAND = "vulcan-brownout/subscribe";
const SET_THRESHOLD_COMMAND = "vulcan-brownout/set_threshold";
const EVENT_DEVICE_CHANGED = "vulcan-brownout/device_changed";
const EVENT_THRESHOLD_UPDATED = "vulcan-brownout/threshold_updated";
const EVENT_STATUS = "vulcan-brownout/status";

const DEFAULT_PAGE_SIZE = 50;
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

  // Mobile state
  @state() show_sort_modal = false;
  @state() show_filter_modal = false;
  @state() is_mobile = window.innerWidth < 768;

  // Connection retry state
  reconnect_attempt = 0;
  reconnect_timer = null;

  connectedCallback() {
    super.connectedCallback();
    this._load_ui_state_from_storage();
    this._load_devices();
    window.addEventListener("resize", () => {
      this.is_mobile = window.innerWidth < 768;
    });
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    this._clear_reconnect_timer();
    window.removeEventListener("resize", this._on_window_resize.bind(this));
  }

  _on_window_resize() {
    this.is_mobile = window.innerWidth < 768;
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
      this.device_statuses = result.data.device_statuses || {};
      this.global_threshold = result.data.device_statuses ? 15 : this.global_threshold;
      this.last_update_time = new Date();
      this.error = null;

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

  /**
   * Subscribe to real-time battery updates via WebSocket.
   */
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

  /**
   * Set up WebSocket message listeners for real-time updates.
   */
  _setup_message_listeners() {
    if (!this.hass || !this.hass.connection) return;

    const original_handleMessage = this.hass.connection._handleMessage;
    if (!original_handleMessage || original_handleMessage._patched) return;

    this.hass.connection._handleMessage = function(msg) {
      if (msg.type === EVENT_DEVICE_CHANGED) {
        this._on_device_changed(msg.data);
      } else if (msg.type === EVENT_THRESHOLD_UPDATED) {
        this._on_threshold_updated(msg.data);
      } else if (msg.type === EVENT_STATUS) {
        this._on_status_updated(msg.data);
      }
      original_handleMessage.call(this, msg);
    }.bind(this);

    original_handleMessage._patched = true;
  }

  /**
   * Handle device_changed event from backend.
   */
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

  /**
   * Handle threshold_updated event from backend.
   */
  _on_threshold_updated(data) {
    this.global_threshold = data.global_threshold;
    this.device_rules = data.device_rules;
    this.settings_global_threshold = data.global_threshold;
    this.settings_device_rules = { ...data.device_rules };

    // Re-calculate statuses for all devices
    for (const device of this.battery_devices) {
      device.status = this._get_status(device);
    }

    this._save_ui_state_to_storage();
    this.requestUpdate();
  }

  /**
   * Handle status event from backend.
   */
  _on_status_updated(data) {
    if (data.status === "connected") {
      this.connection_status = CONNECTION_CONNECTED;
      this.reconnect_attempt = 0;
      this._clear_reconnect_timer();
      this._show_toast("✓ Connection updated");
    } else if (data.status === "disconnected") {
      this.connection_status = CONNECTION_OFFLINE;
      this._schedule_reconnect();
    }
  }

  /**
   * Schedule reconnection with exponential backoff.
   */
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

  /**
   * Clear reconnection timer.
   */
  _clear_reconnect_timer() {
    if (this.reconnect_timer) {
      clearTimeout(this.reconnect_timer);
      this.reconnect_timer = null;
    }
  }

  /**
   * Show temporary toast notification.
   */
  _show_toast(message) {
    // In a real implementation, would use HA's notification service
    console.log(`Toast: ${message}`);
  }

  /**
   * Load UI state from localStorage.
   */
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

  /**
   * Save UI state to localStorage.
   */
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

  /**
   * Call WebSocket command with timeout.
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
    if (!device.available) return STATUS_UNAVAILABLE;
    if (device.battery_level <= this.global_threshold) return STATUS_CRITICAL;
    if (device.battery_level <= (this.global_threshold + 10)) return STATUS_WARNING;
    return STATUS_HEALTHY;
  }

  /**
   * Get icon name based on device status.
   */
  _get_icon(status) {
    if (status === STATUS_CRITICAL) return "mdi:battery-alert";
    if (status === STATUS_WARNING) return "mdi:battery-low";
    if (status === STATUS_UNAVAILABLE) return "mdi:help-circle";
    return "mdi:battery";
  }

  /**
   * Get color for status.
   */
  _get_status_color(status) {
    if (status === STATUS_CRITICAL) return "var(--error-color, #F44336)";
    if (status === STATUS_WARNING) return "var(--warning-color, #FF9800)";
    if (status === STATUS_HEALTHY) return "var(--success-color, #4CAF50)";
    return "var(--disabled-text-color, #9E9E9E)";
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

    if (diffSecs < 2) return "just now";
    if (diffSecs < 60) return `${diffSecs}s ago`;
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    return `${diffDays}d ago`;
  }

  /**
   * Get filtered and sorted device list.
   */
  get _filtered_and_sorted_devices() {
    let filtered = this.battery_devices.filter((d) => {
      const status = this._get_status(d);
      return this.filter_state[status] === true;
    });

    return this._apply_sort(filtered, this.sort_method);
  }

  /**
   * Apply sort algorithm.
   */
  _apply_sort(devices, sort_method) {
    const copy = [...devices];

    switch (sort_method) {
      case "priority":
        const statusOrder = { critical: 0, warning: 1, healthy: 2, unavailable: 3 };
        copy.sort((a, b) => {
          const aStatus = this._get_status(a);
          const bStatus = this._get_status(b);
          if (aStatus !== bStatus) {
            return statusOrder[aStatus] - statusOrder[bStatus];
          }
          return a.battery_level - b.battery_level;
        });
        break;
      case "alphabetical":
        copy.sort((a, b) => a.device_name.localeCompare(b.device_name));
        break;
      case "level_asc":
        copy.sort((a, b) => a.battery_level - b.battery_level);
        break;
      case "level_desc":
        copy.sort((a, b) => b.battery_level - a.battery_level);
        break;
      default:
        return this._apply_sort(devices, "priority");
    }

    return copy;
  }

  /**
   * Event handlers
   */

  async _on_refresh() {
    await this._load_devices();
  }

  _on_settings_click() {
    this.settings_global_threshold = this.global_threshold;
    this.settings_device_rules = { ...this.device_rules };
    this.show_settings_panel = true;
  }

  _on_settings_close() {
    this.show_settings_panel = false;
  }

  async _on_settings_save() {
    try {
      const result = await this._call_websocket({
        type: SET_THRESHOLD_COMMAND,
        data: {
          global_threshold: this.settings_global_threshold,
          device_rules: this.settings_device_rules,
        },
      });

      if (result.success) {
        this.global_threshold = this.settings_global_threshold;
        this.device_rules = { ...this.settings_device_rules };
        this.show_settings_panel = false;
        this._show_toast("✓ Settings saved");
      }
    } catch (err) {
      console.error("Failed to save settings:", err);
      this._show_toast("✗ Failed to save settings");
    }
  }

  _on_sort_changed(method) {
    this.sort_method = method;
    this._save_ui_state_to_storage();
    this.show_sort_modal = false;
    this.requestUpdate();
  }

  _on_filter_changed(status, value) {
    this.filter_state[status] = value;
    this._save_ui_state_to_storage();
    this.requestUpdate();
  }

  _on_reset_filters() {
    this.sort_method = "priority";
    this.filter_state = {
      critical: true,
      warning: true,
      healthy: true,
      unavailable: false,
    };
    this._save_ui_state_to_storage();
    this.show_sort_modal = false;
    this.show_filter_modal = false;
    this.requestUpdate();
  }

  _on_add_device_rule() {
    this.show_add_rule_modal = true;
  }

  _on_add_rule_save() {
    if (this.selected_device_for_rule) {
      this.settings_device_rules[this.selected_device_for_rule] = this.new_rule_threshold;
      this.selected_device_for_rule = null;
      this.new_rule_threshold = 15;
      this.show_add_rule_modal = false;
      this.requestUpdate();
    }
  }

  _on_remove_device_rule(entity_id) {
    delete this.settings_device_rules[entity_id];
    this.requestUpdate();
  }

  /**
   * Rendering
   */

  render() {
    // Loading state
    if (this.isLoading && this.battery_devices.length === 0) {
      return html`
        <div class="panel-container">
          <div class="header">
            <h1>Battery Monitoring</h1>
            <div class="header-buttons">
              <button
                class="icon-button"
                @click=${this._on_refresh}
                aria-label="Refresh"
                title="Refresh"
              >
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
            <h1>Battery Monitoring</h1>
            <div class="header-buttons">
              <button
                class="icon-button"
                @click=${this._on_refresh}
                aria-label="Refresh"
                title="Refresh"
              >
                <ha-icon icon="mdi:refresh"></ha-icon>
              </button>
            </div>
          </div>
          <div class="error-state">
            <div class="error-icon">
              <ha-icon icon="mdi:alert-circle"></ha-icon>
            </div>
            <div class="error-title">Unable to load battery devices</div>
            <div class="error-message">${this.error}</div>
            <button class="cta-button" @click=${this._on_refresh}>Retry</button>
          </div>
        </div>
      `;
    }

    // Empty state
    if (this.battery_devices.length === 0) {
      return html`
        <div class="panel-container">
          <div class="header">
            <h1>Battery Monitoring</h1>
            <div class="header-buttons">
              <button
                class="icon-button"
                @click=${this._on_refresh}
                aria-label="Refresh"
                title="Refresh"
              >
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
          </div>
        </div>
      `;
    }

    // Normal list state
    return html`
      <div class="panel-container">
        <div class="header">
          <h1>Battery Monitoring</h1>
          <div class="header-buttons">
            <button
              class="icon-button settings-button"
              @click=${this._on_settings_click}
              aria-label="Settings"
              title="Settings"
            >
              <ha-icon icon="mdi:cog"></ha-icon>
            </button>
            <div
              class="connection-badge ${this.connection_status}"
              role="status"
              aria-label="Connection status: ${this.connection_status}"
              title="Connection: ${this.connection_status}"
            >
              ${this.connection_status === CONNECTION_CONNECTED
                ? html`<span class="badge-dot connected"></span> 🟢`
                : this.connection_status === CONNECTION_RECONNECTING
                ? html`<span class="badge-dot reconnecting"></span> 🔵`
                : html`<span class="badge-dot offline"></span> 🔴`}
            </div>
          </div>
        </div>

        ${this._render_sort_filter_bar()}

        <div class="device-list-container">
          ${this._filtered_and_sorted_devices.length === 0
            ? html`
                <div class="no-results">
                  <div class="no-results-icon">
                    <ha-icon icon="mdi:filter-outline"></ha-icon>
                  </div>
                  <div class="no-results-text">No devices match your filters</div>
                  <button class="reset-button" @click=${() => this._on_reset_filters()}>
                    Clear Filters
                  </button>
                </div>
              `
            : this._render_device_groups()}
        </div>

        ${this.last_update_time
          ? html`
              <div class="footer">
                🔄 Updated ${this._format_time_ago(this.last_update_time)}
              </div>
            `
          : ""}
      </div>

      ${this.show_settings_panel ? this._render_settings_panel() : ""}
    `;
  }

  /**
   * Render sort/filter bar.
   */
  _render_sort_filter_bar() {
    if (this.is_mobile) {
      return html`
        <div class="sort-filter-bar mobile">
          <button class="sort-button" @click=${() => (this.show_sort_modal = true)}>
            ▼ ${this.sort_method === "priority"
              ? "Priority"
              : this.sort_method === "alphabetical"
              ? "A-Z"
              : this.sort_method === "level_asc"
              ? "Low→High"
              : "High→Low"}
          </button>
          <button
            class="filter-button"
            @click=${() => (this.show_filter_modal = true)}
          >
            ▼ Filter
          </button>
          <button class="reset-button" @click=${() => this._on_reset_filters()}>
            ✕ Reset
          </button>
        </div>

        ${this.show_sort_modal ? this._render_sort_modal() : ""}
        ${this.show_filter_modal ? this._render_filter_modal() : ""}
      `;
    }

    return html`
      <div class="sort-filter-bar desktop">
        <select @change=${(e) => this._on_sort_changed(e.target.value)} aria-label="Sort by">
          <option value="priority" ?selected=${this.sort_method === "priority"}>
            ▼ Priority (Critical First)
          </option>
          <option value="alphabetical" ?selected=${this.sort_method === "alphabetical"}>
            ▼ Alphabetical (A-Z)
          </option>
          <option value="level_asc" ?selected=${this.sort_method === "level_asc"}>
            ▼ Battery Level (Low→High)
          </option>
          <option value="level_desc" ?selected=${this.sort_method === "level_desc"}>
            ▼ Battery Level (High→Low)
          </option>
        </select>

        <div class="filter-dropdowns">
          <label class="filter-label">Filter:</label>
          <label class="filter-checkbox">
            <input
              type="checkbox"
              ?checked=${this.filter_state.critical}
              @change=${(e) => this._on_filter_changed(STATUS_CRITICAL, e.target.checked)}
              aria-label="Show critical devices"
            />
            Critical (${this.device_statuses.critical})
          </label>
          <label class="filter-checkbox">
            <input
              type="checkbox"
              ?checked=${this.filter_state.warning}
              @change=${(e) => this._on_filter_changed(STATUS_WARNING, e.target.checked)}
              aria-label="Show warning devices"
            />
            Warning (${this.device_statuses.warning})
          </label>
          <label class="filter-checkbox">
            <input
              type="checkbox"
              ?checked=${this.filter_state.healthy}
              @change=${(e) => this._on_filter_changed(STATUS_HEALTHY, e.target.checked)}
              aria-label="Show healthy devices"
            />
            Healthy (${this.device_statuses.healthy})
          </label>
          <label class="filter-checkbox">
            <input
              type="checkbox"
              ?checked=${this.filter_state.unavailable}
              @change=${(e) => this._on_filter_changed(STATUS_UNAVAILABLE, e.target.checked)}
              aria-label="Show unavailable devices"
            />
            Unavailable (${this.device_statuses.unavailable})
          </label>
        </div>

        <button class="reset-button" @click=${() => this._on_reset_filters()}>
          ✕ Reset
        </button>
      </div>
    `;
  }

  /**
   * Render sort modal (mobile).
   */
  _render_sort_modal() {
    return html`
      <div class="modal-overlay" @click=${() => (this.show_sort_modal = false)}></div>
      <div class="modal sort-modal">
        <div class="modal-header">
          <h2>Sort By</h2>
          <button
            class="modal-close"
            @click=${() => (this.show_sort_modal = false)}
            aria-label="Close"
          >
            ✕
          </button>
        </div>
        <div class="modal-content">
          ${["priority", "alphabetical", "level_asc", "level_desc"].map(
            (method) => html`
              <label class="radio-label">
                <input
                  type="radio"
                  name="sort"
                  value=${method}
                  ?checked=${this.sort_method === method}
                  @change=${(e) => this._on_sort_changed(e.target.value)}
                />
                ${method === "priority"
                  ? "Priority (Critical First)"
                  : method === "alphabetical"
                  ? "Alphabetical (A-Z)"
                  : method === "level_asc"
                  ? "Battery Level (Low → High)"
                  : "Battery Level (High → Low)"}
              </label>
            `
          )}
        </div>
        <div class="modal-footer">
          <button class="button primary" @click=${() => (this.show_sort_modal = false)}>
            Apply
          </button>
        </div>
      </div>
    `;
  }

  /**
   * Render filter modal (mobile).
   */
  _render_filter_modal() {
    return html`
      <div class="modal-overlay" @click=${() => (this.show_filter_modal = false)}></div>
      <div class="modal filter-modal">
        <div class="modal-header">
          <h2>Filter By Status</h2>
          <button
            class="modal-close"
            @click=${() => (this.show_filter_modal = false)}
            aria-label="Close"
          >
            ✕
          </button>
        </div>
        <div class="modal-content">
          ${[STATUS_CRITICAL, STATUS_WARNING, STATUS_HEALTHY, STATUS_UNAVAILABLE].map(
            (status) => html`
              <label class="checkbox-label">
                <input
                  type="checkbox"
                  ?checked=${this.filter_state[status]}
                  @change=${(e) => this._on_filter_changed(status, e.target.checked)}
                  aria-label="Show ${status} devices"
                />
                ${status.charAt(0).toUpperCase() + status.slice(1)} (${this.device_statuses[status]})
              </label>
            `
          )}
        </div>
        <div class="modal-footer">
          <button class="button primary" @click=${() => (this.show_filter_modal = false)}>
            Apply
          </button>
          <button class="button secondary" @click=${() => {
            this.filter_state = { critical: true, warning: true, healthy: true, unavailable: false };
            this._save_ui_state_to_storage();
            this.show_filter_modal = false;
            this.requestUpdate();
          }}>
            Clear All
          </button>
        </div>
      </div>
    `;
  }

  /**
   * Render settings panel.
   */
  _render_settings_panel() {
    return html`
      <div class="settings-overlay" @click=${this._on_settings_close}></div>
      <div class="settings-panel">
        <div class="settings-header">
          <h2>Battery Monitoring Settings</h2>
          <button
            class="close-button"
            @click=${this._on_settings_close}
            aria-label="Close settings"
          >
            ✕
          </button>
        </div>

        <div class="settings-content">
          <div class="settings-section">
            <h3>Global Threshold</h3>
            <p class="settings-description">
              When battery falls below this level, it shows as CRITICAL
            </p>
            <div class="threshold-control">
              <input
                type="range"
                min="5"
                max="100"
                .value=${this.settings_global_threshold}
                @input=${(e) => (this.settings_global_threshold = parseInt(e.target.value))}
                aria-label="Global threshold slider"
              />
              <input
                type="number"
                min="5"
                max="100"
                .value=${this.settings_global_threshold}
                @input=${(e) => (this.settings_global_threshold = parseInt(e.target.value))}
                aria-label="Global threshold input"
              />
              <span class="threshold-value">%</span>
            </div>
            <div class="threshold-preview">
              ${this.battery_devices.filter((d) => d.battery_level <= this.settings_global_threshold)
                .length} devices below this threshold
            </div>
          </div>

          <div class="settings-section">
            <h3>Device-Specific Overrides</h3>
            <button
              class="add-rule-button"
              @click=${this._on_add_device_rule}
              aria-label="Add device rule"
            >
              + Add Device Rule
            </button>

            ${Object.entries(this.settings_device_rules).length === 0
              ? html`<p class="no-rules">No device-specific rules yet</p>`
              : html`
                  <div class="rules-list">
                    ${Object.entries(this.settings_device_rules).map(
                      ([entity_id, threshold]) => html`
                        <div class="rule-item">
                          <span class="rule-device">
                            ${this.battery_devices.find((d) => d.entity_id === entity_id)
                              ?.device_name || entity_id}
                          </span>
                          <span class="rule-threshold">${threshold}%</span>
                          <button
                            class="delete-button"
                            @click=${() => this._on_remove_device_rule(entity_id)}
                            aria-label="Delete rule"
                          >
                            ✕
                          </button>
                        </div>
                      `
                    )}
                  </div>
                `}
          </div>
        </div>

        <div class="settings-footer">
          <button
            class="button primary"
            @click=${this._on_settings_save}
            aria-label="Save settings"
          >
            Save
          </button>
          <button
            class="button secondary"
            @click=${this._on_settings_close}
            aria-label="Cancel"
          >
            Cancel
          </button>
        </div>
      </div>

      ${this.show_add_rule_modal ? this._render_add_rule_modal() : ""}
    `;
  }

  /**
   * Render add device rule modal.
   */
  _render_add_rule_modal() {
    const available_devices = this.battery_devices.filter(
      (d) => !this.settings_device_rules[d.entity_id]
    );

    return html`
      <div class="modal-overlay" @click=${() => (this.show_add_rule_modal = false)}></div>
      <div class="modal add-rule-modal">
        <div class="modal-header">
          <h2>${!this.selected_device_for_rule ? "Select Device" : "Set Threshold"}</h2>
          <button
            class="modal-close"
            @click=${() => {
              this.show_add_rule_modal = false;
              this.selected_device_for_rule = null;
            }}
            aria-label="Close"
          >
            ✕
          </button>
        </div>

        <div class="modal-content">
          ${!this.selected_device_for_rule
            ? html`
                <div class="device-list">
                  ${available_devices.length === 0
                    ? html`<p>All devices already have rules</p>`
                    : available_devices.map(
                        (device) => html`
                          <button
                            class="device-option"
                            @click=${() => (this.selected_device_for_rule = device.entity_id)}
                          >
                            <span class="device-name">${device.device_name}</span>
                            <span class="device-battery">${device.battery_level}%</span>
                            <span class="device-status ${this._get_status(device)}">
                              ${this._get_status(device).toUpperCase()}
                            </span>
                          </button>
                        `
                      )}
                </div>
              `
            : html`
                <div class="threshold-form">
                  <div class="form-group">
                    <label>Device:</label>
                    <div class="selected-device">
                      ${this.battery_devices.find((d) => d.entity_id === this.selected_device_for_rule)
                        ?.device_name || this.selected_device_for_rule}
                    </div>
                  </div>

                  <div class="form-group">
                    <label>Threshold:</label>
                    <div class="threshold-control">
                      <input
                        type="range"
                        min="5"
                        max="100"
                        .value=${this.new_rule_threshold}
                        @input=${(e) => (this.new_rule_threshold = parseInt(e.target.value))}
                        aria-label="Device threshold slider"
                      />
                      <input
                        type="number"
                        min="5"
                        max="100"
                        .value=${this.new_rule_threshold}
                        @input=${(e) => (this.new_rule_threshold = parseInt(e.target.value))}
                        aria-label="Device threshold input"
                      />
                      <span>%</span>
                    </div>
                  </div>

                  <div class="form-help">
                    Show CRITICAL when battery falls below ${this.new_rule_threshold}%
                  </div>
                </div>
              `}
        </div>

        <div class="modal-footer">
          ${!this.selected_device_for_rule
            ? html`
                <button
                  class="button secondary"
                  @click=${() => (this.show_add_rule_modal = false)}
                >
                  Cancel
                </button>
              `
            : html`
                <button class="button primary" @click=${this._on_add_rule_save}>
                  Save Rule
                </button>
                <button
                  class="button secondary"
                  @click=${() => (this.selected_device_for_rule = null)}
                >
                  Back
                </button>
              `}
        </div>
      </div>
    `;
  }

  /**
   * Render device groups.
   */
  _render_device_groups() {
    const sorted = this._filtered_and_sorted_devices;
    const critical = sorted.filter((d) => this._get_status(d) === STATUS_CRITICAL);
    const warning = sorted.filter((d) => this._get_status(d) === STATUS_WARNING);
    const healthy = sorted.filter((d) => this._get_status(d) === STATUS_HEALTHY);
    const unavailable = sorted.filter((d) => this._get_status(d) === STATUS_UNAVAILABLE);

    return html`
      ${critical.length > 0
        ? html`
            <div class="device-group">
              <div class="group-header">CRITICAL (${critical.length})</div>
              ${critical.map((device) => this._render_device_card(device))}
            </div>
          `
        : ""}
      ${warning.length > 0
        ? html`
            <div class="device-group">
              <div class="group-header">WARNING (${warning.length})</div>
              ${warning.map((device) => this._render_device_card(device))}
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
      ${unavailable.length > 0
        ? html`
            <div class="device-group">
              <div class="group-header">UNAVAILABLE (${unavailable.length})</div>
              ${unavailable.map((device) => this._render_device_card(device))}
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
    const icon = this._get_icon(status);
    const color = this._get_status_color(status);

    return html`
      <div class="device-card ${status}">
        <div class="device-content">
          <ha-icon
            icon="${icon}"
            class="device-icon ${status}"
            style="color: ${color}"
          ></ha-icon>
          <div class="device-info">
            <div class="device-name">${device.device_name}</div>
            <div class="battery-level">${device.battery_level}%</div>
          </div>
        </div>
        <div class="progress-bar">
          <div
            class="progress-bar-fill ${status}"
            style="width: ${device.battery_level}%; background-color: ${color}"
            role="progressbar"
            aria-valuenow="${device.battery_level}"
            aria-valuemin="0"
            aria-valuemax="100"
            aria-label="Battery level: ${device.battery_level}%"
          ></div>
        </div>
        ${device.last_changed
          ? html`
              <div class="device-timestamp">
                Last changed: ${this._format_time_ago(new Date(device.last_changed))}
              </div>
            `
          : ""}
      </div>
    `;
  }

  static get styles() {
    return css`
      :host {
        display: block;
        background-color: var(--card-background-color, #fff);
        --primary-color: var(--primary-color, #1976d2);
        --error-color: var(--error-color, #f44336);
        --warning-color: var(--warning-color, #ff9800);
        --success-color: var(--success-color, #4caf50);
        --text-primary-color: var(--text-primary-color, #212121);
        --text-secondary-color: var(--text-secondary-color, #757575);
        --text-tertiary-color: var(--text-tertiary-color, #bdbdbd);
        --divider-color: var(--divider-color, #e0e0e0);
        --disabled-text-color: var(--disabled-text-color, #9e9e9e);
        --error-color-background: var(--error-color-background, #ffebee);
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
        align-items: center;
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
        min-width: 44px;
        min-height: 44px;
      }

      .icon-button:hover {
        color: var(--primary-color);
      }

      .connection-badge {
        display: flex;
        align-items: center;
        gap: 4px;
        font-size: 12px;
        padding: 4px 8px;
        border-radius: 4px;
        font-weight: 500;
      }

      .connection-badge.connected {
        color: var(--success-color);
      }

      .connection-badge.reconnecting {
        color: var(--primary-color);
      }

      .connection-badge.reconnecting .badge-dot {
        animation: spin 2s linear infinite;
      }

      .connection-badge.offline {
        color: var(--error-color);
      }

      @keyframes spin {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
      }

      .badge-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        display: inline-block;
      }

      .badge-dot.connected {
        background-color: var(--success-color);
      }

      .badge-dot.reconnecting {
        background-color: var(--primary-color);
      }

      .badge-dot.offline {
        background-color: var(--error-color);
      }

      .sort-filter-bar {
        background-color: var(--card-background-color);
        border-bottom: 1px solid var(--divider-color);
        padding: 12px 16px;
        flex-shrink: 0;
        display: flex;
        gap: 8px;
        align-items: center;
      }

      .sort-filter-bar.desktop {
        gap: 12px;
      }

      .sort-filter-bar select {
        padding: 8px 12px;
        border: 1px solid var(--divider-color);
        border-radius: 4px;
        background-color: var(--card-background-color);
        color: var(--text-primary-color);
        font-size: 14px;
        cursor: pointer;
        min-height: 44px;
      }

      .filter-dropdowns {
        display: flex;
        gap: 12px;
        align-items: center;
      }

      .filter-label {
        font-size: 14px;
        font-weight: 500;
        color: var(--text-primary-color);
      }

      .filter-checkbox {
        display: flex;
        align-items: center;
        gap: 6px;
        cursor: pointer;
        font-size: 14px;
        color: var(--text-secondary-color);
      }

      .filter-checkbox input {
        width: 18px;
        height: 18px;
        cursor: pointer;
      }

      .reset-button {
        background: none;
        border: 1px solid var(--divider-color);
        color: var(--text-secondary-color);
        padding: 8px 12px;
        border-radius: 4px;
        cursor: pointer;
        font-size: 14px;
        font-weight: 500;
        min-height: 44px;
        transition: background-color 0.2s;
      }

      .reset-button:hover {
        background-color: var(--divider-color);
      }

      .sort-filter-bar.mobile {
        flex-direction: column;
        gap: 8px;
      }

      .sort-filter-bar.mobile button {
        width: 100%;
      }

      .sort-button,
      .filter-button {
        background-color: var(--primary-color);
        color: white;
        border: none;
        padding: 12px 16px;
        border-radius: 4px;
        cursor: pointer;
        font-size: 14px;
        font-weight: 500;
        min-height: 44px;
        transition: opacity 0.2s;
      }

      .sort-button:hover,
      .filter-button:hover {
        opacity: 0.8;
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
        transition: background-color 0.2s, border-color 0.3s;
      }

      .device-card.critical {
        background-color: var(--error-color-background);
        border-color: var(--error-color);
      }

      .device-card.warning {
        background-color: rgba(255, 152, 0, 0.05);
        border-color: var(--warning-color);
      }

      .device-card.unavailable {
        background-color: rgba(0, 0, 0, 0.02);
        border-color: var(--divider-color);
        opacity: 0.7;
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
        width: 24px;
        height: 24px;
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

      .device-timestamp {
        font-size: 11px;
        color: var(--text-tertiary-color);
        margin-top: 4px;
      }

      .progress-bar {
        height: 4px;
        background-color: var(--divider-color);
        border-radius: 2px;
        overflow: hidden;
        margin-top: 8px;
      }

      .progress-bar-fill {
        height: 100%;
        transition: width 300ms cubic-bezier(0.4, 0, 0.2, 1);
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
        0% { background-position: 200% 0; }
        100% { background-position: -200% 0; }
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

      /* Empty and error states */
      .empty-state,
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

      .empty-icon,
      .error-icon {
        font-size: 64px;
        color: var(--text-tertiary-color);
      }

      .error-icon {
        color: var(--error-color);
      }

      .empty-title,
      .error-title {
        font-size: 20px;
        font-weight: 500;
        color: var(--text-primary-color);
      }

      .empty-message,
      .error-message {
        font-size: 13px;
        color: var(--text-secondary-color);
        max-width: 300px;
      }

      .no-results {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 12px;
        padding: 32px 24px;
        text-align: center;
      }

      .no-results-icon {
        font-size: 48px;
        color: var(--text-tertiary-color);
      }

      .no-results-text {
        font-size: 14px;
        color: var(--text-secondary-color);
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
        min-height: 44px;
      }

      .cta-button:hover {
        opacity: 0.8;
      }

      .footer {
        font-size: 11px;
        color: var(--text-tertiary-color);
        text-align: center;
        padding: 8px;
        border-top: 1px solid var(--divider-color);
        flex-shrink: 0;
      }

      /* Modal styles */
      .modal-overlay {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background-color: rgba(0, 0, 0, 0.4);
        z-index: 1000;
      }

      .modal {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        max-height: 90vh;
        background-color: var(--card-background-color);
        border-radius: 8px 8px 0 0;
        display: flex;
        flex-direction: column;
        z-index: 1001;
        animation: slideUp 300ms ease-out;
      }

      @keyframes slideUp {
        from { transform: translateY(100%); }
        to { transform: translateY(0); }
      }

      .modal-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 16px;
        border-bottom: 1px solid var(--divider-color);
        flex-shrink: 0;
      }

      .modal-header h2 {
        margin: 0;
        font-size: 18px;
        font-weight: 500;
        color: var(--text-primary-color);
      }

      .modal-close {
        background: none;
        border: none;
        font-size: 24px;
        color: var(--text-secondary-color);
        cursor: pointer;
        padding: 8px;
        min-width: 44px;
        min-height: 44px;
      }

      .modal-content {
        flex: 1;
        overflow-y: auto;
        padding: 16px;
      }

      .modal-footer {
        display: flex;
        gap: 8px;
        padding: 16px;
        border-top: 1px solid var(--divider-color);
        flex-shrink: 0;
      }

      .modal-footer .button {
        flex: 1;
        min-height: 44px;
      }

      .radio-label,
      .checkbox-label {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 12px;
        cursor: pointer;
        font-size: 14px;
        color: var(--text-primary-color);
        border-radius: 4px;
        transition: background-color 0.2s;
      }

      .radio-label:hover,
      .checkbox-label:hover {
        background-color: var(--divider-color);
      }

      .radio-label input,
      .checkbox-label input {
        width: 18px;
        height: 18px;
        cursor: pointer;
      }

      .device-list {
        display: flex;
        flex-direction: column;
        gap: 8px;
      }

      .device-option {
        background: none;
        border: 1px solid var(--divider-color);
        padding: 12px;
        border-radius: 4px;
        cursor: pointer;
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 12px;
        min-height: 44px;
        transition: border-color 0.2s;
      }

      .device-option:hover {
        border-color: var(--primary-color);
      }

      .device-name {
        font-size: 14px;
        font-weight: 500;
        color: var(--text-primary-color);
        flex: 1;
        text-align: left;
      }

      .device-battery {
        font-size: 12px;
        color: var(--text-secondary-color);
      }

      .device-status {
        font-size: 11px;
        font-weight: 600;
        padding: 4px 8px;
        border-radius: 2px;
        text-transform: uppercase;
      }

      .device-status.critical {
        background-color: var(--error-color);
        color: white;
      }

      .device-status.warning {
        background-color: var(--warning-color);
        color: white;
      }

      .device-status.healthy {
        background-color: var(--success-color);
        color: white;
      }

      .device-status.unavailable {
        background-color: var(--disabled-text-color);
        color: white;
      }

      .threshold-form {
        display: flex;
        flex-direction: column;
        gap: 16px;
      }

      .form-group {
        display: flex;
        flex-direction: column;
        gap: 8px;
      }

      .form-group label {
        font-size: 14px;
        font-weight: 500;
        color: var(--text-primary-color);
      }

      .selected-device {
        padding: 12px;
        background-color: var(--divider-color);
        border-radius: 4px;
        font-size: 14px;
        color: var(--text-primary-color);
      }

      .threshold-control {
        display: flex;
        gap: 8px;
        align-items: center;
      }

      .threshold-control input[type="range"] {
        flex: 1;
        min-height: 44px;
      }

      .threshold-control input[type="number"] {
        width: 60px;
        padding: 8px;
        border: 1px solid var(--divider-color);
        border-radius: 4px;
        font-size: 14px;
      }

      .form-help {
        font-size: 12px;
        color: var(--text-secondary-color);
        padding: 8px;
        background-color: var(--divider-color);
        border-radius: 4px;
      }

      /* Settings panel styles */
      .settings-overlay {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background-color: rgba(0, 0, 0, 0.4);
        z-index: 1000;
      }

      .settings-panel {
        position: fixed;
        right: 0;
        top: 0;
        bottom: 0;
        width: 400px;
        max-width: 100%;
        background-color: var(--card-background-color);
        display: flex;
        flex-direction: column;
        z-index: 1001;
        animation: slideInRight 300ms ease-out;
      }

      @keyframes slideInRight {
        from { transform: translateX(100%); }
        to { transform: translateX(0); }
      }

      .settings-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 16px;
        border-bottom: 1px solid var(--divider-color);
        flex-shrink: 0;
      }

      .settings-header h2 {
        margin: 0;
        font-size: 18px;
        font-weight: 500;
        color: var(--text-primary-color);
      }

      .close-button {
        background: none;
        border: none;
        font-size: 24px;
        color: var(--text-secondary-color);
        cursor: pointer;
        padding: 8px;
        min-width: 44px;
        min-height: 44px;
      }

      .settings-content {
        flex: 1;
        overflow-y: auto;
        padding: 16px;
      }

      .settings-section {
        margin-bottom: 24px;
      }

      .settings-section h3 {
        margin: 0 0 12px 0;
        font-size: 16px;
        font-weight: 500;
        color: var(--text-primary-color);
      }

      .settings-description {
        margin: 0 0 12px 0;
        font-size: 13px;
        color: var(--text-secondary-color);
      }

      .threshold-value {
        font-size: 14px;
        font-weight: 500;
        color: var(--text-primary-color);
        min-width: 30px;
      }

      .threshold-preview {
        margin-top: 8px;
        font-size: 12px;
        color: var(--text-secondary-color);
      }

      .add-rule-button {
        width: 100%;
        padding: 12px;
        background-color: var(--primary-color);
        color: white;
        border: none;
        border-radius: 4px;
        cursor: pointer;
        font-size: 14px;
        font-weight: 500;
        min-height: 44px;
        margin-bottom: 12px;
      }

      .add-rule-button:hover {
        opacity: 0.8;
      }

      .no-rules {
        margin: 0;
        padding: 12px;
        background-color: var(--divider-color);
        border-radius: 4px;
        font-size: 13px;
        color: var(--text-secondary-color);
        text-align: center;
      }

      .rules-list {
        display: flex;
        flex-direction: column;
        gap: 8px;
      }

      .rule-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 12px;
        background-color: var(--divider-color);
        border-radius: 4px;
        font-size: 14px;
      }

      .rule-device {
        font-weight: 500;
        color: var(--text-primary-color);
        flex: 1;
      }

      .rule-threshold {
        font-weight: 500;
        color: var(--text-secondary-color);
        margin-right: 12px;
      }

      .delete-button {
        background: none;
        border: none;
        color: var(--error-color);
        cursor: pointer;
        font-size: 16px;
        padding: 4px 8px;
        min-width: 44px;
        min-height: 44px;
        display: flex;
        align-items: center;
        justify-content: center;
      }

      .delete-button:hover {
        opacity: 0.8;
      }

      .settings-footer {
        display: flex;
        gap: 8px;
        padding: 16px;
        border-top: 1px solid var(--divider-color);
        flex-shrink: 0;
      }

      .settings-footer .button {
        flex: 1;
        min-height: 44px;
      }

      .button {
        padding: 12px 16px;
        border: none;
        border-radius: 4px;
        cursor: pointer;
        font-size: 14px;
        font-weight: 500;
        transition: opacity 0.2s;
      }

      .button.primary {
        background-color: var(--primary-color);
        color: white;
      }

      .button.primary:hover {
        opacity: 0.8;
      }

      .button.secondary {
        background-color: var(--divider-color);
        color: var(--text-primary-color);
      }

      .button.secondary:hover {
        opacity: 0.8;
      }

      /* Responsive design */
      @media (max-width: 768px) {
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
          width: 20px;
          height: 20px;
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

        .settings-panel {
          width: 100%;
          max-width: 100%;
        }

        .sort-filter-bar.desktop {
          display: none;
        }

        .sort-filter-bar.mobile {
          display: flex;
        }
      }

      @media (min-width: 768px) {
        .sort-filter-bar.mobile {
          display: none;
        }

        .sort-filter-bar.desktop {
          display: flex;
        }
      }
    `;
  }
}
