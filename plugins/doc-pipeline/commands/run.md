---
description: Run the full documentation pipeline (fetch → scout → process → audit → PDF) on a section. Use when the user says "run the pipeline", "process section", "generate reference for", or wants to run the full doc generation workflow.
argument-hint: <section-name> [--from stage] [--prompt-variant name]
allowed-tools: [Read, Write, Edit, Bash, Glob, Grep, Task, AskUserQuestion]
---

# Documentation Pipeline Orchestrator

Run the 4-tier documentation pipeline on one or more sections: **fetch → scout → process → audit → PDF**.

This command runs in the main conversation and spawns agents via the Task tool for each tier.

## Arguments

$ARGUMENTS

Parse the arguments for:
- **section name** (required): e.g. `low-level-dev`, `app-development`, or `all`
- **--from stage** (optional): skip earlier stages, e.g. `--from processor` to re-process without re-scouting
- **--prompt-variant name** (optional): domain-specific prompt names for scout/processor/auditor

## Pipeline Stages

### Stage 1: Fetch (Bash)

Run the project's fetch script to download raw documentation:

```bash
python docs/pipeline.py <section_url> --section-name <section>
```

Skip this stage if `docs/sections/{section}/raw/` already has files and the user didn't request re-fetching.

### Stage 2: Scout (doc-pipeline:doc-scout agent, Haiku)

Spawn the doc-scout agent via Task tool:

```
Task: doc-scout agent
subagent_type: doc-pipeline:doc-scout
prompt: "Process section: {section}. Prompt: {scout_prompt_name}"
```

Wait for completion. Verify scout_gold/ has one JSON per raw file.

### Stage 3: Process (doc-pipeline:doc-processor agent, Sonnet)

Spawn the doc-processor agent via Task tool:

```
Task: doc-processor agent
subagent_type: doc-pipeline:doc-processor
prompt: "Process section: {section}. Prompt: {processor_prompt_name}"
```

Wait for completion. Verify `build_cache/REFERENCE_DRAFT.md` exists.

### Stage 4: Audit (doc-pipeline:doc-auditor agent, Opus)

Spawn the doc-auditor agent via Task tool:

```
Task: doc-auditor agent
subagent_type: doc-pipeline:doc-auditor
prompt: "Process section: {section}. Prompt: {auditor_prompt_name}"
```

Wait for completion. Verify `REFERENCE.md` exists.

### Stage 5: PDF (md-to-pdf skill)

Convert the final REFERENCE.md to PDF:

```bash
cd docs/sections/{section}
# Use the md-to-pdf skill or run make_pdf.py if it exists
```

## Orchestration Rules

1. **Run stages sequentially** — each depends on the previous stage's output.
2. **Verify between stages** — check that expected output files exist before proceeding.
3. **Report progress** — tell the user which stage is running and when each completes.
4. **Handle partial runs** — if the user says `--from processor`, skip fetch and scout.
5. **Handle "all" sections** — if section is "all", list directories under `docs/sections/` and run the pipeline for each sequentially.

## Error Handling

- If fetch fails: report the error and stop. The user needs to fix the URL or fetcher.
- If scout produces no JSONs: stop and report. Likely a prompt issue.
- If processor output is suspiciously small (< 1KB): warn the user before proceeding to audit.
- If audit finds major issues: report them. The user may want to re-process with a different prompt.

## Example Invocations

- `/doc-pipeline:run low-level-dev` → full fetch-to-PDF pipeline
- `/doc-pipeline:run camera-driver --from processor` → skip fetch and scout, re-synthesize and re-audit
- `/doc-pipeline:run all` → run only the scout stage on every section
- `/doc-pipeline:run other-os --prompt-variant scout-custom.md` → use custom prompt variant
