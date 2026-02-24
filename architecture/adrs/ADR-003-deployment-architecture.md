# ADR-003: Deployment Architecture

## Status: Accepted (updated — see amendment below)

## Decision

**Option A: rsync over SSH, HA API restart, API health check**

Deployment via rsync over SSH with idempotent health checks. No CI infrastructure in Sprint 1; QA runs the deploy playbook manually before each test run.

## Rationale

- **Efficiency**: rsync only transfers changed files; resumable on interrupt
- **Idempotency**: Safe to run multiple times (rsync is idempotent, HA restart is idempotent)
- **Reliability**: API health check proves HA is actually ready, not just process alive
- **Key management**: Single SSH user simplifies key rotation

## Implementation Details

**File: `quality/ansible/deploy.yml`**:
- Load config from `quality/environments/staging/vulcan-brownout-config.yaml` and `vulcan-brownout-secrets.yaml` via Ansible `include_vars`
- Validate all required config values are present before proceeding
- Transfer files via rsync over SSH (only changed files)
- Restart HA via HA REST API (called over SSH)
- Health check: Poll `/api/` endpoint with auth token (up to 60 seconds, retry every 5 seconds)
- Verify integration loaded via API check
- Enable debug logging for `custom_components.vulcan_brownout`

**Config files** (YAML, not `.env`):
- `quality/environments/staging/vulcan-brownout-config.yaml` — SSH host, port, user, key path, HA config path, HA URL (committed)
- `quality/environments/staging/vulcan-brownout-secrets.yaml` — HA token, HA password (gitignored)

**Idempotency guarantees**:
- rsync: Only transfers changed files (safe to repeat)
- HA restart: Restarting already-running HA is a no-op
- Health check: Polling API is idempotent
- No cleanup: Integration files preserved across deployments

## Consequences

**Positive**:
- Ansible playbook is declarative, readable, and self-documenting
- Idempotent (safe to run multiple times)
- rsync efficient (only changed files)
- API health check proves HA is actually ready
- YAML config files integrate cleanly with ConfigLoader used by test tooling
- `--check` flag gives dry-run preview with no side effects

**Negative**:
- Requires Ansible installed locally (`brew install ansible`)
- Requires rsync installed locally (managed via `development/ansible/host-setup.yml`)
- Requires SSH access to the staging HA server

## Next Steps

- QA creates SSH key pair and adds public key to staging HA server
- QA populates `quality/environments/staging/vulcan-brownout-secrets.yaml`
- QA runs `ansible-playbook quality/ansible/deploy.yml` to verify deployment works

---

## Amendment: Migration from Bash to Ansible (2026-02-23)

The original implementation used a Bash script (`quality/scripts/deploy.sh`) with secrets loaded from a `.env` file. This was replaced with an Ansible playbook (`quality/ansible/deploy.yml`) that loads config directly from the YAML environment files shared with the test tooling (`ConfigLoader`). The core deployment mechanism (rsync over SSH, HA API restart) is unchanged.
