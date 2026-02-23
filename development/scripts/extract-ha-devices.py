#!/usr/bin/env python3
"""Dump all devices from a Home Assistant server.

Reads HA_URL, HA_PORT, and HA_TOKEN from .env at the project root.
CLI flags override .env values.

Uses a single bulk HA template call to enumerate all unique devices —
no WebSocket or third-party dependencies required.

Output: tmp/ha-devices.yaml  (raw JSON from HA template API)

Usage:
    python development/scripts/extract-ha-devices.py
    python development/scripts/extract-ha-devices.py -u http://localhost -p 8123 -t TOKEN
    python development/scripts/extract-ha-devices.py -o /path/to/output.yaml
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

# Single template that walks all states and returns unique device info as JSON.
_DEVICES_TEMPLATE = """\
{%- set ns = namespace(seen=[], result=[]) -%}
{%- for state in states -%}
  {%- set d = device_id(state.entity_id) -%}
  {%- if d and d not in ns.seen -%}
    {%- set ns.seen = ns.seen + [d] -%}
    {%- set entry = {
      "id": d,
      "name": device_attr(d, "name"),
      "manufacturer": device_attr(d, "manufacturer"),
      "model": device_attr(d, "model"),
      "hw_version": device_attr(d, "hw_version"),
      "sw_version": device_attr(d, "sw_version"),
    } -%}
    {%- set ns.result = ns.result + [entry] -%}
  {%- endif -%}
{%- endfor -%}
{{ ns.result | tojson(indent=2) }}\
"""


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


def build_parser(env: dict[str, str]) -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Dump all devices from HA as raw JSON.",
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
    return p


def main() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    env = load_dotenv(repo_root / ".env")
    args = build_parser(env).parse_args()

    if not args.ha_token:
        print("ERROR: No HA token. Set HA_TOKEN in .env or pass --ha-token.", file=sys.stderr)
        sys.exit(1)

    base = f"{args.ha_url.rstrip('/')}:{args.ha_port}"
    print(f"Connecting to {base} …", file=sys.stderr)

    data = json.dumps({"template": _DEVICES_TEMPLATE}).encode()
    req = urllib.request.Request(
        f"{base}/api/template",
        data=data,
        headers={"Authorization": f"Bearer {args.ha_token}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode()
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code}: {base}/api/template", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Cannot connect to {base}: {e.reason}", file=sys.stderr)
        sys.exit(1)

    devices = json.loads(raw)
    devices.sort(key=lambda d: (d.get("name") or "").lower())
    print(f"Retrieved {len(devices)} devices.", file=sys.stderr)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(devices, indent=2) + "\n")
    print(f"Written: {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
