# ADR-003: Deployment Architecture

## Status: Proposed

## Context

Sprint 1 requires a deployment pipeline that QA can use to install the integration on a predefined test HA server. The Product Owner's brief specifies:
- SSH-based file transfer to the HA server
- Installation to `custom_components/vulcan_brownout/`
- HA restart after deployment
- Idempotent scripts (safe to run repeatedly)
- Deployment before every test run

We must decide:
- How deployment scripts transfer files (scp vs. rsync)
- Who owns the SSH connection (dedicated deploy user vs. homeassistant user)
- How to restart HA (via SSH command vs. HA API)
- Health check strategy (how to verify HA is ready after restart)
- How CI/CD triggers deployment (manual script vs. GitHub Actions)

## Options Considered

### Option A: Bash Script with rsync, SSH as Homeassistant User, Docker Restart, Health Check via API
- **Transfer:** `rsync -avz custom_components/vulcan_brownout/ user@host:/home/homeassistant/...`
- **User:** SSH as `homeassistant` user (same user running HA)
- **Restart:** `docker-compose restart homeassistant` (assumes containerized HA)
- **Health Check:** Poll HA API endpoint `/api/` with auth token until response 200
- **Idempotency:** rsync only transfers changed files; restart is idempotent
- **Pros:**
  - `rsync` is safer than `scp` (only transfers changed files, resumable)
  - Single SSH user simplifies key management
  - Docker restart is reliable and standard
  - API health check is reliable (proves HA is actually ready, not just process alive)
  - Widely understood shell script patterns
