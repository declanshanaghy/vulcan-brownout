# ADR-004: Secrets Management

## Status: Proposed

## Context

Sprint 1 requires storing deployment secrets (SSH keys, HA tokens, server addresses) outside the codebase. Secrets must:
1. Never be committed to git
2. Be easy for QA to provision locally
3. Support CI/CD injection (for Sprint 2)
4. Follow industry best practices

Per the Product Owner's brief, all secrets live in a `.env` file that is sourced at runtime by deployment scripts.

We must decide:
- What format (.env vs. JSON vs. YAML vs. other)
- Which secrets are needed
- How to version control a template
- How to structure variable names
- What happens if a secret is missing
- How to rotate secrets

## Options Considered

### Option A: .env File (Key=Value), .env.example Template, .gitignore
- **Format:** Plain text, one variable per line: `VAR_NAME=value`
- **Source:** Bash `source .env` or Python `python-dotenv`
- **Template:** Committed `.env.example` with placeholder values
- **Gitignore:** `.env`, `*.pem`, `id_rsa*` patterns
- **Validation:** Script checks for required variables before use
- **Pros:**
  - Industry standard (used by Django, Node.js, Ruby, etc.)
  - Simple, human-readable format
  - Easy for QA to edit manually
  - Many tools support it (dotenv libraries)
  - Works in CI/CD (GitHub Actions can inject via secrets)
- **Cons:**
  - No built-in validation (must manually check variables)
  - No encryption at rest (file is plaintext)
  - Easy to accidentally commit if gitignore is misconfigured
  - No version history

### Option B: .env.json, .env.example.json, .gitignore
- **Format:** JSON with nested structure for clarity
- **Source:** Python/JavaScript `json.load()`
- **Pros:**
  - Structured, easier to parse programmatically
  - Can include comments (if using JSON5 library)
  - Can validate against schema
- **Cons:**
  - More verbose than key=value
  - Requires JSON parser in Bash (less convenient)
  - Not as standard for secrets management

### Option C: AWS Secrets Manager / HashiCorp Vault
- **Format:** Centralized secret store (not local .env)
- **Source:** Deployment script queries API
- **Pros:**
  - Secrets never on disk
  - Audit trail for access
  - Easy rotation
  - Production-grade security
- **Cons:**
  - Overkill for Sprint 1 (adds infrastructure)
  - QA doesn't have AWS/Vault access (not their responsibility)
  - Requires network access during deployment
  - Setup complexity

### Option D: .env with Encryption, .env.enc
- **Format:** Encrypted .env file
- **Source:** Decryption script before deployment
- **Pros:**
  - Secrets not plaintext on disk
  - Can commit encrypted version
- **Cons:**
  - Decryption adds complexity
  - QA still needs master key somewhere
  - Doesn't prevent accidental commit of unencrypted version

## Decision

**Option A: .env File (Key=Value), .env.example Template, .gitignore**

This is the simplest approach that balances convenience for QA with industry standards and CI/CD compatibility.

### Rationale

1. **Sprint 1 Scope:** This is a test environment, not production. Plaintext .env is acceptable with proper gitignore discipline. Production deployments (future) can upgrade to AWS Secrets Manager.

2. **QA Convenience:** QA can manually edit `.env` with a text editor. No special tools or APIs needed. This is critical for quick iteration.

3. **CI/CD Ready:** GitHub Actions (Sprint 2) can inject .env variables directly via `${{ secrets.VAR_NAME }}`. Same format works for both manual and automated deployments.

4. **Industry Standard:** Django, Rails, Node.js, Python all use .env. Every developer already knows the pattern. Minimal training needed.

5. **Template-Driven:** `.env.example` in git serves as documentation. QA knows exactly what variables to set.

### Implementation

**File: `.env.example` (Committed to repo as template)**

```bash
# SSH Configuration
# Used by deploy.sh to connect to test HA server
SSH_HOST=192.168.1.100
SSH_USER=homeassistant
SSH_PORT=22
SSH_KEY_PATH=/path/to/ssh/private/key

# Home Assistant Configuration
# Long-lived token generated in HA UI (Settings > Devices & Services > Developer Tools > Create Long-Lived Token)
HA_API_TOKEN=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# Optional: If using different port or protocol
HA_HOST=192.168.1.100
HA_PORT=8123
```

**File: `.gitignore` (Prevent accidental commits)**

```
# Environment files
.env
.env.local
.env.*.local

# SSH keys and certificates
*.pem
*.key
id_rsa
id_rsa.pub
id_dsa
id_ecdsa
known_hosts

# OS-specific files
.DS_Store
Thumbs.db

# IDE
.vscode/
.idea/
*.swp
*.swo

# Dependencies
node_modules/
venv/
__pycache__/
```

