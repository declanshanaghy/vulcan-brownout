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

const QUERY_DEVICES_COMMAND = "vulcan-brownout/query_devices";
const SUBSCRIBE_COMMAND = "vulcan-brownout/subscribe";
const SET_THRESHOLD_COMMAND = "vulcan-brownout/set_threshold";
const GET_NOTIFICATION_PREFERENCES_COMMAND = "vulcan-brownout/get_notification_preferences";
const SET_NOTIFICATION_PREFERENCES_COMMAND = "vulcan-brownout/set_notification_preferences";
const GET_FILTER_OPTIONS_COMMAND = "vulcan-brownout/get_filter_options";
const EVENT_DEVICE_CHANGED = "vulcan-brownout/device_changed";
const EVENT_THRESHOLD_UPDATED = "vulcan-brownout/threshold_updated";
const EVENT_STATUS = "vulcan-brownout/status";
const EVENT_NOTIFICATION_SENT = "vulcan-brownout/notification_sent";

const FILTER_STORAGE_KEY = "vulcan_brownout_filters";
const DEFAULT_FILTERS = { manufacturer: [], device_class: [], status: [], area: [] };

const FILTER_CATEGORY_LABELS = {
  manufacturer: "Manufacturer",
  device_class: "Device Class",
  status: "Status",
  area: "Room",
};

const MOBILE_BREAKPOINT_PX = 768;

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

class VulcanBrownoutPanel extends LitElement {
  // Lit reactive properties (replaces @property and @state decorators)
  static properties = {
    // HA-provided property
    hass: { attribute: false },
    // Data state
    battery_devices: { state: true },
    global_threshold: { state: true },
    device_rules: { state: true },
    device_statuses: { state: true },
    // Pagination state (Sprint 3: cursor-based)
    current_cursor: { state: true },
    has_more: { state: true },
    is_fetching: { state: true },
    show_skeleton_loaders: { state: true },
    // UI state
    isLoading: { state: true },
    error: { state: true },
    sort_method: { state: true },
    filter_state: { state: true },
    // Connection state
    connection_status: { state: true },
    last_update_time: { state: true },
    subscription_id: { state: true },
    // Modal state
    show_settings_panel: { state: true },
    settings_global_threshold: { state: true },
    settings_device_rules: { state: true },
    show_add_rule_modal: { state: true },
    selected_device_for_rule: { state: true },
    new_rule_threshold: { state: true },
    // Sprint 3: Notification preferences modal
    show_notification_modal: { state: true },
    notification_prefs: { state: true },
    notification_history: { state: true },
    notification_search: { state: true },
    // Mobile state
    show_sort_modal: { state: true },
    show_filter_modal: { state: true },
    is_mobile: { state: true },
    // Sprint 3: Back to top button and dark mode
    show_back_to_top: { state: true },
    current_theme: { state: true },
    // Sprint 5: Filter state
    active_filters: { state: true },
    staged_filters: { state: true },
    filter_options: { state: true },
    filter_options_loading: { state: true },
    filter_options_error: { state: true },
    show_filter_dropdown: { state: true },
    show_mobile_filter_sheet: { state: true },
  };

  constructor() {
    super();
    this.hass = null;
    this.battery_devices = [];
    this.global_threshold = 15;
    this.device_rules = {};
    this.device_statuses = { critical: 0, warning: 0, healthy: 0, unavailable: 0 };
    this.current_cursor = null;
    this.has_more = false;
    this.is_fetching = false;
    this.show_skeleton_loaders = false;
    this.isLoading = false;
    this.error = null;
    this.sort_method = "priority";
    this.filter_state = { critical: true, warning: true, healthy: true, unavailable: false };
    this.connection_status = CONNECTION_OFFLINE;
    this.last_update_time = null;
    this.subscription_id = null;
    this.show_settings_panel = false;
    this.settings_global_threshold = 15;
    this.settings_device_rules = {};
    this.show_add_rule_modal = false;
    this.selected_device_for_rule = null;
    this.new_rule_threshold = 15;
    this.show_notification_modal = false;
    this.notification_prefs = { enabled: true, frequency_cap_hours: 6, severity_filter: "critical_only", per_device: {} };
    this.notification_history = [];
    this.notification_search = "";
    this.show_sort_modal = false;
    this.show_filter_modal = false;
    this.is_mobile = window.innerWidth < 768;
    this.show_back_to_top = false;
    this.current_theme = "light";
    // Sprint 5: Filter initialization
    this.active_filters = this._load_filters_from_localstorage();
    this.staged_filters = null;
    this.filter_options = null;
    this.filter_options_loading = false;
    this.filter_options_error = null;
    this.show_filter_dropdown = null;
    this.show_mobile_filter_sheet = false;
  }

