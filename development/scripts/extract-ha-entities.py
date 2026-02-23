#!/usr/bin/env python3
"""Extract battery entities from a Home Assistant server.

Reads HA_URL, HA_PORT, and HA_TOKEN from .env at the project root.
CLI flags override .env values.

Output format matches template.yaml — copy the output to
  development/environments/docker/config/ha-entities.yaml
then switch configuration.yaml to:
  template: !include ha-entities.yaml

Usage:
    python development/scripts/extract-ha-entities.py
    python development/scripts/extract-ha-entities.py -u http://localhost -p 8123 -t TOKEN
    python development/scripts/extract-ha-entities.py --all   # all entities, not just battery
    python development/scripts/extract-ha-entities.py -o development/environments/docker/config/ha-entities.yaml
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
        description="Extract battery entities from HA as template sensor YAML.",
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
                   help="Output file (copy to docker/config/ to use with !include)")
    p.add_argument("--all",
                   action="store_true",
                   help="Include all entity states, not just device_class=battery")
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


# ── YAML formatting ───────────────────────────────────────────────────────────

def slugify(text: str) -> str:
    return text.lower().replace(" ", "_").replace("-", "_").replace(".", "_")


def sort_key(state: dict[str, Any]) -> float:
    try:
        return float(state["state"])
    except (ValueError, KeyError):
        return float("inf")


def entity_to_yaml(state: dict[str, Any]) -> list[str]:
    attrs = state.get("attributes", {})
    name = attrs.get("friendly_name", state["entity_id"])
    value = state["state"]
    unit = attrs.get("unit_of_measurement", "%")
    device_class = attrs.get("device_class", "battery")
    unique_id = f"extracted_{slugify(state['entity_id'])}"
    return [
        f'    - name: "{name}"',
        f"      unique_id: {unique_id}",
        f'      state: "{value}"',
        f"      device_class: {device_class}",
        f'      unit_of_measurement: "{unit}"',
    ]


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

    states: list[dict[str, Any]] = api_get(f"{base}/api/states", args.ha_token)
    print(f"Retrieved {len(states)} total entities.", file=sys.stderr)

    targets = states if args.all else [
        s for s in states
        if s.get("attributes", {}).get("device_class") == "battery"
    ]
    targets.sort(key=sort_key)
    print(f"Writing {len(targets)} entities.", file=sys.stderr)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines: list[str] = [
        f"# ha-entities.yaml — battery entities extracted from {ha_url}:{args.ha_port}",
        f"# Generated: {now}  Entities: {len(targets)}",
        "#",
        "# Include from configuration.yaml:",
        "#   template: !include ha-entities.yaml",
        "",
        "- sensor:",
    ]

    for i, state in enumerate(targets):
        lines.extend(entity_to_yaml(state))
        if i < len(targets) - 1:
            lines.append("")

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n")
    print(f"Written: {out_path}", file=sys.stderr)
    print(f"\nTo use in Docker environment:", file=sys.stderr)
    print(f"  cp {out_path} development/environments/docker/config/ha-entities.yaml", file=sys.stderr)
    print(f"  # then set in configuration.yaml:  template: !include ha-entities.yaml", file=sys.stderr)


if __name__ == "__main__":
    main()
