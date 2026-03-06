---
description: "Run collaborative team research with a swarm of communicating agents. Use when the user says 'swarm research', 'ultra research', 'team research', or '/swarm'."
argument-hint: "<topic>"
allowed-tools: [Read, Write, Edit, Bash, Glob, Grep, WebSearch, WebFetch, AskUserQuestion, TeamCreate, TeamDelete, SendMessage, Task, Agent]
---

# Swarm Research Pipeline Orchestrator

Run a collaborative research pipeline using a team of communicating Sonnet agents:
**Lead (you) -> TeamCreate -> Scouts + Analysts + Synthesizer + Adversarial -> Convergence -> REPORT.md -> PDF + Discord**

This command runs in the main conversation. You ARE the Lead agent.

## Topic

The user's input is the research topic:

**TOPIC:** $ARGUMENTS

If the topic is empty or too vague (fewer than 3 words), use AskUserQuestion to ask: "What topic should I swarm-research?"

## Collect Options

Immediately use **AskUserQuestion** to collect pipeline options:

```
I'll set up the swarm research pipeline for: "{topic}"

Before I begin, a few quick options:

1. **Preset** — agent composition (default: standard)
   - `standard`: 5 scouts, 3 analysts — balanced breadth and depth
   - `wide`: 8 scouts, 2 analysts — maximum source coverage
   - `deep`: 3 scouts, 5 analysts — fewer sources, exhaustive analysis
2. **Domain** — `web`, `codebase`, or `mixed` (default: infer from topic)
3. **Slug** — output directory name (default: auto-generated from topic)
4. **Composable** — output in overnight-compatible format? (default: no)

Reply with any overrides (e.g. "preset wide, domain web") or just "go" to use defaults.
```

Parse the user's reply for:
- **preset**: `standard`|`wide`|`deep` (default: `standard`)
- **domain**: `codebase`|`web`|`mixed` (default: infer from topic)
- **slug**: string (default: derive from topic — lowercase, hyphens, max 40 chars)
- **composable**: boolean (default: false) — set if user says "composable", "--composable", or "overnight compatible"

If the user replies with just "go", "defaults", "ok", or similar, use all defaults.

### Preset Agent Counts

| Role | standard | wide | deep |
|-|-|-|-|
| Scout | 5 | 8 | 3 |
| Analyst | 3 | 2 | 5 |
| Synthesizer | 1 | 1 | 1 |
| Adversarial | 1 | 1 | 1 |
| **Total** | **10** | **12** | **10** |

---

## Phase 0 — Setup

1. Use the topic and options collected above.
2. Derive slug from topic if not provided.
3. Create directory structure:

```bash
mkdir -p research/{slug}/cache
mkdir -p research/{slug}/swarm/scout-findings
mkdir -p research/{slug}/swarm/analysis
mkdir -p research/{slug}/swarm/synthesis
mkdir -p research/{slug}/swarm/adversarial
```

4. Write `research/{slug}/metadata.json`:
```json
{
  "topic": "...",
  "pipeline": "swarm",
  "preset": "standard|wide|deep",
  "domain": "codebase|web|mixed",
  "slug": "...",
  "composable": false,
  "created": "ISO timestamp",
  "agent_counts": { "scouts": N, "analysts": N, "synthesizer": 1, "adversarial": 1 },
  "extraction_categories": [],
  "core_categories": [],
  "adjacent_categories": [],
  "stages_completed": [],
  "safety_cap": 50
}
```

5. **Slug collision handling:** If `research/{slug}/` already exists, use AskUserQuestion to ask: overwrite or rename.

Print: `[SWARM] phase=setup status=complete slug={slug} preset={preset}`

---

## Phase 1 — Survey & Schema

### Initial Survey

Run 2-3 **WebSearch** calls (or Glob/Grep for codebase domain) to survey the topic landscape. From results, identify **5-8 subtopics** that should be investigated.

### Extraction Schema

Design extraction categories:
- **Core categories (5-6):** must-cover, gaps reported
- **Adjacent categories (4-5):** extract-if-found, no gap reporting

Update metadata.json with `extraction_categories`, `core_categories`, `adjacent_categories`.

