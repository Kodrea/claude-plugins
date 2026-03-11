---
description: "Analyze a completed research pipeline run. Parses session JSONL + subagent logs, correlates with research outputs, and produces a run report with timing, token usage, and improvement suggestions."
argument-hint: "[--session UUID] [--slug name]"
allowed-tools: [Read, Write, Bash, Glob, Grep]
---

# Research Run Analyzer

Analyze a completed research pipeline run to produce timing, token usage, decision quality, and improvement suggestions.

## Arguments

$ARGUMENTS

Parse the arguments for:
- **--session**: UUID of the Claude Code session to analyze
- **--slug**: research output slug name to find the matching session

If neither is provided, find the latest session automatically.

---

## Step 1 — Session Discovery

Determine the project directory and find the session JSONL:

1. Derive project dir from cwd: `~/.claude/projects/-{path-with-hyphens}/` (replace `/` with `-` in the absolute cwd path, stripping the leading `/`)
2. **If `--session` provided:** Look for `{project-dir}/{UUID}.jsonl`
3. **If `--slug` provided:** Scan recent `.jsonl` files in project dir (by modification time, newest first) for a `[PIPELINE]` marker containing `slug={slug}`. Use the first match.
4. **Default (no args):** Find the most recently modified `.jsonl` in the project dir that contains `[PIPELINE]` markers.

If no matching session found, report the error and stop.

---

## Step 2 — Parse Main Session JSONL

Read the session JSONL file. Each line is a JSON object. Process as follows:

### 2A — Extract [PIPELINE] markers

1. Find all lines with `type: "assistant"` that contain `[PIPELINE]` in the message content
2. For each marker, record:
   - **timestamp** from the JSONL line
   - **phase** and **status** from the marker text
   - **all key=value pairs** from the marker (sources_found, scout_count, rationale, etc.)
3. Build a phase timeline array: `[{phase, status, timestamp, data: {key: value}}]`

### 2B — Extract Agent spawns

1. Find all `tool_use` blocks where `name == "Agent"` (or `name == "Task"`)
2. For each, record:
   - `toolUseId` (the `id` field on the tool_use block)
   - `subagent_type` from `input.subagent_type`
   - `description` from `input.description` or `input.prompt` (first 100 chars)
   - `timestamp` from the enclosing message

### 2C — Extract Agent progress events

1. Find lines with `type: "progress"` and `data.type: "agent_progress"`
2. For each, map `data.agentId` to `parentToolUseID`
3. This links each subagent JSONL file (`agent-{agentId}.jsonl`) back to its spawn tool_use

### 2D — Extract token usage from main session

1. Find all assistant messages with `message.usage`
2. Sum `input_tokens`, `output_tokens`, `cache_read_input_tokens`, `cache_creation_input_tokens`
3. Record as orchestrator token usage

---

## Step 3 — Parse Subagent JSONLs

For each agent identified in Step 2:

1. Locate the subagent JSONL at `{sessionDir}/subagents/agent-{agentId}.jsonl`
   - If the subagents directory doesn't exist or file is missing, note it as unavailable and skip
2. Parse the file:
   - **Model:** from the first assistant message's `message.model` field
   - **Duration:** difference between first and last message timestamps
   - **Token usage:** sum `message.usage` across all assistant messages: `input_tokens`, `output_tokens`, `cache_read_input_tokens`, `cache_creation_input_tokens`
   - **Tool calls:** count `tool_use` blocks, categorize by tool name (Read, Write, Grep, WebFetch, etc.)

### Tier Identification

Classify each agent by its `subagent_type`:
- Contains `research-scout` or `scout` → **Scout** (expected model: `claude-haiku-*`)
- Contains `research-analyst` or `analyst` → **Analyst** (expected model: `claude-sonnet-*`)
- Contains `research-auditor` or `auditor` → **Auditor** (expected model: `claude-opus-*`)

---

## Step 4 — Correlate with Research Outputs

Using the slug from the `[PIPELINE] phase=output-setup` marker (or `--slug` arg):

1. **metadata.json** — `research/{slug}/metadata.json`
   - Extract: stages_completed, source count, extraction_categories
2. **Scout JSONs** — `research/{slug}/scout/*.json`
   - For each: findings count, gaps, sources processed, high/medium/low relevance breakdown
3. **Analyst draft** — `research/{slug}/analysis/DRAFT.md`
   - File size in bytes
