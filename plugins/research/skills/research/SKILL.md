---
name: research
description: Tiered subagent research pipeline (scout → analyst → auditor). Use when user says "tiered subagent approach", "tiered research", "use the research pipeline", "scout analyst auditor", "multi-tier research", "research this thoroughly", "deep research on", or wants to run a structured multi-agent investigation on any topic — codebase, web, or mixed.
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, WebSearch, WebFetch, Task, AskUserQuestion
---

# Tiered Research Pipeline

When triggered, run the `/research` command with the user's topic. This skill is the natural-language entry point for the research pipeline.

## How to proceed

1. Parse the user's message for the research topic and any preferences (codebase vs web, specific files/URLs).
2. Invoke the `research:research` command by running the full pipeline as described in the research command.

## Quick reference

The pipeline has 3 tiers:
- **Scout (Haiku):** Fast, cheap extraction — reads sources, produces structured JSON with verbatim excerpts
- **Analyst (Sonnet):** Synthesizes scout JSONs into a coherent draft document
- **Auditor (Opus):** Verifies the draft against original sources, produces final `{slug}-report.md`

Output goes to `research/{slug}/` with scout JSONs, analyst draft, and final report.
