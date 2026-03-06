---
description: "Run multi-round iterative research with gap-driven follow-up and adversarial audit. Use when the user says 'overnight research', 'deep iterative research', 'multi-round research', or '/overnight'."
argument-hint: "<topic> [--rounds N] [--domain web|codebase|mixed] [--slug name]"
allowed-tools: [Read, Write, Edit, Bash, Glob, Grep, WebSearch, WebFetch, Task, AskUserQuestion]
---

# Overnight Research Pipeline Orchestrator

Run a multi-round iterative research pipeline with gap-driven follow-up rounds and adversarial audit:
**scout (Haiku) -> analyst (Sonnet) -> compiler (Opus) -> [repeat if gaps] -> adversarial audit (Opus) -> PDF + Discord notification**

This command runs in the main conversation and spawns agents via the Task tool for each tier.

## Arguments

$ARGUMENTS

Parse the arguments for:
- **topic** (required): free-text research subject
- **--rounds**: maximum number of research rounds (default: 3)
- **--domain**: `codebase`|`web`|`mixed` (infer from context if omitted — files/globs suggest codebase, URLs suggest web, both or ambiguous suggest mixed)
- **--slug**: output directory name (default: derive from topic — lowercase, hyphens, max 40 chars)

If the topic is too vague (fewer than 3 words), use AskUserQuestion to ask the user to clarify scope.

---

## Phase 0 — Setup

1. Parse arguments. Default `--rounds 3` if not specified.
2. Derive slug from topic if not provided (lowercase, hyphens, max 40 chars).
3. Create directory structure:

```bash
mkdir -p research/{slug}/cache
mkdir -p research/{slug}/round-1/scout
mkdir -p research/{slug}/round-1/analysis
```

4. Write `research/{slug}/metadata.json`:
```json
{
  "topic": "...",
  "domain": "codebase|web|mixed",
  "slug": "...",
  "max_rounds": N,
  "created": "ISO timestamp",
  "sources": [],
  "extraction_categories": [],
  "core_categories": [],
  "adjacent_categories": [],
  "stages_completed": [],
  "rounds_completed": 0,
  "deduplicated_gaps": []
}
```

5. **Slug collision handling:** If `research/{slug}/` already exists, use AskUserQuestion to ask: overwrite, rename, or resume from last completed round.

Print: `[OVERNIGHT] phase=setup status=complete slug={slug} max_rounds={N}`

---

## Phase 1 — Round 1 Discovery & Scouting

### Discovery (same as v1.2.0 Phase 1)

**Codebase domain:**
- Run 2-4 Glob calls to find relevant files by pattern.
- Run 2-3 Grep calls to find files containing key terms.
- Merge, deduplicate, rank by relevance. Cap at 80 files.

**Web domain:**
- Run 1-2 WebSearch calls with topic keywords.
- **URL pre-validation:** WebFetch the first 1KB of each candidate URL. Drop URLs that return HTTP errors, <100 chars of content, or security challenge text. Replace dropped URLs with next-best results.
- Collect validated URLs. Cap at 30 URLs.

**Mixed domain:** Run both, merge into single source manifest.

Build source manifest:
```
[{type: "file"|"url", location: "path or URL", relevance_note: "why included"}]
```

If discovery finds **zero sources**: use AskUserQuestion to refine. Never spawn scouts with zero sources.

Update metadata.json with `sources` array.

Print: `[OVERNIGHT] phase=discovery status=complete sources_found={N} domain={domain}`

### Scout Allocation (same as v1.2.0 Phase 2)

| Sources | Scouts |
|-|-|
| 1-3 files or 1-2 URLs | 1 |
| 4-10 files or 3-5 URLs | 2 |
| 11-30 files or 6-15 URLs | 3-4 |
| 31-50 files or 16-25 URLs | 5-6 |
| 50+ files or 25+ URLs | 7-8 (hard cap) |

Print: `[OVERNIGHT] phase=scout-allocation status=complete scout_count={N}`

### Extraction Schema (same as v1.2.0 Phase 3)

Split categories into:
- **Core categories (5-6):** must-cover, gaps reported
- **Adjacent categories (4-5):** extract if found, no gap reporting

Update metadata.json with `extraction_categories`, `core_categories`, `adjacent_categories`.

The core JSON schema for scouts:
```json
{
  "scout_id": "scout-001",
  "sources_processed": [
    { "location": "file:line or URL", "type": "file|url", "status": "success|partial|failed" }
  ],
  "findings": [
    {
      "category": "string",
      "subcategory": "string|null",
      "summary": "one sentence",
      "raw_excerpt": "VERBATIM quoted text - mandatory",
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
    "processing_notes": "any issues"
  }
}
```

