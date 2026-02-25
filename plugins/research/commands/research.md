---
description: "Run a tiered research pipeline on any topic. Use when the user says 'research X', 'use tiered subagent approach', 'tiered research', or '/research'."
argument-hint: "<topic> [--domain codebase|web|mixed] [--from scout|analyst|auditor] [--files ...] [--urls ...] [--slug name]"
allowed-tools: [Read, Write, Edit, Bash, Glob, Grep, WebSearch, WebFetch, Task, AskUserQuestion]
---

# Research Pipeline Orchestrator

Run a 3-tier research pipeline on any topic: **scout (Haiku) -> analyst (Sonnet) -> auditor (Opus)**.

This command runs in the main conversation and spawns agents via the Task tool for each tier.

## Arguments

$ARGUMENTS

Parse the arguments for:
- **topic** (required): free-text research subject
- **--domain**: `codebase`|`web`|`mixed` (infer from context if omitted — files/globs suggest codebase, URLs suggest web, both or ambiguous suggest mixed)
- **--from**: resume from a later stage, skipping earlier ones (`analyst` skips scouts, `auditor` skips both)
- **--files**: explicit file paths or glob patterns to research
- **--urls**: explicit URLs to research
- **--slug**: output directory name (default: derive from topic — lowercase, hyphens, max 40 chars, e.g. "rk3566-mipi-csi2")

If the topic is too vague (fewer than 3 words AND no --files/--urls provided), use AskUserQuestion to ask the user to clarify scope.

---

## Phase 1 — Discovery

**Skip if:** user provided `--files`/`--urls` that fully cover the scope, OR resuming with `--from analyst` or `--from auditor`.

### Codebase domain
- Run 2-4 Glob calls to find relevant files by pattern.
- Run 2-3 Grep calls to find files containing key terms from the topic.
- Merge results, deduplicate, rank by relevance.
- **Cap at 80 files.** If more than 80 match, select the most relevant and suggest the user run multiple focused passes.

### Web domain
- Run 1-2 WebSearch calls with topic keywords.
- Collect result URLs. **Cap at 30 URLs.**

### Mixed domain
- Run both codebase and web discovery. Merge into a single source manifest.

### Source manifest format
Build an internal list:
```
[{type: "file"|"url", location: "path or URL", relevance_note: "why included"}]
```

If discovery finds **zero sources**: use AskUserQuestion to ask the user to refine the topic or provide explicit paths/URLs. **Never spawn scouts with zero sources.**

---

## Phase 2 — Scout Allocation

Determine how many scouts to spawn based on source count:

| Sources | Scouts |
|---------|--------|
| 1-3 files or 1-2 URLs | 1 |
| 4-10 files or 3-5 URLs | 2 |
| 11-30 files or 6-15 URLs | 3-4 |
| 31-50 files or 16-25 URLs | 5-6 |
| 50+ files or 25+ URLs | 7-8 (hard cap) |

Target per codebase scout: ~5-10 files or ~20K tokens of source material.
Target per web scout: ~3-5 pages.

Distribute sources across scouts, keeping related files together when possible (e.g. files from the same directory).

---

## Phase 3 — Generate Extraction Schema

Craft 5-10 topic-specific extraction categories based on the research topic. Examples:

- **Kernel drivers:** `[initialization, register_access, interrupt_handling, power_management, dt_binding, data_structures, error_paths]`
- **API docs:** `[endpoints, authentication, request_format, response_format, error_codes, rate_limits, examples]`
- **Architecture:** `[entry_points, data_flow, dependencies, configuration, public_api, state_management]`
- **General codebase:** `[purpose, key_functions, data_structures, control_flow, error_handling, configuration, dependencies]`

The core JSON schema that all scouts must produce:

```json
{
  "scout_id": "scout-001",
  "sources_processed": [
    { "location": "file:line or URL", "type": "file|url", "status": "success|partial|failed" }
  ],
  "findings": [
    {
      "category": "string (from extraction categories)",
      "subcategory": "string|null",
      "summary": "one sentence",
      "raw_excerpt": "VERBATIM quoted text - mandatory, never paraphrased",
      "source_location": "file:line or URL#section",
      "relevance": "high|medium|low",
      "tags": ["freeform"]
    }
  ],
  "cross_references": [
    { "from": "source_location", "to": "source_location", "relationship": "calls|imports|extends|documents|contradicts" }
  ],
  "gaps": ["things expected but not found"],
  "metadata": {
    "total_sources": 0,
    "total_findings": 0,
    "processing_notes": "any issues encountered"
  }
}
```

Scouts may add extra fields to individual findings (e.g. `register_address`, `http_method`) but the core fields above are mandatory.

