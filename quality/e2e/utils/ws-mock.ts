/**
 * WebSocket mock helper for intercepting and mocking HA API calls
 * Handles the HA WebSocket authentication flow and routes custom commands
 *
 * In staging mode (STAGING_MODE=true), all methods become no-ops and
 * the real HA WebSocket backend handles all commands directly.
 */

import { Page, WebSocketRoute } from '@playwright/test';
import { Device, DeviceListResponse } from './device-factory';

export interface HAWebSocketMessage {
  id?: number;
  type: string;
  [key: string]: any;
}

export interface HAWebSocketResponse {
  id?: number;
  type: string;
  success?: boolean;
  [key: string]: any;
}

export class WebSocketMock {
  private page: Page;
  private messageHandlers: Map<string, (data: any) => any> = new Map();
  private messageId = 0;
  private isStaging: boolean;

  constructor(page: Page) {
    this.page = page;
    this.isStaging = process.env.STAGING_MODE === 'true';
    if (!this.isStaging) {
      this.setupDefaultHandlers();
    }
  }

  /**
   * Setup WebSocket interception (no-op in staging mode)
   */
  async setup(): Promise<void> {
    if (this.isStaging) return;
    await this.page.routeWebSocket('/api/websocket', async (route) => {
      await this.handleWebSocket(route);
    });
  }

  /**
   * Handle WebSocket connection and messages
   */
  private async handleWebSocket(route: WebSocketRoute): Promise<void> {
    // For auth flow, we need to proxy to the real server
    // But intercept vulcan-brownout/* commands and respond with mocks
    const server = await route.connectToServer();

    route.onMessage((message) => {
      const data = JSON.parse(message) as HAWebSocketMessage;

      // Check if this is a vulcan-brownout command
      if (this.messageHandlers.has(data.type)) {
        const handler = this.messageHandlers.get(data.type)!;
        const response = handler(data);

        if (response) {
          // Send mock response to client, don't pass to server
          route.send(JSON.stringify(response));
        }
      } else {
        // Pass through to real server for HA built-in commands
        server.send(message);
      }
    });

    // Forward server messages to client
    server.onMessage((message) => {
      route.send(message);
    });

    route.onClose(() => {
      server.close();
    });
  }

  /**
   * Setup default HA handlers (auth flow, etc.)
   */
  private setupDefaultHandlers(): void {
    // HA sends auth_required on connection
    this.registerHandler('auth_required', () => ({
      type: 'auth_required',
      ha_version: '2024.2.0',
    }));

    // Client sends auth with token
    this.registerHandler('auth', (data) => {
      return {
        type: 'auth_ok',
        ha_version: '2024.2.0',
      };
    });

    // Generic result for unhandled messages
    this.registerHandler('subscribe_events', (data) => ({
      id: data.id,
      type: 'result',
      success: true,
    }));

    this.registerHandler('get_panels', (data) => ({
      id: data.id,
      type: 'result',
      success: true,
      result: {
        vulcan_brownout: {
          component_name: 'vulcan_brownout',
          config: {},
          icon: 'mdi:battery-alert-variant-outline',
          title: 'Vulcan Brownout',
          url_path: 'vulcan-brownout',
        },
      },
    }));
  }

  /**
   * Register a message handler (no-op in staging mode)
   */
  registerHandler(
    messageType: string,
    handler: (data: HAWebSocketMessage) => HAWebSocketResponse | null
  ): void {
    if (this.isStaging) return;
    this.messageHandlers.set(messageType, handler);
  }

  /**
   * Mock vulcan-brownout/query_devices response with optional filtering
   */
  mockQueryDevices(devices: Device[]): void {
    if (this.isStaging) return;
    this.registerHandler('vulcan-brownout/query_devices', (data) => {
      let filtered = devices;

      // Apply filters if provided
      if (data.filter_manufacturer && data.filter_manufacturer.length > 0) {
        filtered = filtered.filter(d =>
          data.filter_manufacturer.includes(d.manufacturer)
        );
      }

      if (data.filter_device_class && data.filter_device_class.length > 0) {
        // All test devices have device_class 'battery'
        filtered = filtered.filter(d =>
          data.filter_device_class.includes('battery')
        );
      }

      if (data.filter_status && data.filter_status.length > 0) {
        filtered = filtered.filter(d =>
          data.filter_status.includes(d.status)
        );
      }

      if (data.filter_area && data.filter_area.length > 0) {
        filtered = filtered.filter(d =>
          data.filter_area.includes(d.area_name)
        );
      }

      // Calculate device_statuses for filtered results
      const statuses = { critical: 0, warning: 0, healthy: 0, unavailable: 0 };
      filtered.forEach(d => {
        statuses[d.status as keyof typeof statuses]++;
      });

      return {
        id: data.id,
        type: 'result',
        success: true,
        result: {
          devices: filtered,
          device_statuses: statuses,
          next_cursor: null,
          has_more: false,
        },
      };
    });
  }

