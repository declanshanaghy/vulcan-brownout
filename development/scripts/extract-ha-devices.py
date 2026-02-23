#!/usr/bin/env python3
"""Extract device registry (with battery entities) from a Home Assistant server.

Reads HA_URL, HA_PORT, and HA_TOKEN from .env at the project root.
CLI flags override .env values.

Uses the HA template API to resolve device info for each battery entity —
no WebSocket or third-party dependencies required.

Output: tmp/ha-devices.yaml
  Reference YAML: one entry per device, listing its battery entities.
  Copy to development/environments/docker/config/ha-devices.yaml for reference
  when adding device-grouped template sensors to the docker environment.

Usage:
    python development/scripts/extract-ha-devices.py
    python development/scripts/extract-ha-devices.py -u http://localhost -p 8123 -t TOKEN
    python development/scripts/extract-ha-devices.py --battery-only
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# ── .env loader ───────────────────────────────────────────────────────────────

def load_dotenv(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not path.exists():
        return env
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, _, val = line.partition("=")
            env[key.strip()] = val.strip().strip('"').strip("'")
    return env


# ── CLI ───────────────────────────────────────────────────────────────────────

def build_parser(env: dict[str, str]) -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Extract device registry (with battery entities) from HA as YAML.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("-u", "--ha-url",
                   default=env.get("HA_URL", "http://homeassistant.lan"),
                   help="HA base URL")
    p.add_argument("-p", "--ha-port",
                   type=int,
                   default=int(env.get("HA_PORT", "8123")),
                   help="HA port")
    p.add_argument("-t", "--ha-token",
                   default=env.get("HA_TOKEN", ""),
                   help="HA long-lived access token")
    p.add_argument("-o", "--output",
                   default="tmp/ha-devices.yaml",
                   help="Output file path")
    p.add_argument("--battery-only",
                   action="store_true",
                   help="Only include devices that have at least one battery entity")
    return p


# ── HA REST ───────────────────────────────────────────────────────────────────

def api_get(url: str, token: str) -> Any:
    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code}: {url}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Cannot connect to {url}: {e.reason}", file=sys.stderr)
        sys.exit(1)


def render_template(base: str, token: str, template: str) -> str:
    """Call POST /api/template to render a Jinja2 template on the HA server."""
    data = json.dumps({"template": template}).encode()
    req = urllib.request.Request(
        f"{base}/api/template",
        data=data,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode().strip()
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code} from template API", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Cannot connect to template API: {e.reason}", file=sys.stderr)
        sys.exit(1)


# ── device resolution ─────────────────────────────────────────────────────────

def _none(val: str) -> str | None:
    return None if val in ("", "None", "none", "null") else val


def get_devices(base: str, token: str) -> list[dict[str, Any]]:
    """Build a device map by querying the HA template API for each battery entity."""
    states: list[dict[str, Any]] = api_get(f"{base}/api/states", token)
    battery_states = [
        s for s in states
        if s.get("attributes", {}).get("device_class") == "battery"
    ]
    print(f"Found {len(battery_states)} battery entities.", file=sys.stderr)

    devices: dict[str, dict[str, Any]] = {}

    for i, state in enumerate(battery_states):
        entity_id = state["entity_id"]
        print(f"  [{i+1}/{len(battery_states)}] {entity_id} …", file=sys.stderr, end="\r")

        dev_id = _none(render_template(base, token, f"{{{{ device_id('{entity_id}') }}}}"))
        if dev_id is None:
            # Entity has no associated device — group under a synthetic "no device" bucket
            dev_id = "__no_device__"

        if dev_id not in devices:
            if dev_id == "__no_device__":
                devices[dev_id] = {
                    "id": None,
                    "name": "(no device)",
                    "manufacturer": None,
                    "model": None,
                    "area": None,
                    "battery_entities": [],
                }
            else:
                name = _none(render_template(base, token, f"{{{{ device_attr('{dev_id}', 'name') }}}}"))
                manufacturer = _none(render_template(base, token, f"{{{{ device_attr('{dev_id}', 'manufacturer') }}}}"))
                model = _none(render_template(base, token, f"{{{{ device_attr('{dev_id}', 'model') }}}}"))
                # area_name(area_id(entity_id)) — resolves entity → area
                area = _none(render_template(base, token, f"{{{{ area_name(area_id('{entity_id}')) }}}}"))
                devices[dev_id] = {
                    "id": dev_id,
                    "name": name,
                    "manufacturer": manufacturer,
                    "model": model,
                    "area": area,
                    "battery_entities": [],
                }

        attrs = state.get("attributes", {})
        devices[dev_id]["battery_entities"].append({
            "entity_id": entity_id,
            "name": attrs.get("friendly_name", entity_id),
            "state": state["state"],
            "unit": attrs.get("unit_of_measurement", "%"),
        })

    print("", file=sys.stderr)  # clear progress line
    return list(devices.values())


# ── YAML formatting ───────────────────────────────────────────────────────────

def _yaml_str(val: Any) -> str:
    if val is None:
        return "~"
    s = str(val)
    # Quote strings that contain special YAML characters
    if any(c in s for c in (':', '#', '[', ']', '{', '}', ',', '&', '*', '?', '|', '-', '<', '>', '=', '!', '%', '@', '`', '"', "'")):
        return json.dumps(s)
    return s


def format_device(device: dict[str, Any]) -> list[str]:
    lines = [
        f"  - name: {_yaml_str(device['name'])}",
    ]
    if device["id"]:
        lines.append(f"    id: {device['id']}")
    if device["manufacturer"]:
        lines.append(f"    manufacturer: {_yaml_str(device['manufacturer'])}")
    if device["model"]:
        lines.append(f"    model: {_yaml_str(device['model'])}")
    if device["area"]:
        lines.append(f"    area: {_yaml_str(device['area'])}")
    lines.append("    battery_entities:")
    for e in device["battery_entities"]:
        lines.append(f"      - entity_id: {e['entity_id']}")
        lines.append(f"        name: {_yaml_str(e['name'])}")
        lines.append(f"        state: \"{e['state']}\"")
        lines.append(f"        unit: \"{e['unit']}\"")
    return lines


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    env = load_dotenv(repo_root / ".env")
    args = build_parser(env).parse_args()

    if not args.ha_token:
        print("ERROR: No HA token. Set HA_TOKEN in .env or pass --ha-token.", file=sys.stderr)
        sys.exit(1)

    ha_url = args.ha_url.rstrip("/")
    base = f"{ha_url}:{args.ha_port}"
    print(f"Connecting to {base} …", file=sys.stderr)

    devices = get_devices(base, args.ha_token)

    if args.battery_only:
        devices = [d for d in devices if d["battery_entities"]]

    devices.sort(key=lambda d: (d.get("name") or "").lower())
    print(f"Devices in output: {len(devices)}", file=sys.stderr)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines: list[str] = [
        f"# ha-devices.yaml — devices with battery entities from {ha_url}:{args.ha_port}",
        f"# Generated: {now}  Devices: {len(devices)}",
        "#",
        "# Reference data — use ha-entities.yaml for HA template sensor includes.",
        "# Copy to development/environments/docker/config/ha-devices.yaml",
        "",
        "devices:",
    ]

    for i, device in enumerate(devices):
        lines.extend(format_device(device))
        if i < len(devices) - 1:
            lines.append("")

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n")
    print(f"Written: {out_path}", file=sys.stderr)
    print(f"\nTo use in Docker environment:", file=sys.stderr)
    print(f"  cp {out_path} development/environments/docker/config/ha-devices.yaml", file=sys.stderr)


if __name__ == "__main__":
    main()