### Define the scout JSON schema (same as standard pipeline):
```json
{
  "scout_id": "string",
  "task_id": "string",
  "subtopic": "string",
  "sources_processed": [
    { "location": "string", "type": "file|url", "status": "success|partial|failed" }
  ],
  "findings": [
    {
      "category": "string",
      "subcategory": "string|null",
      "summary": "one sentence",
      "raw_excerpt": "VERBATIM quoted text - mandatory",
      "source_location": "string",
      "relevance": "high|medium|low",
      "claim_era": "2025-2026|historical-context|projection",
      "tags": ["freeform"]
    }
  ],
  "cross_references": [
    { "from": "string", "to": "string", "relationship": "string" }
  ],
  "gaps": [{"description": "string", "gap_type": "source_failure|knowledge_gap"}],
  "metadata": {
    "total_sources": 0,
    "total_findings": 0,
    "source_success_rate": 0.0,
    "processing_notes": "string"
  }
}
```

Print: `[SWARM] phase=survey status=complete subtopics={N} categories={M}`

---

## Phase 2 — Team Creation & Agent Spawning

### Create Team

```
TeamCreate:
  team_name: "swarm-{slug}"
  description: "Swarm research: {topic}"
  agent_type: "lead"
```

### Create Initial Tasks

Create one scout task per subtopic via TaskCreate:
```
title: "Scout: {subtopic name}"
description: "Discover sources and extract findings on: {subtopic description}. Search queries to try: {suggested queries}"
```

Create placeholder analyst tasks (fewer, broader):
```
title: "Analyze: {broad theme}"
description: "Deep-dive analysis on {theme}. Wait for scout leads, then synthesize findings."
```

### Spawn Agents

Spawn ALL agents in parallel using the Agent tool with `team_name: "swarm-{slug}"`.

**Scouts** — spawn {scout_count} agents:
```
For each scout (scout-1 through scout-N):
  Agent:
    name: "scout-{N}"
    team_name: "swarm-{slug}"
    subagent_type: "research:swarm-scout"
    run_in_background: true
    prompt: |
      TEAM_NAME: swarm-{slug}
      RESEARCH TOPIC: {topic}
      OUTPUT DIRECTORY: research/{slug}/swarm/scout-findings/
      EXTRACTION CATEGORIES: {categories}
      CORE CATEGORIES: {core categories}
      ADJACENT CATEGORIES: {adjacent categories}
      CACHE DIRECTORY: research/{slug}/cache/
      OUTPUT SCHEMA: {JSON schema}

      You are scout-{N}. Check TaskList for available scout tasks. Claim one and begin scouting.
      When done, mark complete and claim the next available task. Communicate leads to analysts.
```

**Analysts** — spawn {analyst_count} agents:
```
For each analyst (analyst-1 through analyst-N):
  Agent:
    name: "analyst-{N}"
    team_name: "swarm-{slug}"
    subagent_type: "research:swarm-analyst"
    run_in_background: true
    prompt: |
      TEAM_NAME: swarm-{slug}
      RESEARCH TOPIC: {topic}
      SCOUT FINDINGS DIRECTORY: research/{slug}/swarm/scout-findings/
      OUTPUT DIRECTORY: research/{slug}/swarm/analysis/
      EXTRACTION CATEGORIES: {categories}
      CORE CATEGORIES: {core categories}
      CACHE DIRECTORY: research/{slug}/cache/

      You are analyst-{N}. Check TaskList for analyst tasks or wait for scout messages.
      Deep-dive on threads, request more scouting if gaps found. Message synthesizer when done.
```

**Synthesizer** — spawn 1:
```
Agent:
  name: "synthesizer"
  team_name: "swarm-{slug}"
  subagent_type: "research:swarm-synthesizer"
  run_in_background: true
  prompt: |
    TEAM_NAME: swarm-{slug}
    RESEARCH TOPIC: {topic}
    SCOUT FINDINGS DIRECTORY: research/{slug}/swarm/scout-findings/
    ANALYSIS DIRECTORY: research/{slug}/swarm/analysis/
    SYNTHESIS DIRECTORY: research/{slug}/swarm/synthesis/
    EXTRACTION CATEGORIES: {categories}
    CORE CATEGORIES: {core categories}
    SAFETY CAP: 50

    You are the synthesizer. Monitor incoming findings, update patterns.md/contradictions.md/gaps.md.
    Signal SUFFICIENT to lead when all core categories have 3+ corroborated findings and no high-priority gaps remain.
```

