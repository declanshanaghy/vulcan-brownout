# ADR-001: Integration Architecture

## Status: Accepted

## Context

Vulcan Brownout must integrate with Home Assistant as a custom component to provide real-time monitoring of low-battery devices and unavailable entities. We need to decide whether to implement this as:
- A standard integration using existing HA platform patterns
- A lightweight custom integration with WebSocket real-time capabilities
- A hybrid approach combining both

The integration must support:
- Configurable battery thresholds (default 15%)
- Filtering by `device_class=battery`
- Tracking of unavailable entities
- Real-time updates to a dedicated sidebar panel
- Server-side sorting and pagination

Home Assistant's constraints:
- Custom components must follow strict folder structure (`custom_components/{domain}/`)
- Platform support (sensors, switches, etc.) uses async setup patterns
- WebSocket API requires registration in the core integration
- Configuration UI flows must use `config_flow.py` and `options_flow.py`
- No persistent state between restarts unless explicitly stored in config entries

## Options Considered

### Option A: Pure Sensor Platform (Traditional HA)
Implement battery monitoring solely through custom sensor entities. Each low-battery device gets its own sensor entity tracking battery level.

**Pros:**
- Follows standard HA patterns entirely
- Native entity integration with automations
- Built-in UI discovery

**Cons:**
- Creates hundreds of sensor entities (one per device) — massive entity registry pollution
- No real-time panel updates without polling
- Pagination/sorting done on frontend (inefficient for large datasets)
- Cannot easily track availability without extra entities
- Does not match product requirements for a dedicated panel

### Option B: Custom Integration with WebSocket API + Sidebar Panel
Implement as a lightweight custom integration with:
- Backend Python service managing battery monitoring state
- WebSocket API for real-time frontend communication
- Custom sidebar panel for dedicated UI
- Server-side filtering, sorting, pagination

**Pros:**
- No entity pollution — monitoring state lives in the integration, not the entity registry
- Real-time WebSocket communication matches product requirements exactly
- Server-side processing offloads heavy lifting from frontend
- Dedicated panel provides custom UX not possible with standard entities
- Matches HA's `panel_custom` design pattern
- Can query all entities without creating new ones

**Cons:**
- More complex than standard sensors
- Requires WebSocket API knowledge
- Frontend development needed

### Option C: Hybrid — Sensor Platform + WebSocket Panel
Create both sensor entities AND a dedicated panel with WebSocket.

**Pros:**
- Compatible with existing automations
- Panel provides dedicated UX

**Cons:**
- Defeats purpose of avoiding entity pollution
- Doubles maintenance burden
- Confusing to users (duplicate data sources)
- Against product design principle of separation of concerns

## Decision

**Choose Option B: Custom Integration with WebSocket API + Sidebar Panel**

Vulcan Brownout will be a lightweight custom integration with:

1. **Backend (`__init__.py`, `websocket_api.py`):**
   - Registers a WebSocket command handler for real-time battery data queries
   - Maintains in-memory cache of battery device states (refreshed on state change)
   - Implements server-side filtering by `device_class=battery` and threshold
   - Handles pagination and sorting (limit, offset, sort_key, sort_order)
   - No persistent sensor entities in the entity registry

2. **Configuration (`config_flow.py`):**
   - User sets battery threshold (default 15%)
   - User selects which device classes to track (battery, temperature sensors, etc.)
   - Options flow for runtime changes without restart

3. **Frontend (`vulcan-brownout-panel.js`, `styles.css`):**
   - Custom sidebar panel registered via `panel_custom`
   - Connects to WebSocket API
   - Receives paginated/sorted data from backend
   - Displays battery status with infinite scroll support
   - No sorting/pagination logic in JS — delegates to backend

4. **Project Structure:**
   ```
   custom_components/vulcan_brownout/
   ├── __init__.py              # Integration setup, WebSocket registration
   ├── manifest.json            # Metadata, requires HA 2023.12+
   ├── const.py                 # Domain, defaults (DOMAIN='vulcan_brownout', DEFAULT_THRESHOLD=15)
   ├── config_flow.py           # Configuration UI
   ├── websocket_api.py         # WebSocket command handlers
   ├── battery_monitor.py       # Core battery monitoring logic (entity filtering, state tracking)
   ├── translations/
   │   └── en.json              # i18n strings
   └── frontend/
       ├── vulcan-brownout-panel.js    # Lit element custom sidebar panel
       └── styles.css
   ```

## Consequences

### Positive

1. **Minimal Entity Footprint:** No creation of sensor entities — clean entity registry.
2. **Real-Time Updates:** WebSocket API enables instant battery status updates without polling.
3. **Scalable to Large Installations:** Server-side pagination and filtering handle thousands of entities efficiently.
4. **Dedicated UX:** Sidebar panel provides focused, distraction-free monitoring experience.
5. **Home Assistant Best Practice:** Follows HA's `panel_custom` pattern used by other integrations (e.g., Lovelace, Settings).
6. **Separation of Concerns:** Backend manages data, frontend manages display — clean boundaries.

### Negative

1. **No Automation Integration:** Battery state is not exposed as entities, so users cannot directly trigger automations based on low battery.
   - *Mitigation:* This is by design. For automation, users should use existing entity states or create helpers from the battery data returned by the panel.

2. **WebSocket-Dependent:** Panel requires active WebSocket connection. If it drops, panel loses real-time updates.
   - *Mitigation:* Implement graceful fallback with reconnection logic in frontend. Display "offline" state.

3. **Requires Frontend Development:** More complex onboarding than pure sensor approach.
   - *Mitigation:* Use Lit framework (already used by HA) for consistency.

4. **Limited Backward Compatibility:** Users upgrading from older HA versions may need to restart.
   - *Mitigation:* Document minimum HA version in manifest (2023.12+).

## Trade-offs and Rationale

We are intentionally **not** creating sensor entities. The product brief emphasizes a "dedicated sidebar panel" with "centralized monitoring," which implies a single, consolidated view — not scattered across the entity registry. This avoids the common HA integration anti-pattern of creating hundreds of synthetic entities.

The WebSocket API is chosen over polling REST endpoints because:
- HA's WebSocket is already open (for frontend communication)
- Lower latency for real-time updates
- Built-in authentication via HA session
- Aligns with HA's modern architecture (used by core UI, companion app, etc.)

Server-side sorting/pagination is mandatory per product brief and improves performance with large entity counts (e.g., 500+ devices).
