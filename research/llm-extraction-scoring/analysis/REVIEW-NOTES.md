# Review Notes for Auditor

## TODO Markers

- [ ] **Prometheus version reconciliation** (DRAFT.md — Scoring Metrics, LLM-as-Judge, Additional Notes): The 0.897 Pearson correlation figure and the 0.6-0.7 correlation figure both originate from `prometheus-framework.txt` but are attributed to different versions (v1 13B vs. v2 8x7B). Scout claim_era labels these as "2025-2026" but the source note says "May 2024" for v2. Auditor should confirm: (a) which version each figure belongs to, (b) whether the 0.897 figure is compared against human evaluators or GPT-4 evaluators, and (c) whether the 0.6-0.7 range uses GPT-4-1106 as a proxy for human judgment or as a direct comparison target.

## Unresolved Contradictions

- [ ] **Prometheus correlation figures are inconsistent**: `prometheus-framework.txt:16` reports 0.897 Pearson correlation with human evaluators and `prometheus-framework.txt:17` states "on par with GPT-4 (0.882)". However, `prometheus-framework.txt:18` reports "0.6-0.7 correlation with GPT-4-1106" for Prometheus 2 (8x7B). It is unclear whether these represent: different model versions (v1 vs. v2), different evaluation protocols (human judges vs. GPT-4 as judge proxy), or different datasets. Both figures are presented in the draft; the auditor must establish which is the primary performance claim and under what conditions.

- [ ] **Krippendorff alpha interpretation**: `llm-judge-design-choices.txt:18-21` reports α = 0.908 with criteria + reference and α = 0.896 without both, with the note "removing criteria causes noticeable drop." However a drop from 0.908 to 0.896 (Δ = 0.012) is small and whether it is statistically significant is not established in the source. Auditor should verify whether the source provides significance testing for this difference.

## Low-Confidence Items

- [ ] **"Direct scoring beats CoT when criteria are well-defined"** (DRAFT.md — Scoring Metrics): This is a medium-relevance finding from `llm-judge-design-choices.txt:27` with limited supporting detail in the scout excerpt. The conditional "when criteria are well-defined" is analyst inference; verify whether the source states this condition explicitly or whether it is unstated.

- [ ] **Intermediate rubric level impact claim**: The finding that "intermediate score descriptions (2,3,4) had limited impact" is drawn from correlation comparisons (full rubric 0.666 vs. minimal rubric matching performance). The scout does not indicate whether this was tested across multiple tasks or a single task type. If single-task, generalizability is uncertain.

- [ ] **"5 runs provides adequate sampling"** (`llm-judge-design-choices.txt:25`): This is a practical recommendation without stated statistical power analysis. It is unclear whether "adequate" is defined relative to a specific correlation target or variance threshold. The claim may be task-specific.

- [ ] **TSR implementation via FuzzyWuzzy**: The scout excerpt confirms TSR uses FuzzyWuzzy library (`casereportbench.txt:12`). FuzzyWuzzy is a specific Python library with known behavior. Verify whether the source specifies which FuzzyWuzzy ratio function is used (token_set_ratio vs. token_sort_ratio vs. partial_ratio), as these produce different scores.

- [ ] **KILT/FEVER claim_era**: Both scouts assign "2025-2026" claim_era to KILT and FEVER findings. KILT and FEVER are established benchmarks predating 2025. The claim_era label likely reflects the date of the cached document rather than the original publication date. Auditor should verify that KILT/FEVER findings are presented as historical/established benchmarks rather than novel 2025 contributions.
