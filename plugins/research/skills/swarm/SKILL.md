---
name: swarm
description: Run collaborative team research with a swarm of communicating agents. Use when user says "swarm research", "research swarm", "ultra research", "team research", "collaborative research", or wants maximum-depth multi-agent investigation.
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, WebSearch, WebFetch, AskUserQuestion, TeamCreate, TeamDelete, SendMessage, Task
---

# Swarm Research Pipeline

When triggered, run the `/research:swarm` command with the user's topic. This skill is the natural-language entry point for the collaborative swarm research pipeline.

## How to proceed

1. Parse the user's message for the research topic only.
2. Invoke the `research:swarm` command — it will immediately use AskUserQuestion to collect optional settings (preset, domain, slug, composable) before starting.

## Quick reference

The swarm pipeline creates a team of communicating Sonnet agents:
- **Lead (you):** Creates team, assigns subtopics, monitors, assembles final REPORT.md
- **Scouts (3-8):** Source discovery + JSON extraction, message analysts with leads
- **Analysts (2-5):** Deep-dive on threads, request more sources from scouts
- **Synthesizer (1):** Monitors findings, identifies patterns/gaps, signals convergence
- **Adversarial (1):** Independent verification, bias detection, challenges weak evidence

Preset profiles:
- **standard** (default): 5 scouts, 3 analysts — balanced breadth and depth
- **wide**: 8 scouts, 2 analysts — maximum source coverage
- **deep**: 3 scouts, 5 analysts — fewer sources, exhaustive analysis

Output goes to `research/{slug}/` with swarm-specific structure (scout-findings/, analysis/, synthesis/, adversarial/) and final REPORT.md/REPORT.pdf.

Optional `--composable` flag outputs in overnight-compatible format for continuation with `/research:overnight --from round-2`.
