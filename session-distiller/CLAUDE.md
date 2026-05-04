# Session Distiller

Extracts, strips, and analyzes Claude Code session data to identify interaction patterns between user and assistant. Produces actionable findings — CLAUDE.md rules, skill/hook recommendations, behavioral insights.

## Architecture

Two-stage pipeline:

1. **Strip & Batch (deterministic, Python):** Parse session JONLs, remove noise (progress records, thinking blocks, file-history snapshots, tool result bodies), preserve conversation signal (user messages, assistant text, tool call names/params, timestamps, errors). Batch into context-sized chunks.

2. **Analyze (Opus 4.6):** Feed stripped batches to headless Claude for pattern analysis. Optionally run a review team (synthesizer + verifier + pattern-hunter) for cross-project synthesis.

## Data Sources

Session JONLs live at `~/.claude/projects/<project-id>/*.jsonl` on each machine.

| Machine | SSH | User | Projects |
|-|-|-|-|
| pop-os (local) | n/a | cody | dell-poweredge, a100-gpu, orin-nano, radxa-rock5b, agent-training, etc. |
| Mac Mini | `ssh -o IdentitiesOnly=yes -i ~/.ssh/id_ed25519 codyserban@100.81.185.119` | codyserban | voicemode-ios, esp32s3-sense, iOS-apps, parsec |

## Usage

### Step 1: Strip & Batch

```bash
# Local project — all sessions
python3 pipeline.py \
  --project ~/.claude/projects/-home-cody-Projects-hardware-dell-poweredge \
  --name "dell-poweredge"

# Remote project (Mac Mini) — all sessions
python3 pipeline.py \
  --remote codyserban@100.81.185.119 \
  --project "~/.claude/projects/-Users-codyserban-Projects-iOS-apps-voicemode-ios" \
  --name "voicemode-ios"

# Limit to N largest sessions
python3 pipeline.py --project <path> --name "my-project" --top 10

# Custom output dir
python3 pipeline.py --project <path> --name "my-project" --output ~/distiller-runs/custom
```

Output lands in `~/distiller-runs/<name>_<timestamp>/`:
```
batches/batch-01.jsonl   # Stripped sessions, chronological, ~800KB max per batch
batches/batch-02.jsonl
stripped/                 # Individual stripped session files
manifest.json            # Run metadata, session stats, compression ratio
prompts.md               # Ready-to-paste analysis prompts per batch
```

### Step 2: Analyze (headless Opus)

Run each batch through headless Claude:

```bash
# Single batch
claude -p "read <batch-file>. This file contains N stripped Claude Code sessions \
from the project \"<name>\" spanning <dates>. These are real conversations between \
a user and an AI assistant — what do you notice about how it went?" \
--model claude-opus-4-6 --dangerously-skip-permissions > output.md

# All batches in parallel
for batch in ~/distiller-runs/<run>/batches/batch-*.jsonl; do
  name=$(basename "$batch" .jsonl)
  claude -p "read $batch. This file contains stripped Claude Code sessions. \
  These are real conversations between a user and an AI assistant — what do you \
  notice about how it went? Look for patterns that repeat, moments where the \
  interaction went sideways, and what went well. For each pattern: type, frequency, \
  specific quoted moments, and highest-impact fix. Rank by impact." \
  --model claude-opus-4-6 --dangerously-skip-permissions \
  > ~/distiller-runs/analysis/${project}_${name}.md &
done
wait
```

The prompts.md file in each run has pre-formatted prompts with correct batch paths, session counts, and date ranges.

### Step 3: Review Team (optional, for cross-project synthesis)

After analyzing multiple projects, assemble a review team:
- **synthesizer:** Reads all analysis outputs, normalizes pattern names, identifies systemic issues
- **verifier:** Spot-checks quoted messages and counts against stripped source files
- **pattern-hunter:** Reads stripped sessions directly for non-obvious patterns (timing, behavioral evolution, correction vocabulary)

Use TeamCreate with team_name "distiller-review". See the FINDINGS.md workflow in the existing runs for team prompt templates.

## What Gets Stripped (and why)

| Record type | Action | Reason |
|-|-|-|
| `progress` | STRIP (except subagent prompts) | 64% of file, streaming duplicates |
| `thinking` | STRIP | Empty shells with opaque base64 signatures |
| `file-history-snapshot` | STRIP | Backup metadata, no narrative value |
| `last-prompt` | STRIP | Session-end marker |
| `tool_result` (Read/Glob/Grep) | Replace with `[Read: path — N lines]` | Full file contents are duplicates of on-disk files |
| `tool_result` (Bash) | Truncate to 500 chars | Error messages live in first 500 chars |
| `tool_result` (errors) | KEEP full | Errors are always signal |
| `usage` objects | STRIP | Token counters, 21KB per session |
| Static metadata | Extract once, strip from lines | sessionId, version, gitBranch, cwd repeated on every record |
| User text messages | KEEP full | Primary signal |
| Assistant text responses | KEEP full | Conversation content |
| Tool call name + params | KEEP (summarized) | file_path, command[:200], pattern, query |
| `permissionMode` changes | KEEP | Signals plan mode entry |
| `system` turn_duration | KEEP | How long Claude took per turn |

Typical compression: 8-13x for tool-heavy sessions, 2-3x for paste-heavy sessions.

## Existing Runs

Runs are stored in `~/distiller-runs/`. Each run has a manifest.json.

```bash
# List all runs
for dir in ~/distiller-runs/*/; do
  [ -f "$dir/manifest.json" ] && python3 -c "
import json; m=json.load(open('${dir}manifest.json'))
print(f'{m[\"project\"]:20s} | {len(m[\"sessions\"]):>2} sessions | {m[\"date_range\"]}')"
done
```

## Key Findings (from initial analysis)

The first full analysis (5 projects, 35 sessions) identified 3 root causes behind most interaction problems:

1. **Inference-as-knowledge:** Claude treats its own guesses as verified facts
2. **Progress illusion:** Claude optimizes for visible activity over understanding
3. **No session architecture:** No checkpoints, no structure, scope creeps unchecked

Full findings: `~/distiller-runs/analysis/FINDINGS.md`
Supporting docs: `CROSS-PROJECT-SYNTHESIS.md`, `VERIFICATION-REPORT.md`, `HIDDEN-PATTERNS.md`
