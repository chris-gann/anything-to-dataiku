# anything-to-dataiku

A Claude Code plugin that migrates Alteryx (`.yxmd`), Jupyter (`.ipynb`), Excel (`.xlsx`), and SAS (`.sas`) workflows into native Dataiku flows — visual recipes preferred, Python only as a last resort.

## What it does

Given a source workflow, Claude:
1. Reads and parses the source format.
2. Plans the equivalent Dataiku flow (consolidating column-ops into Prepare recipes, mapping aggregations to Group recipes, etc.).
3. Creates the Dataiku project, uploads source data, builds all recipes via the Dataiku Python API.
4. Runs one final `RECURSIVE_BUILD` on the terminal datasets.
5. Publishes a migration report to the project wiki documenting every design decision.

The plugin bundles 21 skills (one per Dataiku domain — recipes, scenarios, wikis, jobs, etc.) plus a Python MCP server that exposes `execute_python` against an authenticated Dataiku client.

## Requirements

- **Claude Code** with plugin support.
- **Python 3.12+** on your PATH (the plugin auto-creates a venv on first session).
- **Dataiku DSS instance** + a personal API key.

## Install

In Claude Code:

```
/plugin marketplace add https://github.com/chris-gann/anything-to-dataiku
/plugin install anything-to-dataiku@anything-to-dataiku
```

On first session, a `SessionStart` hook automatically creates a Python venv inside the plugin's data directory and installs `mcp-server/requirements.txt`. You'll see a one-time `installing Python dependencies...` message in the session log.

## Configure your Dataiku instance

After install, run:

```
/anything-to-dataiku:setup
```

Claude will ask for your Dataiku URL, API key, and instance name, then write `~/.dataiku-instances.json` for you. Restart Claude Code to pick up the config.

You can re-run `/anything-to-dataiku:setup` any time to add another instance. To switch instances mid-session, ask Claude to run `use_instance("MyInstance")`.

### Manual configuration (alternative)

If you'd rather edit the file yourself, create `~/.dataiku-instances.json`:

```json
{
  "default": "Production",
  "instances": {
    "Production": {
      "url": "https://my-dataiku.example.com",
      "api_key": "dkuaps-XXXXXXXXXXXX",
      "description": "Production Dataiku instance"
    }
  }
}
```

To use a non-default config path, set `ANYTHING_TO_DATAIKU_CONFIG` in your environment.

## Usage

Once configured, hand Claude a source file:

> Migrate `/path/to/my-workflow.yxmd` into a new Dataiku project called `MY_MIGRATION`.

Claude will read the source, plan the flow, build it, and publish a wiki migration report. For Jupyter / Excel / SAS, the entry point is the same — Claude detects the format from the extension.

## What's bundled

- **`skills/`** — 21 skills covering Dataiku recipes, datasets, scenarios, jobs, wikis, code envs, plugins, ML training, LLM Mesh, and the source-specific migration workflows.
- **`mcp-server/`** — Python MCP server exposing `execute_python`, `list_helpers`, `use_instance`, and `list_instances` tools. The `helpers/` package contains parsers for Alteryx / Jupyter / Excel / SAS plus visual-recipe builders for Dataiku.
- **`hooks/install-deps.sh`** — `SessionStart` hook that idempotently maintains the Python venv.

## Updating

```
/plugin marketplace update anything-to-dataiku
/plugin update anything-to-dataiku@anything-to-dataiku
```

Your `~/.dataiku-instances.json` is preserved across plugin updates.

## Troubleshooting

- **"DATAIKU INSTANCES NOT CONFIGURED"** — run `/anything-to-dataiku:setup` and restart Claude Code.
- **MCP server fails to start** — check that Python 3.12+ is on your PATH (`python3 --version`). The first session needs internet access to install Python deps.
- **Dependencies need reinstalling** — delete the plugin's data directory (`~/.claude/plugins/data/anything-to-dataiku/venv`) and start a new session; the hook will recreate it.

## Security

- Credentials in `~/.dataiku-instances.json` are stored in plain text. `chmod 600 ~/.dataiku-instances.json` is recommended.
- Never commit this file. The plugin's `.gitignore` excludes it.

## License

MIT