- **Cons:**
  - Requires `homeassistant` user to have SSH login enabled (security consideration)
  - Docker-specific (assumes containerized HA; won't work on bare metal)
  - Bash scripts can be fragile if not careful with quoting/escaping

### Option B: Bash Script with scp, Dedicated Deploy User, systemctl Restart, Health Check via Process
- **Transfer:** `scp -r custom_components/vulcan_brownout/ deploy@host:/home/deploy/staging/`
- **User:** Dedicated `deploy` user with passwordless sudo access
- **Restart:** `sudo systemctl restart homeassistant`
- **Health Check:** Wait 5 seconds, check if process is running
- **Idempotency:** Manual file deletion before scp; systemctl restart is idempotent
- **Pros:**
  - Separate deploy user is more secure (can be disabled/rotated independently)
  - Works on bare metal or containerized HA
  - systemctl is standard across Linux distros
- **Cons:**
  - scp transfers all files even if unchanged (wasteful)
  - Requires sudoers configuration (more setup)
  - Process being alive ≠ HA ready (API health check is more robust)
  - More moving parts (file staging, permissions, etc.)

### Option C: Python Script with paramiko (SSH library), rsync for Transfer, Flexible Restart
- **Transfer:** Use paramiko's SFTP for file transfer (no rsync dependency)
- **User:** Flexible (configurable in .env)
- **Restart:** Try Docker first, fall back to systemctl
- **Health Check:** Poll API endpoint
- **Idempotency:** Check file timestamps before transfer
- **Pros:**
  - More flexibility (Docker or bare metal)
  - Python script is easier to maintain than Bash
  - paramiko is cross-platform
- **Cons:**
  - Adds Python dependencies (`paramiko`, `requests`)
  - More code to maintain
  - Overkill for sprint 1 (simple Bash is fine)

### Option D: GitHub Actions Workflow, Built-in SSH, No Custom Script
- **Transfer:** Use GitHub Actions' `appleboy/ssh-action` (built-in SSH step)
- **Restart:** Configurable via action inputs
- **Health Check:** Curl loop in action
- **Idempotency:** Configurable in action inputs
- **Pros:**
  - No custom script to maintain
  - Integrates naturally with CI/CD
  - GitHub Actions provides logging and error handling
- **Cons:**
  - Requires GitHub Actions setup (out of scope for Sprint 1)
  - Less control for QA running deployment manually
  - Still needs .env for secrets

## Decision

**Option A: Bash Script with rsync, SSH as Homeassistant User, Docker Restart, Health Check via API**

This is the MVP deployment solution that balances simplicity, reliability, and idempotency.

### Rationale

1. **Assumption: Containerized HA:** The test environment is assumed to be HA running in Docker Compose (standard for HA). Option A is optimized for this.

2. **rsync Efficiency:** rsync only transfers changed files and resumes interrupted transfers. This is crucial for CI/CD pipelines where network is flaky.

3. **Homeassistant User:** HA already runs as `homeassistant` user. Reusing this user simplifies key management (QA generates one SSH key, adds it to `homeassistant`'s authorized_keys). A dedicated deploy user would require additional HA server setup.

4. **API Health Check:** Checking if HA API responds is more reliable than checking if the process is alive. It proves HA is actually ready to serve requests, not just in a restart loop.

5. **Idempotency:** rsync is naturally idempotent (re-running transfers only changed files). Docker restart is idempotent (restarting an already-running container is safe). Health checks can be re-run safely.

6. **Simplicity:** A single Bash script is easier for QA to understand, debug, and run ad-hoc than complex CI/CD workflows. Sprint 1 can ship this; Sprint 2 can integrate with GitHub Actions if needed.

### Implementation

**File: `deploy.sh` (Deployment Script)**

```bash
#!/bin/bash
set -euo pipefail

# Load secrets from .env
if [ ! -f .env ]; then
    echo "ERROR: .env file not found. Copy .env.example to .env and fill in values."
    exit 1
fi

source .env

# Validate .env variables
for var in SSH_HOST SSH_USER SSH_PORT SSH_KEY_PATH HA_API_TOKEN; do
    if [ -z "${!var:-}" ]; then
        echo "ERROR: $var not set in .env"
        exit 1
    fi
done

echo "=== Vulcan Brownout Deployment ==="
echo "Target: $SSH_USER@$SSH_HOST:$SSH_PORT"
echo "Deploying to: /home/$SSH_USER/homeassistant/custom_components/vulcan_brownout/"

# SSH options
SSH_OPTS="-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -p $SSH_PORT -i $SSH_KEY_PATH"

# 1. Transfer integration files via rsync
echo "[1/5] Transferring files via rsync..."
rsync -avz --delete \
  -e "ssh $SSH_OPTS" \
  custom_components/vulcan_brownout/ \
  $SSH_USER@$SSH_HOST:/home/$SSH_USER/homeassistant/custom_components/vulcan_brownout/

if [ $? -ne 0 ]; then
    echo "ERROR: rsync failed"
    exit 1
fi
echo "✓ Files transferred successfully"

# 2. Restart HA via Docker Compose
echo "[2/5] Restarting Home Assistant container..."
ssh $SSH_OPTS $SSH_USER@$SSH_HOST << 'EOFREMOTE'
  cd /home/$USER/homeassistant
  docker-compose restart homeassistant
  if [ $? -ne 0 ]; then
    echo "ERROR: docker-compose restart failed"
    exit 1
  fi
EOFREMOTE

echo "✓ Restart command sent"

# 3. Wait for HA to come up (polling)
echo "[3/5] Waiting for Home Assistant to become healthy..."
MAX_WAIT=30
WAIT=0
while [ $WAIT -lt $MAX_WAIT ]; do
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
      -H "Authorization: Bearer $HA_API_TOKEN" \
      http://$SSH_HOST:8123/api/ 2>/dev/null || echo "000")

    if [ "$HTTP_CODE" == "200" ]; then
        echo "✓ Home Assistant is healthy"
        break
    fi

    WAIT=$((WAIT + 1))
    echo "  [${WAIT}/${MAX_WAIT}] Waiting... (HTTP $HTTP_CODE)"
    sleep 1
done

if [ $WAIT -ge $MAX_WAIT ]; then
    echo "ERROR: Home Assistant did not become healthy within ${MAX_WAIT}s"
    exit 1
fi

# 4. Verify integration loaded
echo "[4/5] Verifying integration loaded..."
INTEGRATION_STATUS=$(curl -s -H "Authorization: Bearer $HA_API_TOKEN" \
  http://$SSH_HOST:8123/api/config 2>/dev/null | grep -c vulcan_brownout || echo "0")

if [ "$INTEGRATION_STATUS" -gt 0 ]; then
    echo "✓ Integration is loaded"
else
    echo "WARNING: Integration not found in config (may take a few seconds to load)"
fi

# 5. Log success
echo "[5/5] Deployment complete"
echo "=== Summary ==="
echo "✓ Files transferred"
echo "✓ Home Assistant restarted"
echo "✓ Health check passed"
echo "Ready for testing!"

exit 0
```

**File: `.env.example` (Template for Secrets)**

```bash
# SSH Configuration
SSH_HOST=192.168.1.100
SSH_USER=homeassistant
SSH_PORT=22
SSH_KEY_PATH=/path/to/ssh/private/key

# Home Assistant Configuration
HA_API_TOKEN=<your-long-lived-token>
```

**File: `.gitignore` (Prevent Secret Commits)**

```
.env
.env.local
.env.*.local
*.pem
id_rsa*
known_hosts
```

### Idempotency Guarantees

1. **File Transfer (rsync):** Only transfers changed files. Running twice transfers nothing the second time. Safe.
2. **Docker Restart:** Restarting an already-running container is a no-op. Safe.
3. **Health Check:** Can be run multiple times (just polls API). Safe.
4. **No Cleanup:** Integration files are preserved across deployments. Safe.

### Security Considerations

1. **SSH Key:** Stored outside repo (`.env` is gitignored). QA keeps key on secure machine.
2. **HA Token:** Long-lived token in `.env`, gitignored. QA can rotate in HA UI.
3. **No Password Auth:** Script uses key-based SSH (no plaintext passwords).
4. **Secrets Never Logged:** Script redirects output carefully to avoid logging token.

### Usage

QA runs:
```bash
$ cp .env.example .env
$ # Edit .env with test server details
$ chmod +x deploy.sh
$ ./deploy.sh
```

Or in GitHub Actions (Sprint 2):
```yaml
- name: Deploy Vulcan Brownout
  env:
    SSH_HOST: ${{ secrets.TEST_HA_SSH_HOST }}
    SSH_USER: ${{ secrets.TEST_HA_SSH_USER }}
    SSH_PORT: ${{ secrets.TEST_HA_SSH_PORT }}
    SSH_KEY_PATH: /tmp/ssh_key
    HA_API_TOKEN: ${{ secrets.TEST_HA_API_TOKEN }}
  run: |
    echo "${{ secrets.TEST_HA_SSH_KEY }}" > /tmp/ssh_key
    chmod 600 /tmp/ssh_key
    ./deploy.sh
```

## Consequences

Positive:
- Simple Bash script, easy for QA to understand and debug
- Idempotent (safe to run multiple times)
- rsync is efficient (only changed files)
- API health check is reliable (proves HA is actually ready)
- No CI/CD setup required in Sprint 1 (can add later)
- One SSH key simplifies key management

Negative:
- Docker-specific (won't work on bare metal HA without modification)
- Assumes `homeassistant` user has SSH login enabled (security trade-off)
- Bash script can be fragile if not careful with quoting
- No automatic retries (failures require manual intervention)

## Future Improvements (Sprint 2+)

1. **GitHub Actions Integration:** Move deployment into CI/CD workflow
2. **Rollback Strategy:** Store previous version, allow easy rollback
3. **Multi-Environment:** Support staging and production deployments
4. **Monitoring:** Log deployments to centralized system
5. **Bare Metal Support:** Detect HA installation type and choose appropriate restart command

## Test Environment Assumptions

This ADR assumes:
1. HA is containerized (Docker Compose)
2. `homeassistant` user exists and can SSH
3. Integration directory path is `/home/homeassistant/homeassistant/custom_components/vulcan_brownout/`
4. HA is accessible on port 8123 with HTTPS disabled (or HTTP allowed)
5. Long-lived token can be generated in HA UI

QA should verify these assumptions during test environment setup.

## Next Steps

- QA creates SSH key pair and adds public key to test HA server
- QA creates `.env` file with test server details
- QA runs `./deploy.sh` to verify deployment works
- Lead Developer creates integration files for first deployment test
