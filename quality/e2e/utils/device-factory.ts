/**
 * Device factory for generating mock device data
 * Simplified for v6: all shown devices are below 15% threshold (critical)
 */

export interface Device {
  entity_id: string;
  device_name: string;
  battery_level: number;
  status: 'critical';
  last_changed: string;
  last_updated: string;
}

export interface DeviceListResponse {
  devices: Device[];
  total: number;
}

/**
 * Generate a single low-battery device with optional overrides
 */
export function generateDevice(overrides?: Partial<Device>): Device {
  const id = Math.random().toString(36).substring(7);
  const batteryLevel = Math.floor(Math.random() * 14); // 0-13%

  return {
    entity_id: `sensor.device_${id}_battery`,
    device_name: `Device ${id.toUpperCase()}`,
    battery_level: batteryLevel,
    status: 'critical',
    last_changed: new Date(Date.now() - Math.random() * 86400000).toISOString(),
    last_updated: new Date(Date.now() - Math.random() * 3600000).toISOString(),
    ...overrides,
  };
}

/**
 * Generate a list of low-battery devices
 */
export function generateDeviceList(
  _pageNum: number = 0,
  count: number = 5,
): Device[] {
  const devices: Device[] = [];
  for (let i = 0; i < count; i++) {
    devices.push({
      entity_id: `sensor.device_${i}_battery`,
      device_name: `Device ${i}`,
      battery_level: Math.floor(Math.random() * 14), // 0-13%
      status: 'critical',
      last_changed: new Date(Date.now() - Math.random() * 86400000).toISOString(),
      last_updated: new Date(Date.now() - Math.random() * 3600000).toISOString(),
    });
  }
  return devices;
}

/**
 * Generate devices with specific names
 */
export function generateDevicesByName(names: string[]): Device[] {
  return names.map((name, idx) => ({
    entity_id: `sensor.device_named_${idx}_battery`,
    device_name: name,
    battery_level: Math.floor(Math.random() * 14),
    status: 'critical' as const,
    last_changed: new Date().toISOString(),
    last_updated: new Date().toISOString(),
  }));
}
