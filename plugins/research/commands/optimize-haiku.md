---
description: "Run optimization loop on solo-haiku-scout agent. Iteratively edits agent instructions, benchmarks against ESP32-S3 sources, scores, keeps/discards."
argument-hint: "[--rounds N] [--tag name]"
allowed-tools: [Read, Write, Edit, Bash, Glob, Grep, Agent, AskUserQuestion]
---

# Haiku Scout Optimizer

Optimize `plugins/research/agents/solo-haiku-scout.md` using an autoresearch-style loop against the ESP32-S3 benchmark.

## Arguments

$ARGUMENTS

Parse:
- **--rounds**: max experiments (default: unlimited)
- **--tag**: run tag (default: date-based, e.g. `mar12h`)

## Setup

1. **Parse arguments** and propose a tag. Branch `optimize/<tag>` must not exist.

2. **Source pre-check**: Verify all benchmark sources exist and have >1KB content:
   ```bash
   for f in plugins/research/benchmark/sources/esp32s3/datasheet.md \
            plugins/research/benchmark/sources/esp32s3/hw-reference.md \
            plugins/research/benchmark/sources/esp32s3/programming-guide.md \
            plugins/research/benchmark/sources/esp32s3/ai-capabilities.md; do
     [ -f "$f" ] && [ $(wc -c < "$f") -gt 1024 ] && echo "OK: $f" || echo "FAIL: $f"
   done
   ```
   If any source fails, STOP and alert user.

3. **Resume protocol**: Check if `plugins/research/benchmark/results.tsv` exists from a prior run:
   - If yes: read it, find the last `keep` row's commit hash, and `git log --oneline` to check if that commit exists on the current branch. If so, offer to resume from there instead of starting fresh.
   - If no: proceed with fresh run.

4. **Create branch**: `git checkout -b optimize/<tag>`

5. **Read context files**:
   - Target: `plugins/research/agents/solo-haiku-scout.md`
   - Rubric: `plugins/research/benchmark/rubric.json`
   - Sources (skim first 50 lines each): `plugins/research/benchmark/sources/esp32s3/*.md`
   - Scorer: `plugins/research/benchmark/score.py`

6. **Initialize results.tsv** (or archive existing as `results-{old_tag}.tsv`):
   ```
   experiment	commit	composite_score	status	description
   ```

7. **Run baseline**: Execute one benchmark WITHOUT modifying the agent file. Log as experiment 0 with status `baseline`.

8. Print summary and begin loop.

## Benchmark Execution

To run a single benchmark experiment:

1. **Clean previous output**: `rm -rf research/esp32s3-benchmark/`

2. **Spawn one Haiku agent** processing ALL 4 sources:

   ```
   Agent tool call:
     subagent_type: research:solo-haiku-scout
     model: haiku
     prompt: |
       SCOUT ID: solo-001
       RESEARCH TOPIC: ESP32-S3 microcontroller capabilities, architecture, peripherals, and AI features
       OUTPUT FILE: research/esp32s3-benchmark/scout/solo-001.json
       SOURCES TO PROCESS:
       - plugins/research/benchmark/sources/esp32s3/datasheet.md
       - plugins/research/benchmark/sources/esp32s3/hw-reference.md
       - plugins/research/benchmark/sources/esp32s3/programming-guide.md
       - plugins/research/benchmark/sources/esp32s3/ai-capabilities.md
       EXTRACTION CATEGORIES: [architecture, peripherals, memory, wireless, ai_acceleration, power_management, development_tools, security, gpio, interfaces]
       CORE CATEGORIES: [architecture, peripherals, memory, wireless, ai_acceleration, power_management]
       ADJACENT CATEGORIES: [development_tools, security, gpio, interfaces]
       OUTPUT SCHEMA:
       {
         "scout_id": "solo-001",
         "sources_processed": [
           {"path": "file.md", "status": "success|partial|failed", "findings_count": 0}
         ],
         "findings": [
           {
             "category": "string",
             "subcategory": "string|null",
             "summary": "one sentence",
             "raw_excerpt": "VERBATIM quoted text from source",
             "source_location": "file:line",
             "relevance": "high|medium|low",
             "claim_era": "current|historical|projection",
             "tags": ["freeform"]
           }
         ],
         "cross_references": [
           {"from_source": "file1.md", "to_source": "file2.md", "relationship": "extends|contradicts|documents", "description": "how they relate"}
         ],
         "gaps": [{"description": "what was missing", "gap_type": "source_failure|knowledge_gap"}],
         "metadata": {
           "total_sources": 0,
           "total_findings": 0,
           "source_success_rate": 0.0,
           "processing_notes": ""
         }
       }
   ```

   **Timeout: 3 minutes.** If the agent hasn't completed by then, kill it, log as `crash`, and revert.