  // Connection retry state
  reconnect_attempt = 0;
  reconnect_timer = null;

  // Sprint 3: Infinite scroll state
  scroll_observer = null;
  scroll_container = null;
  scroll_debounce_timer = null;

  // Sprint 3: Theme observer (deprecated, replaced by event listener)
  theme_observer = null;

  // Sprint 4: Theme event listener for hass_themes_updated
  _themeListener = null;

  connectedCallback() {
    super.connectedCallback();
    this._load_ui_state_from_storage();
    this._apply_theme(this._detect_theme());
    this._setup_theme_listener();
    // Sprint 5: Start filter options fetch in parallel with device load
    this._load_filter_options();
    this._load_devices();
    window.addEventListener("resize", () => {
      this.is_mobile = window.innerWidth < 768;
    });
    // Sprint 5: Set mobile breakpoint listener
    this._resizeListener = () => {
      this.is_mobile = window.innerWidth < MOBILE_BREAKPOINT_PX;
    };
    window.addEventListener('resize', this._resizeListener);
    // Sprint 5: Attach outside-click listener for dropdowns
    this._outsideClickListener = (e) => {
      if (this.show_filter_dropdown && this.shadowRoot && !this.shadowRoot.contains(e.target)) {
        this._close_filter_dropdown();
      }
    };
    document.addEventListener('click', this._outsideClickListener);
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
    // Sprint 4: Clean up theme listener to prevent memory leaks
    if (this._themeListener && this.hass?.connection) {
      this.hass.connection.removeEventListener('hass_themes_updated', this._themeListener);
      this._themeListener = null;
    }
    // Sprint 5: Clean up listeners
    if (this._resizeListener) {
      window.removeEventListener('resize', this._resizeListener);
    }
    if (this._outsideClickListener) {
      document.removeEventListener('click', this._outsideClickListener);
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
      transition: background-color 300ms ease-out, color 300ms ease-out;
    }

    .header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 16px;
      padding-bottom: 12px;
      border-bottom: 1px solid var(--vb-bg-divider);
      transition: border-color 300ms ease-out;
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
      transition: background-color 300ms ease-out, color 300ms ease-out, box-shadow 300ms ease-out;
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
      transition: all 0.2s, background-color 300ms ease-out;
      min-height: 44px;
      min-width: 44px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
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
      transition: opacity 0.3s, background-color 300ms ease-out;
      z-index: 1000;
      touch-action: manipulation;
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
      transition: background-color 300ms ease-out, color 300ms ease-out;
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
      transition: border-color 300ms ease-out;
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
      min-height: 44px;
      min-width: 44px;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: color 300ms ease-out;
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
      transition: background-color 300ms ease-out, color 300ms ease-out;
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

    /* Sprint 5: Filter bar and chips */
    .filter-bar {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 0 16px;
      height: 48px;
      background-color: var(--vb-bg-card);
      border-bottom: 1px solid var(--vb-border-color);
      flex-shrink: 0;
      position: relative;
    }

    .filter-btn {
      height: 44px;
      padding: 0 12px;
      border-radius: 4px;
      border: 1px solid var(--vb-border-color);
      background: var(--vb-bg-primary);
      color: var(--vb-text-primary);
      cursor: pointer;
      font-size: 13px;
      white-space: nowrap;
      transition: background-color 200ms ease-out;
    }

    .filter-btn:hover {
      background-color: var(--vb-bg-divider);
    }

    .filter-btn.active {
      background-color: #e3f2fd;
      color: #1976d2;
      border-color: #1976d2;
    }

    .filter-dropdown {
      position: absolute;
      top: 100%;
      left: 0;
      min-width: 220px;
      max-height: 300px;
      background: var(--vb-bg-primary);
      border: 1px solid var(--vb-border-color);
      border-radius: 4px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.15);
      overflow-y: auto;
      z-index: 100;
      padding: 8px;
    }

