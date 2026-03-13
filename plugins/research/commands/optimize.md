---
description: "Run autoresearch-style optimization loop on research pipeline agent instructions. Iteratively edits agent files, benchmarks, scores, and keeps/discards based on improvement."
argument-hint: "[--target scout|analyst|auditor] [--rounds N] [--tag name]"
allowed-tools: [Read, Write, Edit, Bash, Glob, Grep, Agent, AskUserQuestion]
---

# Research Pipeline Optimizer

Autonomously improve research agent instructions using an optimization loop inspired by Karpathy's autoresearch.

## The Loop

```
edit agent instruction -> run benchmark -> score output -> keep/discard -> repeat
```

Instead of editing `train.py` to minimize `val_bpb`, you edit agent instruction markdown files to maximize a composite quality score measured against a fixed benchmark.

**For track-specific optimizers, use:**
- `/optimize-haiku` — Solo Haiku scout track (30-40 experiments/hr)
- `/optimize-sonnet` — Solo Sonnet researcher track (12-15 experiments/hr)

This command optimizes the tiered pipeline agents (scout, analyst, auditor) against the NSP benchmark.

## Arguments

$ARGUMENTS

Parse the arguments for:
- **--target**: which agent to optimize. `scout` (default), `analyst`, or `auditor`. Optimizes one agent at a time.
- **--rounds**: maximum experiments to run (default: unlimited, runs until interrupted)
- **--tag**: experiment run tag (default: date-based, e.g. `mar12`)

---

## Setup

1. **Agree on a run tag**: propose a tag based on today's date (e.g. `mar12`). The branch `optimize/<tag>` must not already exist.

2. **Source pre-check**: Verify benchmark sources exist before starting:
   ```bash
   for f in plugins/research/benchmark/sources/*.md; do
     [ -f "$f" ] && [ $(wc -c < "$f") -gt 1024 ] && echo "OK: $f" || echo "FAIL: $f"
   done
   ```
   If any source fails, STOP and alert user.

3. **Resume protocol**: Check if `plugins/research/benchmark/results.tsv` exists:
   - Read it and find the last `keep` row's commit hash
   - Check if that commit exists on the current branch
   - If yes: offer to resume from there (checkout that commit, continue from that experiment number)
   - If no: archive as `results-{old_tag}.tsv` and start fresh

4. **Create the branch**: `git checkout -b optimize/<tag>` from current branch.

5. **Determine the target file** based on `--target`:
   - `scout` -> `plugins/research/agents/research-scout.md`
   - `analyst` -> `plugins/research/agents/research-analyst.md`
   - `auditor` -> `plugins/research/agents/research-auditor.md`

6. **Read the in-scope files** for full context:
   - The target agent file (the file you will modify)
   - The benchmark rubric: `plugins/research/benchmark/rubric.json`
   - The benchmark sources (skim): `plugins/research/benchmark/sources/*.md`
   - The scoring script: `plugins/research/benchmark/score.py`

7. **Initialize results.tsv**: Create `plugins/research/benchmark/results.tsv` with header:
   ```
   experiment	commit	composite_score	finding_recall	verbatim_quality	category_coverage	precision	structure	cross_refs	gaps	status	description
   ```

8. **Run baseline**: Execute one benchmark WITHOUT modifying the target file. Log as experiment 0 with status `baseline`.

9. **Confirm and go**: Print summary and kick off the loop.

---

## The Experiment Loop

### Running a Benchmark

1. **Clean previous output**: `rm -rf research/nsp-benchmark/`

