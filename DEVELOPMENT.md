# Claude Plugins Marketplace

This repo is a personal plugin marketplace for Claude Code. Plugins are installed to `~/.claude/plugins/marketplaces/local`.

## Repository Structure

```
claude-plugins/
├── .claude-plugin/
│   └── marketplace.json      # Registry of all available plugins
├── plugins/                   # All plugins live here
│   └── <plugin-name>/
│       ├── .claude-plugin/
│       │   └── plugin.json   # Required: plugin metadata
│       ├── agents/           # Optional: subagents (*.md)
│       ├── commands/         # Optional: slash commands (*.md)
│       ├── skills/           # Optional: agent skills (*/SKILL.md)
│       ├── hooks/
│       │   └── hooks.json    # Optional: event hooks
│       ├── .mcp.json         # Optional: MCP server configs
│       └── .lsp.json         # Optional: LSP server configs
├── install.sh                # One-liner installer for other machines
└── README.md                 # User-facing documentation
```

## Plugin Components

| Component | Location | Invocation | Use Case |
|-----------|----------|------------|----------|
| **Agents** | `agents/*.md` | `Task(subagent_type="plugin:agent")` | Specialized AI assistants |
| **Commands** | `commands/*.md` | `/plugin:command` | User-invoked slash commands |
| **Skills** | `skills/*/SKILL.md` | Auto-invoked by Claude | Domain-specific capabilities |
| **Hooks** | `hooks/hooks.json` | Event-triggered | Automation on events |
| **MCP** | `.mcp.json` | Auto-loaded tools | External tool integrations |
| **LSP** | `.lsp.json` | Auto-loaded | Code intelligence |

## Adding a New Plugin

### 1. Create the plugin directory

```bash
mkdir -p plugins/<plugin-name>/.claude-plugin
mkdir -p plugins/<plugin-name>/{agents,commands,skills,hooks}  # as needed
```

### 2. Create plugin.json (required)

```json
// plugins/<plugin-name>/.claude-plugin/plugin.json
{
  "name": "<plugin-name>",
  "description": "What this plugin does",
  "author": { "name": "Cody" }
}
```

### 3. Add components

**Agent** (`agents/<name>.md`):
```markdown
---
name: <agent-name>
description: When/why to use this agent
model: haiku  # haiku | sonnet | opus
---

You are an agent that does X.

## Instructions
- Step 1
- Step 2

## Output Format
Return results as...
```

**Command** (`commands/<name>.md`):
```markdown
---
description: Short description for /help
argument-hint: <required> [optional]
allowed-tools: [Read, Glob, Grep, Bash, Task]
model: haiku  # optional model override
---

# Command Name

Arguments: $ARGUMENTS

## Instructions
1. Do this
2. Then that
```

**Skill** (`skills/<name>/SKILL.md`):
```markdown
---
name: <skill-name>
description: When this skill applies
triggers:
  - "keyword1"
  - "keyword2"
---

# Skill Name

Instructions for this specialized capability...
```

**Hooks** (`hooks/hooks.json`):
```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": { "tool": "Write", "glob": "*.py" },
        "command": "ruff format $FILEPATH"
      }
    ]
  }
}
```

**MCP Server** (`.mcp.json`):
```json
{
  "mcpServers": {
    "server-name": {
      "command": "npx",
      "args": ["-y", "@some/mcp-server"]
    }
  }
}
```

### 4. Register in marketplace.json

Add entry to `.claude-plugin/marketplace.json`:

```json
{
  "plugins": [
    // ... existing plugins ...
    {
      "name": "<plugin-name>",
      "description": "What this plugin does",
      "version": "1.0.0",
      "author": { "name": "Cody" },
      "source": "./plugins/<plugin-name>",
      "category": "development"
    }
  ]
}
```

### 5. Commit and push

```bash
git add plugins/<plugin-name> .claude-plugin/marketplace.json
git commit -m "Add <plugin-name> plugin"
git push
```

## Managing Plugins

### Update on other machines

```bash
cd ~/.claude/plugins/marketplaces/local && git pull
```

### Enable a plugin

Add to `~/.claude/settings.json`:
```json
{
  "enabledPlugins": {
    "<plugin-name>@local": true
  }
}
```

Or use CLI:
```bash
claude /plugin install <plugin-name>@local
```

### Remove a plugin

1. Delete `plugins/<plugin-name>/`
2. Remove entry from `.claude-plugin/marketplace.json`
3. Commit and push

## Component Quick Reference

### Agent frontmatter fields
- `name`: Agent identifier (required)
- `description`: When to use (required, shown in Task tool)
- `model`: `haiku` | `sonnet` | `opus` (optional, defaults to conversation model)

### Command frontmatter fields
- `description`: Shown in `/help` (required)
- `argument-hint`: Usage hint like `<file> [options]` (optional)
- `allowed-tools`: Array of tools the command can use (optional)
- `model`: Override model for this command (optional)

### Command variables
- `$ARGUMENTS`: Full argument string
- `$1`, `$2`, etc.: Positional arguments
- `$CLAUDE_PLUGIN_ROOT`: Plugin directory path

### Hook event types
- `PreToolUse`: Before tool execution
- `PostToolUse`: After tool execution
- `UserPromptSubmit`: User sends message
- `SessionStart`: Session begins
- `SessionEnd`: Session ends

## Conventions

- Plugin names: lowercase, hyphenated (`my-plugin`)
- One plugin per directory under `plugins/`
- Keep plugins focused - prefer multiple small plugins over one large one
- Test locally before pushing
- Update README.md when adding user-facing plugins
