# subagent-builder

Design well-shaped Claude Code subagents and agent teams with thinking effort matched to role.

## Trigger phrases

The skill auto-loads on any of:

- "build me an agent"
- "I need a critic / scout / analyst / subagent"
- "design an agent team for X"
- "help me scope this role"
- "turn this workflow into agents"
- "create an agent definition"
- "what frontmatter fields does a subagent need"
- "configure a subagent for Y task"

## What it produces

A validated Claude Code agent definition file (`.md` with YAML frontmatter + system prompt body),
with all six design decisions justified:

1. Archetype (from the starter catalog, or bespoke)
2. Model (full model ID + rationale)
3. Effort level (primary lever — `low` / `medium` / `high` / `xhigh` / `max`)
4. Tool list (minimum-capability)
5. Permission mode (explicit, not inherited)
6. Isolation (single subagent vs. team teammate)

## Design philosophy

**Effort first.** A scout that inherits session effort silently burns max-cost deliberation
on pattern matching. This skill routes role characteristics to an effort level first; model
and tools follow from that choice.

## Reference material (bundled)

- `skills/subagent-builder/reference/schemas/` — 10 XML field specs (frontmatter, tools, teams)
- `skills/subagent-builder/reference/annotated/` — annotated docs with cost and effort guidance
- `skills/subagent-builder/reference/role-archetypes.xml` — 8 starter archetypes
- `skills/subagent-builder/reference/anti-patterns.md` — 10 anti-patterns with citations
- `skills/subagent-builder/examples/` — 3 worked examples (scout/Haiku, analyst/Sonnet, critic/Opus)

## Updating reference material

Reference files are sourced from `agents-research` worktree. Re-sync when Anthropic docs update:
run the fetch + parse pipeline, copy updated files from `research/schemas/` and `research/annotated/`,
bump the plugin version, and reinstall.
