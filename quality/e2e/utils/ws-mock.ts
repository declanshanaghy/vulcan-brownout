/**
 * WebSocket mock helper for intercepting and mocking HA API calls
 * Simplified for v6: only query_entities (no params) and subscribe
 *
 * In staging mode (STAGING_MODE=true), all methods become no-ops.
 */

import { Page, WebSocketRoute } from '@playwright/test';
import { Device } from './device-factory';

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
  private isStaging: boolean;

  constructor(page: Page) {
    this.page = page;
    this.isStaging = process.env.STAGING_MODE === 'true';
    if (!this.isStaging) {
      this.setupDefaultHandlers();
    }
  }

  async setup(): Promise<void> {
    if (this.isStaging) return;
    await this.page.routeWebSocket('/api/websocket', async (route) => {
      await this.handleWebSocket(route);
    });
  }

  private async handleWebSocket(route: WebSocketRoute): Promise<void> {
    const server = await route.connectToServer();

    route.onMessage((message) => {
      const data = JSON.parse(message) as HAWebSocketMessage;

      if (this.messageHandlers.has(data.type)) {
        const handler = this.messageHandlers.get(data.type)!;
        const response = handler(data);
        if (response) {
          route.send(JSON.stringify(response));
        }
      } else {
        server.send(message);
      }
    });

    server.onMessage((message) => {
      route.send(message);
    });

    route.onClose(() => {
      server.close();
    });
  }

  private setupDefaultHandlers(): void {
    this.registerHandler('auth_required', () => ({
      type: 'auth_required',
      ha_version: '2024.2.0',
    }));

    this.registerHandler('auth', () => ({
      type: 'auth_ok',
      ha_version: '2024.2.0',
    }));

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

  registerHandler(
    messageType: string,
    handler: (data: HAWebSocketMessage) => HAWebSocketResponse | null
  ): void {
    if (this.isStaging) return;
    this.messageHandlers.set(messageType, handler);
  }

  /**
   * Mock vulcan-brownout/query_entities response (no params in v6)
   */
  mockQueryEntities(entities: Device[]): void {
    if (this.isStaging) return;
    this.registerHandler('vulcan-brownout/query_entities', (data) => ({
      id: data.id,
      type: 'result',
      success: true,
      result: {
        entities,
        total: entities.length,
      },
    }));
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
}
