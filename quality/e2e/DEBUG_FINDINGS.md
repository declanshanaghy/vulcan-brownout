# Debug Findings: Panel Rendering Issue

**Root cause**: `let cursor;` (undefined) → API rejects `cursor=None` → panel fails silently

## Failure Sequence
1. Panel script loads + custom element instantiates ✓
2. Element calls fetchBatteryDevices({cursor: undefined})
3. Backend returns: `{code: invalid_format, message: expected str for dictionary value @ data['cursor']. Got None}`
4. Panel catches error silently, doesn't render

## Evidence
- HA shell loads ✓, panel script injected ✓, panel element created ✓
- Panel NOT in visible DOM tree (hasPanelElement: false)
- No JS exceptions (error caught as console.error)
- Console: 1 error message (the API rejection)

## Fix
`let cursor;` → `let cursor = '';` in vulcan-brownout-panel.js. Also: backend should `cursor = data.get('cursor') or ''`.

## Follow-up
- Add user-facing error display on API failure
- Add retry logic for transient failures
