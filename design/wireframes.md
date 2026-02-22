# Wireframes — Sprint 3

**By**: Luna (UX) | **Status**: IMPLEMENTED

Wireframes were used to guide implementation. The code is the source of truth now. Key layout decisions preserved below.

## Panel Layout
```
┌─ HEADER ──────────────────────────────┐
│ BATTERY MONITORING              ⚙️  🟢 │
├─ SORT/FILTER BAR ─────────────────────┤
│ [▼ PRIORITY] [▼ ALL BATTERIES (N)] [✕] │
├─ DEVICE LIST ─────────────────────────┤
│ CRITICAL (N)                           │
│ [Device Card: icon, name, %, bar, ago] │
│ WARNING (N)                            │
│ [Device Cards...]                      │
│ HEALTHY (N)                            │
│ [Device Cards...]                      │
│ [Skeleton Loaders when fetching]       │
├─ FOOTER ──────────────────────────────┤
│ 🔄 Updated Xs ago         ▲ Back to Top│
└────────────────────────────────────────┘
```

## Notification Preferences Modal
Global toggle → Frequency dropdown → Severity radios → Per-device list (searchable) → History → [Save] [Cancel]

## Key Specs
- Skeleton loaders: shimmer gradient 2s cycle, dark #444/#555, light #E0E0/#F5F5
- Back to Top: 48px square, fixed bottom-right (16px offset), blue with opacity
- Cards: dark #2C2C2C / light #F5F5F5, shadow varies by theme
- Mobile: full-width modal, 44px touch targets, single-column device list
- Typography: Title 18px bold, Body 14px, Secondary 12px, Timestamp 12px italic