**Adversarial** — spawn 1:
```
Agent:
  name: "adversarial"
  team_name: "swarm-{slug}"
  subagent_type: "research:swarm-adversarial"
  run_in_background: true
  prompt: |
    TEAM_NAME: swarm-{slug}
    RESEARCH TOPIC: {topic}
    SCOUT FINDINGS DIRECTORY: research/{slug}/swarm/scout-findings/
    ANALYSIS DIRECTORY: research/{slug}/swarm/analysis/
    OUTPUT DIRECTORY: research/{slug}/swarm/adversarial/
    CACHE DIRECTORY: research/{slug}/cache/

    You are the adversarial verifier. Wait for initial findings (3+ scout JSONs, 1+ analysis file),
    then begin independent verification. Challenge weak claims by messaging analysts directly.
    Message lead with final verdict summary when convergence is signaled.
```

Print: `[SWARM] phase=team-creation status=complete agents_spawned={total}`

---

## Phase 3 — Swarm Execution (Monitoring)

As the Lead, you monitor the swarm. Agents communicate via SendMessage and self-organize via the task list.

### Monitoring Loop

Periodically (after receiving agent messages or idle notifications):

1. **Check messages**: Agents will message you with updates. Respond as needed.
2. **Check TaskList**: Monitor task completion progress.
3. **Read synthesizer outputs**: Check `research/{slug}/swarm/synthesis/` for patterns.md and gaps.md updates.
4. **Watch for convergence signal**: The synthesizer will message you with "SUFFICIENT" when ready.

### Intervention Triggers

Intervene if:
- **No task completions for 3+ consecutive monitoring cycles**: Message idle agents to check status.
- **Synthesizer reports cap approaching**: Prepare for convergence.
- **Agent reports a blocker**: Help resolve (e.g., all URLs failing, topic too broad).

### Handling Agent Messages

- **Scout completion**: Acknowledge, no action needed (scouts self-organize).
- **Analyst completion**: Acknowledge, note which threads are analyzed.
- **Synthesizer gap request**: If synthesizer can't reach free agents, relay the request.
- **Synthesizer SUFFICIENT signal**: Proceed to Phase 4.
- **Adversarial verdict**: Note for final assembly.
- **Agent idle with no tasks**: If more work exists, create tasks. Otherwise, tell them to stand by.

Print periodic status: `[SWARM] phase=execution scouts_done={N}/{total} analyses={M} tasks={T}/{cap}`

---

## Phase 4 — Convergence

When the synthesizer signals SUFFICIENT (or safety cap is reached):

1. **Let in-progress tasks finish**: Check TaskList for in-progress tasks. Wait for them to complete.
2. **Signal adversarial to finalize**: Message adversarial: "Convergence reached. Please finalize your verification and send final verdict."
3. **Wait for adversarial final verdict**: The adversarial agent will message you with their summary.

Print: `[SWARM] phase=convergence status=complete`

---

## Phase 5 — Assembly

Read all outputs and assemble the final report.

### Read Outputs

1. Read all scout JSONs from `research/{slug}/swarm/scout-findings/`
2. Read all analyst analyses from `research/{slug}/swarm/analysis/`
3. Read synthesizer outputs: `patterns.md`, `contradictions.md`, `gaps.md`
4. Read adversarial outputs: `challenged-claims.md`, `bias-assessment.md`

### Write REPORT.md

Assemble `research/{slug}/REPORT.md`:

```markdown
# {Research Topic}

## Executive Summary
{2-4 paragraphs synthesizing the overall findings, using patterns.md as the structural guide}

## {Section per core category}
{Content drawn from analyst deep-dives, with scout JSON excerpts as citations}

> {raw_excerpt from scout findings}
> — *{source_location}*

{Confidence annotations from adversarial verdicts where applicable:}
{[CONFIRMED], [SUPPORTED], [DISPUTED] inline markers}

## Cross-Cutting Patterns
{From synthesizer's patterns.md — themes that span multiple categories}

## Contradictions & Open Questions
{From synthesizer's contradictions.md and gaps.md — what remains unresolved}

## Adversarial Audit Summary
{From challenged-claims.md — verdict counts and key findings}
{From bias-assessment.md — overall confidence assessment}

---

## Sources
{Compiled from all scout JSONs and analyst files — every URL referenced}

[1] Title - URL - accessed {date}
[2] ...

---

<!-- PIPELINE METADATA
Pipeline: swarm
Preset: {preset}
Agents: {scout_count} scouts, {analyst_count} analysts, 1 synthesizer, 1 adversarial
Tasks created: {total}
Safety cap: {cap}
Adversarial verdict: {overall assessment}
Generated: {ISO timestamp}
-->
```

### Write sources.md

Write `research/{slug}/sources.md` with all URLs from scout JSONs and analyst files, deduplicated.

Print: `[SWARM] phase=assembly status=complete report_size={bytes}`

