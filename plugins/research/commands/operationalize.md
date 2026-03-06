---
description: "Transform research into operational artifacts for Claude Code. Use when user says 'operationalize', 'distill', 'make actionable', 'create quick reference', or wants to convert research output to machine-consumable files."
argument-hint: "<slug> [--force] [--integrate]"
allowed-tools: [Read, Write, Edit, Bash, Glob, Grep, Task, AskUserQuestion]
---

# Operationalize Command

Transform a completed research pipeline output into three operational artifacts optimized for Claude Code consumption.

This command runs in the main conversation and spawns agents via the Task tool for extraction and formatting.

## Arguments

$ARGUMENTS

Parse the arguments for:
- **slug** (required): the research project slug (e.g. `qwen3-tts`)
- **--force**: overwrite existing `ops/` directory without asking
- **--integrate**: append reference block to project CLAUDE.md after completion

If no slug is provided, use AskUserQuestion to ask the user which research project to operationalize. List available slugs by running `ls research/`.

---

## Phase 1 — Validate

1. **Check research directory exists:**
   - Verify `research/{slug}/` exists using Glob.
   - If not found: tell the user and stop.

2. **Check REPORT.md exists:**
   - Verify `research/{slug}/REPORT.md` exists.
   - If not found: tell the user the research hasn't been completed yet and stop.

3. **Check audit status:**
   - Read `research/{slug}/metadata.json`.
   - Check that `stages_completed` contains `"auditor"`.
   - If not: warn the user that the research hasn't been audited. Use AskUserQuestion to ask whether to proceed anyway or stop.

4. **Handle existing ops directory:**
   - Check if `research/{slug}/ops/` already exists.
   - If it exists AND `--force` was NOT passed: use AskUserQuestion to ask whether to overwrite or skip.
   - If it exists AND `--force` was passed: proceed (will overwrite).

Print: `[OPS] phase=validate status=complete slug={slug}`

---

## Phase 2 — Extract

Create the ops output directory:
```bash
mkdir -p research/{slug}/ops
```

Spawn the ops-extractor agent (Haiku) via Task:

```
subagent_type: research:ops-extractor
model: haiku
prompt: |
  SLUG: {slug}
  REPORT FILE: research/{slug}/REPORT.md
  SCOUT DIRECTORY: research/{slug}/scout/
  METADATA FILE: research/{slug}/metadata.json
  OUTPUT FILE: research/{slug}/ops/extraction.json
```

**Verification after extraction:**
1. Check `research/{slug}/ops/extraction.json` exists.
2. Read the file and verify it parses as valid JSON.
3. Check that at least 2 of these sections are non-empty arrays: `constraints.hard_limits`, `commands`, `recipes`, `gotchas`, `decision_trees`.
4. If verification fails: report the issue to the user. Offer to re-run extraction.

Print: `[OPS] phase=extract status=complete items={total items across all sections}`

---

## Phase 3 — Format

Spawn the ops-formatter agent (Sonnet) via Task:

```
subagent_type: research:ops-formatter
model: sonnet
prompt: |
  SLUG: {slug}
  EXTRACTION FILE: research/{slug}/ops/extraction.json
  METADATA FILE: research/{slug}/metadata.json
  OUTPUT DIRECTORY: research/{slug}/ops/
```

**Verification after formatting:**
1. Check all three files exist:
   - `research/{slug}/ops/QUICK-REFERENCE.md`
   - `research/{slug}/ops/COOKBOOK.md`
   - `research/{slug}/ops/RULES.md`
2. Check QUICK-REFERENCE.md is ≤200 lines (soft limit — warn if over 150).
3. Check RULES.md is ≤150 lines (soft limit — warn if over 100).
4. If any file is missing: report the issue and offer to re-run formatting.

Print: `[OPS] phase=format status=complete files=3`

---

## Phase 4 — Integrate (optional)

**Only run if `--integrate` flag was passed.**

1. Find the project's CLAUDE.md file. Check these paths in order:
   - `CLAUDE.md` (project root)
   - `.claude/CLAUDE.md`
   - If neither exists: create `CLAUDE.md` at project root.

2. Append this reference block (do not duplicate if already present):

```markdown

## Operational Reference: {topic}

- Quick Reference: `research/{slug}/ops/QUICK-REFERENCE.md`
- Cookbook: `research/{slug}/ops/COOKBOOK.md`
- Rules: `research/{slug}/ops/RULES.md`
- Full Report: `research/{slug}/REPORT.md`
```

3. Print: `[OPS] phase=integrate status=complete target={path to CLAUDE.md}`

If `--integrate` was NOT passed, skip this phase and print:
`[OPS] phase=integrate status=skipped (use --integrate to add references to CLAUDE.md)`

---

## Phase 5 — Finalize

1. **Update metadata.json:**
   - Read `research/{slug}/metadata.json`.
   - Add `"ops"` to `stages_completed` array (if not already present).
   - Write the updated metadata back.

2. **Print summary:**

```
Operationalization complete: {topic}
Slug: {slug}

Output files:
  research/{slug}/ops/extraction.json    — structured extraction ({N} items)
  research/{slug}/ops/QUICK-REFERENCE.md — always-loadable context ({N} lines)
  research/{slug}/ops/COOKBOOK.md         — copy-paste recipes ({N} lines)
  research/{slug}/ops/RULES.md           — hard limits & decision trees ({N} lines)

Run `/research:operationalize {slug} --integrate` to add references to CLAUDE.md.
```

Print: `[OPS] phase=finalize status=complete`

---

## Error Handling

- If research directory doesn't exist: stop with clear message.
- If REPORT.md missing: stop — research not completed.
- If metadata.json missing or unreadable: warn but attempt to proceed (extract from REPORT.md alone).
- If extraction produces empty JSON: ask user whether to proceed or investigate.
- If any formatter output is missing: offer to re-run formatter only.
- Never silently skip phases. Always report what happened.
