# Private Claude Code Plugins

Personal plugin marketplace for Claude Code.

## Installation (Other Devices)

```bash
# One-liner install
curl -sL https://raw.githubusercontent.com/kodrea/claude-plugins/main/install.sh | bash

# Or clone manually
git clone git@github.com:kodrea/claude-plugins.git ~/.claude/plugins/marketplaces/local
```

## Available Plugins

| Plugin | Description |
|--------|-------------|
| haiku-scout | Fast, low-cost codebase mapping agent using Haiku |

## Usage

```bash
# Install a plugin
claude /plugin install haiku-scout@local

# Or enable in ~/.claude/settings.json
{
  "enabledPlugins": {
    "haiku-scout@local": true
  }
}
```

## Adding New Plugins

1. Create plugin directory: `plugins/my-plugin/`
2. Add required files:
   ```
   plugins/my-plugin/
   ├── .claude-plugin/
   │   └── plugin.json      # Required: name, description, author
   ├── agents/              # Optional: agent definitions (.md)
   ├── commands/            # Optional: slash commands (.md)
   └── skills/              # Optional: skill definitions
   ```
3. Add entry to `.claude-plugin/marketplace.json`
4. Commit and push

## Plugin Structure

### plugin.json (required)
```json
{
  "name": "my-plugin",
  "description": "What this plugin does",
  "author": { "name": "Your Name" }
}
```

### Agent (.md in agents/)
```markdown
---
name: my-agent
description: What the agent does
model: haiku  # or sonnet, opus
---

Agent instructions here...
```

### Command (.md in commands/)
```markdown
---
description: What the command does
argument-hint: [optional-args]
allowed-tools: [Read, Glob, Grep]
---

Command instructions here...
```

## Updating

```bash
cd ~/.claude/plugins/marketplaces/local
git pull
```
