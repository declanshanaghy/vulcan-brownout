#!/usr/bin/env python3
"""Extract all entities and devices from a real HA server and inject them
directly into the Docker dev environment's HA storage registries.

Reads HA_URL, HA_PORT, HA_TOKEN from .env at the project root.
CLI flags override .env values.

All three API calls are READ-ONLY (GET /api/states, POST /api/template x2).
POST /api/template is a server-side Jinja2 render — it never modifies any state.

Outputs are MERGED with existing registry entries (no duplicates by id/entity_id):
  development/environments/docker/config/.storage/core.device_registry
  development/environments/docker/config/.storage/core.entity_registry

Usage:
    python development/scripts/extract-ha-entities.py
    python development/scripts/extract-ha-entities.py -u http://localhost -p 8123 -t TOKEN
    python development/scripts/extract-ha-entities.py --device-registry /path/to/core.device_registry
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# HA Jinja2 templates (server-side renders, read-only)
# ---------------------------------------------------------------------------

# Maps every entity_id → device_id in a single round-trip.
_DEVICE_ID_TEMPLATE = """\
{%- set ns = namespace(result=[]) -%}
{%- for state in states -%}
  {%- set ns.result = ns.result + [{"entity_id": state.entity_id, "device_id": device_id(state.entity_id)}] -%}
{%- endfor -%}
{{ ns.result | tojson }}\
"""

# Returns all unique devices with their entity lists.
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
      "entities": device_entities(d) | list,
    } -%}
    {%- set ns.result = ns.result + [entry] -%}
  {%- endif -%}
{%- endfor -%}
{{ ns.result | tojson(indent=2) }}\
"""

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[2]
_STORAGE_DIR = _REPO_ROOT / "development/environments/docker/config/.storage"
_DEFAULT_DEVICE_REGISTRY = str(_STORAGE_DIR / "core.device_registry")
_DEFAULT_ENTITY_REGISTRY = str(_STORAGE_DIR / "core.entity_registry")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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
        description="Extract HA entities/devices and inject into Docker .storage/ registries.",
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
    p.add_argument("--device-registry",
                   default=_DEFAULT_DEVICE_REGISTRY,
                   help="Path to core.device_registry to update")
    p.add_argument("--entity-registry",
                   default=_DEFAULT_ENTITY_REGISTRY,
                   help="Path to core.entity_registry to update")
    return p


def _get(base: str, path: str, token: str, timeout: int = 15) -> bytes:
    req = urllib.request.Request(
        f"{base}{path}",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code}: GET {base}{path}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Cannot connect to {base}: {e.reason}", file=sys.stderr)
        sys.exit(1)


def _post_template(base: str, template: str, token: str, timeout: int = 60) -> bytes:
    data = json.dumps({"template": template}).encode()
    req = urllib.request.Request(
        f"{base}/api/template",
        data=data,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code}: POST {base}/api/template", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Cannot connect to {base}: {e.reason}", file=sys.stderr)
        sys.exit(1)


def _read_registry(path: Path) -> dict:  # type: ignore[type-arg]
    if not path.exists():
        print(f"ERROR: Registry file not found: {path}", file=sys.stderr)
        sys.exit(1)
    return json.loads(path.read_text())


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _entity_uuid(entity_id: str) -> str:
    """Deterministic UUID derived from entity_id."""
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, entity_id))


# ---------------------------------------------------------------------------
# Registry entry builders
# ---------------------------------------------------------------------------

def _device_entry(device: dict) -> dict:  # type: ignore[type-arg]
    ts = _now_iso()
    return {
        "area_id": None,
        "config_entries": [],
        "config_entries_subentries": {},
        "configuration_url": None,
        "connections": [],
        "created_at": ts,
        "disabled_by": None,
        "entry_type": None,
        "hw_version": device.get("hw_version"),
        "id": device["id"],
        "identifiers": [],
        "labels": [],
        "manufacturer": device.get("manufacturer"),
        "model": device.get("model"),
        "model_id": None,
        "modified_at": ts,
        "name_by_user": None,
        "name": device.get("name"),
        "primary_config_entry": None,
        "serial_number": None,
        "sw_version": device.get("sw_version"),
        "via_device_id": None,
    }


