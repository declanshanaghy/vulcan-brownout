#!/usr/bin/env python3
"""Dump all entity states from a Home Assistant server.

Reads HA_URL, HA_PORT, and HA_TOKEN from .env at the project root.
CLI flags override .env values.

Each entity is enriched with a device_id field via a single bulk
POST /api/template call — no WebSocket or third-party dependencies required.

Output: tmp/ha-entities.yaml  (all entity states with device_id injected)

Usage:
    python development/scripts/extract-ha-entities.py
    python development/scripts/extract-ha-entities.py -u http://localhost -p 8123 -t TOKEN
    python development/scripts/extract-ha-entities.py -o /path/to/output.yaml
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

import yaml

# Bulk template that maps every entity_id → device_id in a single round-trip.
_DEVICE_ID_TEMPLATE = """\
{%- set ns = namespace(result=[]) -%}
{%- for state in states -%}
  {%- set ns.result = ns.result + [{"entity_id": state.entity_id, "device_id": device_id(state.entity_id)}] -%}
{%- endfor -%}
{{ ns.result | tojson }}\
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
        description="Dump all entity states from HA as raw JSON.",
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
                   default="tmp/ha-entities.yaml",
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

    req = urllib.request.Request(
        f"{base}/api/states",
        headers={"Authorization": f"Bearer {args.ha_token}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            states = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code}: {base}/api/states", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Cannot connect to {base}: {e.reason}", file=sys.stderr)
        sys.exit(1)

    print(f"Retrieved {len(states)} entities.", file=sys.stderr)

    # Fetch entity → device_id mapping via a bulk template call.
    print("Fetching device_id mapping …", file=sys.stderr)
    tpl_data = json.dumps({"template": _DEVICE_ID_TEMPLATE}).encode()
    tpl_req = urllib.request.Request(
        f"{base}/api/template",
        data=tpl_data,
        headers={"Authorization": f"Bearer {args.ha_token}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(tpl_req, timeout=30) as resp:
            device_id_map: dict[str, str | None] = {
                entry["entity_id"]: entry["device_id"]
                for entry in json.loads(resp.read().decode())
            }
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code}: {base}/api/template", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Cannot connect to {base}: {e.reason}", file=sys.stderr)
        sys.exit(1)

    # Inject device_id as the second key in each state dict.
    enriched = []
    for state in states:
        eid = state.get("entity_id", "")
        enriched_state = {"entity_id": eid, "device_id": device_id_map.get(eid)}
        enriched_state.update({k: v for k, v in state.items() if k != "entity_id"})
        enriched.append(enriched_state)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(yaml.dump(enriched, default_flow_style=False, allow_unicode=True))
    print(f"Written: {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