Print: `[OVERNIGHT] phase=schema-gen status=complete categories={N}`

### Scout Execution

Spawn ALL scouts in parallel via Task tool:

```
subagent_type: research:research-scout
model: haiku
prompt: |
  SCOUT ID: scout-{NNN}
  RESEARCH TOPIC: {topic}
  OUTPUT FILE: research/{slug}/round-1/scout/scout-{NNN}.json
  SOURCES TO PROCESS:
  {list of assigned sources}
  EXTRACTION CATEGORIES: {categories list}
  CORE CATEGORIES: {core categories list}
  ADJACENT CATEGORIES: {adjacent categories list}
  EXTRACTION FOCUS: {specific focus from topic}
  CACHE DIRECTORY: research/{slug}/cache/
  OUTPUT SCHEMA:
  {the JSON schema}
```

After each scout completes, print: `[OVERNIGHT] scout={id} status={pass|fail} findings={N}`
After all complete: `[OVERNIGHT] phase=round-1-scouts status=complete total_findings={F}`

### Post-Scout Verification (same as v1.2.0 Phase 5)

1. Parse each output JSON. Check valid JSON.
2. If >50% scouts produced 0 findings: AskUserQuestion whether to continue.
3. Malformed JSON: offer to re-run failed scouts only.
4. **Source success rate:** Log degraded scouts (<0.5): `[OVERNIGHT] scout={id} source_success_rate={rate} status=degraded`
5. **Retry degraded scouts:** Spawn retry scout (`scout-{NNN}-retry`) with failed sources. Max one retry per original.
6. **Gap deduplication:** Merge gaps sharing 3+ significant words (excluding stopwords). Write `deduplicated_gaps` to metadata.json.

Print: `[OVERNIGHT] gaps_raw={N} gaps_deduped={M}`

Update metadata.json: add `"round-1-scout"` to `stages_completed`.

---

## Phase 2 — Round 1 Analysis

Spawn `research:overnight-analyst` (Sonnet):

```
subagent_type: research:overnight-analyst
model: sonnet
prompt: |
  RESEARCH TOPIC: {topic}
  SCOUT DIRECTORY: research/{slug}/round-1/scout/
  OUTPUT FILE: research/{slug}/round-1/analysis/DRAFT.md
  EXTRACTION CATEGORIES: {categories list}
  CORE CATEGORIES: {core categories list}
  ADJACENT CATEGORIES: {adjacent categories list}
  ROUND NUMBER: 1
```

No PRIOR DRAFT for round 1 — analyst behaves like standard analyst with improvements.

**Verification:**
- Check `research/{slug}/round-1/analysis/DRAFT.md` exists.
- If <2KB: warn draft seems thin.
- If >100KB: warn draft is very large.

Print: `[OVERNIGHT] phase=round-1-analysis status=complete draft_size={bytes}`

Update metadata.json: add `"round-1-analysis"` to `stages_completed`.

---

## Phase 3 — Compilation (Opus)

Spawn `research:research-compiler`:

```
subagent_type: research:research-compiler
model: opus
prompt: |
  RESEARCH TOPIC: {topic}
  ROUND NUMBER: 1
  MAX ROUNDS: {max_rounds}
  DRAFT FILE: research/{slug}/round-1/analysis/DRAFT.md
  REVIEW NOTES FILE: research/{slug}/round-1/analysis/REVIEW-NOTES.md
  SCOUT DIRECTORY: research/{slug}/round-1/scout/
  EXTRACTION CATEGORIES: {categories list}
  CORE CATEGORIES: {core categories list}
  METADATA FILE: research/{slug}/metadata.json
  OUTPUT FILE: research/{slug}/round-1/compilation.md
```

**After completion:**
1. Read `research/{slug}/round-1/compilation.md`.
2. Parse the `## Decision` section for CONTINUE or FINALIZE.
3. If CONTINUE: extract scout prompts from `## Next Round Scout Prompts`.
4. Print: `[OVERNIGHT] phase=round-1-compilation status=complete decision={CONTINUE|FINALIZE} marginal_gain={X}%`

Update metadata.json: add `"round-1-compilation"` to `stages_completed`.

**Decision point:** If FINALIZE, skip to Phase 7 (Adversarial Audit). If CONTINUE, proceed to Phase 4.

---

## Phase 4 — Round N Scouting (N >= 2)

Create round directory:
```bash
mkdir -p research/{slug}/round-{N}/scout
mkdir -p research/{slug}/round-{N}/analysis
```

