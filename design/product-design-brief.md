# Product Design Brief — Sprint 3

**By**: Freya (PO) + Luna (UX) | **Status**: IMPLEMENTED

## Problems Solved
1. Scroll performance crashing with 150+ entities → Cursor-based infinite scroll
2. Reactive-only monitoring → Proactive HA notifications with frequency caps
3. Light-mode only (dark mode is 85%+ of HA users) → Auto-detecting dark mode
4. Binary sensors showing as 0% battery → Server-side entity filtering
5. Deployment reliability → Idempotent deploy with health checks

## UX Decisions

### Infinite Scroll
- 50 items/page, auto-fetch at 100px from bottom
- Skeleton loaders (shimmer animation, 5 placeholders) — not blank space
- Back-to-top button after 30 items (fixed bottom-right)
- Scroll position saved to sessionStorage

### Notifications
- Separate modal from Settings (not inline)
- Sections: Global toggle → Frequency cap dropdown (1h/6h/24h) → Severity radio (critical only / critical+warning) → Per-device checkboxes (searchable) → History (last 5)
- Modal slides from right (desktop) / bottom (mobile)
- Changes only persist on Save

### Dark Mode
- Automatic detection only — no manual toggle
- CSS custom properties for all colors (no hardcoded values)
- MutationObserver for live theme switching (300ms CSS transition)
- Status colors adjusted for dark contrast: Critical #FF5252, Warning #FFB74D, Healthy #66BB6A

### Empty State
- Friendly message + battery icon + requirements list + [Docs] [Refresh] [Settings] buttons

## Color Tokens
See system-design.md for full light/dark color table. All dark mode colors WCAG AA compliant.

## Touch Targets
All interactive elements: minimum 44px. Checkboxes, toggles, radio buttons, buttons.

## Deferred to Sprint 4+
Historical trends, bulk operations, CSV export, advanced filtering, multi-language, mobile app deep linking.
