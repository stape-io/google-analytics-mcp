# MCP Server for Google Analytics 4
[![Trust Score](https://archestra.ai/mcp-catalog/api/badge/quality/stape-io/google-analytics-mcp)](https://archestra.ai/mcp-catalog/stape-io__google-analytics-mcp)

A hosted MCP server for the Google Analytics 4 Admin and Data APIs, with Google OAuth built in.

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
  - [Useful resources](#useful-resources)
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

This server is a remote, HTTP-based MCP endpoint at `https://mcp-google-analytics.stape.io/mcp`, with Google OAuth built in. Clients that complete the OAuth flow themselves (Claude Desktop, Claude Code, VS Code, Copilot CLI, Cursor, ChatGPT) connect straight to that URL; the rest (Antigravity, stdio-only clients) reach it through [`mcp-remote`](https://github.com/geelen/mcp-remote#readme), a small bridge to remote HTTP MCP servers.

Each client signs you in with Google the first time it connects, to grant access to your Google Analytics data. Restart the client after changing its config.

### Claude Desktop

<details>
<summary>⬇️ Click to expand ⬇️</summary>

**Custom connector (recommended).**

1. Go to **Customize → Connectors → Add custom connector**. On Team and Enterprise plans, an Owner adds it under **Organization settings → Connectors → Add → Custom** instead, and each member then selects **Connect** on it under **Customize → Connectors** and signs in with their own Google account.
2. Set a name (e.g. `ga4-mcp-server`) and the URL to `https://mcp-google-analytics.stape.io/mcp`. If the dialog asks how to authenticate, choose **Sign in now**; if it asks for an OAuth client, choose **Register automatically**.
3. Select **Add**, then **Connect**, and sign in with Google.

The connector also works on claude.ai.

**`mcp-remote`.** To configure it through `claude_desktop_config.json` (Settings → Developer → Edit Config) instead:

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

</details>

### Claude Code

<details>
<summary>⬇️ Click to expand ⬇️</summary>

Claude Code speaks HTTP directly, including the OAuth flow, so no bridge is needed:

```bash
claude mcp add --transport http ga4-mcp-server https://mcp-google-analytics.stape.io/mcp
```

Then run `/mcp` inside Claude Code (or `claude mcp login ga4-mcp-server` from the shell) and sign in with Google. `claude mcp list` shows whether it connected.

This adds the server to the current project only. Add `--scope user` to use it in every project, or `--scope project` to write it to the project's `.mcp.json` so teammates get it too (each still signs in with their own Google account).

</details>

### VS Code

<details>
<summary>⬇️ Click to expand ⬇️</summary>

VS Code's MCP client supports HTTP servers and their OAuth flow natively, no `mcp-remote` needed. Add this to `.vscode/mcp.json` (this workspace) or to the file **MCP: Open User Configuration** opens (every workspace):

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

VS Code asks you to sign in with Google when the server first starts.

</details>

### GitHub Copilot

<details>
<summary>⬇️ Click to expand ⬇️</summary>

GitHub Copilot Chat in VS Code uses VS Code's own MCP client, so it reads the same MCP configuration — see [VS Code](#vs-code) above. No separate configuration is needed.

</details>

### Copilot CLI

<details>
<summary>⬇️ Click to expand ⬇️</summary>

Copilot CLI completes OAuth natively for remote HTTP servers:

```bash
copilot mcp add --transport http ga4-mcp-server https://mcp-google-analytics.stape.io/mcp
```

This writes the server entry into `~/.copilot/mcp-config.json`; sign in with Google when Copilot CLI prompts you. Run `copilot mcp get ga4-mcp-server` to check it. Inside an interactive session, `/mcp add` does the same through a form. See [GitHub's docs](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-mcp-servers#using-the-copilot-mcp-add-subcommand) for more.

</details>

### Cursor

<details>
<summary>⬇️ Click to expand ⬇️</summary>

Cursor speaks HTTP directly, including the OAuth flow, no `mcp-remote` needed. Add this to `.cursor/mcp.json` (this project) or `~/.cursor/mcp.json` (every project):

```json
{
  "mcpServers": {
    "ga4-mcp-server": {
      "url": "https://mcp-google-analytics.stape.io/mcp"
    }
  }
}
```

Then sign in with Google from the server's entry under **Customize** in Cursor's sidebar.

</details>

### Antigravity

<details>
<summary>⬇️ Click to expand ⬇️</summary>

Antigravity's OAuth support for remote HTTP servers doesn't get a token to the server yet ([antigravity-cli#25](https://github.com/google-antigravity/antigravity-cli/issues/25)), so use `mcp-remote` here. Add this to `~/.gemini/config/mcp_config.json`, which the Antigravity editor and CLI share. In the editor, open it from the agent panel via **… → MCP Servers → Manage MCP Servers → View raw config**:

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

Or, from the Antigravity CLI:

```bash
agy mcp add ga4-mcp-server -- npx -y mcp-remote https://mcp-google-analytics.stape.io/mcp
```

`mcp-remote` opens the Google sign-in in your browser the first time it connects.

</details>

### ChatGPT

<details>
<summary>⬇️ Click to expand ⬇️</summary>

1. In ChatGPT on the web, go to [Plugins](https://chatgpt.com/plugins), select **+**, then **Add custom MCP server**.
2. Enter a name (e.g. `ga4-mcp-server`) and, under **Connection**, set the server URL to `https://mcp-google-analytics.stape.io/mcp`.
3. Set authentication to **OAuth**. The server supports Dynamic Client Registration, so no client ID or secret is needed.
4. Confirm the risk warning (**I understand and want to continue**), then select **Create as a plugin**.
5. Install the plugin from your personal plugins, sign in with Google, and pick it with `@` in the prompt box.

Workspace admins can restrict custom MCP servers. See [OpenAI's docs](https://developers.openai.com/api/docs/guides/custom-mcp-server) for more.

</details>

### Other MCP clients

<details>
<summary>⬇️ Click to expand ⬇️</summary>

If your client supports remote HTTP MCP servers with OAuth, point it at `https://mcp-google-analytics.stape.io/mcp`, as in the [Cursor](#cursor) config. Otherwise, use `mcp-remote`:

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

</details>

### Troubleshooting

**MCP Server Name Length Limit**

Some MCP clients (like Cursor AI) have a 60-character limit for the combined MCP server name + tool name length. If you use a longer server name in your configuration (e.g., `ga4-mcp-server-your-additional-long-name`), some tools may be filtered out.

To avoid this issue:
- Use shorter server names in your MCP configuration (e.g., `ga4-mcp-server`)

**Clearing MCP Cache**

If you're connecting through `mcp-remote` (Antigravity, Claude Desktop configured that way, or other clients using the `mcp-remote` block), it stores all the credential information inside `~/.mcp-auth` (or wherever your `MCP_REMOTE_CONFIG_DIR` points to). If you're having persistent issues, try running:

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

Requires Python 3.11+. To test changes by issuing prompts in Gemini, point the `analytics-mcp` entry in your `~/.gemini/settings.json` at your local checkout:

```json
"command": "PATH_TO_REPO/.venv/bin/analytics-mcp"
```

Then run `gemini --debug` so Gemini prints debug output as it processes prompts. This local stdio server has no OAuth flow of its own — it authenticates via `google.auth.default()`, the same as the hosted server's own local dev fallback — so leave `GOOGLE_ANALYTICS_MCP_AUTH_PROVIDER` unset in your environment; setting it would make the local server try to build a real OAuth provider too.

```bash
nox -s format   # applies black formatting (80-char line width)
nox -s lint     # checks formatting only, fails on drift
nox -s tests    # unit tests across supported Python versions
ruff check .    # lint
mypy            # type check
```

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the CLA and pull request process.

## Useful resources

- [Step-by-step guide: MCP Server for Google Analytics](https://stape.io/blog/mcp-server-for-google-analytics)

## Open Source

The **MCP Server for Google Analytics 4** is a fork of [Google's official `google-analytics-mcp`](https://github.com/googleanalytics/google-analytics-mcp), maintained by [Stape Team](https://stape.io/) under the Apache 2.0 license.