---

## Phase 4 — Setup Output Directory

Create the output directory structure:

```bash
mkdir -p research/{slug}/scout
mkdir -p research/{slug}/analysis
```

The final structure will be:
```
research/{slug}/
  scout/           # Haiku JSONs (audit trail - never delete)
  analysis/        # Sonnet draft
  REPORT.md        # Final audited output
  metadata.json    # Research config and stage completion tracking
```

Write `research/{slug}/metadata.json` with the research brief:
```json
{
  "topic": "...",
  "domain": "codebase|web|mixed",
  "slug": "...",
  "created": "ISO timestamp",
  "sources": [... source manifest ...],
  "extraction_categories": [...],
  "stages_completed": []
}
```

**Slug collision handling:** If `research/{slug}/` already exists and `--from` was NOT specified, use AskUserQuestion to ask: overwrite, rename, or resume from last completed stage.

---

## Phase 5 — Scout Execution

Spawn ALL scouts in parallel via Task tool:

```
subagent_type: research:research-scout
model: haiku
prompt: |
  SCOUT ID: scout-{NNN}
  RESEARCH TOPIC: {topic}
  OUTPUT FILE: research/{slug}/scout/scout-{NNN}.json
  SOURCES TO PROCESS:
  {list of assigned sources with paths/URLs}
  EXTRACTION CATEGORIES: {categories list}
  EXTRACTION FOCUS: {any specific focus areas from topic}
  OUTPUT SCHEMA:
  {the JSON schema from Phase 3}
```

After all scouts complete:

**Verification checkpoint:**
1. Parse each output JSON file. Check it is valid JSON.
2. If >50% of scouts produced 0 findings: use AskUserQuestion to ask whether to continue or refine the topic.
3. If any JSON is malformed: offer to re-run only the failed scouts.

Update `metadata.json` → add `"scout"` to `stages_completed`.

---

## Phase 6 — Analyst Execution

Spawn a single Sonnet agent:

```
subagent_type: research:research-analyst
model: sonnet
prompt: |
  RESEARCH TOPIC: {topic}
  SCOUT DIRECTORY: research/{slug}/scout/
  OUTPUT FILE: research/{slug}/analysis/DRAFT.md
  EXTRACTION CATEGORIES: {categories list}
```

After completion:

**Verification:**
- Check `research/{slug}/analysis/DRAFT.md` exists.
- If file is <2KB: warn user the draft seems thin.
- If file is >100KB: warn user the draft is very large.

Update `metadata.json` → add `"analyst"` to `stages_completed`.

---

## Phase 7 — Auditor Execution

Spawn a single Opus agent:

```
subagent_type: research:research-auditor
model: opus
prompt: |
  RESEARCH TOPIC: {topic}
  SCOUT DIRECTORY: research/{slug}/scout/
  DRAFT FILE: research/{slug}/analysis/DRAFT.md
  OUTPUT FILE: research/{slug}/REPORT.md
  SOURCES: {source manifest for spot-checking}
```

After completion:

**Verification:**
- Check `research/{slug}/REPORT.md` exists.
- If REPORT.md is smaller than the draft: warn user that content may have been dropped.

Update `metadata.json` → add `"auditor"` to `stages_completed`.

---

## Phase 8 — Summary

Print a summary to the user:

```
Research complete: {topic}
Domain: {domain}
Scouts: {N} | Sources: {M} | Findings: {F total across all scout JSONs}
Output: research/{slug}/REPORT.md
Scout JSONs: research/{slug}/scout/
Draft: research/{slug}/analysis/DRAFT.md
```

---

## Orchestration Rules

1. **Run stages sequentially** — each depends on the previous stage's output.
2. **Scouts run in parallel** within their stage.
3. **Verify between stages** — check that expected output files exist before proceeding.
4. **Report progress** — tell the user which stage is running and when each completes.
5. **Handle --from** — if `--from analyst`, skip phases 1-5 and go straight to analyst. If `--from auditor`, skip to auditor. The slug must exist with prior stage outputs.
6. **Core invariant:** Haiku scouts write JSON files to disk with verbatim excerpts. Opus reads those files directly — never relying on Sonnet to relay information. The scout JSONs are the audit trail.

## Error Handling

- If discovery finds nothing: AskUserQuestion to refine. Never spawn scouts with zero sources.
- If >50% scouts produce 0 findings: AskUserQuestion whether to continue.
- If any scout JSON is malformed: offer to re-run failed scouts only.
- If analyst draft is suspiciously small (<2KB): warn before proceeding to auditor.
- If auditor drops content (REPORT < DRAFT size): warn user.
