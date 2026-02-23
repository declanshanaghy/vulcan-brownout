# Home Assistant Logging Reference

Source: https://www.home-assistant.io/integrations/logger/
Developer guidelines: https://developers.home-assistant.io/docs/development_guidelines

---

## How an Integration Appears in the HA Logs Page Provider Dropdown

The Settings → System → Logs page includes a **provider picker** (dropdown) that filters log output by integration. An integration appears in that dropdown **only if it declares its logger namespaces in `manifest.json`**.

### Required: `loggers` field in `manifest.json`

```json
{
  "domain": "vulcan_brownout",
  "name": "Vulcan Brownout",
  "loggers": ["custom_components.vulcan_brownout"],
  ...
}
```

The `loggers` field is a list of Python logger namespace strings. For most custom integrations this is exactly `["custom_components.<your_domain>"]`. If your integration uses a third-party library that does its own logging, add those namespaces too:

```json
"loggers": ["custom_components.my_integration", "my_library"]
```

Without this field, HA has no way to associate your log output with your integration's entry in the logs UI.

### Deep-link to your integration's logs

```
http://{HOME_ASSISTANT_URL}/config/logs?provider={DOMAIN}
```

Example for Vulcan Brownout:
```
http://homeassistant.lan:8123/config/logs?provider=vulcan_brownout
```

---

## Logger Setup in Python

Every module should create its logger at module level using `__name__`:

```python
import logging

_LOGGER = logging.getLogger(__name__)
```

When the module is `custom_components.vulcan_brownout.battery_monitor`, `__name__` resolves to that full dotted path, which is a child of `custom_components.vulcan_brownout`. All child loggers inherit level settings from the parent.

---

## Log Levels

| Level | Use when |
|---|---|
| `debug` | Input/output of every function, internal state, flow control |
| `info` | Significant lifecycle events (startup, shutdown, subscription created) |
| `warning` | Recoverable unexpected conditions (device not found in registry, stale subscription cleaned up) |
| `error` | Failures that prevent correct operation; include `exc_info=True` |
| `critical` | Reserved for unrecoverable failures — almost never used in integrations |

---

## Enabling Debug Logging for Vulcan Brownout

### Via `configuration.yaml` (persists across restarts)

```yaml
logger:
  default: warning
  logs:
    custom_components.vulcan_brownout: debug
```

### Via the HA Logger service (runtime, no restart needed)

```yaml
service: logger.set_level
data:
  custom_components.vulcan_brownout: debug
```

Or via the Developer Tools → Services UI.

### Via the HA Logs page

1. Go to Settings → System → Logs
2. Select **Vulcan Brownout** from the provider dropdown
3. Use the **Enable debug logging** button

Note: the UI button only covers `custom_components.vulcan_brownout.*`. Logs emitted during HA startup (before the integration loads) may not appear; use `configuration.yaml` for those.

---

## Log Output Format

HA writes log lines in this format:

```
2026-02-23 04:12:01.234 DEBUG (MainThread) [custom_components.vulcan_brownout.battery_monitor] query_entities: below_threshold=3 tracked_total=47 threshold=15%
```

Fields: `timestamp level (thread) [namespace] message`

---

## HA Developer Guidelines Summary (logging section)

- Use `%s`/`%d`/`%.1f` lazy formatting — never f-strings or `.format()` in log calls (avoids string building when level is disabled)
- `warning` for unexpected but recoverable conditions
- `error` for failures; always pass `exc_info=True` when catching exceptions
- `debug` for detailed tracing; safe to leave in production code
- Never log passwords, tokens, or sensitive user data
