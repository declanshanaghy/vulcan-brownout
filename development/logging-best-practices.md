# Vulcan Brownout — Logging Best Practices

This document describes the logging standards for all Python files in the Vulcan Brownout integration.

---

## Guiding Principles

1. **Every function logs its inputs and outputs at `debug` level** — this is the primary tool for troubleshooting in production without code changes.
2. **Significant lifecycle events log at `info`** — startup, teardown, subscriptions created/removed, query results returned.
3. **Recoverable unexpected conditions log at `warning`** — missing registry entries, stale subscriptions, panel registration failures.
4. **Caught exceptions log at `error` with `exc_info=True`** — this captures the full traceback.
5. **Never log sensitive data** — no tokens, passwords, or PII.

---

## Logger Setup

Each module declares its logger at module level:

```python
import logging

_LOGGER = logging.getLogger(__name__)
```

`__name__` resolves to the full dotted module path (e.g. `custom_components.vulcan_brownout.battery_monitor`), which is a child of the namespace declared in `manifest.json`. This means setting the log level on `custom_components.vulcan_brownout` in HA's logger config automatically applies to all submodules.

---

## Message Format: Structured KV Pairs

All log messages follow the pattern:

```
<function_name>: key1=value1 key2=value2 ...
```

### Rules

- **Prefix every message with the function name** — makes log grep easy without needing timestamps or thread info.
- **Use KV pairs separated by spaces** — machine-parseable without a structured logging library.
- **Use `%s`/`%d`/`%.1f` lazy formatting**, never f-strings or `.format()` in log calls — Python's logging skips string building entirely if the level is disabled.
- **Boolean states use descriptive values**: `result=true`, `skip=binary_sensor`, `source=cache`, `send=failed`.
- **Counts and numeric values** include units where relevant: `battery_level=12.5%%`, `threshold=15%%`.

### Examples

```python
# ✅ Correct — lazy format, KV pairs, function prefix
_LOGGER.debug(
    "query_entities: starting threshold=%d%% tracked_total=%d",
    BATTERY_THRESHOLD, len(self.entities),
)

_LOGGER.info(
    "handle_subscribe: subscription_id=%s entity_count=%d total_subscribers=%d",
    subscription_id, len(entity_ids), subscription_manager.get_subscription_count(),
)

_LOGGER.warning(
    "subscribe: subscription_id=%s result=rejected reason=limit_exceeded current=%d max=%d",
    subscription_id, current_count, MAX_SUBSCRIPTIONS,
)

_LOGGER.error(
    "async_setup_entry: setup=failed error=%s", e, exc_info=True
)

# ❌ Wrong — f-string (builds string even when level disabled)
_LOGGER.debug(f"query_entities: threshold={BATTERY_THRESHOLD}")

# ❌ Wrong — no function prefix, hard to grep
_LOGGER.debug("Threshold is %d", BATTERY_THRESHOLD)

# ❌ Wrong — no KV structure, ambiguous
_LOGGER.error("Failed: %s %s", entity_id, e)
```

---

## What to Log Per Function

### Entry (debug)
Log all input parameters:
```python
_LOGGER.debug(
    "on_state_changed: entity_id=%s new_state=%s",
    entity_id, new_state.state if new_state else None,
)
```

### Decision points (debug)
Log branches taken and why:
```python
_LOGGER.debug(
    "on_state_changed: entity_id=%s is_battery=false skipping", entity_id
)
```

### External calls (debug)
Log the result of registry lookups:
```python
_LOGGER.debug(
    "_resolve_device_info: entity_id=%s device_id=%s manufacturer=%s model=%s",
    entity_id, device_id, manufacturer, model,
)
```

### Exit / result (info for lifecycle, debug for query results)
```python
_LOGGER.info(
    "query_entities: complete below_threshold=%d tracked_total=%d threshold=%d%%",
    result_count, len(self.entities), BATTERY_THRESHOLD,
)
```

### Errors
Always include `exc_info=True` when catching exceptions so the traceback is captured:
```python
except Exception as e:
    _LOGGER.error(
        "discover_entities: discovery=failed error=%s", e, exc_info=True
    )
```

---

## Log Level Decision Guide

| Situation | Level |
|---|---|
| Function entry with input params | `debug` |
| Function exit with output/result | `debug` (or `info` for lifecycle events) |
| Skipping an entity (expected) | `debug` |
| Registry lookup result | `debug` |
| Integration started/stopped | `info` |
| Subscription created/removed | `info` |
| Query result returned | `info` |
| Device/area not found in registry | `debug` (common, not a problem) |
| Subscription limit hit | `warning` |
| Panel registration failed | `warning` |
| Dead connection cleaned up | `warning` |
| Exception caught in handler | `error` + `exc_info=True` |
| Setup/unload failed | `error` + `exc_info=True` |

---

## Enabling Debug Logs

### Runtime (no restart)
```yaml
service: logger.set_level
data:
  custom_components.vulcan_brownout: debug
```

### Via configuration.yaml (persists)
```yaml
logger:
  logs:
    custom_components.vulcan_brownout: debug
```

### Via HA UI
Settings → System → Logs → select **Vulcan Brownout** from the provider dropdown → Enable debug logging.

The integration appears in that dropdown because `manifest.json` declares:
```json
"loggers": ["custom_components.vulcan_brownout"]
```

---

## Complexity Budget

flake8 enforces `--max-complexity=10` on all files. Because debug logging adds conditional branches, keep per-function complexity in check by:

1. **Extracting helper methods** for repeated patterns (device registry lookup, entity validation).
2. **Moving skip/filter logic** into dedicated `_get_valid_*` helpers.
3. **Keeping log calls inside existing branches** — don't add new `if` blocks purely for logging.
