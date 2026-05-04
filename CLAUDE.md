# Claude Plugins

Plugin-based extensions for Claude Code. Each plugin lives under `plugins/` with `commands/`, `agents/`, and `skills/` subdirectories.

## Key Plugins

| Plugin | Purpose |
|-|-|
| research | Tiered research pipeline (scout→analyst→auditor) + optimization loops |
| doc-pipeline | Documentation generation from web sources |
| permission-manager | Configure Claude Code permission rules |
| haiku-scout | Fast codebase mapping with Haiku |
| text-to-audio | Document-to-audio conversion via qwen3-tts |
| self-learning | Insight capture system |

## Research Optimization System

Autoresearch-style loops optimize agent instructions by iterating: edit agent file → spawn agent on benchmark sources → score → keep/discard → repeat.

The training loop lives in a separate repo: `/home/cody/Projects/ai-ml/agent-training/`

```bash
# Run from agent-training repo (or a git worktree of it)
bash scripts/training-loop.sh configs/haiku-esp32s3.json --rounds 20 --tag my-tag
```

For parallel runs (both configs edit the same agent file), use git worktrees for isolation.

### Agent-Training Repo Layout
```
agent-training/
├── agents/solo-haiku-scout.md    # Optimization target (Haiku)
├── agents/solo-sonnet-researcher.md
├── configs/                      # Benchmark configs (haiku-esp32s3, haiku-sqlite, sonnet-esp32s3)
├── benchmarks/esp32s3/           # 4 cached docs (datasheet, hw-ref, programming, ai)
├── benchmarks/sqlite/            # 4 cached docs (architecture, c-api, performance, sql-reference)
├── rubrics/esp32s3.json          # 28 expected findings
├── rubrics/sqlite.json           # 32 expected findings
├── rubrics/esp32s3-sonnet.json   # 32 expected findings (5 sources incl. community thread)
├── scoring/score.py              # Deterministic scorer, 10 dimensions
├── scripts/training-loop.sh      # Main loop script
└── summaries/                    # Auto-generated run summary JSONs
```

### Run Summaries
After each training loop completes, a JSON summary is written to `summaries/` in the agent-training repo. Each file is named `{datetime}_{run-name}.json` and contains baseline/best scores, kept rounds with descriptions, dimension breakdowns, and a full config snapshot. Browse this folder to review completed runs without parsing TSV or logs.

Legacy copies of rubrics and score.py remain in `plugins/research/benchmark/` but are not actively used.

### Scoring Dimensions (weights)
finding_recall (25%), verbatim_quality (20%), category_coverage (15%), information_density (15%), cross_references (10%), gap_identification (5%), gap_quality (5%), source_attribution (5%)

### Plans & Reports
- `dual-track-optimization-plan.html` — full plan with ESP32-S3 benchmark design
- `build-report.html` — what was actually built
- `tiered-research-optimization-plan.md` — future Phase 3 (tiered pipeline optimization)
