# Interaction Specs — Sprint 3

**By**: Luna (UX) | **Status**: IMPLEMENTED

## Infinite Scroll
- Intersection Observer detects 100px from bottom
- Debounce: max 1 fetch/500ms, isFetching guard prevents duplicates
- Flow: skeleton loaders appear → API fetch → append devices → fade in new / fade out skeletons
- Error: "Failed to load more devices" + [RETRY] button (ARIA role=alert)
- End of list: "All devices loaded" message, no more fetches

## Back to Top
- Show: scrolled past 30 items (~1000px)
- Hide: scrollTop < 100px
- Click: smooth scroll to top (500ms ease-out)
- Position: fixed bottom-right, 48px square, fade in/out 300ms

## Notification Preferences Modal
- Open: "[CONFIGURE NOTIFICATIONS]" button in Settings panel
- Global toggle: green ON / gray OFF, disables per-device list when OFF
- Frequency cap: dropdown (1h/6h/24h)
- Severity: radio buttons (critical only / critical+warning)
- Per-device: checkboxes with search filter, "Show more" if >5
- Save: validates → POST → close modal → toast "Preferences saved"
- Cancel: if unsaved changes → confirm dialog "Discard changes?"
- Keyboard: Tab navigation, Space toggles, Enter saves, Escape cancels

## Dark Mode
- Detection on load → apply CSS variables → MutationObserver for live changes
- Transition: 300ms CSS on background + text colors, no page reload
- All WebSocket updates continue during theme switch

## Empty State
- Shows when devices.length === 0
- [Docs] opens new tab, [Refresh] re-queries API, [Settings] opens settings

## Accessibility
- Tab order: Settings icon → Connection badge → Sort → Filter → Battery items → Back to Top → Notification Preferences
- Screen reader: ARIA live regions for loading, notifications, theme changes
- WCAG AA contrast verified in both themes