2. **Run a mini research pipeline** using the Agent tool. Spawn 2 scouts against the benchmark sources:

   ```
   Agent tool call:
     subagent_type: research:research-scout
     model: haiku
     prompt: |
       SCOUT ID: scout-001
       RESEARCH TOPIC: Nexus Stream Processor architecture, API, and deployment
       OUTPUT FILE: research/nsp-benchmark/scout/scout-001.json
       SOURCES TO PROCESS:
       - plugins/research/benchmark/sources/architecture-overview.md
       - plugins/research/benchmark/sources/api-reference.md
       EXTRACTION CATEGORIES: [architecture, api, configuration, fault_tolerance, state_management, known_issues]
       CORE CATEGORIES: [architecture, api, configuration, deployment, fault_tolerance, monitoring]
       ADJACENT CATEGORIES: [known_issues, performance_tuning, state_management, upgrade_procedures]
       EXTRACTION FOCUS: Extract all technical details, configuration values, API endpoints, and operational guidance
       CACHE DIRECTORY: research/nsp-benchmark/cache/
       OUTPUT SCHEMA:
       {
         "scout_id": "scout-001",
         "sources_processed": [
           {"location": "file:line or URL", "type": "file|url", "status": "success|partial|failed"}
         ],
         "findings": [
           {
             "category": "string",
             "subcategory": "string|null",
             "summary": "one sentence",
             "raw_excerpt": "VERBATIM quoted text",
             "source_location": "file:line or URL#section",
             "relevance": "high|medium|low",
             "claim_era": "2025-2026|historical-context|projection",
             "tags": ["freeform"]
           }
         ],
         "cross_references": [
           {"from": "source_location", "to": "source_location", "relationship": "calls|imports|extends|documents|contradicts"}
         ],
         "gaps": [{"description": "what was expected but not found", "gap_type": "source_failure|knowledge_gap"}],
         "metadata": {
           "total_sources": 0,
           "total_findings": 0,
           "source_success_rate": 0.0,
           "processing_notes": ""
         }
       }
   ```

   ```
   Agent tool call:
     subagent_type: research:research-scout
     model: haiku
     prompt: |
       SCOUT ID: scout-002
       RESEARCH TOPIC: Nexus Stream Processor architecture, API, and deployment
       OUTPUT FILE: research/nsp-benchmark/scout/scout-002.json
       SOURCES TO PROCESS:
       - plugins/research/benchmark/sources/deployment-guide.md
       EXTRACTION CATEGORIES: [deployment, monitoring, performance_tuning, fault_tolerance, upgrade_procedures]
       CORE CATEGORIES: [architecture, api, configuration, deployment, fault_tolerance, monitoring]
       ADJACENT CATEGORIES: [known_issues, performance_tuning, state_management, upgrade_procedures]
       EXTRACTION FOCUS: Extract all deployment configs, monitoring setup, tuning parameters, and operational procedures
       CACHE DIRECTORY: research/nsp-benchmark/cache/
       OUTPUT SCHEMA: (same schema as above)
   ```

   **Spawn BOTH scouts in parallel.** Timeout: 3 minutes per agent.

3. **Score the output**:
   ```bash
   python3 plugins/research/benchmark/score.py research/nsp-benchmark/scout/ --json
   ```

   Example output:
   ```json
   {"composite_score": 0.523400, "dimensions": {"finding_recall": 0.65, "verbatim_quality": 0.45, "category_coverage": 0.83, "precision": 0.72, "structure_quality": 1.0, "cross_references": 0.0, "gap_detection": 0.33}, "total_findings": 18, "scouts_evaluated": 2, "missed_findings": ["F005", "F012"]}
   ```

4. **Parse the JSON output** to get composite score and dimension breakdown.

### The Loop

LOOP FOREVER (or until `--rounds` is reached):

1. **Check git state**: current branch and commit.

2. **Make one experimental edit** to the target agent file. Be creative but focused:
   - Reorder rules or sections for emphasis
   - Add or remove constraints
   - Change extraction guidance (e.g., excerpt length hints, category detection rules)
   - Add concrete examples
   - Simplify or clarify instructions
   - Adjust thresholds or heuristics
   - Try different framing (imperative vs descriptive, strict vs flexible)
   - Remove redundant instructions
   - Add new rules you hypothesize will help

   **Simplicity criterion (from autoresearch):** All else being equal, simpler is better. A small improvement that adds ugly complexity is not worth it. Removing instructions while maintaining score is a win.

