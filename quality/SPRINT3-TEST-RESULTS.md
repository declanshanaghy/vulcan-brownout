# Sprint 3 Detailed Test Results

**Date**: 2026-02-22 | **Result**: 24/28 PASS | **Duration**: 190ms

For summary and bugs, see SPRINT3-INDEX.md.

## Detailed Failures

### FAIL: SET notification preferences (spec values)
- Input: `{enabled: true, frequency_cap_hours: 12, severity_filter: "all"}`
- Expected: Success
- Actual: `invalid_format` error
- Root cause: API only accepts [1,6,24] and ["critical_only","critical_and_warning"]

### FAIL: Preferences persistence (depends on above)
- Blocked by BUG-S3-001

### FAIL: Legacy sort_key="battery_level"
- Input: `{sort_key: "battery_level"}`
- Expected: Sorted results
- Actual: No response (5s timeout)
- Root cause: Likely infinite loop in legacy key mapping

### WARN: limit=1000
- Input: `{limit: 1000}`
- Expected: Results or error
- Actual: No response (5s timeout)
- Root cause: No limit enforcement, performance degradation

## All Passing Tests
Connection, binary sensor filtering (3/3), cursor pagination (6/6), GET preferences, SET with valid values, reject invalid frequency/severity, sort priority/alphabetical/level_asc/level_desc, backward compat (3/3), invalid cursor, limit=1, empty cursor.
