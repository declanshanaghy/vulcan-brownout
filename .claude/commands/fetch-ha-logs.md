---
description: Fetch a log file from the HA server
argument-hint: [file]
allowed-tools: Bash(ssh *), Bash(scp *), Bash(mkdir *), Bash(source *)
---

Fetch a log file from the Home Assistant server and save it locally.

FILE argument: $ARGUMENTS
If no argument is provided, default to `home-assistant.log`.

Steps:
1. Determine the filename: use `$ARGUMENTS` if provided, otherwise `home-assistant.log`.
2. Source the `.env` file in the project root to load SSH credentials:
   `SSH_HOST`, `SSH_PORT`, `SSH_USER`, `SSH_KEY_PATH`, `HA_CONFIG_PATH`.
   Resolve SSH_KEY_PATH relative to project root if not absolute.
3. Create the local destination directory: `tmp/home-assistant-logs/`
4. Fetch the file via SCP:
   ```
   scp -i $SSH_KEY_PATH -P $SSH_PORT -o StrictHostKeyChecking=accept-new \
     $SSH_USER@$SSH_HOST:$HA_CONFIG_PATH/<filename> \
     tmp/home-assistant-logs/<filename>
   ```
5. Report the local path where the file was saved and its size.

Use a single Bash command that sources `.env` inline so credentials are available, for example:
```bash
set -a; source .env; set +a
# resolve relative SSH key path
[[ "$SSH_KEY_PATH" != /* ]] && SSH_KEY_PATH="$PWD/$SSH_KEY_PATH"
FILE="${ARGUMENTS:-home-assistant.log}"
mkdir -p tmp/home-assistant-logs
scp -i "$SSH_KEY_PATH" -P "$SSH_PORT" -o StrictHostKeyChecking=accept-new \
  "$SSH_USER@$SSH_HOST:$HA_CONFIG_PATH/$FILE" \
  "tmp/home-assistant-logs/$FILE"
```

After fetching, print the file size and first few lines so the user can confirm it looks correct.
