# ADR-004: Secrets Management

## Status: Proposed

## Decision

**Option A: .env File (Key=Value), .env.example Template, .gitignore**

Store secrets in `.env` file using plaintext key=value format. Template `.env.example` committed to repo. Secrets file excluded via `.gitignore`.

## Rationale

- **Sprint 1 scope**: This is test environment, not production. Plaintext .env acceptable with proper gitignore discipline
- **QA convenience**: QA can manually edit `.env` with text editor. No special tools needed
- **CI/CD ready**: GitHub Actions (Sprint 2) can inject variables via `${{ secrets.VAR_NAME }}`
- **Industry standard**: Django, Rails, Node.js all use .env; every developer knows pattern
- **Template-driven**: `.env.example` documents required variables

## Implementation Details

**File: `.env.example`** (committed to repo):
```
SSH_HOST=192.168.1.100
SSH_USER=homeassistant
SSH_PORT=22
SSH_KEY_PATH=/path/to/ssh/private/key
HA_API_TOKEN=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
HA_HOST=192.168.1.100 (optional)
HA_PORT=8123 (optional)
```

**File: `.gitignore`**:
```
.env
.env.local
.env.*.local
*.pem
*.key
id_rsa*
known_hosts
```

**File: `deploy.sh`** (Load and validate .env):
- Check .env exists before sourcing
- Source .env variables
- Validate required variables present (SSH_HOST, SSH_USER, SSH_PORT, SSH_KEY_PATH, HA_API_TOKEN)
- Validate SSH key exists and has correct permissions (600)
- Exit with helpful error if validation fails

**Variable naming convention**:
- SSH_HOST, SSH_USER, SSH_PORT, SSH_KEY_PATH
- HA_API_TOKEN, HA_HOST, HA_PORT

**Missing secret handling**:
- Script checks for required variables before use
- Exit with helpful error: "ERROR: Required variable 'SSH_HOST' not set in .env"
- Force QA to configure before running

## Consequences

**Positive**:
- Simple, human-readable format (QA can edit with any text editor)
- Industry standard (every developer knows .env pattern)
- CI/CD compatible (GitHub Actions can inject secrets)
- No external dependencies or services
- Template-driven (.env.example documents what's needed)
- Easy to rotate manually

**Negative**:
- Plaintext on disk (acceptable for test environment, not production)
- Requires gitignore discipline (easy to accidentally commit)
- No encryption at rest
- No audit trail for manual changes

## Security Notes

- **Gitignore is critical**: `.env` MUST be in `.gitignore`. Verify with `git check-ignore .env`
- **File permissions**: Keep `.env` readable only by you: `chmod 600 .env`
- **SSH key permissions**: SSH keys must be 600: `chmod 600 $SSH_KEY_PATH`
- **Token rotation**: Periodically rotate HA tokens (can revoke in HA UI)

## Future Enhancements (Sprint 2+)

- GitHub Actions Secrets for CI/CD
- AWS Secrets Manager for production deployments
- Encryption at rest (e.g., ansible-vault)