Parse the compiler's scout prompts from the prior round's compilation.md. For each scout assignment:

```
subagent_type: research:research-scout
model: haiku
prompt: |
  SCOUT ID: scout-r{N}-{NNN}
  RESEARCH TOPIC: {topic}
  OUTPUT FILE: research/{slug}/round-{N}/scout/scout-r{N}-{NNN}.json
  SOURCES TO PROCESS:
  {compiler-specified search queries — use WebSearch to find URLs first, then assign}
  EXTRACTION CATEGORIES: {categories list}
  CORE CATEGORIES: {core categories list}
  ADJACENT CATEGORIES: {adjacent categories list}
  EXTRACTION FOCUS: {gap-specific focus from compiler prompts}
  CACHE DIRECTORY: research/{slug}/cache/
  OUTPUT SCHEMA:
  {the JSON schema}
```

**Important:** Before spawning gap-targeted scouts, run the compiler's suggested search queries via WebSearch to discover actual URLs. Then assign discovered URLs to scouts. The cache directory is shared across all rounds.

Run the same post-scout verification as Phase 1 (JSON validation, degraded retry, gap deduplication).

Print: `[OVERNIGHT] phase=round-{N}-scouts status=complete findings={F}`

Update metadata.json: add `"round-{N}-scout"` to `stages_completed`, increment `rounds_completed`.

---

## Phase 5 — Round N Analysis (N >= 2)

Spawn `research:overnight-analyst` (Sonnet) with prior round context:

```
subagent_type: research:overnight-analyst
model: sonnet
prompt: |
  RESEARCH TOPIC: {topic}
  SCOUT DIRECTORY: research/{slug}/round-{N}/scout/
  OUTPUT FILE: research/{slug}/round-{N}/analysis/DRAFT.md
  EXTRACTION CATEGORIES: {categories list}
  CORE CATEGORIES: {core categories list}
  ADJACENT CATEGORIES: {adjacent categories list}
  PRIOR DRAFT: research/{slug}/round-{N-1}/analysis/DRAFT.md
  ROUND NUMBER: {N}
```

The key difference from round 1: analyst receives PRIOR DRAFT and builds on it rather than starting from scratch.

**Verification:** Same as Phase 2.

Print: `[OVERNIGHT] phase=round-{N}-analysis status=complete draft_size={bytes}`

Update metadata.json: add `"round-{N}-analysis"` to `stages_completed`.

---

## Phase 6 — Round N Compilation (N >= 2)

Spawn `research:research-compiler` again:

```
subagent_type: research:research-compiler
model: opus
prompt: |
  RESEARCH TOPIC: {topic}
  ROUND NUMBER: {N}
  MAX ROUNDS: {max_rounds}
  DRAFT FILE: research/{slug}/round-{N}/analysis/DRAFT.md
  REVIEW NOTES FILE: research/{slug}/round-{N}/analysis/REVIEW-NOTES.md
  SCOUT DIRECTORY: research/{slug}/round-{N}/scout/
  EXTRACTION CATEGORIES: {categories list}
  CORE CATEGORIES: {core categories list}
  PRIOR COMPILATIONS: research/{slug}/round-1/compilation.md, ..., research/{slug}/round-{N-1}/compilation.md
  METADATA FILE: research/{slug}/metadata.json
  OUTPUT FILE: research/{slug}/round-{N}/compilation.md
```

**After completion:**
1. Parse decision: CONTINUE or FINALIZE.
2. Decision criteria: `marginal_gain < 10%` OR `round >= max_rounds` OR no knowledge_gaps remain.
3. If CONTINUE: go to Phase 4 with N+1. If FINALIZE: go to Phase 7.

Print: `[OVERNIGHT] phase=round-{N}-compilation status=complete decision={CONTINUE|FINALIZE} marginal_gain={X}%`

Update metadata.json: add `"round-{N}-compilation"` to `stages_completed`.

---

## Phase 7 — Adversarial Audit

Determine the latest round number from metadata.json. Spawn `research:research-adversarial` (fresh Opus, independent):

```
subagent_type: research:research-adversarial
model: opus
prompt: |
  RESEARCH TOPIC: {topic}
  COMPILATION FILE: research/{slug}/round-{latest}/compilation.md
  CACHE DIRECTORY: research/{slug}/cache/
  SOURCE MANIFEST: {source manifest from metadata.json}
  SCOUT DIRECTORY: research/{slug}/round-1/scout/, research/{slug}/round-2/scout/, ...
  OUTPUT FILE: research/{slug}/adversarial-audit.md
```

