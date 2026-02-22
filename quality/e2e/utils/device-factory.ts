/**
 * Device factory for generating mock device data
 * Provides realistic device data for testing without hitting real HA API
 */

export interface Device {
  entity_id: string;
  device_name: string;
  battery_level: number;
  available: boolean;
  status: 'critical' | 'warning' | 'healthy' | 'unavailable';
  last_changed: string;
  last_updated: string;
}

export interface DeviceListResponse {
  devices: Device[];
  device_statuses: { critical: number; warning: number; healthy: number; unavailable: number };
  next_cursor: string | null;
  has_more: boolean;
}

const DEVICE_STATUSES = ['critical', 'warning', 'healthy', 'unavailable'] as const;

/**
 * Determine status based on battery level
 */
function getStatusFromBattery(level: number, available: boolean): Device['status'] {
  if (!available) return 'unavailable';
  if (level <= 10) return 'critical';
  if (level <= 20) return 'warning';
  return 'healthy';
}

/**
 * Generate a single device with optional overrides
 */
export function generateDevice(overrides?: Partial<Device>): Device {
  const id = Math.random().toString(36).substring(7);
  const batteryLevel = Math.floor(Math.random() * 100);
  const available = Math.random() > 0.1;
  const status = getStatusFromBattery(batteryLevel, available);

  return {
    entity_id: `sensor.device_${id}_battery`,
    device_name: `Device ${id.toUpperCase()}`,
    battery_level: batteryLevel,
    available,
    status,
    last_changed: new Date(Date.now() - Math.random() * 86400000).toISOString(),
    last_updated: new Date(Date.now() - Math.random() * 3600000).toISOString(),
    ...overrides,
  };
}

/**
 * Generate a list of devices for a specific page
 */
export function generateDeviceList(
  pageNum: number,
  perPage: number = 20,
  options?: { seed?: number; statusOverride?: Device['status'] }
): Device[] {
  const devices: Device[] = [];
  const startId = pageNum * perPage;

  for (let i = 0; i < perPage; i++) {
    const id = startId + i;
    let batteryLevel = Math.floor(50 + Math.random() * 50);
    const available = Math.random() > 0.1;

    // Apply status override if provided
    if (options?.statusOverride) {
      if (options.statusOverride === 'critical') batteryLevel = Math.floor(Math.random() * 10);
      if (options.statusOverride === 'warning') batteryLevel = 10 + Math.floor(Math.random() * 10);
      if (options.statusOverride === 'healthy') batteryLevel = 50 + Math.floor(Math.random() * 50);
    }

    devices.push({
      entity_id: `sensor.device_${id}_battery`,
      device_name: `Device ${id}`,
      battery_level: batteryLevel,
      available: options?.statusOverride === 'unavailable' ? false : available,
      status: getStatusFromBattery(batteryLevel, available),
      last_changed: new Date(Date.now() - Math.random() * 86400000).toISOString(),
      last_updated: new Date(Date.now() - Math.random() * 3600000).toISOString(),
    });
  }

  return devices;
}

/**
 * Generate device list response with pagination info
 */
export function generateDeviceListResponse(
  pageNum: number = 0,
  perPage: number = 20,
  totalPages: number = 3
): DeviceListResponse {
  const devices = generateDeviceList(pageNum, perPage);

  // Calculate device_statuses
  const statuses = { critical: 0, warning: 0, healthy: 0, unavailable: 0 };
  devices.forEach(d => {
    statuses[d.status as keyof typeof statuses]++;
  });

  return {
    devices,
    device_statuses: statuses,
    next_cursor: pageNum < totalPages - 1 ? `cursor_${pageNum + 1}` : null,
    has_more: pageNum < totalPages - 1,
  };
}

/**
 * Generate devices with specific names (useful for sorting/filtering tests)
 */
export function generateDevicesByName(names: string[]): Device[] {
  return names.map((name, idx) => {
    const batteryLevel = Math.floor(50 + Math.random() * 50);
    return {
      entity_id: `sensor.device_named_${idx}_battery`,
      device_name: name,
      battery_level: batteryLevel,
      available: true,
      status: getStatusFromBattery(batteryLevel, true),
      last_changed: new Date().toISOString(),
      last_updated: new Date().toISOString(),
    };
  });
}

/**
 * Generate devices with specific battery levels (useful for level sorting tests)
 */
export function generateDevicesByBatteryLevel(
  levels: { name: string; level: number }[]
): Device[] {
  return levels.map(({ name, level }, idx) => ({
    entity_id: `sensor.device_level_${idx}_battery`,
    device_name: name,
    battery_level: level,
    available: level > 0,
    status: getStatusFromBattery(level, level > 0),
    last_changed: new Date().toISOString(),
    last_updated: new Date().toISOString(),
  }));
}

/**
 * Generate a critical device (low battery)
 */
export function generateCriticalDevice(): Device {
  return generateDevice({
    device_name: 'Critical Battery Device',
    battery_level: 5,
    available: true,
    status: 'critical',
  });
}

/**
 * Generate a healthy device (full battery)
 */
export function generateHealthyDevice(): Device {
  return generateDevice({
    device_name: 'Healthy Battery Device',
    battery_level: 95,
    available: true,
    status: 'healthy',
  });
}

/**
 * Generate a mixed list with various battery levels for threshold testing
 */
export function generateMixedBatteryDevices(count: number = 10): Device[] {
  const devices: Device[] = [];
  for (let i = 0; i < count; i++) {
    const level = Math.floor((i / count) * 100);
    const available = level > 10;
    devices.push(
      generateDevice({
        device_name: `Device ${i} (${level}%)`,
        battery_level: level,
        available,
        status: getStatusFromBattery(level, available),
      })
    );
  }
  return devices;
}
