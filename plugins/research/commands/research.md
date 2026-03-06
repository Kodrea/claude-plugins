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
- **URL pre-validation:** WebFetch the first 1KB of each candidate URL. Drop URLs that return: HTTP errors, <100 chars of content, or security challenge text (e.g. "enable JavaScript", "captcha"). Replace dropped URLs with next-best WebSearch results. Log each drop: `[PIPELINE] url_dropped={URL} reason={reason}`
- Collect validated URLs. **Cap at 30 URLs.**

### Mixed domain
- Run both codebase and web discovery. Merge into a single source manifest.

### Source manifest format
Build an internal list:
```
[{type: "file"|"url", location: "path or URL", relevance_note: "why included"}]
```

If discovery finds **zero sources**: use AskUserQuestion to ask the user to refine the topic or provide explicit paths/URLs. **Never spawn scouts with zero sources.**

After discovery completes, print: `[PIPELINE] phase=discovery status=complete sources_found={N} domain={domain}`

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

After allocation, print: `[PIPELINE] phase=scout-allocation status=complete scout_count={N} rationale="{reason}"`

---

## Phase 3 — Generate Extraction Schema

Split categories into two tiers:
- **Core categories (5-6):** must-cover topics, gaps reported for these
- **Adjacent categories (4-5):** extract if found, no gap reporting

Format in the scout prompt: `CORE CATEGORIES=[...] ADJACENT CATEGORIES=[...]`

Craft topic-specific extraction categories based on the research topic. Examples:

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
      "claim_era": "2025-2026|historical-context|projection",
      "tags": ["freeform"]
    }
  ],
  "cross_references": [
    { "from": "source_location", "to": "source_location", "relationship": "calls|imports|extends|documents|contradicts" }
  ],
  "gaps": [{"description": "what was expected but not found", "gap_type": "source_failure|knowledge_gap"}],
  "metadata": {
    "total_sources": 0,
    "total_findings": 0,
    "source_success_rate": 0.0,
    "processing_notes": "any issues encountered"
  }
}
```

**Backward compatibility:** If gaps contain bare strings (from older scout runs), treat each as `{"description": str, "gap_type": "knowledge_gap"}`.

Scouts may add extra fields to individual findings (e.g. `register_address`, `http_method`) but the core fields above are mandatory.

After schema generation, print: `[PIPELINE] phase=schema-gen status=complete categories={N} list=[{csv}]`

---

## Phase 4 — Setup Output Directory

Create the output directory structure:

```bash
mkdir -p research/{slug}/scout
mkdir -p research/{slug}/analysis
mkdir -p research/{slug}/cache
```

The final structure will be:
```
research/{slug}/
  scout/           # Haiku JSONs (audit trail - never delete)
  analysis/        # Sonnet draft
  cache/           # Cached web content from scouts (URL first line, content after)
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

After output setup, print: `[PIPELINE] phase=output-setup status=complete slug={slug}`

---

## Phase 5 — Scout Execution

Before spawning, print: `[PIPELINE] phase=scout-exec status=started scout_count={N}`

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
  CORE CATEGORIES: {core categories list}
  ADJACENT CATEGORIES: {adjacent categories list}
  EXTRACTION FOCUS: {any specific focus areas from topic}
  CACHE DIRECTORY: research/{slug}/cache/
  OUTPUT SCHEMA:
  {the JSON schema from Phase 3}
```

After each scout completes, print: `[PIPELINE] scout={id} status={pass|fail} findings={N}`

After all scouts complete, print: `[PIPELINE] phase=scout-exec status=complete total_findings={F} checkpoint={pass|warn|fail}`

**Verification checkpoint:**
1. Parse each output JSON file. Check it is valid JSON.
2. If >50% of scouts produced 0 findings: use AskUserQuestion to ask whether to continue or refine the topic.
3. If any JSON is malformed: offer to re-run only the failed scouts.
4. **Source success rate check:** Check each scout's `metadata.source_success_rate`. Log degraded scouts (<0.5): `[PIPELINE] scout={id} source_success_rate={rate} status=degraded`
5. **Retry degraded scouts:** For each scout with rate <0.5, collect its failed sources, spawn a retry scout (`scout-{NNN}-retry`) with only the failed sources. Max one retry per original scout. Log: `[PIPELINE] retry_scout={id} failed_sources={N}`
6. **Gap deduplication:** Collect all gaps from all scouts. Merge gaps sharing 3+ significant words (excluding stopwords: the, a, an, of, in, to, for, and, or, is, are, was, were, not, no, with, from, by, on, at, this, that). Write `deduplicated_gaps` to `metadata.json`. Log: `[PIPELINE] gaps_raw={N} gaps_deduped={M}`

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

After completion, print: `[PIPELINE] phase=analyst status=complete draft_size={bytes}`

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
  CACHE DIRECTORY: research/{slug}/cache/
  REVIEW NOTES: research/{slug}/analysis/REVIEW-NOTES.md
```

After completion, print: `[PIPELINE] phase=auditor status=complete corrections={N} verdict={PASS|PASS_WITH_WARNINGS}`

**Verification:**
- Check `research/{slug}/REPORT.md` exists.
- If REPORT.md is smaller than the draft: warn user that content may have been dropped.

Update `metadata.json` → add `"auditor"` to `stages_completed`.

---

## Phase 8 — Summary

Print: `[PIPELINE] phase=summary status=complete`

Then print a summary to the user:

```
Research complete: {topic}
Domain: {domain}
Scouts: {N} | Sources: {M} | Findings: {F total across all scout JSONs}
Output: research/{slug}/REPORT.md
Scout JSONs: research/{slug}/scout/
Draft: research/{slug}/analysis/DRAFT.md

Run `/research:operationalize {slug}` to create operational artifacts (quick reference, cookbook, rules).
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
