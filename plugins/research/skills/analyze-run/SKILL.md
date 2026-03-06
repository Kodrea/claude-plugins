---
name: analyze-run
description: Analyze a completed research pipeline run to produce timing, token usage, and quality metrics. Use when user says "analyze the run", "run report", "pipeline metrics", "how did the research go", "research run stats", "what happened in that run", or wants post-run analysis of a research pipeline execution.
allowed-tools: Read, Write, Bash, Glob, Grep
---

# Research Run Analyzer

When triggered, run the `/research:analyze-run` command to analyze a completed research pipeline run.

## How to proceed

1. Parse the user's message for optional `--session` UUID or `--slug` name.
2. Invoke the `research:analyze-run` command with any provided arguments.
3. The command handles session discovery, JSONL parsing, output correlation, and report generation.

## Output

Two files written to `research/{slug}/`:
- **RUN-REPORT.md** — human-readable run report with timeline, agent metrics, quality signals, and improvement suggestions
- **run-metrics.json** — machine-readable metrics for programmatic analysis
