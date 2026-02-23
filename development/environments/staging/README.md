# Local Docker Staging Environment

A local Home Assistant instance running in Docker for testing the Vulcan Brownout integration before opening a PR. Any developer can spin it up without access to the physical `homeassistant.lan` server.

---

## Prerequisites

- Docker Desktop (or Docker Engine + Compose plugin)
- `curl` and `python3` in your `$PATH` (used by `up.sh` for onboarding)
- Port `8123` free on localhost

---

## How to Start

```bash
./development/environments/staging/up.sh
```

`up.sh` will:
1. Pull and start `ghcr.io/home-assistant/home-assistant:stable`
2. Wait for HA to be healthy (up to 90s)
3. Run the full HA onboarding sequence via REST API (creates admin user)
4. Generate a long-lived access token
5. Configure the `vulcan_brownout` integration via the config flow API
6. Enable debug logging for `custom_components.vulcan_brownout`
7. Write `HA_URL`, `HA_TOKEN`, `HA_USERNAME`, `HA_PASSWORD` to `.env` in the project root
8. Print a summary with login credentials and next steps

Open **http://localhost:8123** after the script completes.

---

## How to Stop

```bash
./development/environments/staging/down.sh
```

Stops and removes the container. All HA state is discarded.

---

## What Resets on Each `up`

Everything. HA starts fresh on every `docker compose up`:
- No users, no config entries, no history
- `up.sh` re-runs the full onboarding sequence each time
- A new long-lived token is generated and written to `.env`

This is intentional — fresh state prevents test pollution.

## What Persists

Nothing. There is no Docker volume for HA data.

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

## Running Staging E2E Tests

```bash
# Load the token written by up.sh
source .env

# Run staging tests against local Docker HA
HA_URL=http://localhost:8123 ./quality/scripts/run-all-tests.sh --staging
```

Or set `HA_URL` in your `.env` and run without the prefix.

---

## Credentials

`up.sh` prints credentials to the terminal and writes them to `.env`. Default values:

| | Value |
|---|---|
| URL | http://localhost:8123 |
| Username | admin |
| Password | vulcan-staging-2026 |
| Token | generated — see `.env` |

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

**`up.sh` says "already onboarded"**
Run `down.sh` first to remove the container, then `up.sh` again.

**Integration not showing in sidebar**
Check HA logs for errors:
```bash
docker logs vulcan-brownout-ha | grep vulcan
```
Verify the bind-mount path exists:
```bash
ls development/src/custom_components/vulcan_brownout/
```

**Staging tests fail with auth errors**
Re-run `up.sh` to generate a fresh token, then `source .env`.