3. **Score the output**:
   ```bash
   python3 plugins/research/benchmark/score.py research/esp32s3-benchmark/scout/ \
     --rubric plugins/research/benchmark/rubric.json \
     --source-dir plugins/research/benchmark/sources/esp32s3/ \
     --json
   ```

   The scorer returns JSON with at minimum a `composite_score` field (0.0-1.0). It may also include dimension breakdowns depending on configuration.

4. **Parse the JSON** to get the composite score. Use whatever fields are present.

## The Loop

LOOP FOREVER (or until `--rounds` exhausted):

1. **Check git state**: current branch and commit. **Re-read `results.tsv`** to refresh your memory of all prior experiments, scores, and strategies. This is essential — your context may have been compacted.

2. **Make one experimental edit** to `plugins/research/agents/solo-haiku-scout.md`. Ideas:
   - Reorder sections for emphasis
   - Add/remove constraints
   - Change extraction guidance (excerpt length hints, category detection)
   - Add concrete examples of good findings
   - Simplify or clarify instructions
   - Try different framing (imperative vs descriptive)
   - Add rules about minimum findings per category
   - Add emphasis on verbatim copying
   - Remove redundant instructions

   **Simplicity criterion:** Simpler is better. Removing instructions while maintaining score is a win.

3. **git commit** with descriptive message.

4. **Run benchmark** (clean → spawn → score).

5. **If score IMPROVED**:
   - Log to results.tsv with status `keep`
   - Print: `[OPTIMIZE] KEEP experiment={N} commit={hash} score={score} delta=+{delta} | {description}`

6. **If score EQUAL or WORSE**:
   - Log to results.tsv with status `discard`
   - Print: `[OPTIMIZE] DISCARD experiment={N} commit={hash} score={score} delta={delta} | {description}`
   - `git reset --hard HEAD~1`

7. **Crash handling**: If agent crashes or produces invalid JSON:
   - Try once more (retry). If retry also fails:
   - Log as status `crash` with score 0.000000
   - `git reset --hard HEAD~1`

8. **Plateau detection**: If 10+ consecutive discards:
   - Print: `[OPTIMIZE] PLATEAU DETECTED — switching to radical changes`
   - Try changes that are fundamentally different: complete restructure, opposite approach, minimal instructions, maximum specificity

9. **Rewind guidance**: If 15+ consecutive discards:
   - Find the best `keep` commit from results.tsv
   - `git reset --hard {best_commit}`
   - Print: `[OPTIMIZE] REWIND to best={score} at {commit}`
   - Resume with fresh ideas from that point

10. **Progress summary** every 5 experiments:
    ```
    [OPTIMIZE] progress: {N} experiments | best={score} | keeps={K} | discards={D} | current_streak={streak_type}:{count}
    ```

11. **Go to step 1**.

## What You CAN Modify

- `plugins/research/agents/solo-haiku-scout.md` — the target file

## What You CANNOT Modify

- Benchmark sources (`plugins/research/benchmark/sources/esp32s3/`)
- Scoring system (`plugins/research/benchmark/score.py`)
- Any other files besides the target agent file

## Important Rules

**NEVER STOP**: Run until `--rounds` exhausted or manually interrupted. If stuck, re-read the target file, rubric, sources, and results for inspiration.

**ONE CHANGE AT A TIME**: Each experiment tests one hypothesis.

**LOG EVERYTHING**: Every experiment logged to results.tsv — keeps, discards, and crashes.

**DO NOT COMMIT results.tsv**: It's untracked experiment data.

**CONTEXT MANAGEMENT**: Use `--json` with scorer for single-line output. Don't let agent output flood your context.

## Strategy Guide

The composite score reflects overall extraction quality. Optimize by trying different approaches:

- **Thoroughness**: Add extraction guidance, minimum finding counts, second-pass rules.
- **Accuracy**: Emphasize verbatim copying, add copy-paste rules, remove paraphrasing escape hatches.
- **Coverage**: Add minimum-per-category rules, category detection guidance.
- **Completeness**: Clarify required fields, add validation rules.
- **Connections**: Add cross-reference instructions between sources.
- **Self-awareness**: Add guidance on identifying missing information.
- **Simplicity**: Remove redundant instructions. Shorter prompts that maintain score are wins.

When score plateaus, try radical changes to escape local optima. Re-read results.tsv to avoid repeating failed strategies.