**File: `deploy.sh` (Load and Validate .env)**

```bash
#!/bin/bash
set -euo pipefail

# Function to check if .env exists and is readable
if [ ! -f .env ]; then
    echo "ERROR: .env file not found."
    echo "Run: cp .env.example .env"
    echo "Then edit .env with your test server details."
    exit 1
fi

# Source .env variables
source .env

# Function to validate required variable
validate_var() {
    local var_name=$1
    if [ -z "${!var_name:-}" ]; then
        echo "ERROR: Required variable '$var_name' not set in .env"
        exit 1
    fi
}

# Validate all required variables
echo "Validating .env..."
validate_var SSH_HOST
validate_var SSH_USER
validate_var SSH_PORT
validate_var SSH_KEY_PATH
validate_var HA_API_TOKEN

# Validate SSH key exists and has correct permissions
if [ ! -f "$SSH_KEY_PATH" ]; then
    echo "ERROR: SSH key not found at $SSH_KEY_PATH"
    exit 1
fi

if [ ! -r "$SSH_KEY_PATH" ]; then
    echo "ERROR: SSH key not readable. Run: chmod 600 $SSH_KEY_PATH"
    exit 1
fi

# Check key permissions (should be 600)
KEY_PERMS=$(stat -c '%a' "$SSH_KEY_PATH" 2>/dev/null || stat -f '%OLp' "$SSH_KEY_PATH" 2>/dev/null || echo "unknown")
if [ "$KEY_PERMS" != "600" ] && [ "$KEY_PERMS" != "-rw-------" ]; then
    echo "WARNING: SSH key permissions are $KEY_PERMS (should be 600)"
fi

echo "✓ All variables validated"

# Rest of deployment script continues...
```

**File: `TESTING.md` (Instructions for QA)**

```markdown
# Testing Setup Guide

## Prerequisites

1. Access to test HA server (via SSH)
2. Home Assistant instance running (version 2023.12+)
3. Bash shell (Linux/macOS) or WSL2 (Windows)

## Setup Steps

### Step 1: Generate SSH Key (One-Time)

On your local machine:

```bash
ssh-keygen -t ed25519 -f ~/.ssh/vulcan_brownout_deploy -C "vulcan-brownout-deploy"
```

This creates:
- `~/.ssh/vulcan_brownout_deploy` — private key (keep secret)
- `~/.ssh/vulcan_brownout_deploy.pub` — public key (share with test HA)

### Step 2: Add Public Key to Test HA Server

On test HA server, as the `homeassistant` user:

```bash
# Log in as homeassistant (or su - homeassistant)
ssh homeassistant@ha-test-server.local

# Add your public key to authorized_keys
echo "YOUR_PUBLIC_KEY_CONTENT" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

Get `YOUR_PUBLIC_KEY_CONTENT` from:
```bash
cat ~/.ssh/vulcan_brownout_deploy.pub
```

### Step 3: Create Long-Lived Token in HA

