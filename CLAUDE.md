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

Two autoresearch-style loops optimize agent instructions against an ESP32-S3 benchmark:

**Haiku track** — optimizes `plugins/research/agents/solo-haiku-scout.md`
```bash
claude --dangerously-skip-permissions -p "/optimize-haiku --rounds 100 --tag <tag>"
```

**Sonnet track** — optimizes `plugins/research/agents/solo-sonnet-researcher.md`
```bash
claude --dangerously-skip-permissions -p "/optimize-sonnet --rounds 50 --tag <tag>"
```

Each loop: edit agent file → git commit → spawn agent on benchmark sources → score with `score.py` → keep/discard → repeat.

### Benchmark Layout
```
plugins/research/benchmark/
├── sources/esp32s3/     # 5 cached ESP32-S3 docs (datasheet, hw-ref, programming, AI, community)
├── rubric.json          # 28 expected findings (Haiku track, 4 sources)
├── rubric-sonnet.json   # 32 expected findings (Sonnet track, 5 sources)
├── score.py             # Deterministic scorer, 7 dimensions, outputs JSON
├── results.tsv          # Haiku experiment log (untracked)
└── results-sonnet.tsv   # Sonnet experiment log (untracked)
```

### Scoring Dimensions (weights)
finding_recall (25%), verbatim_quality (20%), category_coverage (15%), precision (15%), cross_references (10%), gap_detection (10%), structure_quality (5%)

### Plans & Reports
- `dual-track-optimization-plan.html` — full plan with ESP32-S3 benchmark design
- `build-report.html` — what was actually built
- `tiered-research-optimization-plan.md` — future Phase 3 (tiered pipeline optimization)
