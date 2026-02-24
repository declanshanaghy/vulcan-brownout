# Development Environment Setup

**macOS only** (Sonoma or later)

## Prerequisites

1. **Docker Desktop** — https://www.docker.com/products/docker-desktop
   - Install and run it once to complete setup
   - Leave it running during development
2. **Homebrew** — https://brew.sh
3. **Ansible** — `brew install ansible`

## Docker Environment Setup

The Ansible playbook handles all system-level configuration automatically.

### Step 1: Run the Setup Playbook

```bash
ansible-playbook development/ansible/host-setup.yml
```

This:
- Installs Python 3.12 via Homebrew
- Verifies Docker Desktop is installed
- Creates an isolated Python venv at `development/venv/`
- Installs Python dependencies (pyyaml) from `development/requirements.txt`
- Initializes configuration templates

### Step 2: Configure Secrets

After the playbook completes, edit your Docker environment secrets:

```bash
vi development/environments/docker/vulcan-brownout-secrets.yaml
```

The file has `ha.token` and `ha.password` fields. Leave them as placeholders for now — you'll fill them in after starting Docker.

### Step 3: Start Docker Environment

```bash
./development/environments/docker/up.sh
```

This:
1. Starts Home Assistant in Docker
2. Waits for it to be ready
3. Prints access instructions

### Step 4: Get Your HA Token

1. Open http://localhost:8123 in your browser
2. Log in with: `admin` / `sprocket`
3. Click your profile icon (bottom left) → **Security**
4. Scroll to "Long-Lived Access Tokens"
5. Create a new token and copy it

### Step 5: Update Secrets

Edit `development/environments/docker/vulcan-brownout-secrets.yaml` and replace the placeholder:

```yaml
ha:
  token: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  password: "_7BMbAup8ZBTE2"
```

Now all configuration is ready.

## Using the Environment

### Verify Configuration

```bash
source development/venv/bin/activate
PYTHONPATH=development/scripts python development/scripts/config_loader.py docker
```

This loads and displays your merged configuration.

### Accessing Home Assistant

- **UI:** http://localhost:8123
- **Credentials:** admin / sprocket

The vulcan-brownout panel is automatically available in the sidebar once loaded.

### Restart Home Assistant

After editing Python source code:

```bash
curl -X POST \
  -H "Authorization: Bearer $HA_TOKEN" \
  http://localhost:8123/api/services/homeassistant/restart
```

(The `$HA_TOKEN` is available from your secrets file or in the environment after running up.sh)

### Stop Docker Environment

```bash
./development/environments/docker/down.sh
```

## Configuration Structure

### Main Configuration
`development/environments/docker/vulcan-brownout-config.yaml` — committed to repo

Contains defaults:
- HA URL, port, username
- SSH host/port/user (for future deployment)

### Secrets
`development/environments/docker/vulcan-brownout-secrets.yaml` — `.gitignore`d, auto-created

Contains sensitive values:
- HA long-lived token
- HA password

### Python Code

Configuration is loaded via `development/scripts/config_loader.py`.

Set PYTHONPATH before running:

```bash
export PYTHONPATH=development/scripts
python your_script.py
```

Then in your code:

```python
from config_loader import ConfigLoader

loader = ConfigLoader('docker')
config = loader.load()

# Access values
ha_token = config['ha']['token']
ha_url = config['ha']['url']
```

## Troubleshooting

**"ERROR: Development environment not initialized"**
- The venv at `development/venv/` doesn't exist
- Run: `ansible-playbook development/ansible/host-setup.yml`

**Docker fails to start**
- Docker Desktop may not be running
- Check: `pgrep Docker` or open Docker.app manually
- Retry: `./development/environments/docker/up.sh`

**Configuration loading fails**
- Verify `development/environments/docker/vulcan-brownout-secrets.yaml` exists
- Verify the file is valid YAML (check indentation)
- Verify venv is created: `ls -la development/venv/bin/python`

**HA login fails (admin/sprocket)**
- HA may still be initializing
- Wait 30 seconds and try again
- Check logs: `docker logs vulcan-brownout-ha`

**"secrets.yaml not found"**
- The Ansible playbook auto-creates it from `.example`
- If missing, manually create: `cp development/environments/docker/vulcan-brownout-secrets.yaml.example development/environments/docker/vulcan-brownout-secrets.yaml`

## HA Config: Seed vs Runtime

`development/environments/docker/ansible/seed/` is **not tracked by git**. It is seeded once by the Ansible playbook from `development/ansible/seed/` and then owned by HA at runtime.

- `development/ansible/seed/` — committed, canonical initial state (`.storage/`, `home-assistant_v2.db`, `configuration.yaml`, blueprints)
- `development/environments/docker/config/` — runtime directory, git-ignored, HA mutates it freely

The Ansible playbook copies `seed/` → `config/` only if `config/configuration.yaml` does not already exist. A running HA instance is never overwritten by re-running the playbook.

To update the seed (e.g. after intentional HA config changes you want to preserve for other developers), manually copy the relevant files from `config/` back into `seed/` and commit them.

## Next Steps

Once Docker environment is working:
- Run tests: `./quality/scripts/run-all-tests.sh --docker`
- Develop against live HA instance
- Staging environment setup (coming later)

---

## Documentation Index

This directory contains setup guides and technical documentation for Vulcan Brownout development:

### Setup & Environment
- [Local Docker Environment](environments/docker/README.md) — How to run a local Home Assistant instance in Docker for testing the integration.

### Development Standards
- [Logging Best Practices](logging-best-practices.md) — Python logging standards, message formats, and debug-enabling procedures for the integration.

### Home Assistant Reference
- [Logging Reference](home-assistant/logging-reference.md) — Technical reference for HA's logger system, log levels, and integration configuration.
- [Registry & Navigation Research](home-assistant/registry-and-navigation-research.md) — Device/entity/area registry lookups and entity management page navigation patterns.

### Sprint Documentation
- [QA Handoff (Sprint 6)](qa-handoff.md) — Quality assurance test scenarios and acceptance criteria for Sprint 6 tabbed UI feature. ⚠️ *Work in progress, not yet merged into v6.0.0.*
- [Implementation Plan (Sprint 6)](implementation-plan.md) — Backend and frontend implementation details for Sprint 6 tabbed UI feature. ⚠️ *Work in progress, not yet merged into v6.0.0.*