1. Open Home Assistant UI (http://ha-test-server:8123)
2. Go to **Settings** > **Devices & Services**
3. Scroll to **Developer Tools**
4. Click **Create Long-Lived Access Token**
5. Name: "Vulcan Brownout Deploy"
6. Copy the token (starts with `eyJhbGciOi...`)

### Step 4: Create .env File

```bash
# In repo root
cp .env.example .env
```

Edit `.env` with your test server details:

```bash
SSH_HOST=192.168.1.100            # or ha-test-server.local
SSH_USER=homeassistant
SSH_PORT=22
SSH_KEY_PATH=~/.ssh/vulcan_brownout_deploy
HA_API_TOKEN=eyJhbGciOiJIUzI1NiIs... # paste your token
```

### Step 5: Test SSH Connection

```bash
ssh -i ~/.ssh/vulcan_brownout_deploy homeassistant@192.168.1.100 "echo 'SSH works!'"
```

Should print: `SSH works!`

If it fails:
- Check SSH key permissions: `chmod 600 ~/.ssh/vulcan_brownout_deploy`
- Verify public key on server: `cat ~/.ssh/authorized_keys` (should contain your public key)
- Check firewall: `telnet 192.168.1.100 22` (should connect)

### Step 6: Test Deployment

```bash
./deploy.sh
```

Should see:
```
=== Vulcan Brownout Deployment ===
[1/5] Transferring files via rsync...
✓ Files transferred successfully
[2/5] Restarting Home Assistant container...
✓ Restart command sent
[3/5] Waiting for Home Assistant to become healthy...
✓ Home Assistant is healthy
[4/5] Verifying integration loaded...
✓ Integration is loaded
[5/5] Deployment complete
```

If deployment fails, check:
- HA is running: `docker-compose ps` on HA server
- Token is valid: Try accessing HA API with curl
- Permissions: SSH key and directory ownership

## Troubleshooting

### "Permission denied (publickey)"
- Check SSH key permissions: `chmod 600 ~/.ssh/vulcan_brownout_deploy`
- Verify public key on server: `cat ~/.ssh/authorized_keys`

### "Connection timeout"
- Verify HA server is reachable: `ping 192.168.1.100`
- Check firewall: `telnet 192.168.1.100 22`
- Verify SSH port is 22 (not forwarded to different port)

### "Home Assistant did not become healthy"
- Check HA logs: `docker-compose logs homeassistant` on HA server
- Verify HA started: `docker-compose ps` (should show homeassistant RUNNING)
- Wait longer: Increase MAX_WAIT in deploy.sh if HA is slow to start

### Token issues
- Regenerate: Settings > Devices & Services > Developer Tools > Create new token
- Verify token format: Should start with `eyJhbGci`
- Check token not expired: Long-lived tokens don't expire by default

## Rotating Secrets

### Rotate SSH Key
1. Generate new key: `ssh-keygen -t ed25519 -f ~/.ssh/vulcan_brownout_deploy_new`
2. Add new public key to `~/.ssh/authorized_keys` on HA server
3. Update `.env` with new SSH_KEY_PATH
4. Test deployment
5. Remove old public key from `~/.ssh/authorized_keys`

### Rotate HA Token
1. Create new token in HA (Settings > Developer Tools)
2. Update `HA_API_TOKEN` in `.env`
3. Test deployment
4. Revoke old token (Settings > Developer Tools)

## Next Steps

- Run integration tests: `python -m pytest tests/`
- Run UI tests: `npm run test:ui`
- Open panel in browser: http://ha-test-server:8123/developer-tools/
```

### Variable Naming Convention

All secret variable names follow this pattern:

| Variable | Purpose | Example |
|----------|---------|---------|
| `SSH_HOST` | Test HA server IP/hostname | `192.168.1.100` |
| `SSH_USER` | User account for SSH | `homeassistant` |
| `SSH_PORT` | SSH port (usually 22) | `22` |
| `SSH_KEY_PATH` | Path to private SSH key | `/home/user/.ssh/id_rsa` |
| `HA_API_TOKEN` | Long-lived HA token | `eyJhbGciOi...` |
| `HA_HOST` | HA server address (optional) | `192.168.1.100` |
| `HA_PORT` | HA port (optional, default 8123) | `8123` |

### Missing Secret Handling

If a required variable is missing, deployment script exits with helpful error:

```bash
$ ./deploy.sh
ERROR: Required variable 'SSH_HOST' not set in .env
Run: cp .env.example .env
Then edit .env with your test server details.
```

This forces QA to configure before running, preventing silent failures.

## Consequences

Positive:
- Simple, human-readable format (QA can edit with any text editor)
- Industry standard (every developer knows .env pattern)
- CI/CD compatible (GitHub Actions can inject secrets)
- No external dependencies or services
- Template-driven (`.env.example` documents what's needed)
- Easy to rotate manually

Negative:
- Plaintext on disk (acceptable for test environment, not production)
- Requires gitignore discipline (easy to accidentally commit)
- No encryption at rest
- No audit trail for manual changes

## Security Notes

1. **Gitignore is Critical:** `.env` MUST be in `.gitignore`. Use `git check-ignore .env` to verify.
2. **File Permissions:** Keep `.env` readable only by you: `chmod 600 .env`
3. **SSH Key Permissions:** SSH keys must be `600`: `chmod 600 $SSH_KEY_PATH`
4. **Token Expiration:** HA long-lived tokens don't expire by default. Can revoke in HA UI at any time.
5. **Key Rotation:** Periodically rotate SSH keys and tokens (documented in TESTING.md)

## Future Enhancements (Sprint 2+)

1. **GitHub Actions Secrets:** Use `${{ secrets.VAR_NAME }}` for CI/CD
2. **AWS Secrets Manager:** For production deployments
3. **Encryption:** Encrypt `.env` at rest (e.g., with `ansible-vault`)
4. **Audit Logging:** Track secret access

## Next Steps

- QA sets up SSH key and long-lived token (see TESTING.md)
- QA creates `.env` file
- QA tests deployment with `./deploy.sh`
- Lead Developer implements integration files
