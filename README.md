# MCP Server for Google Analytics 4
[![Trust Score](https://archestra.ai/mcp-catalog/api/badge/quality/stape-io/google-analytics-mcp)](https://archestra.ai/mcp-catalog/stape-io__google-analytics-mcp)

An interface to the Google Analytics 4 Admin and Data APIs over MCP, in two flavours: a hosted server with Google OAuth built in, and a local CLI that runs on your own credentials.

## Table of Contents

- [MCP Server for Google Analytics 4](#mcp-server-for-google-analytics-4)
  - [Table of Contents](#table-of-contents)
  - [Available tools](#available-tools)
  - [Installation](#installation)
    - [Claude Desktop](#claude-desktop)
    - [Claude Code](#claude-code)
    - [VS Code](#vs-code)
    - [GitHub Copilot](#github-copilot)
    - [Copilot CLI](#copilot-cli)
    - [Cursor](#cursor)
    - [Antigravity](#antigravity)
    - [ChatGPT](#chatgpt)
    - [Other MCP clients](#other-mcp-clients)
    - [Troubleshooting](#troubleshooting)
  - [Local Development](#local-development)
  - [Open Source](#open-source)

## Available tools

All tools are read-only (`analytics.readonly` scope) — this server can query GA4 accounts and run reports, but never modify anything. A typical flow: `get_account_summaries` to find a property, `get_property_details` or `get_custom_dimensions_and_metrics` to see what's available on it, then one of the `run_*_report` tools to pull data.

| Tool | Purpose | Key arguments |
| --- | --- | --- |
| `get_account_summaries` | Lists the GA4 accounts and properties accessible to the authenticated user | none |
| `get_property_details` | Returns details of a GA4 property | `property_id` |
| `list_google_ads_links` | Lists the Google Ads accounts linked to a property | `property_id` |
| `list_property_annotations` | Lists annotations (notes on dates or periods, e.g. releases or campaigns) for a property | `property_id` |
| `get_custom_dimensions_and_metrics` | Returns a property's custom dimensions and metrics | `property_id` |
| `run_report` | Runs a core GA4 report | `property_id`, `date_ranges`, `dimensions`, `metrics` |
| `run_realtime_report` | Runs a realtime GA4 report | `property_id`, `dimensions`, `metrics` |
| `run_funnel_report` | Runs a funnel report (Alpha) | `property_id`, `funnel_steps` |
| `run_conversions_report` | Runs a conversions/attribution report (Alpha) — ad cost, ROAS, attribution model | `property_id`, `date_ranges`, `dimensions`, `metrics`, `conversion_spec` |

Every reporting tool also accepts optional filters, sort orders, pagination, and currency/quota options. Tool descriptions surfaced to the model include worked examples of these — see `analytics_mcp/tools/reporting/`.

## Installation

This server comes in two flavours: Hosted server and Local CLI. Both give you the same 9 tools; the difference is who handles Google auth.

| | Hosted server | Local CLI |
| --- | --- | --- |
| Auth | Google OAuth in your browser, handled for you | You supply a service account key via `GOOGLE_APPLICATION_CREDENTIALS` |
| Data | Passes through `mcp-google-analytics.stape.io` | Only ever leaves your machine |
| Setup | None | Set two environment variables |

Pick your client below. The hosted server needs the [`mcp-remote`](https://github.com/geelen/mcp-remote#readme) bridge on clients whose MCP support doesn't complete Google's OAuth flow natively; where a client does that itself, it connects straight to `https://mcp-google-analytics.stape.io/mcp`.

### Claude Desktop

<details>
<summary>⬇️ Click to expand ⬇️</summary>

Open Claude Desktop and navigate to Settings -> Developer -> Edit Config. This opens the configuration file that controls which MCP servers Claude can access.

**Hosted server** — restart Claude Desktop after saving; a browser window opens for the Google OAuth flow. Complete it to grant Claude access:

```json
{
  "mcpServers": {
    "ga4-mcp-server": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote",
        "https://mcp-google-analytics.stape.io/mcp"
      ]
    }
  }
}
```

**Local CLI** — no OAuth flow, no data through anyone else's server, you supply your own Google Cloud service account:

```json
{
  "mcpServers": {
    "ga4-mcp-server": {
      "command": "pipx",
      "args": ["run", "analytics-mcp"],
      "env": {
        "GOOGLE_APPLICATION_CREDENTIALS": "PATH_TO_CREDENTIALS_JSON",
        "GOOGLE_PROJECT_ID": "YOUR_PROJECT_ID"
      }
    }
  }
}
```

</details>

### Claude Code

<details>
<summary>⬇️ Click to expand ⬇️</summary>

Claude Code speaks HTTP directly, including the OAuth handshake, so the hosted server needs no bridge.

**Hosted server**:

```bash
claude mcp add --transport http ga4-mcp-server https://mcp-google-analytics.stape.io/mcp
```

A browser window opens for the Google OAuth flow the first time a tool is used. Run `/mcp` inside Claude Code to confirm it connected.

**Local CLI**:

```bash
claude mcp add ga4-mcp-server -e GOOGLE_APPLICATION_CREDENTIALS='PATH_TO_CREDENTIALS_JSON' -e GOOGLE_PROJECT_ID='YOUR_PROJECT_ID' -- pipx run analytics-mcp
```

Both write into `.mcp.json` / your Claude Code MCP config.

</details>

### VS Code

<details>
<summary>⬇️ Click to expand ⬇️</summary>

VS Code's MCP client supports HTTP servers and their OAuth flow natively, no `mcp-remote` needed. Add this to `.vscode/mcp.json`:

**Hosted server**:

```json
{
  "servers": {
    "ga4-mcp-server": {
      "type": "http",
      "url": "https://mcp-google-analytics.stape.io/mcp"
    }
  }
}
```

**Local CLI**:

```json
{
  "servers": {
    "ga4-mcp-server": {
      "type": "stdio",
      "command": "pipx",
      "args": ["run", "analytics-mcp"],
      "env": {
        "GOOGLE_APPLICATION_CREDENTIALS": "PATH_TO_CREDENTIALS_JSON",
        "GOOGLE_PROJECT_ID": "YOUR_PROJECT_ID"
      }
    }
  }
}
```

</details>

### GitHub Copilot

<details>
<summary>⬇️ Click to expand ⬇️</summary>

GitHub Copilot Chat in VS Code uses VS Code's own MCP client, so it reads the same `.vscode/mcp.json` file — see [VS Code](#vs-code) above. No separate configuration is needed.

</details>

### Copilot CLI

<details>
<summary>⬇️ Click to expand ⬇️</summary>

Copilot CLI also completes OAuth natively for remote HTTP servers. Add this to `~/.copilot/mcp-config.json`:

**Hosted server**:

```json
{
  "mcpServers": {
    "ga4-mcp-server": {
      "type": "http",
      "url": "https://mcp-google-analytics.stape.io/mcp"
    }
  }
}
```

**Local CLI**:

```json
{
  "mcpServers": {
    "ga4-mcp-server": {
      "command": "pipx",
      "args": ["run", "analytics-mcp"],
      "env": {
        "GOOGLE_APPLICATION_CREDENTIALS": "PATH_TO_CREDENTIALS_JSON",
        "GOOGLE_PROJECT_ID": "YOUR_PROJECT_ID"
      }
    }
  }
}
```

See [GitHub's docs](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-mcp-servers) for the equivalent `copilot mcp add` subcommand.

</details>

### Cursor

<details>
<summary>⬇️ Click to expand ⬇️</summary>

Cursor speaks HTTP directly too, no `mcp-remote` needed. Add this to `.cursor/mcp.json` (project-level) or `~/.cursor/mcp.json` (global — Settings → MCP → Add new global MCP server):

**Hosted server**:

```json
{
  "mcpServers": {
    "ga4-mcp-server": {
      "url": "https://mcp-google-analytics.stape.io/mcp"
    }
  }
}
```

A browser window opens for the Google OAuth flow the first time a tool is used.

**Local CLI**:

```json
{
  "mcpServers": {
    "ga4-mcp-server": {
      "command": "pipx",
      "args": ["run", "analytics-mcp"],
      "env": {
        "GOOGLE_APPLICATION_CREDENTIALS": "PATH_TO_CREDENTIALS_JSON",
        "GOOGLE_PROJECT_ID": "YOUR_PROJECT_ID"
      }
    }
  }
}
```

</details>

### Antigravity

<details>
<summary>⬇️ Click to expand ⬇️</summary>

Antigravity's own OAuth support for remote HTTP servers doesn't reliably reach a token to the server yet ([antigravity-cli#25](https://github.com/google-antigravity/antigravity-cli/issues/25)), so use `mcp-remote` for the hosted server here too, the same way Claude Desktop does. Add this to `~/.gemini/config/mcp_config.json` (global) or `.agents/mcp_config.json` (workspace-local) — accessible from the editor's agent panel via **… → MCP Servers → Manage MCP Servers → View raw config**:

**Hosted server**:

```json
{
  "mcpServers": {
    "ga4-mcp-server": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote",
        "https://mcp-google-analytics.stape.io/mcp"
      ]
    }
  }
}
```

**Local CLI**:

```json
{
  "mcpServers": {
    "ga4-mcp-server": {
      "command": "pipx",
      "args": ["run", "analytics-mcp"],
      "env": {
        "GOOGLE_APPLICATION_CREDENTIALS": "PATH_TO_CREDENTIALS_JSON",
        "GOOGLE_PROJECT_ID": "YOUR_PROJECT_ID"
      }
    }
  }
}
```

</details>

### ChatGPT

<details>
<summary>⬇️ Click to expand ⬇️</summary>

1. In ChatGPT, enable Developer mode: Settings → Apps & Connectors → Advanced settings → Developer mode.
2. Go to Settings → Connectors → Create, and set the server URL to `https://mcp-google-analytics.stape.io/mcp`.
3. Set Authentication to **OAuth** and complete the Google login in the browser window that opens.

ChatGPT only reaches servers over the public internet, it can't spawn a local process — so there's no Local CLI option here, only the hosted server.

</details>

### Other MCP clients

<details>
<summary>⬇️ Click to expand ⬇️</summary>

Any other MCP-compatible client that expects a stdio-style `command`/`args` config can use the same `mcp-remote` block for the hosted server:

```json
{
  "mcpServers": {
    "ga4-mcp-server": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote",
        "https://mcp-google-analytics.stape.io/mcp"
      ]
    }
  }
}
```

Or the local CLI directly, with your own credentials:

```json
{
  "mcpServers": {
    "ga4-mcp-server": {
      "command": "pipx",
      "args": ["run", "analytics-mcp"],
      "env": {
        "GOOGLE_APPLICATION_CREDENTIALS": "PATH_TO_CREDENTIALS_JSON",
        "GOOGLE_PROJECT_ID": "YOUR_PROJECT_ID"
      }
    }
  }
}
```

</details>

### Troubleshooting

**MCP Server Name Length Limit**

Some MCP clients (like Cursor AI) have a 60-character limit for the combined MCP server name + tool name length. If you use a longer server name in your configuration (e.g., `ga4-mcp-server-your-additional-long-name`), some tools may be filtered out.

To avoid this issue:
- Use shorter server names in your MCP configuration (e.g., `ga4-mcp-server`)

**Clearing MCP Cache**

If you're connecting through `mcp-remote` (Claude Desktop, Antigravity), it stores all the credential information inside `~/.mcp-auth` (or wherever your `MCP_REMOTE_CONFIG_DIR` points to). If you're having persistent issues, try running:

```bash
rm -rf ~/.mcp-auth
```

Then, restart your MCP client.

## Local Development

```bash
git clone https://github.com/stape-io/google-analytics-mcp
cd google-analytics-mcp
uv sync --all-extras
```

Requires Python 3.10+. To test changes by issuing prompts in Gemini, point the `analytics-mcp` entry in your `~/.gemini/settings.json` at your local checkout:

```json
"command": "PATH_TO_REPO/.venv/bin/analytics-mcp"
```

Then run `gemini --debug` so Gemini prints debug output as it processes prompts.

```bash
nox -s format   # applies black formatting (80-char line width)
nox -s lint     # checks formatting only, fails on drift
nox -s tests    # unit tests across supported Python versions
```

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the CLA and pull request process.

## Open Source

The **MCP Server for Google Analytics 4** is a fork of [Google's official `google-analytics-mcp`](https://github.com/googleanalytics/google-analytics-mcp), maintained by [Stape Team](https://stape.io/) under the Apache 2.0 license.

Learn more: [Step-by-step guide: MCP Server for Google Analytics](https://stape.io/blog/mcp-server-for-google-analytics)
