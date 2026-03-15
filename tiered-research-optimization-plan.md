# Fix Optimization Loop — Audit Remediation

## Context

Built an autoresearch-style optimization loop (`/research:optimize`) that iteratively improves research agent instructions by benchmarking against synthetic sources and scoring output. An Opus audit found 4 confirmed bugs in scoring, 2 operational gaps in the loop, and several rubric calibration issues. This plan fixes all of them before first use.

## Changes

### 1. Fix `score.py` — Scoring Bugs

**File:** `plugins/research/benchmark/score.py`

**a) Placeholder detection (CRITICAL)**
Line 94 — `excerpt.startswith("[")` catches markdown links, JSON arrays, etc.
```python
# Replace with:
if re.match(r'\[(?:could not|unable to|no )', excerpt.lower()):
```

**b) Category coverage bidirectional match (CONFIRMED)**
Line 143 — `if core in found or found in core` inflates coverage (e.g., `"api_configuration"` matches both `"api"` AND `"configuration"`).
```python
# Replace with exact match after normalization:
if core == found:
```

**c) Verbatim minimum window size**
Add `max(5, ...)` floor so short excerpts (3-4 words) don't pass by coincidence.

**d) Add cross-reference and gap scoring**
Add `score_cross_references()` and `score_gap_detection()` functions. Update `scoring_weights` to redistribute:
```
finding_recall:    0.25  (was 0.30)
verbatim_quality:  0.20  (was 0.25)
category_coverage: 0.15  (was 0.20)
precision:         0.15  (unchanged)
structure_quality: 0.05  (was 0.10)
cross_references:  0.10  (NEW)
gap_detection:     0.10  (NEW)
```

### 2. Fix `rubric.json` — Generic Fragments

**File:** `plugins/research/benchmark/rubric.json`

| Finding | Old Fragment | New Fragment |
|-|-|-|
| F011 | `"recovery"` | `"recovery time"` |
| F013 | `"controller"` | `"controller-worker"` |
| F014 | `"workers"` | `"1 controller + 2 workers"` |
| F021 | `"rolling"` | `"rolling upgrade"` |

Update `scoring_weights` to include new dimensions (match score.py changes).

### 3. Fix `optimize.md` — Loop Mechanics

**File:** `plugins/research/commands/optimize.md`

**a) Add resume protocol**
Add a "Resume" section before the loop: "If results.tsv exists with entries, read the last `keep` row, `git checkout` that commit, set best_score from that row, continue from next experiment number."

**b) Double-run averaging**
Change benchmark step: "Run each benchmark 2x (spawn 2+2 scouts = 4 total), average the composite scores. This costs 4 Haiku calls instead of 2 but eliminates false keeps/discards from non-determinism."

**c) Inline the scout JSON schema**
Replace the comment `(use the schema from the research.md command)` with the actual JSON schema copy-pasted from research.md.

**d) Clarify baseline logging**
Add explicit step: "Log baseline to results.tsv with status `baseline`. Set this as the initial `best_score` for comparison."

**e) Add example score.py JSON output**
Show what `--json` mode returns so the agent knows what to parse.

**f) Normalize tool name**
Change `allowed-tools` from `Agent` to `Task` to match other orchestrators. Update body text references.

**g) Add per-dimension tracking in results.tsv**
The header already includes all dimensions — just make clear in the loop body that the agent should parse and log each dimension from `--json` output, not just composite.

### 4. Fix `optimize.md` — Gaps from Autoresearch Cross-Check

**File:** `plugins/research/commands/optimize.md`

**h) Add experiment timeout**
Autoresearch kills runs exceeding 10 minutes. Add: "Each scout has a 3-minute timeout. If a scout doesn't return within 3 minutes, treat the experiment as a crash — log it, revert, move on."

**i) Add crash retry logic**
Autoresearch retries fixable errors (typos, missing imports) before skipping. Add: "If a scout crashes or produces invalid JSON, check if the error is in the agent instructions you just edited (e.g., malformed example JSON). If fixable, amend the commit and re-run once. If it crashes again, log as crash and revert."

**j) Add source pre-check**
Autoresearch verifies data shards exist before starting. Add to Setup: "Verify benchmark sources exist: `ls plugins/research/benchmark/sources/*.md` — expect 3 files. If missing, abort with an error."

**k) Add rewind guidance**
Autoresearch mentions reverting to an earlier successful commit if deeply stuck. Add: "If you are stuck after 15+ consecutive discards, consider reverting to the highest-scoring commit in results.tsv and trying a completely different direction."

### 5. Add plateau detection

Soft rule in the loop: "If no improvement in 10 consecutive experiments, try 3 radical changes (large rewrites, opposite approaches). If still no improvement, print a summary and suggest the user review results.tsv."

## Files Modified

| File | Changes |
|-|-|
| `plugins/research/benchmark/score.py` | Fix placeholder detection, category matching, add cross-ref/gap scoring |
| `plugins/research/benchmark/rubric.json` | Fix generic fragments, update scoring weights |
| `plugins/research/commands/optimize.md` | Add resume, double-run, inline schema, baseline logging, example output, timeout, crash retry, source pre-check, rewind guidance |

## Verification

1. Run `python3 plugins/research/benchmark/score.py --help` — should show updated help
2. Create a test scout JSON with a `[markdown link](url)` excerpt — should NOT be classified as placeholder
3. Create a test scout JSON with category `"api_configuration"` — should only match one core category, not two
4. Run full scoring against a test scout dir — should show all 7 dimensions including cross_references and gap_detection
5. Read optimize.md and verify the scout prompt contains the full JSON schema inline
6. Read optimize.md and verify resume protocol, double-run instructions, and baseline logging are clear
