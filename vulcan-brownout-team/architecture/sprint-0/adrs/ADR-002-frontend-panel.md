# ADR-002: Frontend Panel Approach

## Status: Accepted

## Context

The Vulcan Brownout sidebar panel must display paginated, sortable battery status for potentially hundreds of devices. We need to decide:

1. **Framework Choice:** Lit, Polymer, vanilla JavaScript, or React?
2. **Rendering Strategy:** Server-side pagination with "Load More" button, infinite scroll, or virtual scrolling?
3. **State Management:** Local component state, Redux, or rely on Home Assistant's API state?
4. **Styling Approach:** CSS, Material Design, or custom HA-themed styles?

Key requirements:
- Server-side sorting and pagination (already decided in ADR-001)
- Infinite scroll capability
- Real-time updates via WebSocket
- Works within HA's sidebar panel constraints
- Minimal dependencies (HA is conservative about bundle size)

## Options Considered

### Option A: Vanilla JavaScript with Manual State Management
Plain JavaScript component with direct DOM manipulation.

**Pros:**
- Zero dependencies
- Full control over code
- Lightweight bundle

**Cons:**
- Difficult to manage state
- Prone to bugs (manual DOM updates)
- Hard to maintain and extend
- Not idiomatic for HA ecosystem

### Option B: Lit (Home Assistant's Preferred Framework)
Use Lit v2 (lightweight Web Components library), same as HA's core UI.

**Pros:**
- Home Assistant's official choice for custom elements
- Tiny bundle size (~5KB minified)
- Reactive declarative syntax
- Shadow DOM support for style isolation
- Already loaded in HA frontend (no extra dependency)
- Ecosystem: HA's component library (@ha/components) available
- DevTools support for Web Components

**Cons:**
- Smaller community than React
- Less example code online
- Steeper learning curve for React developers

### Option C: React with TypeScript
Full-featured framework with strong tooling.

**Pros:**
- Mature ecosystem
- Large community
- Great DevTools

**Cons:**
- Large bundle (React alone is 40+ KB)
- Not idiomatic for HA (which uses Web Components)
- Extra build step required
- Overkill for a sidebar panel
- Performance overhead

### Option D: Preact (Lightweight React Alternative)
React-compatible library, ~3KB.

**Pros:**
- Familiar React syntax
- Smaller than React
- JSX support

**Cons:**
- Less integrated with HA ecosystem
- Still not idiomatic for HA
- Requires build tooling

## Decision

**Choose Option B: Lit 2 with TypeScript**

The Vulcan Brownout panel will be implemented as a Lit custom element extending `LitElement`:

1. **Framework:** Lit 2 (Web Components)
2. **Language:** TypeScript for type safety
3. **Rendering:** Reactive templates with automatic re-rendering on state change
4. **Styling:** Shadow DOM + CSS custom properties for HA theme support
5. **State Management:** Lit's reactive properties + component state (no Redux needed)
6. **Build:** Minify with esbuild or rollup; ship single `vulcan-brownout-panel.js` file

### Rendering Strategy

**Infinite Scroll with Lazy Loading:**

1. **Initial Load:** Display first 20 items (page size = 20)
2. **Intersection Observer:** Detect when user scrolls near bottom
3. **Auto-Fetch:** Trigger WebSocket query for next page when 80% scrolled
4. **Append:** Add new items to DOM (no re-render of existing items)
5. **Loading State:** Show spinner while fetching
6. **End Indicator:** Show "No more devices" when `total_items <= current_offset + items_length`

This avoids the complexity of virtual scrolling while supporting large datasets.

### State Management Structure

```javascript
class Vulcan BrownoutPanel extends LitElement {
  @property({ attribute: false })
  battery_devices = [];  // Current page items

  @property({ attribute: false })
  isLoading = false;

  @property({ attribute: false })
  hasMore = true;

  @property({ attribute: false })
  totalItems = 0;

  @property({ attribute: false })
  currentOffset = 0;

  @property({ attribute: false })
  sortKey = 'battery_level';

  @property({ attribute: false })
  sortOrder = 'asc';  // 'asc' | 'desc'

  @property({ attribute: false })
  threshold = 15;

  // WebSocket connection managed here
  private _connection = null;
}
```

### Styling Approach

- Use HA's design tokens (CSS custom properties): `var(--primary-color)`, `var(--text-primary)`, etc.
- Shadow DOM for style encapsulation
- Responsive design: works on mobile and desktop
- Respect HA's dark/light theme automatically

## Consequences

### Positive

1. **Idiomatic HA Integration:** Using Lit aligns with Home Assistant's architecture (HA uses Lit for its UI).
2. **Minimal Bundle:** Lit is ~5KB; panel JS will be ~20-30KB total (including our code).
3. **Type Safety:** TypeScript catches errors early.
4. **Reactive Rendering:** State changes automatically trigger UI updates — clean mental model.
5. **Theme Support:** HA's CSS custom properties automatically apply theme colors.
6. **No Extra Dependencies:** Lit is already loaded in HA's frontend.
7. **Future-Proof:** Web Components standard is stable; not dependent on framework trends.

### Negative

1. **Limited Community Knowledge:** Fewer StackOverflow answers than React.
   - *Mitigation:* HA community is strong; reference HA's own components.

2. **Build Tooling Required:** Need esbuild/rollup to minify and optimize.
   - *Mitigation:* Simple one-line build command; not complex like webpack.

3. **Debugging Web Components:** Browser DevTools less mature for Shadow DOM.
   - *Mitigation:* Chrome DevTools has improved; use `--inspect-brk` for Node debugging.

## Rendering Strategy Rationale

We chose **infinite scroll over "Load More" button** because:
- Better UX for browsing large lists (users expect this pattern from mobile apps)
- Automatic pagination reduces user friction
- Still respects server limits (only fetch when needed)

We rejected **virtual scrolling** because:
- Adds complexity (measuring item heights, calculating visible range)
- Overkill for this use case (we expect 20-50 items on screen at once)
- Infinite scroll achieves 90% of the performance benefit with 10% of the code

## Integration with Home Assistant

The panel integrates with HA via:

1. **Panel Registration:** In `__init__.py`:
   ```python
   hass.components.frontend.async_create_custom_panel(
       frontend_path='local/community/vulcan-brownout-panel.js',
       sidebar_title='Battery Sentinel',
       sidebar_icon='mdi:battery-alert'
   )
   ```

2. **Theme Access:** CSS custom properties automatically inherit from HA's theme system.

3. **Notification System:** Use HA's `fire_dom_event()` for toast notifications (low battery alerts, connection errors).

4. **Localization:** Support for multiple languages via HA's translation system (loaded in panel).

## Testing Implications

- Unit tests for state management logic (Jest or Vitest)
- Integration tests for WebSocket communication
- Manual testing on mobile (touch scroll performance)
- Dark/light theme switching
- Connection loss/reconnection scenarios