    .filter-dropdown-title {
      font-weight: 600;
      font-size: 13px;
      padding: 8px;
      margin-bottom: 4px;
      color: var(--vb-text-primary);
    }

    .filter-option {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 8px;
      cursor: pointer;
      border-radius: 4px;
      font-size: 13px;
      color: var(--vb-text-primary);
    }

    .filter-option:hover {
      background-color: var(--vb-bg-divider);
    }

    .filter-option input[type="checkbox"] {
      cursor: pointer;
    }

    .chip-row {
      display: flex;
      flex-wrap: nowrap;
      overflow-x: auto;
      padding: 6px 16px;
      gap: 8px;
      align-items: center;
      background: var(--vb-bg-primary);
      border-bottom: 1px solid var(--vb-border-color);
      scrollbar-width: thin;
      animation: chipRowIn 200ms ease-out;
    }

    .filter-chip {
      display: inline-flex;
      align-items: center;
      height: 32px;
      padding: 0 8px;
      border-radius: 16px;
      background: #f3f3f3;
      border: 1px solid #e0e0e0;
      color: var(--vb-text-primary);
      font-size: 12px;
      white-space: nowrap;
      flex-shrink: 0;
    }

    .filter-chip button {
      background: none;
      border: none;
      cursor: pointer;
      padding: 4px;
      color: var(--vb-text-primary);
      font-size: 14px;
      line-height: 1;
      margin-left: 4px;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .chip-clear-all {
      background: none;
      border: none;
      cursor: pointer;
      color: var(--vb-color-primary-action);
      font-size: 12px;
      padding: 8px 4px;
      margin-left: auto;
      white-space: nowrap;
      flex-shrink: 0;
      text-decoration: underline;
    }

    /* Mobile bottom sheet */
    .sheet-overlay {
      position: fixed;
      inset: 0;
      background: rgba(0,0,0,0.5);
      z-index: 200;
    }

    .bottom-sheet {
      position: fixed;
      bottom: 0;
      left: 0;
      right: 0;
      max-height: 85vh;
      overflow-y: auto;
      background: var(--vb-bg-primary);
      border-radius: 16px 16px 0 0;
      box-shadow: 0 -4px 20px rgba(0,0,0,0.2);
      z-index: 201;
      animation: slideUp 300ms ease-out;
      padding: 16px;
    }

    .sheet-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 16px;
      padding-bottom: 12px;
      border-bottom: 1px solid var(--vb-bg-divider);
    }

    .sheet-header h2 {
      margin: 0;
      font-size: 16px;
      font-weight: 600;
    }

    .sheet-section {
      margin-bottom: 16px;
    }

    .sheet-section-title {
      font-weight: 600;
      font-size: 13px;
      margin-bottom: 8px;
      color: var(--vb-text-primary);
    }

    .sheet-buttons {
      display: flex;
      gap: 8px;
      margin-top: 16px;
      padding-top: 16px;
      border-top: 1px solid var(--vb-bg-divider);
    }

    .sheet-buttons button {
      flex: 1;
    }

    @keyframes chipRowIn {
      from { max-height: 0; opacity: 0; }
      to { max-height: 48px; opacity: 1; }
    }

    .filter-trigger {
      background-color: var(--vb-bg-primary);
      color: var(--vb-text-primary);
      border: 1px solid var(--vb-border-color);
      border-radius: 4px;
      padding: 0 12px;
      height: 44px;
      cursor: pointer;
      font-size: 13px;
      white-space: nowrap;
      transition: all 200ms ease-out;
      min-width: 44px;
    }

