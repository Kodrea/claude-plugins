---
description: Scout the current project with haiku-scout agent (fast, low-cost codebase mapping)
argument-hint: [path or focus area]
allowed-tools: [Task, Read, Glob, Grep]
---

# Scout Command

Use the haiku-scout agent to quickly map this codebase.

## Arguments

$ARGUMENTS

## Instructions

Launch the `haiku-scout:haiku-scout` agent to scout the current project directory.

If the user provided arguments:
- If it looks like a path, scout that specific directory
- If it's descriptive text (e.g., "authentication", "api layer"), focus the scout on that area

Use the Task tool with these parameters:
- `subagent_type`: "haiku-scout:haiku-scout"
- `model`: "haiku"
- `prompt`: "Scout the [target] project. Map the codebase structure, identify key files, their purposes, important symbols, and provide line references. [Include any focus area from arguments]"

After the scout completes, summarize the key findings for the user.
