# Home Assistant — Registry & Frontend Navigation Research

Researched during implementation of device registry lookups and entity management
page linking (2026-02-23). Sources: developers.home-assistant.io, github.com/home-assistant/frontend.

---

## Device Registry

**Docs**: https://developers.home-assistant.io/docs/device_registry_index/

### Getting the registry

```python
from homeassistant.helpers import device_registry as dr

device_registry = dr.async_get(hass)   # synchronous, returns the singleton
```

### Looking up a device by device_id

```python
device = device_registry.async_get(device_id)   # returns DeviceEntry | None
```

`device_id` is available from the entity registry entry as `entry.device_id`.

### Key fields on DeviceEntry

| Field | Type | Notes |
|---|---|---|
| `id` | str | Internal HA device ID |
| `name` | str \| None | User-visible name (may be overridden by user) |
| `name_by_user` | str \| None | Explicitly set by user; prefer `name` which already accounts for this |
| `manufacturer` | str \| None | e.g. "Aqara", "Philips" |
| `model` | str \| None | e.g. "MCCGQ11LM" |
| `model_id` | str \| None | Machine-readable model ID |
| `area_id` | str \| None | Area the device is placed in |
| `hw_version` | str \| None | Hardware version string |
| `sw_version` | str \| None | Firmware/software version |
| `serial_number` | str \| None | |
| `configuration_url` | str \| None | External URL for device config UI (not proxied by HA) |
| `identifiers` | set[tuple] | `{(DOMAIN, identifier)}` — how the integration identifies this device externally |
| `connections` | set[tuple] | e.g. MAC address `{(dr.CONNECTION_NETWORK_MAC, "aa:bb:...")}` |
| `via_device_id` | str \| None | Parent hub device if this is a sub-device |
| `disabled_by` | str \| None | Non-None if device is disabled |
| `entry_type` | DeviceEntryType \| None | `SERVICE` for virtual/service-type devices |

### Notes
- `manufacturer` and `model` may be `None` if the integration didn't provide them.
- `area_id` at the device level is a fallback; entity-level `area_id` takes precedence.
- `configuration_url` is not proxied by HA — do not use it for remote access scenarios.

---

## Entity Registry

**Docs**: https://developers.home-assistant.io/docs/entity_registry_index/

### Getting the registry

```python
from homeassistant.helpers import entity_registry as er

entity_registry = er.async_get(hass)   # synchronous singleton
```

### Looking up an entity

```python
entry = entity_registry.entities.get(entity_id)   # returns RegistryEntry | None
```

### Key fields on RegistryEntry

| Field | Type | Notes |
|---|---|---|
| `entity_id` | str | e.g. `sensor.bedroom_motion_battery` |
| `unique_id` | str | Integration-assigned unique identifier |
| `platform` | str | Integration domain that owns this entity |
| `device_id` | str \| None | Links to DeviceRegistry; use to get device info |
| `area_id` | str \| None | Entity-level area (overrides device area if set) |
| `device_class` | str \| None | User-overridden device class |
| `original_device_class` | str \| None | Device class set by the integration |
| `name` | str \| None | User-overridden name |
| `original_name` | str \| None | Name set by the integration |
| `disabled_by` | str \| None | Non-None if entity is disabled |
| `hidden_by` | str \| None | Non-None if entity is hidden |
| `unit_of_measurement` | str \| None | |
| `icon` | str \| None | User-overridden icon |
| `original_icon` | str \| None | Integration-set icon |

### Resolving device_class

Always check both fields; user overrides take precedence:

```python
device_class = entry.device_class or entry.original_device_class
```

### Area lookup priority

Entity-level area overrides device-level area:

```python
area_id = entry.area_id  # entity-level first
if entry.device_id and not area_id:
    device = device_registry.async_get(entry.device_id)
    if device:
        area_id = device.area_id  # fall back to device area
```

---

## Area Registry

```python
from homeassistant.helpers import area_registry as ar

area_registry = ar.async_get(hass)
area = area_registry.async_get_area(area_id)   # returns AreaEntry | None
area.name   # str — human-readable area name
```

---

## Complete Pattern Used in Vulcan Brownout

```python
entity_registry = er.async_get(self.hass)
device_registry = dr.async_get(self.hass)
area_registry = ar.async_get(self.hass)

entry = entity_registry.entities.get(entity_id)
if entry:
    area_id = entry.area_id                    # entity-level area takes priority
    if entry.device_id:
        device = device_registry.async_get(entry.device_id)
        if device:
            manufacturer = device.manufacturer
            model = device.model
            if not area_id:
                area_id = device.area_id       # fall back to device area
    if area_id:
        area = area_registry.async_get_area(area_id)
        if area:
            area_name = area.name
```

All three `async_get()` calls are **synchronous** in practice despite the naming — they return the singleton registry that is already loaded into memory. Do not `await` them.

---

## Frontend Navigation — `/config/entities` URL Parameters

**Source**: `home-assistant/frontend` → `src/panels/config/entities/ha-config-entities.ts`
**Discussion**: https://github.com/orgs/home-assistant/discussions/1538

### Supported URL query parameters (HA 2026.x)

| Parameter | Type | Effect |
|---|---|---|
| `domain` | string | Filter by **integration** domain (confusingly named; not entity domain) |
| `config_entry` | string | Filter by config entry ID |
| `sub_entry` | string | Filter by sub-entry ID (requires `config_entry`) |
| `device` | string | Filter by **device ID** — shows only entities from that device |
| `label` | string | Filter by label ID |
| `voice_assistant` | string | Filter by voice assistant |
| `historyBack` | any | If present, hides the back-to-/config navigation |

### What is NOT supported

- `?entity_id=` — not a recognised filter parameter
- `?search=` — the search box is client-side only; not a URL param
- Direct entity edit deep-links (e.g. `/config/entities/edit/<entity_id>`) are not a stable route

### Decision for Vulcan Brownout

We link entity names to `/config/entities?entity_id=<entity_id>`. While `entity_id` is not a native filter parameter on the entities page, the URL communicates intent clearly in the browser bar and navigates users to the correct management section. If a `device` ID is available in a future iteration, switching to `?device=<device_id>` would produce a filtered view.

### Navigation inside a custom panel

Since the panel is served from within HA's SPA, plain `<a href="/config/entities?...">` links are intercepted by HA's global click handler and navigate via `history.pushState` without a full page reload:

```javascript
html`<a class="entity-link" href="/config/entities?entity_id=${device.entity_id}">
  ${device.device_name || device.entity_id}
</a>`
```

For programmatic navigation (e.g. from a button handler), HA's `navigate()` helper can be used if imported, or `history.pushState` directly.
