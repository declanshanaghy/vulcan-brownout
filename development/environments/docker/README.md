# Local Docker Environment

A local Home Assistant instance running in Docker for testing the Vulcan Brownout integration before opening a PR. Any developer can spin it up without access to the physical `homeassistant.lan` server.

---

## Prerequisites

- Docker Desktop (or Docker Engine + Compose plugin)
- `curl` in your `$PATH`
- Port `8123` free on localhost

---

## How to Start

```bash
./development/environments/docker/up.sh
```

`up.sh` will:
1. Pull and start `ghcr.io/home-assistant/home-assistant:stable`
2. Wait for HA to be ready (up to 90s)
3. Print a summary with next steps

Open **http://localhost:8123** after the script completes.

---

## How to Stop

```bash
./development/environments/docker/down.sh
```

Stops and removes the container. HA state in `config/` is preserved.

---

## What Persists

The entire `config/` directory is bind-mounted into the container. HA state — users, tokens, config entries, history — survives container restarts. To reset to a clean state, clear the HA-generated files:

```bash
./development/environments/docker/down.sh
git clean -fdx development/environments/docker/config/
./development/environments/docker/up.sh
```

After a clean wipe you will need to complete HA onboarding at http://localhost:8123 before the integration is usable.

---

## Mock Battery Entities

`config/configuration.yaml` pre-seeds HA with 8 template sensor entities:

| Entity | Battery % | Appears in Panel? |
|---|---|---|
| Living Room Remote | 5% | Yes |
| Front Door Sensor | 8% | Yes |
| Garage Motion | 12% | Yes |
| Office Button | 14% | Yes |
| Hallway Sensor | 15% | No (at boundary) |
| Kitchen Motion | 45% | No |
| Back Door Lock | 80% | No |
| Master Bedroom Remote | 95% | No |

The panel should show exactly the 4 entities below the 15% threshold.

---

## Code Changes

The integration source is bind-mounted read-only into the container:

```
development/src/custom_components/vulcan_brownout/
  → /config/custom_components/vulcan_brownout (inside container)
```

**Frontend (JS) changes** — take effect immediately on browser reload.

**Backend (Python) changes** — require an HA restart:

```bash
source .env
curl -X POST \
  -H "Authorization: Bearer $HA_TOKEN" \
  http://localhost:8123/api/services/homeassistant/restart
```

Wait ~15s for HA to come back up, then reload the browser.

---

## Running E2E Tests

```bash
# Load credentials from .env
source .env

# Run E2E tests against local Docker HA
HA_URL=http://localhost:8123 ./quality/scripts/run-all-tests.sh --docker
```

Or set `HA_URL` in your `.env` and run without the prefix.

---

## Credentials

Credentials are set during initial HA onboarding and stored in `config/.storage/`. They are also saved in `.env`. See `.env.example` for the variable names.

`.env` is gitignored. Never commit it.

---

## Troubleshooting

**Container won't start / port conflict**
```bash
# Check if 8123 is in use
lsof -i :8123
# Or use docker logs
docker logs vulcan-brownout-ha
```

**Integration not showing in sidebar**
Check HA logs for errors:
```bash
docker logs vulcan-brownout-ha | grep vulcan
```
Verify the bind-mount path exists:
```bash
ls development/src/custom_components/vulcan_brownout/
```

**E2E tests fail with auth errors**
Ensure `HA_TOKEN` in `.env` is valid. Generate a new long-lived token from the HA UI at **http://localhost:8123/profile/security** and update `.env`.
