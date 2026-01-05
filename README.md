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

### Quick Start

```bash
cd ~/.claude/plugins/marketplaces/local

# 1. Create plugin structure
mkdir -p plugins/my-plugin/.claude-plugin
mkdir -p plugins/my-plugin/agents
mkdir -p plugins/my-plugin/commands

# 2. Create plugin.json (required)
cat > plugins/my-plugin/.claude-plugin/plugin.json << 'EOF'
{
  "name": "my-plugin",
  "description": "What this plugin does",
  "author": { "name": "Kodrea" }
}
EOF

# 3. Register in marketplace.json (see below)

# 4. Commit and push
git add . && git commit -m "Add my-plugin" && git push
```

### Step-by-Step Guide

#### 1. Create Plugin Directory Structure

```
plugins/my-plugin/
├── .claude-plugin/
│   └── plugin.json         # Required: plugin metadata
├── agents/                  # Optional: AI agents
│   └── my-agent.md
├── commands/                # Optional: slash commands
│   └── my-command.md
└── skills/                  # Optional: specialized skills
    └── my-skill/
        └── SKILL.md
```

#### 2. Create plugin.json (Required)

```json
{
  "name": "my-plugin",
  "description": "Brief description of what this plugin does",
  "author": {
    "name": "Kodrea",
    "email": ""
  }
}
```

#### 3. Register in marketplace.json

Edit `.claude-plugin/marketplace.json` and add your plugin to the `plugins` array:

```json
{
  "plugins": [
    {
      "name": "haiku-scout",
      "description": "Low-cost codebase mapping agent using Haiku",
      "version": "1.0.0",
      "author": { "name": "Kodrea" },
      "source": "./plugins/haiku-scout",
      "category": "development"
    },
    {
      "name": "my-plugin",
      "description": "What this plugin does",
      "version": "1.0.0",
      "author": { "name": "Kodrea" },
      "source": "./plugins/my-plugin",
      "category": "development"
    }
  ]
}
```

#### 4. Commit and Push

```bash
git add .
git commit -m "Add my-plugin"
git push
```

#### 5. Enable on Other Devices

```bash
# Pull latest changes
cd ~/.claude/plugins/marketplaces/local && git pull

# Enable in settings.json
# Add: "my-plugin@local": true
```

---

## Plugin Components Reference

### Agents (agents/*.md)

Agents are AI assistants spawned via the Task tool.

```markdown
---
name: my-agent
description: What the agent does (shown in Task tool)
model: haiku  # haiku (fast/cheap), sonnet (balanced), opus (powerful)
---

You are an agent that does X.

## Instructions
- Do this
- Then do that

## Output Format
Return results in this format...
```

**Usage:** `Task(subagent_type="my-plugin:my-agent", prompt="...")`

### Commands (commands/*.md)

Slash commands invoked with `/command-name`.

```markdown
---
description: Short description shown in /help
argument-hint: <required> [optional]
allowed-tools: [Read, Glob, Grep, Bash, Task]
model: haiku  # Optional: override model
---

# My Command

The user ran this command with arguments: $ARGUMENTS

## Instructions
1. Do this first
2. Then do that
3. Return results to user
```

**Usage:** `/my-command arg1 arg2`

### Skills (skills/*/SKILL.md)

Skills are specialized capabilities auto-invoked for certain tasks.

```markdown
---
name: my-skill
description: When to use this skill
triggers:
  - "keyword1"
  - "keyword2"
---

# My Skill

Instructions for handling this type of task...
```

---

## Examples

### Example: Code Review Agent

```bash
mkdir -p plugins/reviewer/.claude-plugin plugins/reviewer/agents

cat > plugins/reviewer/.claude-plugin/plugin.json << 'EOF'
{
  "name": "reviewer",
  "description": "Code review utilities",
  "author": { "name": "Kodrea" }
}
EOF

cat > plugins/reviewer/agents/quick-review.md << 'EOF'
---
name: quick-review
description: Fast code review using Haiku
model: haiku
---

You are a code reviewer. Review the code for:
- Bugs and logic errors
- Security issues
- Style problems

Be concise. List issues with file:line references.
EOF
```

### Example: Build Command

```bash
mkdir -p plugins/build/.claude-plugin plugins/build/commands

cat > plugins/build/.claude-plugin/plugin.json << 'EOF'
{
  "name": "build",
  "description": "Build utilities",
  "author": { "name": "Kodrea" }
}
EOF

cat > plugins/build/commands/build.md << 'EOF'
---
description: Build and test the project
argument-hint: [target]
allowed-tools: [Bash, Read]
---

# Build Command

Target: $ARGUMENTS (default: all)

Run the appropriate build command for this project type.
EOF
```

---

## Syncing

```bash
cd ~/.claude/plugins/marketplaces/local

# Pull updates
git pull

# Push your changes
git add . && git commit -m "Update" && git push
```
