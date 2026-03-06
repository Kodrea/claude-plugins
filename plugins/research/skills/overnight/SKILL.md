---
name: overnight
description: Run multi-round iterative research with gap-driven follow-up and adversarial audit. Use when user says "overnight research", "deep iterative research", "multi-round research", "research overnight", "thorough multi-pass research", or wants iterative research that runs multiple rounds with gap analysis.
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, WebSearch, WebFetch, Task, AskUserQuestion
---

# Overnight Research Pipeline

When triggered, run the `/research:overnight` command with the user's topic. This skill is the natural-language entry point for the multi-round overnight research pipeline.

## How to proceed

1. Parse the user's message for the research topic only.
2. Invoke the `research:overnight` command — it will immediately use AskUserQuestion to collect optional settings (rounds, domain, slug) before starting.

## Quick reference

The pipeline runs iterative rounds:
- **Scout (Haiku):** Fast extraction — reads sources, produces structured JSON with verbatim excerpts
- **Analyst (Sonnet):** Synthesizes scout JSONs into a draft, building on prior rounds
- **Compiler (Opus):** Analyzes gaps, estimates marginal gain, decides whether to run another round
- **Adversarial Auditor (Opus):** Independent verification of highest-stakes claims
- **Final:** Merges report, generates PDF, sends Discord notification

Output goes to `research/{slug}/` with per-round directories, adversarial audit, and final REPORT.md/REPORT.pdf.
