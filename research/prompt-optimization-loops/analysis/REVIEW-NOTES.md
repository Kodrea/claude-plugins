# Review Notes for Auditor

## TODO Markers

- [ ] **Convergence plateau / K threshold** (DRAFT.md — "Convergence and Plateau Escape" section): No concrete source-backed value for K (non-improving step count) found across all three scouts. The draft uses K=5–10 as a placeholder in the Recommendations section. Auditor should locate an empirical recommendation or decide on a value based on benchmark cost.

- [ ] **APO edits-per-candidate N** (DRAFT.md — "Population Management" section): The APO N parameter (edits applied per candidate per step) is described in source text but no recommended value is given. Auditor should determine whether this parameter is exposed in any open-source APO implementation with default values.

- [ ] **Claude-3.5-Sonnet model comparison currency** (DRAFT.md — Executive Summary and Cost Optimization section): The finding that Claude-3.5-Sonnet outperforms O1 and GPT-4o as an optimization engine derives from ca. 2025 sources. This ranking is likely stale given the pace of model releases. Verify against current model comparisons before relying on this recommendation.

## Unresolved Contradictions

- [ ] **Population size: 20–50 (PromptBreeder) vs. 3 (evolving-excellence)**: PromptBreeder recommends population size 20–50 with generations 10–30. The evolving-excellence framework achieved competitive results with population size 3 and only 2–3 generations. These are not strictly contradictory (different task types, benchmark scales, and mutation quality), but the auditor should determine which regime applies to the current system's benchmark scale before selecting a population size.

- [ ] **Convergence window: 20–50 iterations (SI-Agent) vs. 2–3 generations (evolving-excellence)**: These two data points both suggest rapid convergence but are not directly comparable — SI-Agent counts individual iterations while evolving-excellence counts generations over a population. Without knowing the population size and how many evaluations per generation, it is unclear whether these figures are consistent or contradictory. Auditor should normalize both to total benchmark evaluations.

## Low-Confidence Items

- [ ] **Source content depth**: All three scouts note that the cached source files contain highly condensed summaries (3 lines per file in some cases) rather than full article or paper content. All findings are sourced from these summaries. This limits the depth of technical detail available and means some nuances in the original sources may not be captured. The auditor may want to obtain full source documents for any finding that will be acted on.

- [ ] **Explicit anti-overfitting instruction effectiveness**: The finding "Explicit anti-overfitting instruction in prompts" (evidently-practical.txt) is reported without supporting evidence or effect size. Its inclusion in the recommendations is low-cost but the actual effectiveness is unverified.

- [ ] **PromptBreeder smoothing alpha range (0.7–0.9)**: This parameter range is reported verbatim from the scout summary but without the underlying reasoning or empirical justification. The auditor should verify whether this range is task-specific or general.

- [ ] **5–10 labeled examples claim**: The claim that "5-10 labeled examples often sufficient" (evidently-practical.txt) is a strong generalization. The context is not clear — this may apply to simple classification tasks rather than complex agent instruction tuning. Treat as a lower-bound data point, not a recommendation.

- [ ] **dev set curves predict test reliability**: This finding (langchain-optimization.txt) is stated without qualification about conditions under which it holds. If the dev set was itself used to guide selection strategy choices (i.e., was used at the experiment-design level), it is not truly independent and cannot reliably predict test performance.