    .filter-trigger:hover {
      background-color: var(--vb-bg-divider);
    }

    .filter-trigger.active {
      background-color: #e3f2fd;
      color: #1976d2;
      border-color: #1976d2;
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
            <button class="button" @click=${this._open_settings_modal} aria-label="Settings" title="Settings">⚙️ Settings</button>
            <button class="button" @click=${this._open_notification_modal} aria-label="Notification settings" title="Notification settings">🔔 Notifications</button>
          </div>
        </div>

        ${this.error
          ? html`<div style="color: var(--vb-color-critical); padding: 8px; border-radius: 4px;">
              ⚠️ ${this.error}
            </div>`
          : ""}

        <!-- Sprint 5: Filter bar -->
        ${this._render_filter_bar()}

        <!-- Sprint 5: Active filter chips row -->
        ${this._has_active_filters() ? this._render_chip_row() : ''}

        <!-- Sprint 5: Conditional empty state rendering -->
        ${this._is_filtered_empty_state()
          ? this._render_filtered_empty_state()
          : this.battery_devices.length === 0 && !this.isLoading
          ? html`<div class="empty-state">
              <div class="empty-state-icon">🔋</div>
              <div class="empty-state-text">No battery entities found</div>
              <small style="color: var(--vb-text-secondary); max-width: 400px; line-height: 1.5;">
                Check that your devices have a <code style="background-color: var(--vb-bg-card); padding: 2px 4px; border-radius: 2px;">battery_level</code> attribute and are not binary sensors.
              </small>
              <div style="display: flex; gap: 8px; margin-top: 16px; flex-wrap: wrap; justify-content: center;">
                <button class="button" @click=${this._load_devices}>
                  🔄 Refresh
                </button>
                <button class="button" @click=${this._open_settings_modal}>
                  ⚙️ Settings
                </button>
                <button class="button" @click=${() => window.open('https://www.home-assistant.io/docs', '_blank')}>
                  📖 Docs
                </button>
              </div>
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
                    () => html`<div class="skeleton-loader" style="height: 68px; margin-top: 8px;"></div>`
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
        <!-- Sprint 5: Mobile filter bottom sheet -->
        ${this.show_mobile_filter_sheet ? this._render_mobile_filter_sheet() : ""}
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
          sort_key: "priority",
          sort_order: "asc",
          // Sprint 5: Include active filters
          filter_manufacturer: this.active_filters.manufacturer || [],
          filter_device_class: this.active_filters.device_class || [],
          filter_status: this.active_filters.status || [],
          filter_area: this.active_filters.area || [],
        },
      });

      if (!result) {
        throw new Error("Invalid response from server");
      }

      // callWS returns the result field directly (no wrapping data object)
      this.battery_devices = result.devices || [];
      this.device_statuses = result.device_statuses || {};
      this.current_cursor = result.next_cursor || null;
      this.has_more = result.has_more || false;
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

  // Load filter state from localStorage on panel init
  _load_filters_from_localstorage() {
    try {
      const saved = localStorage.getItem(FILTER_STORAGE_KEY);
      if (saved) {
        const parsed = JSON.parse(saved);
        // Ensure all four categories present (handle partial/old data)
        return {
          manufacturer: parsed.manufacturer || [],
          device_class: parsed.device_class || [],
          status: parsed.status || [],
          area: parsed.area || [],
        };
      }
    } catch (e) {
      // Silently ignore localStorage errors
    }
    return { ...DEFAULT_FILTERS };
  }

  // Save filter state to localStorage
  _save_filters_to_localstorage() {
    try {
      localStorage.setItem(FILTER_STORAGE_KEY, JSON.stringify(this.active_filters));
    } catch (e) {
      // Silently ignore (quota exceeded, etc.)
    }
  }

  // Called when filters change — centralized entry point
  _on_filter_changed() {
    this._save_filters_to_localstorage();
    this.current_cursor = null;   // Reset pagination
    this._load_devices();         // Re-fetch with new filters
  }

  // Remove a single filter value
  _remove_filter_chip(category, value) {
    const updated = { ...this.active_filters };
    updated[category] = updated[category].filter(v => v !== value);
    this.active_filters = updated;
    this._on_filter_changed();
  }

  // Clear all active filters
  _clear_all_filters() {
    this.active_filters = { ...DEFAULT_FILTERS };
    this._on_filter_changed();
  }

  // Toggle a filter value in a category (desktop dropdown)
  _toggle_filter_value(category, value) {
    const updated = { ...this.active_filters };
    const list = updated[category] || [];
    if (list.includes(value)) {
      updated[category] = list.filter(v => v !== value);
    } else {
      updated[category] = [...list, value];
    }
    this.active_filters = updated;
    // Note: For desktop, filter is applied on dropdown CLOSE, not on each toggle
    // The trigger label and chip row update reactively via render()
    this._save_filters_to_localstorage();
    // Debounced query — use a timer to avoid calling on every checkbox toggle
    clearTimeout(this._filter_debounce_timer);
    this._filter_debounce_timer = setTimeout(() => {
      this.current_cursor = null;
      this._load_devices();
    }, 300);
  }

  // Dropdown open/close
  _open_filter_dropdown(category) {
    this.show_filter_dropdown = category;
  }

  _close_filter_dropdown() {
    this.show_filter_dropdown = null;
  }

  // Mobile bottom sheet methods
  _open_mobile_filter_sheet() {
    // Deep copy active_filters into staged_filters
    this.staged_filters = JSON.parse(JSON.stringify(this.active_filters));
    this.show_mobile_filter_sheet = true;
  }

  _apply_mobile_filters() {
    this.active_filters = this.staged_filters;
    this.staged_filters = null;
    this.show_mobile_filter_sheet = false;
    this._on_filter_changed();
  }

  _cancel_mobile_filters() {
    this.staged_filters = null;
    this.show_mobile_filter_sheet = false;
    // No change to active_filters, no API call
  }

  _toggle_staged_filter_value(category, value) {
    const updated = { ...this.staged_filters };
    const list = updated[category] || [];
    if (list.includes(value)) {
      updated[category] = list.filter(v => v !== value);
    } else {
      updated[category] = [...list, value];
    }
    this.staged_filters = updated;
  }

  _clear_staged_filters() {
    this.staged_filters = { ...DEFAULT_FILTERS };
  }

  // Load filter options from backend (called once on connectedCallback)
  async _load_filter_options() {
    if (this._filter_options_fetch_promise) {
      return this._filter_options_fetch_promise;
    }
    this.filter_options_loading = true;
    this.filter_options_error = null;

    this._filter_options_fetch_promise = this.hass.connection.sendMessagePromise({
      type: GET_FILTER_OPTIONS_COMMAND,
    }).then(result => {
      this.filter_options = result;
      this.filter_options_loading = false;
      // Validate and clean persisted filters
      if (this.active_filters && this.filter_options) {
        const cleaned = { ...this.active_filters };
        const options = this.filter_options;

        if (options.manufacturers && cleaned.manufacturer.length > 0) {
          cleaned.manufacturer = cleaned.manufacturer.filter(v => options.manufacturers.includes(v));
        }
        if (options.device_classes && cleaned.device_class.length > 0) {
          cleaned.device_class = cleaned.device_class.filter(v => options.device_classes.includes(v));
        }
        if (options.statuses && cleaned.status.length > 0) {
          cleaned.status = cleaned.status.filter(v => options.statuses.includes(v));
        }
        if (options.areas && cleaned.area.length > 0) {
          const areaNames = options.areas.map(a => a.name);
          cleaned.area = cleaned.area.filter(v => areaNames.includes(v));
        }

        if (JSON.stringify(cleaned) !== JSON.stringify(this.active_filters)) {
          this.active_filters = cleaned;
          this._save_filters_to_localstorage();
        }
      }
      this._filter_options_fetch_promise = null;
    }).catch(err => {
      this.filter_options_error = err.message || "Failed to load filter options";
      this.filter_options_loading = false;
      this._filter_options_fetch_promise = null;
    });

    return this._filter_options_fetch_promise;
  }

  // Retry loading filter options (called from [Retry] button in dropdown error state)
  _retry_filter_options() {
    this.filter_options_error = null;
    this._load_filter_options();
  }

  // Check if any filter category has active selections
  _has_active_filters() {
    const f = this.active_filters;
    return (f.manufacturer.length + f.device_class.length + f.status.length + f.area.length) > 0;
  }

  // Count total active filter values across all categories
  _active_filter_count() {
    const f = this.active_filters;
    return f.manufacturer.length + f.device_class.length + f.status.length + f.area.length;
  }

  // Check if current empty state is due to filters (not "no devices at all")
  _is_filtered_empty_state() {
    return this.battery_devices.length === 0
      && !this.isLoading
      && this._has_active_filters();
  }

  // Render filter bar with category buttons
  _render_filter_bar() {
    if (this.is_mobile) {
      // Mobile: single Filter button with counter
      return html`
        <div class="filter-bar">
          <button
            class="filter-trigger ${this._active_filter_count() > 0 ? 'active' : ''}"
            @click="${this._open_mobile_filter_sheet}"
            aria-label="Filter options, ${this._active_filter_count()} active"
            aria-haspopup="dialog">
            🔍 Filter${this._active_filter_count() > 0 ? ` (${this._active_filter_count()})` : ''}
          </button>
        </div>
      `;
    } else {
      // Desktop: filter buttons for each category
      return html`
        <div class="filter-bar" role="toolbar" aria-label="Filter controls">
          ${Object.keys(FILTER_CATEGORY_LABELS).map(category => {
            const isActive = this.active_filters[category] && this.active_filters[category].length > 0;
            return html`
              <div style="position: relative;">
                <button
                  class="filter-btn ${isActive ? 'active' : ''}"
                  @click="${() => this.show_filter_dropdown === category ? this._close_filter_dropdown() : this._open_filter_dropdown(category)}"
                  aria-expanded="${this.show_filter_dropdown === category}"
                  aria-haspopup="listbox">
                  ${FILTER_CATEGORY_LABELS[category]}
                  ${isActive ? ` (${this.active_filters[category].length})` : ''}
                </button>
                ${this.show_filter_dropdown === category ? this._render_filter_dropdown(category) : ''}
              </div>
            `;
          })}
        </div>
      `;
    }
  }

  // Render dropdown menu for a filter category
  _render_filter_dropdown(category) {
    if (!this.filter_options) {
      return html`
        <div class="filter-dropdown">
          <div style="padding: 12px; text-align: center; color: var(--vb-text-secondary); font-size: 12px;">
            Loading...
          </div>
        </div>
      `;
    }

    if (this.filter_options_error) {
      return html`
        <div class="filter-dropdown">
          <div style="padding: 12px; color: var(--vb-color-critical); font-size: 12px;">
            Error loading options
          </div>
          <button
            class="button"
            @click="${this._retry_filter_options}"
            style="width: calc(100% - 16px); margin: 8px;">
            Retry
          </button>
        </div>
      `;
    }

    let options = [];
    if (category === 'manufacturer' && this.filter_options.manufacturers) {
      options = this.filter_options.manufacturers;
    } else if (category === 'device_class' && this.filter_options.device_classes) {
      options = this.filter_options.device_classes;
    } else if (category === 'status' && this.filter_options.statuses) {
      options = this.filter_options.statuses;
    } else if (category === 'area' && this.filter_options.areas) {
      options = this.filter_options.areas.map(a => a.name);
    }

    if (options.length === 0) {
      return html`
        <div class="filter-dropdown">
          <div style="padding: 12px; color: var(--vb-text-secondary); font-size: 12px;">
            No options available
          </div>
        </div>
      `;
    }

    const activeValues = this.active_filters[category] || [];

    return html`
      <div class="filter-dropdown" role="listbox">
        ${options.map(option => html`
          <label class="filter-option">
            <input
              type="checkbox"
              ?checked="${activeValues.includes(option)}"
              @change="${() => this._toggle_filter_value(category, option)}"
              role="option"
              aria-selected="${activeValues.includes(option)}">
            <span>${option}</span>
          </label>
        `)}
      </div>
    `;
  }

  // Render active filter chips row
  _render_chip_row() {
    const allFilters = [
      ...(this.active_filters.manufacturer || []).map(v => ({ category: 'manufacturer', value: v })),
      ...(this.active_filters.device_class || []).map(v => ({ category: 'device_class', value: v })),
      ...(this.active_filters.status || []).map(v => ({ category: 'status', value: v })),
      ...(this.active_filters.area || []).map(v => ({ category: 'area', value: v })),
    ];

    return html`
      <div class="chip-row" aria-label="Active filters">
        ${allFilters.map(filter => html`
          <div class="filter-chip">
            ${filter.value}
            <button
              @click="${() => this._remove_filter_chip(filter.category, filter.value)}"
              aria-label="Remove ${FILTER_CATEGORY_LABELS[filter.category]} filter: ${filter.value}">
              ✕
            </button>
          </div>
        `)}
        <button class="chip-clear-all" @click="${this._clear_all_filters}">
          Clear all
        </button>
      </div>
    `;
  }

  // Render mobile bottom sheet
  _render_mobile_filter_sheet() {
    if (!this.filter_options) {
      return html`
        <div class="sheet-overlay" @click="${this._cancel_mobile_filters}">
          <div class="bottom-sheet" @click="${(e) => e.stopPropagation()}">
            <div style="text-align: center; padding: 32px 16px; color: var(--vb-text-secondary);">
              Loading filters...
            </div>
          </div>
        </div>
      `;
    }

    return html`
      <div class="sheet-overlay" @click="${this._cancel_mobile_filters}">
        <div class="bottom-sheet" @click="${(e) => e.stopPropagation()}" role="dialog" aria-modal="true">
          <div class="sheet-header">
            <h2>Filters</h2>
            <button class="modal-close" @click="${this._cancel_mobile_filters}">✕</button>
          </div>

          ${Object.keys(FILTER_CATEGORY_LABELS).map(category => {
            let options = [];
            if (category === 'manufacturer' && this.filter_options.manufacturers) {
              options = this.filter_options.manufacturers;
            } else if (category === 'device_class' && this.filter_options.device_classes) {
              options = this.filter_options.device_classes;
            } else if (category === 'status' && this.filter_options.statuses) {
              options = this.filter_options.statuses;
            } else if (category === 'area' && this.filter_options.areas) {
              options = this.filter_options.areas.map(a => a.name);
            }

            const stagedValues = this.staged_filters[category] || [];

            return html`
              <div class="sheet-section">
                <div class="sheet-section-title">${FILTER_CATEGORY_LABELS[category]}</div>
                ${options.map(option => html`
                  <label class="filter-option">
                    <input
                      type="checkbox"
                      ?checked="${stagedValues.includes(option)}"
                      @change="${() => this._toggle_staged_filter_value(category, option)}">
                    <span>${option}</span>
                  </label>
                `)}
              </div>
            `;
          })}

          <div class="sheet-buttons">
            <button class="button" @click="${this._apply_mobile_filters}" style="flex: 1;">
              Apply Filters
            </button>
            <button class="button" @click="${this._cancel_mobile_filters}" style="flex: 1; background-color: var(--vb-text-disabled);">
              Cancel
            </button>
          </div>
        </div>
      </div>
    `;
  }

  // Render filtered empty state
  _render_filtered_empty_state() {
    return html`
      <div class="empty-state">
        <div class="empty-state-icon">🔍</div>
        <div class="empty-state-text">No devices match your filters</div>
        <small style="color: var(--vb-text-secondary); max-width: 400px; line-height: 1.5;">
          Try adjusting your filter criteria or check that your devices are configured correctly.
        </small>
        <div style="display: flex; gap: 8px; margin-top: 16px; flex-wrap: wrap; justify-content: center;">
          <button class="button" @click=${this._clear_all_filters}>
            🔄 Clear Filters
          </button>
          <button class="button" @click=${this._load_devices}>
            🔄 Refresh
          </button>
        </div>
      </div>
    `;
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

    // Observe the bottom sentinel (min-height prevents layout shifts)
    const sentinel = document.createElement("div");
    sentinel.style.minHeight = "1px";
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
          // Sprint 5: Include active filters
          filter_manufacturer: this.active_filters.manufacturer || [],
          filter_device_class: this.active_filters.device_class || [],
          filter_status: this.active_filters.status || [],
          filter_area: this.active_filters.area || [],
        },
      });

      if (result) {
        this.battery_devices = [...this.battery_devices, ...(result.devices || [])];
        this.current_cursor = result.next_cursor || null;
        this.has_more = result.has_more || false;
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

      if (!result) {
        throw new Error("Invalid subscription response");
      }

      this.subscription_id = result.subscription_id;
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
    // Sprint 4: Primary source - hass.themes.darkMode (authoritative HA theme setting)
    if (this.hass?.themes?.darkMode !== undefined) {
      return this.hass.themes.darkMode ? 'dark' : 'light';
    }

    // Fallback 1: DOM attribute (legacy, from older HA versions)
    const domTheme = document.documentElement.getAttribute('data-theme');
    if (domTheme === 'dark' || domTheme === 'dark-theme') {
      return 'dark';
    }

    // Fallback 2: OS preference (system-wide dark mode)
    if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
      return 'dark';
    }

    // Default: light mode
    return 'light';
  }

  _apply_theme(theme) {
    // Sprint 4: Apply theme to DOM and trigger re-render
    const newTheme = theme || 'light';
    document.documentElement.setAttribute('data-theme', newTheme);
    this.current_theme = newTheme;
    // Request update to apply CSS custom properties
    this.requestUpdate();
  }

  _setup_theme_listener() {
    // Sprint 4: Listen to hass_themes_updated event for real-time theme changes
    if (!this.hass?.connection) {
      return;
    }

    // Arrow function to preserve 'this' context
    this._themeListener = () => {
      const newTheme = this._detect_theme();
      if (newTheme !== this.current_theme) {
        this._apply_theme(newTheme);
      }
    };

    this.hass.connection.addEventListener('hass_themes_updated', this._themeListener);
  }

  _setup_theme_observer() {
    // Sprint 3 legacy: MutationObserver for older HA versions (deprecated)
    // Kept as fallback if hass.connection unavailable
    if (this.theme_observer) {
      this.theme_observer.disconnect();
    }

    this.theme_observer = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        if (mutation.attributeName === "data-theme") {
          const newTheme = this._detect_theme();
          this._apply_theme(newTheme);
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
      if (result) {
        this.notification_prefs = {
          enabled: result.enabled,
          frequency_cap_hours: result.frequency_cap_hours,
          severity_filter: result.severity_filter,
          per_device: result.per_device || {},
        };
        this.notification_history = result.notification_history || [];
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
    if (!this.hass || !this.hass.callWS) {
      throw new Error("Home Assistant WebSocket not available");
    }
    // Flatten nested 'data' field — HA callWS expects params at the top level,
    // not wrapped in a data object. Also strip null/undefined values to avoid
    // schema validation errors (e.g., cursor: null fails vol.Optional("cursor"): str)
    const { data, ...rest } = message;
    const merged = data ? { ...rest, ...data } : rest;
    const flatMessage = Object.fromEntries(
      Object.entries(merged).filter(([_, v]) => v !== null && v !== undefined)
    );
    return this.hass.callWS(flatMessage);
  }

  _on_window_resize() {
    this.is_mobile = window.innerWidth < 768;
  }
}

customElements.define("vulcan-brownout-panel", VulcanBrownoutPanel);