3. **git commit** the change with a descriptive message.

4. **Run the benchmark** (clean output -> spawn scouts -> score).

5. **If composite_score IMPROVED** (higher is better):
   - Log to results.tsv with status `keep`
   - Print: `[OPTIMIZE] KEEP experiment={N} commit={hash} score={score} delta=+{improvement} | {description}`

6. **If composite_score is EQUAL or WORSE**:
   - Log to results.tsv with status `discard`
   - Print: `[OPTIMIZE] DISCARD experiment={N} commit={hash} score={score} delta={delta} | {description}`
   - `git reset --hard HEAD~1`

7. **Crash handling**: If a scout crashes or produces invalid JSON:
   - Retry once (re-run the benchmark). If retry also fails:
   - Log as status `crash` with score 0.000000
   - `git reset --hard HEAD~1`

8. **Plateau detection**: If 10+ consecutive discards:
   - Print: `[OPTIMIZE] PLATEAU DETECTED — switching to radical changes`
   - Try fundamentally different approaches: complete restructure, opposite framing, minimal instructions

9. **Rewind guidance**: If 15+ consecutive discards:
   - Find the best `keep` commit from results.tsv
   - `git reset --hard {best_commit}`
   - Print: `[OPTIMIZE] REWIND to best={score} at {commit}`

10. **Print running summary** every 5 experiments:
    ```
    [OPTIMIZE] progress: {N} experiments | best={best_score} | keeps={K} | discards={D}
    ```

11. **Go to step 1**.

---

## What You CAN Modify

- The target agent instruction file (one file per `--target` setting)
- That's it. One file at a time.

## What You CANNOT Modify

- Benchmark source files (`plugins/research/benchmark/sources/`)
- The scoring script (`plugins/research/benchmark/score.py`)
- The rubric (`plugins/research/benchmark/rubric.json`)
- Other agent files (unless they're the current target)

## Important Rules

**NEVER STOP**: Once the loop begins, do NOT pause to ask if you should continue. The user may be away. Run until `--rounds` is exhausted or you are manually interrupted. If you run out of ideas, re-read the target file, the rubric, the benchmark sources, and previous results for inspiration. Try combining near-misses. Try more radical changes. Try the opposite of what you've been trying.

**ONE CHANGE AT A TIME**: Each experiment should test exactly one hypothesis. Don't bundle multiple changes — you won't know which one helped or hurt.

**LOG EVERYTHING**: Every experiment gets logged to results.tsv, including crashes and discards. The log is the research artifact.

**DO NOT COMMIT results.tsv**: Leave it untracked. It's a local experiment log, not part of the agent instructions.

**CONTEXT MANAGEMENT**: Use `--json` with scorer for single-line output. Don't let scout output flood your context.

---

## Strategy Guide

When optimizing scouts, consider these dimensions (from the scoring rubric):

1. **Finding recall (25%)**: Are the scouts finding all the important facts? Try adding more specific extraction guidance, examples of what "good" findings look like, or rules about thoroughness.

2. **Verbatim quality (20%)**: Are excerpts actually copied from the source? Try emphasizing the verbatim requirement differently, adding examples of good vs bad excerpts, or changing how the instruction frames the excerpt task.

3. **Category coverage (15%)**: Are findings spread across all core categories? Try adding guidance about minimum findings per category, or how to classify findings.

4. **Precision (15%)**: Are findings complete and well-formed? Try clarifying required fields, adding validation rules, or restructuring the output format guidance.

5. **Cross-references (10%)**: Are relationships between sources identified? Try adding explicit cross-reference examples or guidance on what to look for.

6. **Gap detection (10%)**: Are missing topics identified? Try adding guidance on what gaps look like, or examples of common gaps.

7. **Structure quality (5%)**: Is the JSON well-structured? Try simplifying the schema description, adding a concrete example JSON, or clarifying metadata fields.

When you plateau on one dimension, shift focus to another. The composite score may have local optima — try a radical change to escape them.