  /**
   * Mock device list responses for pagination using cursor-based pagination
   */
  mockDevicePages(pages: DeviceListResponse[]): void {
    if (this.isStaging) return;
    // Create a map: cursor -> page response
    const cursorMap = new Map<string | null, DeviceListResponse>();
    pages.forEach((page, index) => {
      cursorMap.set(index === 0 ? null : `cursor_${index}`, page);
    });

    this.registerHandler('vulcan-brownout/query_devices', (data) => {
      const cursor = data.cursor || null;
      const page = cursorMap.get(cursor);

      if (page) {
        return {
          id: data.id,
          type: 'result',
          success: true,
          result: {
            devices: page.devices,
            device_statuses: page.device_statuses,
            next_cursor: page.next_cursor,
            has_more: page.has_more,
          },
        };
      }

      return {
        id: data.id,
        type: 'result',
        success: false,
        error: 'Cursor not found',
      };
    });
  }

  /**
   * Mock sorted device response
   */
  mockSortedDevices(devices: Device[], sortKey?: string): void {
    if (this.isStaging) return;
    this.registerHandler('vulcan-brownout/query_devices', (data) => {
      // If sort parameter matches, return sorted devices
      if (!sortKey || data.sort_key === sortKey) {
        // Calculate device_statuses
        const statuses = { critical: 0, warning: 0, healthy: 0, unavailable: 0 };
        devices.forEach(d => {
          statuses[d.status as keyof typeof statuses]++;
        });

        return {
          id: data.id,
          type: 'result',
          success: true,
          result: {
            devices,
            device_statuses: statuses,
            next_cursor: null,
            has_more: false,
          },
        };
      }

      return {
        id: data.id,
        type: 'result',
        success: false,
        error: 'Sort key mismatch',
      };
    });
  }

  /**
   * Mock subscription response
   */
  mockSubscribe(subscriptionId: string): void {
    if (this.isStaging) return;
    this.registerHandler('vulcan-brownout/subscribe', (data) => ({
      id: data.id,
      type: 'result',
      success: true,
      subscription_id: subscriptionId,
    }));
  }

  /**
   * Mock notification preferences response
   */
  mockNotificationPrefs(prefs: any): void {
    if (this.isStaging) return;
    this.registerHandler('vulcan-brownout/get_notification_preferences', (data) => ({
      id: data.id,
      type: 'result',
      success: true,
      result: prefs,
    }));

    this.registerHandler('vulcan-brownout/set_notification_preferences', (data) => ({
      id: data.id,
      type: 'result',
      success: true,
      result: data.preferences,
    }));
  }

  /**
   * Mock set threshold response
   */
  mockSetThreshold(threshold: number): void {
    if (this.isStaging) return;
    this.registerHandler('vulcan-brownout/set_threshold', (data) => ({
      id: data.id,
      type: 'result',
      success: true,
      threshold: data.threshold || threshold,
    }));
  }

  /**
   * Mock get_filter_options response
   */
  mockGetFilterOptions(options?: any): void {
    if (this.isStaging) return;
    const defaultOptions = {
      manufacturers: ['Aqara', 'Philips', 'IKEA', 'Sonoff'],
      device_classes: ['battery'],
      areas: [
        { id: 'living_room', name: 'Living Room' },
        { id: 'kitchen', name: 'Kitchen' },
        { id: 'bedroom', name: 'Bedroom' },
        { id: 'office', name: 'Office' },
      ],
      statuses: ['critical', 'warning', 'healthy', 'unavailable'],
    };

    this.registerHandler('vulcan-brownout/get_filter_options', (data) => ({
      id: data.id,
      type: 'result',
      success: true,
      result: options || defaultOptions,
    }));
  }

  /**
   * Inject an event into the WebSocket (simulating server push)
   */
  async injectEvent(eventType: string, data: any): Promise<void> {
    // This would require storing the WebSocket connection reference
    // For now, events are handled via polling/query responses
  }
}
