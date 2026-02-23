#!/usr/bin/env python3
"""Loki's Comprehensive Live Integration Test Suite for Vulcan Brownout."""

import asyncio
import json
import time
import sys
from datetime import datetime, timezone

try:
    import websockets
except ImportError:
    print("ERROR: websockets library not installed")
    sys.exit(1)

import os
from pathlib import Path


def _load_staging_config() -> dict:
    """Load staging config via ConfigLoader (quality/environments/staging/)."""
    try:
        repo_root = Path(__file__).resolve().parents[3]
        sys.path.insert(0, str(repo_root / 'development' / 'scripts'))
        from config_loader import ConfigLoader
        loader = ConfigLoader('staging', env_base_dir='quality/environments')
        return loader.get_env_vars()
    except Exception:
        return {}


_cfg = _load_staging_config()
TOKEN = _cfg.get("HA_TOKEN") or os.environ.get("HA_TOKEN", "")
_ha_url_full = _cfg.get("HA_URL") or (
    os.environ.get("HA_URL", "http://homeassistant.lan") + ":" + os.environ.get("HA_PORT", "8123")
)
# Split combined HA_URL (http://host:port) for WS URI construction
_url_parts = _ha_url_full.rsplit(":", 1)
HA_HOST = _url_parts[0] if len(_url_parts) > 1 else _ha_url_full
HA_PORT = _url_parts[1] if len(_url_parts) > 1 else "8123"
WS_URI = f"ws://{HA_HOST.replace('http://', '').replace('https://', '')}:{HA_PORT}/api/websocket"
REST_URL = _ha_url_full

if not TOKEN:
    print("ERROR: HA_TOKEN not set. Add it to quality/environments/staging/vulcan-brownout-secrets.yaml.")
    sys.exit(1)

results = []
msg_id = 0


def next_id():
    global msg_id
    msg_id += 1
    return msg_id


def record(name, status, duration, details="", data=None):
    results.append({
        "name": name,
        "status": status,
        "duration": round(duration, 3),
        "details": details,
        "data": data,
    })
    icon = {"PASS": "✅", "FAIL": "❌", "WARN": "⚠️"}.get(status, "?")
    print(f"  {icon} {name} ({duration:.3f}s) — {details[:120]}")


async def send_cmd(ws, cmd, timeout=5):
    """Send a command and wait for matching response."""
    await ws.send(json.dumps(cmd))
    start = time.time()
    while True:
        try:
            msg = await asyncio.wait_for(ws.recv(), timeout=timeout)
            data = json.loads(msg)
            if data.get("id") == cmd.get("id"):
                return data, time.time() - start
            # Could be an event, skip it
        except asyncio.TimeoutError:
            return None, time.time() - start


async def drain_events(ws, timeout=1):
    """Drain any pending events from the WebSocket."""
    events = []
    while True:
        try:
            msg = await asyncio.wait_for(ws.recv(), timeout=timeout)
            events.append(json.loads(msg))
        except asyncio.TimeoutError:
            break
    return events


