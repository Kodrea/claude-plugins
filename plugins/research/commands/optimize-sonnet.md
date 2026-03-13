---
description: "Run optimization loop on solo-sonnet-researcher agent. Iteratively edits agent instructions, benchmarks against ESP32-S3 sources (incl. community thread), scores, keeps/discards."
argument-hint: "[--rounds N] [--tag name]"
allowed-tools: [Read, Write, Edit, Bash, Glob, Grep, Agent, AskUserQuestion]
---

# Sonnet Researcher Optimizer

Optimize `plugins/research/agents/solo-sonnet-researcher.md` using an autoresearch-style loop against the ESP32-S3 benchmark (5 sources including community thread).

## Arguments

$ARGUMENTS

Parse:
- **--rounds**: max experiments (default: unlimited)
- **--tag**: run tag (default: date-based, e.g. `mar12s`)

## Setup

1. **Parse arguments** and propose a tag. Branch `optimize/<tag>` must not exist.

2. **Source pre-check**: Verify all 5 benchmark sources exist and have >1KB content:
   ```bash
   for f in plugins/research/benchmark/sources/esp32s3/datasheet.md \
            plugins/research/benchmark/sources/esp32s3/hw-reference.md \
            plugins/research/benchmark/sources/esp32s3/programming-guide.md \
            plugins/research/benchmark/sources/esp32s3/ai-capabilities.md \
            plugins/research/benchmark/sources/esp32s3/community-thread.md; do
     [ -f "$f" ] && [ $(wc -c < "$f") -gt 1024 ] && echo "OK: $f" || echo "FAIL: $f"
   done
   ```
   If any source fails, STOP and alert user.

3. **Resume protocol**: Check if `plugins/research/benchmark/results-sonnet.tsv` exists:
   - If yes: read it, find last `keep` commit, offer to resume.
   - If no: fresh run.

4. **Create branch**: `git checkout -b optimize/<tag>`

5. **Read context files**:
   - Target: `plugins/research/agents/solo-sonnet-researcher.md`
   - Rubric: `plugins/research/benchmark/rubric-sonnet.json`
   - Sources (skim first 50 lines each): `plugins/research/benchmark/sources/esp32s3/*.md`
   - Scorer: `plugins/research/benchmark/score.py`

6. **Initialize results-sonnet.tsv** (or archive existing):
   ```
   experiment	commit	composite_score	finding_recall	verbatim_quality	category_coverage	precision	structure	cross_refs	gaps	status	description
   ```

7. **Run baseline**: Execute one benchmark WITHOUT modifying the agent file. Log as experiment 0 with status `baseline`.

8. Print summary and begin loop.

## Benchmark Execution

To run a single benchmark experiment:

1. **Clean previous output**: `rm -rf research/esp32s3-benchmark-sonnet/`

