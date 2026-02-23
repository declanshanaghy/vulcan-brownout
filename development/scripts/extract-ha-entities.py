#!/usr/bin/env python3
"""Dump all entity states from a Home Assistant server.

Reads HA_URL, HA_PORT, and HA_TOKEN from .env at the project root.
CLI flags override .env values.

Output: tmp/ha-entities.yaml  (raw JSON from GET /api/states)

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

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(yaml.dump(states, default_flow_style=False, allow_unicode=True))
    print(f"Written: {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
