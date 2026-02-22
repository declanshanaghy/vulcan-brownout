# ADR-003: Deployment Architecture

## Status: Proposed

## Decision

**Option A: Bash Script with rsync, SSH as Homeassistant User, Docker Restart, Health Check via API**

Deployment via rsync over SSH with idempotent health checks. No CI infrastructure in Sprint 1; QA runs script manually before each test run.

## Rationale

- **Efficiency**: rsync only transfers changed files; resumable on interrupt
- **Simplicity**: Bash script easy for QA to understand and debug ad-hoc
- **Idempotency**: Safe to run multiple times (rsync is idempotent, docker restart is idempotent)
- **Reliability**: API health check proves HA is actually ready, not just process alive
- **Key management**: Single SSH user simplifies key rotation

## Implementation Details

**File: `deploy.sh`**:
- Load secrets from `.env` (SSH_HOST, SSH_USER, SSH_PORT, SSH_KEY_PATH, HA_API_TOKEN)
- Validate .env variables exist before proceeding
- Transfer files via rsync (only changed files, using SSH options)
- Restart HA via Docker: `docker-compose restart homeassistant`
- Health check: Poll `/api/` endpoint with auth token (up to 30 seconds, retry every 1 second)
- Verify integration loaded via API check

**File: `.env.example`**:
- Template for SSH_HOST, SSH_USER, SSH_PORT, SSH_KEY_PATH, HA_API_TOKEN
- Document how to generate long-lived token in HA UI

**Idempotency guarantees**:
- rsync: Only transfers changed files (safe to repeat)
- Docker restart: Restarting already-running container is a no-op
- Health check: Polling API is idempotent
- No cleanup: Integration files preserved across deployments

## Consequences

**Positive**:
- Simple Bash script, easy for QA to understand and debug
- Idempotent (safe to run multiple times)
- rsync efficient (only changed files)
- API health check proves HA is actually ready
- No CI/CD setup required in Sprint 1

**Negative**:
- Docker-specific (won't work on bare metal HA without modification)
- Requires homeassistant user to have SSH login enabled (security trade-off)
- Bash scripts can be fragile without careful quoting
- No automatic retries (failures require manual intervention)

## Next Steps

- QA creates SSH key pair and adds public key to test HA server
- QA creates `.env` file with test server details
- QA runs `./deploy.sh` to verify deployment works
