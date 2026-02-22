# ADR-002: Frontend Panel Technology

## Status: Proposed

## Decision

**Option B: Lit Element**

Use Lit Element for the sidebar panel component. Lit is already bundled in Home Assistant, provides reactive property system with minimal boilerplate, and aligns with HA's own architecture.

## Rationale

- **HA native alignment**: HA's frontend uses Lit; future developers will recognize patterns
- **Zero external dependencies**: Lit already bundled in HA; no additional bundle size
- **Reactivity without complexity**: `@property` decorator eliminates manual DOM updates
- **Perfect scope fit**: Lit excels at single components with complex state (lists, pagination, sorting)
- **Developer experience**: TypeScript optional, excellent IDE support, readable template syntax

## Implementation Details

**File: `frontend/vulcan-brownout-panel.js`**:
- Extend LitElement base class
- Use `@property` and `@state` decorators for reactive rendering
- Implement WebSocket communication via `this.hass.callWS()`
- Shadow DOM provides style isolation
- Use HA CSS custom properties for theme integration

**File: `manifest.json`**:
- Register panel via `panel_custom` manifest entry
- Specify sidebar title and icon
- Set `js_url` to panel component path

**Styling strategy**:
- CSS custom properties for dark/light mode support
- Shadow DOM for style scoping
- HA's theme tokens (`--primary-color`, `--card-background-color`, etc.)
- Responsive CSS media queries

## Consequences

**Positive**:
- No external dependencies; zero bundle size impact
- Zero build step (drop .js file, it works)
- Reactive rendering (property changes trigger re-renders automatically)
- Great IDE support and type safety
- Aligns with HA's architecture

**Negative**:
- Developers unfamiliar with Web Components/Lit need to learn
- More abstraction than vanilla JS
- No JSX syntax (template literals are similar)

## Next Steps

- Lead Developer creates `vulcan-brownout-panel.js` using Lit
- Implement WebSocket communication to backend
- Implement infinite scroll with IntersectionObserver
- QA tests panel rendering and responsiveness