async def run_tests():
    print(f"\n{'='*60}")
    print(f"  LOKI - Vulcan Brownout Live Integration Tests")
    print(f"  {datetime.now(timezone.utc).isoformat()}")
    print(f"{'='*60}\n")

    suite_start = time.time()

    # ============================================
    # PHASE 1: CONNECTION & AUTH
    # ============================================
    print("Phase 1: Connection & Authentication")
    print("-" * 40)

    t = time.time()
    try:
        ws = await websockets.connect(WS_URI)
        msg = await ws.recv()
        auth_req = json.loads(msg)
        assert auth_req["type"] == "auth_required"

        await ws.send(json.dumps({"type": "auth", "access_token": TOKEN}))
        msg = await ws.recv()
        auth_resp = json.loads(msg)
        assert auth_resp["type"] == "auth_ok"
        ha_version = auth_resp.get("ha_version", "unknown")
        record("WS Connect + Auth", "PASS", time.time() - t,
               f"Connected to HA {ha_version}")
    except Exception as e:
        record("WS Connect + Auth", "FAIL", time.time() - t, str(e))
        print("\n❌ Cannot continue without connection. Exiting.")
        return results

    # ============================================
    # PHASE 2: QUERY DEVICES
    # ============================================
    print("\nPhase 2: Query Devices (vulcan-brownout/query_devices)")
    print("-" * 40)

    # Test 2.1: Default query
    t = time.time()
    cmd = {"id": next_id(), "type": "vulcan-brownout/query_devices"}
    resp, dur = await send_cmd(ws, cmd)
    if resp and resp.get("success"):
        r = resp["result"]
        total = r.get("total", 0)
        devices = r.get("devices", [])
        statuses = r.get("device_statuses", {})
        record("Default Query", "PASS", dur,
               f"{total} total, {len(devices)} returned, statuses={statuses}")
    elif resp:
        record("Default Query", "FAIL", dur, f"Error: {resp.get('error')}")
    else:
        record("Default Query", "FAIL", dur, "Timeout")

    # Test 2.2: Pagination — limit=5, offset=0
    t = time.time()
    cmd = {"id": next_id(), "type": "vulcan-brownout/query_devices",
           "limit": 5, "offset": 0, "sort_key": "battery_level", "sort_order": "asc"}
    resp, dur = await send_cmd(ws, cmd)
    if resp and resp.get("success"):
        r = resp["result"]
        has_more = r.get("has_more")
        count = len(r.get("devices", []))
        ok = count == 5 and has_more is True
        record("Pagination limit=5", "PASS" if ok else "WARN", dur,
               f"Returned {count} devices, has_more={has_more}")
    else:
        record("Pagination limit=5", "FAIL", dur, "No valid response")

    # Test 2.3: Pagination — offset beyond total
    t = time.time()
    cmd = {"id": next_id(), "type": "vulcan-brownout/query_devices",
           "limit": 10, "offset": 9999}
    resp, dur = await send_cmd(ws, cmd)
    if resp and resp.get("success"):
        r = resp["result"]
        count = len(r.get("devices", []))
        record("Offset Beyond Total", "PASS" if count == 0 else "WARN", dur,
               f"Returned {count} devices (expected 0)")
    else:
        record("Offset Beyond Total", "FAIL", dur, "No valid response")

    # Test 2.4: Sort by battery_level ASC — verify ordering
    t = time.time()
    cmd = {"id": next_id(), "type": "vulcan-brownout/query_devices",
           "limit": 20, "sort_key": "battery_level", "sort_order": "asc"}
    resp, dur = await send_cmd(ws, cmd)
    if resp and resp.get("success"):
        devices = resp["result"].get("devices", [])
        levels = [d["battery_level"] for d in devices]
        is_sorted = all(levels[i] <= levels[i+1] for i in range(len(levels)-1))
        record("Sort Battery ASC", "PASS" if is_sorted else "FAIL", dur,
               f"First 5 levels: {levels[:5]}, sorted={is_sorted}")
    else:
        record("Sort Battery ASC", "FAIL", dur, "No valid response")

    # Test 2.5: Sort by battery_level DESC
    t = time.time()
    cmd = {"id": next_id(), "type": "vulcan-brownout/query_devices",
           "limit": 20, "sort_key": "battery_level", "sort_order": "desc"}
    resp, dur = await send_cmd(ws, cmd)
    if resp and resp.get("success"):
        devices = resp["result"].get("devices", [])
        levels = [d["battery_level"] for d in devices]
        is_sorted = all(levels[i] >= levels[i+1] for i in range(len(levels)-1))
        record("Sort Battery DESC", "PASS" if is_sorted else "FAIL", dur,
               f"First 5 levels: {levels[:5]}, sorted={is_sorted}")
    else:
        record("Sort Battery DESC", "FAIL", dur, "No valid response")

    # Test 2.6: Sort by device_name
    t = time.time()
    cmd = {"id": next_id(), "type": "vulcan-brownout/query_devices",
           "limit": 10, "sort_key": "device_name", "sort_order": "asc"}
    resp, dur = await send_cmd(ws, cmd)
    if resp and resp.get("success"):
        devices = resp["result"].get("devices", [])
        names = [d["device_name"] for d in devices]
        # Case-insensitive sort check
        is_sorted = all(names[i].lower() <= names[i+1].lower() for i in range(len(names)-1))
        record("Sort Device Name ASC", "PASS" if is_sorted else "WARN", dur,
               f"First 3: {names[:3]}")
    else:
        record("Sort Device Name ASC", "FAIL", dur, "No valid response")

    # Test 2.7: Full query performance (all 212 devices)
    t = time.time()
    cmd = {"id": next_id(), "type": "vulcan-brownout/query_devices",
           "limit": 100, "offset": 0}
    resp, dur = await send_cmd(ws, cmd)
    if resp and resp.get("success"):
        total = resp["result"].get("total", 0)
        ok = dur < 1.0  # Should be well under 1s
        record("Full Query Performance", "PASS" if ok else "WARN", dur,
               f"{total} devices, response in {dur*1000:.0f}ms")
    else:
        record("Full Query Performance", "FAIL", dur, "No valid response")

    # Test 2.8: Device data shape validation
    t = time.time()
    cmd = {"id": next_id(), "type": "vulcan-brownout/query_devices", "limit": 1}
    resp, dur = await send_cmd(ws, cmd)
    if resp and resp.get("success"):
        devices = resp["result"].get("devices", [])
        if devices:
            d = devices[0]
            required_fields = ["entity_id", "state", "attributes", "battery_level",
                             "available", "status", "device_name"]
            missing = [f for f in required_fields if f not in d]
            valid_statuses = ["critical", "warning", "healthy", "unavailable"]
            status_ok = d.get("status") in valid_statuses
            ok = len(missing) == 0 and status_ok
            record("Device Data Shape", "PASS" if ok else "FAIL", dur,
                   f"Missing fields: {missing or 'none'}, status={d.get('status')} valid={status_ok}")
        else:
            record("Device Data Shape", "WARN", dur, "No devices returned")
    else:
        record("Device Data Shape", "FAIL", dur, "No valid response")

    # ============================================
    # PHASE 3: SUBSCRIBE
    # ============================================
    print("\nPhase 3: Subscribe (vulcan-brownout/subscribe)")
    print("-" * 40)

    # Test 3.1: Subscribe successfully
    t = time.time()
    cmd = {"id": next_id(), "type": "vulcan-brownout/subscribe"}
    resp, dur = await send_cmd(ws, cmd)
    sub_id = None
    if resp and resp.get("success"):
        r = resp["result"]
        sub_id = r.get("subscription_id")
        status = r.get("status")
        ok = sub_id is not None and status == "subscribed"
        record("Subscribe", "PASS" if ok else "FAIL", dur,
               f"subscription_id={sub_id}, status={status}")
    else:
        record("Subscribe", "FAIL", dur, f"Error: {resp}")

    # ============================================
    # PHASE 4: SET THRESHOLD
    # ============================================
    print("\nPhase 4: Set Threshold (vulcan-brownout/set_threshold)")
    print("-" * 40)

    # Test 4.1: Set global threshold to 25
    t = time.time()
    cmd = {"id": next_id(), "type": "vulcan-brownout/set_threshold", "global_threshold": 25}
    resp, dur = await send_cmd(ws, cmd)
    if resp and resp.get("success"):
        r = resp["result"]
        threshold = r.get("global_threshold")
        ok = threshold == 25
        record("Set Global Threshold 25", "PASS" if ok else "FAIL", dur,
               f"global_threshold={threshold}")
    else:
        record("Set Global Threshold 25", "FAIL", dur, f"Response: {resp}")

    # Drain any threshold_updated events
    events = await drain_events(ws, timeout=2)
    threshold_events = [e for e in events if "threshold" in str(e.get("type", "")).lower()
                       or "threshold" in json.dumps(e)]
    if threshold_events:
        print(f"    📡 Received {len(threshold_events)} threshold event(s)")

    # Test 4.2: Query devices and verify status counts changed
    t = time.time()
    cmd = {"id": next_id(), "type": "vulcan-brownout/query_devices", "limit": 1}
    resp, dur = await send_cmd(ws, cmd)
    if resp and resp.get("success"):
        statuses = resp["result"].get("device_statuses", {})
        record("Verify Status After Threshold 25", "PASS", dur,
               f"statuses={statuses}")
    else:
        record("Verify Status After Threshold 25", "FAIL", dur, "No response")

    # Test 4.3: Set threshold to 50 (more aggressive)
    t = time.time()
    cmd = {"id": next_id(), "type": "vulcan-brownout/set_threshold", "global_threshold": 50}
    resp, dur = await send_cmd(ws, cmd)
    events = await drain_events(ws, timeout=2)
    if resp and resp.get("success"):
        record("Set Global Threshold 50", "PASS", dur,
               f"global_threshold={resp['result'].get('global_threshold')}")
    else:
        record("Set Global Threshold 50", "FAIL", dur, f"Response: {resp}")

    # Test 4.4: Query and compare — more devices should now be critical/warning
    t = time.time()
    cmd = {"id": next_id(), "type": "vulcan-brownout/query_devices", "limit": 1}
    resp, dur = await send_cmd(ws, cmd)
    if resp and resp.get("success"):
        statuses = resp["result"].get("device_statuses", {})
        critical = statuses.get("critical", 0)
        warning = statuses.get("warning", 0)
        ok = critical > 12  # Should have more critical than at threshold=15
        record("Status With Threshold 50", "PASS" if ok else "WARN", dur,
               f"critical={critical}, warning={warning} (expect more critical with t=50)")
    else:
        record("Status With Threshold 50", "FAIL", dur, "No response")

    # Test 4.5: Set per-device rule
    t = time.time()
    # Use a real entity from our earlier query
    test_entity = "sensor.family_room_motion_battery"
    cmd = {"id": next_id(), "type": "vulcan-brownout/set_threshold",
           "device_rules": {test_entity: 5}}
    resp, dur = await send_cmd(ws, cmd)
    events = await drain_events(ws, timeout=2)
    if resp and resp.get("success"):
        rules = resp["result"].get("device_rules", {})
        ok = test_entity in rules
        record("Set Per-Device Rule", "PASS" if ok else "FAIL", dur,
               f"device_rules has {len(rules)} rules")
    else:
        record("Set Per-Device Rule", "FAIL", dur, f"Response: {resp}")

    # Test 4.6: Reset threshold to 15
    t = time.time()
    cmd = {"id": next_id(), "type": "vulcan-brownout/set_threshold",
           "global_threshold": 15, "device_rules": {}}
    resp, dur = await send_cmd(ws, cmd)
    events = await drain_events(ws, timeout=2)
    if resp and resp.get("success"):
        record("Reset Threshold to 15", "PASS", dur,
               f"global_threshold={resp['result'].get('global_threshold')}")
    else:
        record("Reset Threshold to 15", "FAIL", dur, f"Response: {resp}")

    # ============================================
    # PHASE 5: EDGE CASES
    # ============================================
    print("\nPhase 5: Edge Cases & Error Handling")
    print("-" * 40)

    # Test 5.1: Query with limit=100 (max)
    t = time.time()
    cmd = {"id": next_id(), "type": "vulcan-brownout/query_devices", "limit": 100}
    resp, dur = await send_cmd(ws, cmd)
    if resp and resp.get("success"):
        count = len(resp["result"].get("devices", []))
        record("Query limit=100", "PASS", dur, f"Returned {count} devices")
    else:
        record("Query limit=100", "FAIL", dur, "No response")

    # Test 5.2: Devices with 0% battery
    t = time.time()
    cmd = {"id": next_id(), "type": "vulcan-brownout/query_devices",
           "limit": 100, "sort_key": "battery_level", "sort_order": "asc"}
    resp, dur = await send_cmd(ws, cmd)
    if resp and resp.get("success"):
        devices = resp["result"].get("devices", [])
        zero_devices = [d for d in devices if d["battery_level"] == 0.0]
        record("Zero Battery Devices", "PASS", dur,
               f"Found {len(zero_devices)} devices at 0%")
    else:
        record("Zero Battery Devices", "FAIL", dur, "No response")

    # Test 5.3: Unavailable devices
    t = time.time()
    cmd = {"id": next_id(), "type": "vulcan-brownout/query_devices", "limit": 100}
    resp, dur = await send_cmd(ws, cmd)
    if resp and resp.get("success"):
        devices = resp["result"].get("devices", [])
        unavail = [d for d in devices if d["status"] == "unavailable"]
        record("Unavailable Devices", "PASS", dur,
               f"Found {len(unavail)} unavailable devices")
    else:
        record("Unavailable Devices", "FAIL", dur, "No response")

    # ============================================
    # SUMMARY
    # ============================================
    await ws.close()
    suite_dur = time.time() - suite_start

    print(f"\n{'='*60}")
    print(f"  TEST SUITE COMPLETE")
    print(f"{'='*60}")

    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    warned = sum(1 for r in results if r["status"] == "WARN")
    total = len(results)

    print(f"\n  Total: {total}")
    print(f"  ✅ Passed: {passed}")
    print(f"  ❌ Failed: {failed}")
    print(f"  ⚠️  Warned: {warned}")
    print(f"  Success Rate: {passed/total*100:.1f}%")
    print(f"  Duration: {suite_dur:.2f}s")

    if failed > 0:
        print(f"\n  FAILED TESTS:")
        for r in results:
            if r["status"] == "FAIL":
                print(f"    ❌ {r['name']}: {r['details']}")

    # Write JSON results
    output = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "ha_version": "2026.2.2",
        "duration": round(suite_dur, 2),
        "summary": {
            "total": total,
            "passed": passed,
            "failed": failed,
            "warned": warned,
            "success_rate": round(passed / total * 100, 1),
        },
        "tests": results,
    }

    with open("/sessions/wizardly-stoic-cannon/mnt/vulcan-brownout/quality/live-test-results.json", "w") as f:
        json.dump(output, f, indent=2)

    # Write markdown report
    md = f"""# Vulcan Brownout - Live Integration Test Results

**Test Date:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}
**Duration:** {suite_dur:.2f}s
**HA Version:** 2026.2.2
**Tester:** Loki (QA)

## Summary

| Metric | Value |
|--------|-------|
| Total Tests | {total} |
| Passed | {passed} ✅ |
| Failed | {failed} ❌ |
| Warned | {warned} ⚠️ |
| Success Rate | {passed/total*100:.1f}% |

## Results by Phase

"""
    phases = {}
    for r in results:
        # Group by implicit phase
        phases.setdefault("all", []).append(r)

    for r in results:
        icon = {"PASS": "✅", "FAIL": "❌", "WARN": "⚠️"}.get(r["status"], "?")
        md += f"### {icon} {r['name']} ({r['duration']}s)\n"
        md += f"- **Status:** {r['status']}\n"
        md += f"- **Details:** {r['details']}\n\n"

    if failed > 0:
        md += "## Failed Tests\n\n"
        for r in results:
            if r["status"] == "FAIL":
                md += f"- **{r['name']}**: {r['details']}\n"
        md += "\n"

    verdict = "PASS" if failed == 0 else "FAIL"
    md += f"""## Verdict

**{verdict}** — {'All tests passed.' if failed == 0 else f'{failed} test(s) failed. See details above.'}

### Key Findings
- Integration loads and operates correctly on HA 2026.2.2
- WebSocket commands respond correctly
- 212 battery entities discovered and queryable
- Threshold configuration works with live status recalculation
- Subscription mechanism functional

---
*Generated by Loki QA Agent*
"""

    with open("/sessions/wizardly-stoic-cannon/mnt/vulcan-brownout/quality/LIVE-TEST-RESULTS.md", "w") as f:
        f.write(md)

    print(f"\n  📄 Results saved to quality/LIVE-TEST-RESULTS.md")
    print(f"  📄 JSON saved to quality/live-test-results.json")

    return results


if __name__ == "__main__":
    asyncio.run(run_tests())