2. **Spawn one Sonnet agent** processing ALL 5 sources:

   ```
   Agent tool call:
     subagent_type: research:solo-sonnet-researcher
     model: sonnet
     prompt: |
       RESEARCHER ID: solo-001
       RESEARCH TOPIC: ESP32-S3 microcontroller capabilities, architecture, peripherals, AI features, and real-world usage
       OUTPUT FILE: research/esp32s3-benchmark-sonnet/scout/solo-001.json
       SOURCES TO PROCESS:
       - plugins/research/benchmark/sources/esp32s3/datasheet.md
       - plugins/research/benchmark/sources/esp32s3/hw-reference.md
       - plugins/research/benchmark/sources/esp32s3/programming-guide.md
       - plugins/research/benchmark/sources/esp32s3/ai-capabilities.md
       - plugins/research/benchmark/sources/esp32s3/community-thread.md
       EXTRACTION CATEGORIES: [architecture, peripherals, memory, wireless, ai_acceleration, power_management, development_tools, security, gpio, interfaces, community_reports, workarounds]
       CORE CATEGORIES: [architecture, peripherals, memory, wireless, ai_acceleration, power_management]
       ADJACENT CATEGORIES: [development_tools, security, gpio, interfaces, community_reports, workarounds]
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
         "synthesis": "## Key Findings\n\n### Architecture\n...\n\n### Gaps & Open Questions\n...",
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

   **Timeout: 3 minutes.** If agent hasn't completed, kill it, log `crash`, revert.

3. **Score the output** (scores JSON findings only, ignores synthesis):
   ```bash
   python3 plugins/research/benchmark/score.py research/esp32s3-benchmark-sonnet/scout/ \
     --rubric plugins/research/benchmark/rubric-sonnet.json \
     --source-dir plugins/research/benchmark/sources/esp32s3/ \
     --json
   ```

   Example output:
   ```json
   {"composite_score": 0.548200, "dimensions": {"finding_recall": 0.70, "verbatim_quality": 0.50, "category_coverage": 0.83, "precision": 0.78, "structure_quality": 1.0, "cross_references": 0.25, "gap_detection": 0.50}, "total_findings": 22, "scouts_evaluated": 1, "missed_findings": ["F008", "F015"]}
   ```

4. **Parse JSON** for composite score and dimensions.

## The Loop

LOOP FOREVER (or until `--rounds` exhausted):

1. **Check git state**: current branch and commit.

2. **Make one experimental edit** to `plugins/research/agents/solo-sonnet-researcher.md`. Ideas:
   - Reorder phases or sections
   - Add/remove constraints
   - Change extraction vs synthesis balance
   - Add examples of good findings from noisy sources
   - Improve community-source handling (signal vs noise)
   - Add cross-reference detection guidance
   - Simplify or clarify instructions
   - Try different synthesis prompting strategies
   - Add quality self-check steps

   **Simplicity criterion:** Simpler is better. Removing instructions while maintaining score is a win.

3. **git commit** with descriptive message.

4. **Run benchmark** (clean → spawn → score).

5. **If score IMPROVED**:
   - Log to results-sonnet.tsv with status `keep`
   - Print: `[OPTIMIZE] KEEP experiment={N} commit={hash} score={score} delta=+{delta} | {description}`

6. **If score EQUAL or WORSE**:
   - Log to results-sonnet.tsv with status `discard`
   - Print: `[OPTIMIZE] DISCARD experiment={N} commit={hash} score={score} delta={delta} | {description}`
   - `git reset --hard HEAD~1`

7. **Crash handling**: If agent crashes or produces invalid JSON:
   - Retry once. If retry also fails:
   - Log as status `crash` with score 0.000000
   - `git reset --hard HEAD~1`

8. **Plateau detection**: 10+ consecutive discards → switch to radical changes.

9. **Rewind guidance**: 15+ consecutive discards → revert to best keep commit.

10. **Progress summary** every 5 experiments:
    ```
    [OPTIMIZE] progress: {N} experiments | best={score} | keeps={K} | discards={D}
    ```

11. **Go to step 1**.

## What You CAN Modify

- `plugins/research/agents/solo-sonnet-researcher.md` — the target file

## What You CANNOT Modify

- Benchmark sources, scorer, rubric, other agent files

## Important Rules

**NEVER STOP**: Run until interrupted or `--rounds` exhausted.

**ONE CHANGE AT A TIME**: Each experiment tests one hypothesis.

**LOG EVERYTHING**: Every experiment to results-sonnet.tsv.

**DO NOT COMMIT results-sonnet.tsv**: Untracked experiment data.

**SYNTHESIS NOT SCORED**: The `synthesis` field is included in output but NOT scored in the loop. It's evaluated manually after convergence.

## Strategy Guide

Same 7 dimensions as Haiku track, but Sonnet has more capacity. Focus areas:

1. **Finding recall (25%)**: Sonnet should find more — push for deeper extraction.
2. **Verbatim quality (20%)**: Sonnet may paraphrase more — emphasize verbatim discipline.
3. **Category coverage (15%)**: With 5 sources, coverage should be high — focus on community source categories.
4. **Precision (15%)**: Sonnet tends to produce complete findings — optimize for source_location specificity.
5. **Cross-references (10%)**: Sonnet excels at connecting sources — add explicit cross-ref prompting.
6. **Gap detection (10%)**: Sonnet is better at noticing what's missing — add gap identification examples.
7. **Structure (5%)**: Should be consistently high — not a bottleneck.

Unique to Sonnet track: test how synthesis prompts affect extraction quality. Sometimes asking for synthesis changes what the model pays attention to during extraction.
