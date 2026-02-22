# Panel Debug: cursor=undefined Bug

**Status**: ROOT CAUSE IDENTIFIED | **Fix time**: 5 minutes

## Problem
Panel sends `cursor=undefined` on initial load. Backend rejects with `invalid_format`. Panel fails silently (blank).

## Fix (choose one)
**Frontend** (recommended): Change `let cursor;` → `let cursor = '';` in `vulcan-brownout-panel.js`
**Backend**: `cursor = data.get('cursor') or ''`

## Debug test
```bash
npx playwright test tests/debug-panel.spec.ts --timeout 60000
```
Debug output in `debug-output/` (console-logs.json has the API error).

See DEBUG_FINDINGS.md for full investigation details.