def _entity_entry(state: dict, device_id_map: dict[str, str | None]) -> dict:  # type: ignore[type-arg]
    entity_id: str = state["entity_id"]
    attrs: dict = state.get("attributes", {})  # type: ignore[type-arg]
    ts = _now_iso()
    device_class = attrs.get("device_class")
    state_class = attrs.get("state_class")
    unit = attrs.get("unit_of_measurement")
    friendly_name = attrs.get("friendly_name") or entity_id
    capabilities = {"state_class": state_class} if state_class else None
    return {
        "aliases": [],
        "area_id": None,
        "categories": {},
        "capabilities": capabilities,
        "config_entry_id": None,
        "config_subentry_id": None,
        "created_at": ts,
        "device_class": None,
        "device_id": device_id_map.get(entity_id),
        "disabled_by": None,
        "entity_category": None,
        "entity_id": entity_id,
        "hidden_by": None,
        "icon": None,
        "id": _entity_uuid(entity_id),
        "has_entity_name": False,
        "labels": [],
        "modified_at": ts,
        "name": None,
        "object_id_base": friendly_name,
        "options": {"conversation": {"should_expose": False}},
        "original_device_class": device_class,
        "original_icon": None,
        "original_name": friendly_name,
        "platform": "vulcan_brownout",
        "suggested_object_id": None,
        "supported_features": 0,
        "translation_key": None,
        "unique_id": entity_id,
        "previous_unique_id": None,
        "unit_of_measurement": unit,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    env = load_dotenv(_REPO_ROOT / ".env")
    args = build_parser(env).parse_args()

    if not args.ha_token:
        print("ERROR: No HA token. Set HA_TOKEN in .env or pass --ha-token.", file=sys.stderr)
        sys.exit(1)

    base = f"{args.ha_url.rstrip('/')}:{args.ha_port}"
    print(f"Connecting to {base} …", file=sys.stderr)

    # --- 1. Fetch all entity states ---
    print("  GET /api/states …", file=sys.stderr)
    states: list[dict] = json.loads(_get(base, "/api/states", args.ha_token))  # type: ignore[type-arg]
    print(f"  → {len(states)} entities", file=sys.stderr)

    # --- 2. Fetch entity → device_id mapping ---
    print("  POST /api/template (entity→device_id) …", file=sys.stderr)
    device_id_map: dict[str, str | None] = {
        entry["entity_id"]: entry["device_id"]
        for entry in json.loads(_post_template(base, _DEVICE_ID_TEMPLATE, args.ha_token))
    }

    # --- 3. Fetch all devices with entity lists ---
    print("  POST /api/template (devices) …", file=sys.stderr)
    devices: list[dict] = json.loads(_post_template(base, _DEVICES_TEMPLATE, args.ha_token))  # type: ignore[type-arg]
    devices.sort(key=lambda d: (d.get("name") or "").lower())
    print(f"  → {len(devices)} devices", file=sys.stderr)

    # --- 4. Merge devices into core.device_registry ---
    dev_reg_path = Path(args.device_registry)
    dev_reg = _read_registry(dev_reg_path)
    existing_device_ids = {d["id"] for d in dev_reg["data"]["devices"]}
    new_devices = [_device_entry(d) for d in devices if d["id"] not in existing_device_ids]
    dev_reg["data"]["devices"].extend(new_devices)
    dev_reg_path.write_text(json.dumps(dev_reg, indent=2))
    print(f"  Devices: {len(existing_device_ids)} existing + {len(new_devices)} added "
          f"→ {len(dev_reg['data']['devices'])} total", file=sys.stderr)
    print(f"  Written: {dev_reg_path}", file=sys.stderr)

    # --- 5. Merge entities into core.entity_registry ---
    ent_reg_path = Path(args.entity_registry)
    ent_reg = _read_registry(ent_reg_path)
    existing_entity_ids = {e["entity_id"] for e in ent_reg["data"]["entities"]}
    new_entities = [
        _entity_entry(s, device_id_map)
        for s in states
        if s["entity_id"] not in existing_entity_ids
    ]
    ent_reg["data"]["entities"].extend(new_entities)
    ent_reg_path.write_text(json.dumps(ent_reg, indent=2))
    print(f"  Entities: {len(existing_entity_ids)} existing + {len(new_entities)} added "
          f"→ {len(ent_reg['data']['entities'])} total", file=sys.stderr)
    print(f"  Written: {ent_reg_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