**After completion:**
- Check `research/{slug}/adversarial-audit.md` exists.
- Read the audit summary to extract verdict counts.
- Print: `[OVERNIGHT] phase=adversarial-audit status=complete confirmed={N} supported={N} disputed={N} incorrect={N}`

Update metadata.json: add `"adversarial-audit"` to `stages_completed`.

---

## Phase 8 — Final Assembly

### Merge into REPORT.md

1. Read the latest round's DRAFT.md (the most complete analyst output).
2. Read the adversarial audit.
3. Apply any corrections from the audit's `## Corrections Required` section to the draft.
4. Append the adversarial audit summary as a section at the end.
5. Write the merged result to `research/{slug}/REPORT.md`.

The final REPORT.md structure:
```markdown
# {Research Topic}

{content from latest analyst DRAFT.md, with adversarial corrections applied}

---

## Adversarial Audit Summary
{summary section from adversarial-audit.md}

---

<!-- PIPELINE METADATA
Pipeline: overnight
Rounds completed: {N}
Total scouts: {count across all rounds}
Total findings: {count}
Adversarial verdict: {overall assessment}
Generated: {ISO timestamp}
-->
```

Print: `[OVERNIGHT] phase=final-assembly status=complete report_size={bytes}`

### Generate PDF

Use the md-to-pdf skill to convert REPORT.md to PDF:

Invoke the `md-to-pdf` skill:
```
Convert research/{slug}/REPORT.md to PDF at research/{slug}/REPORT.pdf
```

If PDF generation fails, log the error and continue — the markdown report is the primary artifact.

### Discord Notification

Read the Discord webhook URL from `~/.claude/tts-config.json` (the `completed` webhook under `discord_webhooks`).

If `research/{slug}/REPORT.pdf` exists and is under 25MB:
```bash
curl -F "file1=@research/{slug}/REPORT.pdf" \
  -F 'payload_json={"content":"Research complete: {topic}"}' \
  "$(cat ~/.claude/tts-config.json | python3 -c \"import json,sys; print(json.load(sys.stdin)['discord_webhooks']['completed'])\")"
```

If PDF is missing or >25MB, fall back to text-only notification:
```bash
curl -H "Content-Type: application/json" \
  -d '{"content":"Research complete: {topic} (PDF unavailable, see REPORT.md)"}' \
  "$(cat ~/.claude/tts-config.json | python3 -c \"import json,sys; print(json.load(sys.stdin)['discord_webhooks']['completed'])\")"
```

Print: `[OVERNIGHT] phase=notification status=complete`

Update metadata.json: add `"final-assembly"` to `stages_completed`.

---

## Final Summary

Print:

```
Research complete: {topic}
Pipeline: overnight (multi-round iterative)
Domain: {domain}
Rounds: {rounds_completed} / {max_rounds}
Scouts: {total across all rounds} | Sources: {total} | Findings: {total}
Adversarial audit: {overall assessment}

Output:
  research/{slug}/REPORT.md          — Final report
  research/{slug}/REPORT.pdf         — PDF version
  research/{slug}/adversarial-audit.md — Adversarial audit
  research/{slug}/round-*/           — Per-round scout JSONs, drafts, compilations

Run `/research:operationalize {slug}` to create operational artifacts.
```

---

## Orchestration Rules

1. **Rounds run sequentially** — each round depends on the previous round's compilation decision.
2. **Within a round:** scouts run in parallel, then analyst, then compiler — sequential dependencies.
3. **Verify between stages** — check that expected output files exist before proceeding.
4. **Report progress** — tell the user which phase/round is running and when each completes.
5. **Cache is shared** — all rounds use the same `cache/` directory. Scouts from any round can benefit from cached content fetched by earlier scouts.
6. **Core invariant:** Haiku scouts write JSON files to disk with verbatim excerpts. Higher-tier agents read those files directly — never relying on lower-tier agents to relay information.
7. **Gap-driven iteration:** Follow-up rounds target only the knowledge_gaps identified by the compiler. They don't re-do broad discovery.

## Error Handling

- If discovery finds nothing: AskUserQuestion to refine. Never spawn scouts with zero sources.
- If >50% scouts produce 0 findings: AskUserQuestion whether to continue.
- If any scout JSON is malformed: offer to re-run failed scouts only.
- If analyst draft is suspiciously small (<2KB): warn before proceeding to compiler.
- If compiler compilation.md is missing or unparseable: warn and attempt to finalize with analyst draft only.
- If adversarial audit fails: proceed with REPORT.md from analyst draft without audit (warn user).
- If PDF generation fails: continue with markdown report and note in Discord notification.
- Never silently skip phases. Always report what happened.