4. **Final report** — `research/{slug}/REPORT.md`
   - File size in bytes
   - Extract audit log section if present (look for "## Audit" or "## Corrections" heading)

---

## Step 5 — Signal Detection

Evaluate every rule below against the data from Steps 2-4. For each rule where the condition is true, record a signal with its severity and data. Collect all triggered signals into a list.

### Load Balance Rules

| Rule | Condition | Severity | Signal Data |
|------|-----------|----------|-------------|
| Unbalanced scouts | max_findings / min_findings > 3 | warn | `{heavy_scout, light_scout, ratio}` |
| Dead scout | any scout with 0 findings | error | `{scout_id, sources_assigned}` |
| Overloaded scout | any scout with >30 findings | warn | `{scout_id, count}` |

### Efficiency Rules

| Rule | Condition | Severity | Signal Data |
|------|-----------|----------|-------------|
| Phase bottleneck | any phase > 40% of wall time | warn | `{phase, pct, duration}` |
| Slow scout | any scout duration > 2x median scout duration | info | `{scout_id, duration, median}` |
| High cache utilization | cache_read > 80% of total input | good | `{pct}` |
| Low cache utilization | cache_read < 20% of total input | info | `{pct}` |

### Quality Rules

| Rule | Condition | Severity | Signal Data |
|------|-----------|----------|-------------|
| Thin draft | draft_size < 5KB | warn | `{bytes}` |
| Bloated draft | draft_size > 100KB | warn | `{bytes}` |
| High corrections | auditor corrections > 5 | warn | `{count}` |
| Many source failures | gaps with gap_type=="source_failure" > 5 | warn | `{count, threshold: 5, examples}` |
| Many knowledge gaps | gaps with gap_type=="knowledge_gap" > 8 | warn | `{count, threshold: 8, examples}` |
| Low relevance ratio | high-relevance findings < 30% of total | info | `{high, medium, low}` |

### Token Economy Rules

| Rule | Condition | Severity | Signal Data |
|------|-----------|----------|-------------|
| Scout token outlier | any scout tokens > 2x median | info | `{scout_id, tokens, median}` |
| Expensive run | total tokens > 500K | info | `{total}` |
| Auditor heavier than analyst | auditor tokens > analyst tokens * 2 | info | `{auditor, analyst}` |

Build a signals array: `[{rule, severity, signal_data}]`

Also record which rules were checked but did NOT trigger — this confirms they were evaluated.

---

## Step 6 — Interpret Signals

Review the triggered signals together. Consider how they interact — signals in combination often reveal root causes that individual signals miss:

- **Dead scout + unbalanced load** → source allocation was wrong, not just unlucky
- **High corrections + thin draft** → analyst lacked data, not necessarily sloppy
- **Phase bottleneck + slow scout** → one scout may have blocked the pipeline
- **Low relevance ratio + many knowledge gaps** → extraction categories may not match the topic well
- **Expensive run + low cache utilization** → pipeline isn't benefiting from prompt caching
- **Many source failures + high corrections** → source failures cascaded into analyst
  speculation; fix pre-validation
- **Many knowledge gaps + low relevance ratio** → extraction categories may not match
  the topic's actual coverage in available sources
- **Many source failures alone (no many_knowledge_gaps)** → sources were poorly chosen,
  not a topic/category problem

Generate 3-5 improvement suggestions. Each suggestion MUST:
1. Reference the specific signal(s) that triggered it by rule name
2. Include the actual numbers from the signal data
3. Propose a concrete action for the next run

If no signals triggered (all rules passed), note that the run was clean and suggest no changes.

Do NOT generate generic advice. Every suggestion must be grounded in a triggered signal.

---

## Step 7 — Write Reports

Write two files to `research/{slug}/`:

### 7A — `RUN-REPORT.md`