---

## Phase 6 — Finalize

### Generate PDF

Invoke the `md-to-pdf` skill:
```
Convert research/{slug}/REPORT.md to PDF at research/{slug}/REPORT.pdf
```

If PDF generation fails, log the error and continue.

### Discord Notification

Read the Discord webhook URL from `~/.claude/tts-config.json` (the `completed` webhook under `discord_webhooks`).

If `research/{slug}/REPORT.pdf` exists and is under 25MB:
```bash
curl -F "file1=@research/{slug}/REPORT.pdf" \
  -F 'payload_json={"content":"Research complete: {topic}"}' \
  "$(cat ~/.claude/tts-config.json | python3 -c \"import json,sys; print(json.load(sys.stdin)['discord_webhooks']['completed'])\")"
```

If PDF is missing or >25MB, fall back to text-only notification.

### Shutdown Team

1. Send `shutdown_request` to all agents via SendMessage.
2. Wait for shutdown confirmations.
3. Run TeamDelete to clean up team and task resources.

Print: `[SWARM] phase=finalize status=complete`

Update metadata.json: add `"finalized"` to `stages_completed`.

---

## Phase 7 — Bridge (only if composable=true)

If the user requested `--composable` output:

1. **Create overnight-compatible structure**:
```bash
mkdir -p research/{slug}/round-1/scout
mkdir -p research/{slug}/round-1/analysis
```

2. **Copy/symlink swarm outputs**:
```bash
# Copy scout findings as round-1 scout output
cp research/{slug}/swarm/scout-findings/*.json research/{slug}/round-1/scout/

# Copy first analyst analysis as round-1 DRAFT.md
# Concatenate all analyst files into a single draft
cat research/{slug}/swarm/analysis/*.md > research/{slug}/round-1/analysis/DRAFT.md
```

3. **Generate compilation.md from synthesizer**:
   - Read `research/{slug}/swarm/synthesis/gaps.md`
   - Convert remaining gaps into the compiler's format (with suggested searches)
   - Write `research/{slug}/round-1/compilation.md` with Decision: CONTINUE if gaps remain, FINALIZE if not

4. **Update metadata.json**:
```json
{
  "pipeline": "swarm+overnight",
  "rounds_completed": 1,
  "stages_completed": [..., "round-1-scout", "round-1-analysis", "round-1-compilation"]
}
```

5. Print instructions:
```
Swarm output bridged to overnight format.
To continue with iterative follow-up rounds:
  /research:overnight --from round-2 --slug {slug}
```

---

## Final Summary

Print:

```
Research complete: {topic}
Pipeline: swarm ({preset} preset)
Domain: {domain}
Agents: {scout_count} scouts, {analyst_count} analysts, 1 synthesizer, 1 adversarial
Tasks created: {total_tasks}
Findings: {total from scout JSONs}
Adversarial audit: {overall assessment}

Output:
  research/{slug}/REPORT.md              — Final report
  research/{slug}/REPORT.pdf             — PDF version
  research/{slug}/swarm/scout-findings/  — Scout extraction JSONs
  research/{slug}/swarm/analysis/        — Analyst deep-dives
  research/{slug}/swarm/synthesis/       — Patterns, contradictions, gaps
  research/{slug}/swarm/adversarial/     — Verification & bias assessment
  research/{slug}/sources.md             — All URLs referenced

Run `/research:operationalize {slug}` to create operational artifacts.
```

---

## Orchestration Rules

1. **All agents run in the background.** Use `run_in_background: true` for every agent spawn.
2. **Agents self-organize via task list + messaging.** You monitor and intervene only when needed.
3. **Verify between phases** — check that expected output files exist before proceeding.
4. **Report progress** — tell the user which phase is running and key milestones.
5. **Cache is shared** — all agents use the same `cache/` directory.
6. **Core invariant:** Scouts write JSON files to disk with verbatim excerpts. Analysts read those files directly.
7. **Safety cap:** Maximum 50 tasks total. Synthesizer tracks and signals when approaching.

## Error Handling

- If no subtopics identified in survey: AskUserQuestion to refine topic.
- If team creation fails: Report error, suggest retrying.
- If no scout outputs after reasonable time: Message scouts for status, intervene if stuck.
- If synthesizer never signals SUFFICIENT: Force convergence after safety cap or extended inactivity.
- If adversarial fails: Proceed with REPORT.md without adversarial section (warn user).
- If PDF generation fails: Continue with markdown report.
- Never silently skip phases. Always report what happened.
