---
name: setup
description: Configure Dataiku instance credentials for the anything-to-dataiku plugin. Run this once after installing the plugin, or again to add additional Dataiku instances.
---

# Setup

This skill walks the user through configuring their Dataiku instance credentials so the plugin's MCP server can connect.

The credentials live in `~/.dataiku-instances.json` (override path via `ANYTHING_TO_DATAIKU_CONFIG` env var). They are NEVER stored inside the plugin install directory — they belong to the user, persist across plugin updates, and are independent of which Claude Code surface (CLI, desktop, IDE) the user runs.

## What to do

### Step 1 — Check for an existing config

Use the Read tool to check whether `~/.dataiku-instances.json` already exists. If it does, read it and show the user the configured instance names (NOT the API keys) and ask whether they want to:
- Add a new instance
- Replace an existing one
- Change the default
- Cancel

If it does not exist, proceed to Step 2.

### Step 2 — Collect instance details from the user

Ask the user for:
1. **Instance name** — short identifier they'll use to switch between instances (e.g. `Argano`, `Production`, `Dev`). Must be a valid JSON key.
2. **Instance URL** — full URL like `https://argano-dataiku.com` (no trailing slash).
3. **API key** — they generate this in Dataiku via *Profile & settings → API keys → Personal API key*. It starts with `dkuaps-`.
4. **Description** (optional) — one-line label shown in the instance list.

If they're configuring their first instance, also confirm it should be the default. If they're adding to an existing config, ask whether to make this one the new default.

### Step 3 — Write the config file

Build the JSON object. Schema:
```json
{
  "default": "<instance-name>",
  "instances": {
    "<instance-name>": {
      "url": "<https-url>",
      "api_key": "<dkuaps-...>",
      "description": "<one-liner>"
    }
  }
}
```

Use the Write tool to save it to `~/.dataiku-instances.json` (resolve `~` to the user's home directory — the Write tool supports absolute paths, so use something like `/Users/<username>/.dataiku-instances.json` after detecting their home from `$HOME` via Bash).

### Step 4 — Verify and prompt for restart

After writing the file, tell the user:
1. Their config is at `~/.dataiku-instances.json`.
2. They need to **restart Claude Code** for the MCP server to pick up the new config (the server reads the file once at startup).
3. After restart, they can run `use_instance("<instance-name>")` to switch between configured instances if they have more than one.
4. To add another instance later, they can re-run `/anything-to-dataiku:setup`.

## Security notes to mention to the user

- The API key is stored in plain text in `~/.dataiku-instances.json`. File permissions default to user-readable only on macOS/Linux, but consider `chmod 600` for extra safety.
- Never commit `.dataiku-instances.json` to a git repo. The plugin's `.gitignore` already excludes it.
- API keys can be revoked in Dataiku under *Profile & settings → API keys* if leaked.

## Edge cases

- **User pastes a URL with a trailing slash**: strip it before writing.
- **User pastes an API key with surrounding whitespace**: strip it.
- **The `~/.dataiku-instances.json` file exists but is malformed JSON**: tell the user, show the error, ask whether to overwrite or abort.
- **User chooses a name that already exists**: confirm overwrite before proceeding.