```markdown
# Run Report: {topic}
**Session:** {id} | **Date:** {date} | **Wall Time:** {mm:ss}

## Timeline
| Phase | Duration | Notes |
|-------|----------|-------|
| Discovery | Xs | {sources_found} sources |
| Scout Allocation | Xs | {scout_count} scouts — {rationale} |
| Schema Gen | Xs | {N} categories |
| Output Setup | Xs | slug={slug} |
| Scout Exec | Xs | {total_findings} findings, checkpoint={result} |
| Analyst | Xs | draft {bytes} bytes |
| Auditor | Xs | {corrections} corrections, verdict={verdict} |
| Summary | Xs | |
**Bottleneck:** {phase} ({X}% of total)

## Agent Metrics
### Scouts
| Agent | Model | Duration | In Tok | Out Tok | Cache Read | Tools | Findings |
|-------|-------|----------|--------|---------|------------|-------|----------|
(one row per scout)

### Analyst
| Metric | Value |
|--------|-------|
| Model | ... |
| Duration | ... |
| Input Tokens | ... |
| Output Tokens | ... |
| Cache Read | ... |
| Tool Calls | ... |
| Draft Size | ... |

### Auditor
| Metric | Value |
|--------|-------|
| Model | ... |
| Duration | ... |
| Input Tokens | ... |
| Output Tokens | ... |
| Cache Read | ... |
| Tool Calls | ... |
| Corrections | ... |
| Verdict | ... |

### Token Summary
| Tier | Input | Output | Cache Read | Cache Create | Total |
|------|-------|--------|------------|--------------|-------|
| Orchestrator | ... | ... | ... | ... | ... |
| Scouts (sum) | ... | ... | ... | ... | ... |
| Analyst | ... | ... | ... | ... | ... |
| Auditor | ... | ... | ... | ... | ... |
| **Total** | ... | ... | ... | ... | ... |

## Decision Log
- Scout allocation: {N} scouts for {M} sources — "{rationale}"
- Categories: {list}
- Checkpoints: scout={result}, draft-size={assessment}

## Signals
| Severity | Rule | Details |
|----------|------|---------|
(one row per triggered signal — show severity as icon: error, warn, info, good)

If no signals triggered, show: "All rules passed — clean run."

## Improvement Suggestions
(3-5 suggestions from Step 6, each referencing specific signals with actual numbers)
```

### 7B — `run-metrics.json`

Write a machine-readable JSON with this structure:

```json
{
  "session_id": "...",
  "date": "ISO timestamp",
  "wall_time_seconds": 0,
  "topic": "...",
  "slug": "...",
  "phases": [
    {
      "name": "discovery",
      "duration_seconds": 0,
      "data": { "sources_found": 0, "domain": "..." }
    }
  ],
  "agents": [
    {
      "id": "...",
      "tier": "scout|analyst|auditor",
      "model": "...",
      "duration_seconds": 0,
      "tokens": {
        "input": 0,
        "output": 0,
        "cache_read": 0,
        "cache_create": 0
      },
      "tool_calls": { "Read": 0, "Write": 0 },
      "findings": 0
    }
  ],
  "token_summary": {
    "orchestrator": { "input": 0, "output": 0, "cache_read": 0, "cache_create": 0 },
    "scouts": { "input": 0, "output": 0, "cache_read": 0, "cache_create": 0 },
    "analyst": { "input": 0, "output": 0, "cache_read": 0, "cache_create": 0 },
    "auditor": { "input": 0, "output": 0, "cache_read": 0, "cache_create": 0 },
    "total": { "input": 0, "output": 0, "cache_read": 0, "cache_create": 0 }
  },
  "signals": [
    {
      "rule": "...",
      "severity": "error|warn|info|good",
      "data": {}
    }
  ],
  "quality": {
    "findings_per_scout": [],
    "relevance_breakdown": { "high": 0, "medium": 0, "low": 0 },
    "gaps": [],
    "auditor_corrections": 0,
    "auditor_verdict": "..."
  },
  "bottleneck": {
    "phase": "...",
    "percentage": 0
  },
  "suggestions": ["..."]
}
```

---

## Step 8 — Report to User

After writing both files, print:

```
Run analysis complete for: {topic}
  RUN-REPORT.md: research/{slug}/RUN-REPORT.md
  run-metrics.json: research/{slug}/run-metrics.json
  Wall time: {mm:ss}
  Total tokens: {N} (input: {I}, output: {O}, cache read: {C})
  Bottleneck: {phase} ({pct}%)
  Signals: {triggered}/{total rules checked} ({error} errors, {warn} warnings)
  Suggestions: {count}
```

---

## Error Handling

- If session JSONL not found: report which paths were checked and stop
- If no `[PIPELINE]` markers found in session: report that the session doesn't appear to be a research pipeline run
- If subagent JONLs are missing: produce the report with available data, noting "subagent logs unavailable" where metrics would go
- If research output directory doesn't exist: produce the report from JSONL data only, noting "research outputs not found"
- If JSONL parsing encounters malformed lines: skip them and note the count of skipped lines in the report
