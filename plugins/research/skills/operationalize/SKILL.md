---
name: operationalize
description: Transform research reports into operational artifacts for Claude Code. Use when user says "operationalize", "distill this research", "make this actionable", "create quick reference", "ops docs from research", "operationalize the research", or wants to turn research output into machine-consumable reference files.
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Task, AskUserQuestion
---

# Operationalize Research

When triggered, run the `/research:operationalize` command to transform completed research into operational artifacts.

## How to proceed

1. Parse the user's message for the research slug and any flags (`--force`, `--integrate`).
2. If no slug is mentioned, list available research projects under `research/` and ask the user which one.
3. Invoke the `research:operationalize` command with the parsed arguments.

## Output

Three files written to `research/{slug}/ops/`:
- **QUICK-REFERENCE.md** — Always-loadable context (~100-150 lines): constraints, decision rules, commands, API signatures
- **COOKBOOK.md** — Complete, copy-paste code recipes by use case
- **RULES.md** — Hard limits, valid enums, error patterns, decision trees (~50-100 lines)

Plus an auditable intermediate: `extraction.json` (structured data from which the above are generated).
