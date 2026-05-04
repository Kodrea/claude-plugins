# Scoring and Evaluation Rubric Design for LLM Information Extraction Benchmarks

## Executive Summary

This report synthesizes findings from two scout passes covering six primary sources: a noisy hypothesis testing framework for LLM judges, an empirical study of LLM judge design choices, a survey of LLM-as-judge methods, the Prometheus evaluation framework, and two benchmark datasets (CaseReportBench and KILT/FEVER). Together these sources yield 56 raw findings (31 from scout-001, 25 from scout-002) across nine categories: scoring metrics, rubric design, noise and variance, bias mitigation, datasets and benchmarks, partial matching, LLM-as-judge, inter-rater reliability, and calibration.

The central practical findings are: (1) **rubric design matters more than model size** -- providing reference answers alongside score descriptions is the single highest-leverage design decision for consistent LLM judge evaluation; (2) **sampling beats greedy decoding** -- mean aggregation over five sampled runs achieves 0.666 correlation with humans versus 0.593-0.635 for greedy decoding; (3) **intermediate rubric levels add little** -- minimal rubrics describing only extremes match full five-level rubric performance; and (4) **partial matching metrics are essential** for real extraction benchmarks where exact match severely underestimates model performance.

Real-world benchmark data (CaseReportBench) underscores that inter-annotator agreement can vary enormously by category (42.5%-98.5% TSR), revealing that ground truth quality is itself a first-class concern. The noisy hypothesis testing framework addresses this directly by providing formal Type-I error bounds when using LLM judges as proxies for human evaluation, enabling rigorous statistical guarantees even with imperfect judges.

Gaps remain in: practical thresholds for acceptable judge noise levels, guidance on calibration set sizing, comparison of rubric-based scoring against similarity-based alternatives, and handling of tasks with multiple valid answers or deeply subjective ground truth.

---

## Scoring Metrics

### Multi-Metric Coverage for Information Extraction

Real extraction benchmarks require a portfolio of metrics rather than any single measure. CaseReportBench applies five complementary metrics simultaneously:

> - Token Set Ratio (TSR%): measures token selection correctness (0-100), uses FuzzyWuzzy
> - Levenshtein Similarity: character-level edit distance (0-100)
> - Exact Match: percentage of perfect matches
> - BLEU and ROUGE-L
> -- *casereportbench.txt:12-15*

A dedicated hallucination rate metric captures the failure mode of generating content absent from the ground truth:

> Hallucination Rate: percentage of extracted info absent from benchmark
> -- *casereportbench.txt:16*

Provenance-grounded benchmarks like KILT/FEVER go further by requiring source attribution accuracy:

> Provenance: Wikipedia IDs, titles, sections, paragraph positions, character offsets
> - Structured ground truth with exact source attribution
> -- *kilt-fever-benchmarks.txt:17-18*

### LLM Judge Aggregation and Correlation with Humans

When LLM judges produce numeric scores, aggregation strategy matters significantly. Mean aggregation over five sampled runs is the empirical optimum:

> Mean aggregation of 5 sampled scores: 0.666 correlation (best)
> - Median: 0.648, Majority voting: 0.647
> -- *llm-judge-design-choices.txt:9-10*

For the Prometheus framework specifically, the headline human correlation figure belongs to Prometheus v1 (13B parameters), evaluated against human evaluators:

> Pearson correlation 0.897 with human evaluators (45 customized rubrics)
> -- *prometheus-framework.txt:16*

This 0.897 figure represents Prometheus v1 (13B) correlation with **human evaluators** on 45 customized rubrics. The comparison point is GPT-4's 0.882 correlation with the same human evaluators, meaning Prometheus v1 slightly exceeded GPT-4 on this benchmark. The original Prometheus paper was published at ICLR 2024.

Prometheus v2 (8x7B MoE, released May 2024) achieves a lower correlation range, but against a **different comparison target** -- GPT-4-1106 as the reference rather than human evaluators:

> Prometheus 2 (8x7B): 0.6-0.7 correlation with GPT-4-1106
> -- *prometheus-framework.txt:18*

The difference between 0.897 and 0.6-0.7 reflects both a different model version (v1 13B vs. v2 8x7B) and a fundamentally different evaluation protocol (correlation with human evaluators vs. correlation with GPT-4-1106 as proxy). These figures should not be directly compared as they measure different things.

### Decoding Strategy Impact on Score Reliability

Greedy decoding is a trap for LLM judge implementers: it produces zero variance in scores while delivering the worst human alignment:

> Greedy decoding: zero score variance but poor human correlation (0.593-0.635)
> - Sampling-based: higher variance but better human alignment (0.641-0.666)
> -- *llm-judge-design-choices.txt:7-8*

### Direct Scoring vs. Chain-of-Thought

> Direct scoring + averaging beats CoT when criteria are well-defined
> -- *llm-judge-design-choices.txt:27*

The conditional "when criteria are well-defined" is stated explicitly in the source. This is a medium-confidence finding from a single study; the source does not define what constitutes "well-defined" criteria, though the rubric design findings in this report (reference answers, clear extreme-level descriptions) provide practical guidance on achieving that condition.

### Clinical Actionability Evaluation

Beyond automated metrics, CaseReportBench demonstrates physician re-evaluation using a structured human evaluation instrument:

> Physician re-evaluation used 7 dimensions on 1-5 Likert scales
> -- *casereportbench.txt:29*

This mirrors the Prometheus five-point approach but applies it to human clinical judges rather than LLM judges, illustrating the cross-applicability of structured scale design.

---

## Rubric Design

### Structured Five-Point Scale as the Standard

The most empirically validated rubric format uses a five-point Likert scale with explicit level descriptions. Prometheus encodes this as:

> Five-point scale (1-5)
> - Each rubric specifies: criteria name, five descending quality level descriptions
> - Format: "Score 1: {description}" through "Score 5: {description}"
> - Score 5 = highest quality
> -- *prometheus-framework.txt:5-8*

### The Reference Answer Is More Important Than Intermediate Descriptions

Two scout passes from shared sources independently confirm this finding (high confidence):

> Providing both reference answers and score descriptions is crucial
> - Reference answers matter more than detailed intermediate rubric levels
> -- *llm-judge-design-choices.txt:16,26*

The empirical evidence for this claim comes from correlation comparisons:

> Full rubric (all 5 levels described): 0.666 correlation
> - Minimal (only extremes 1 and 5 described): matched full rubric performance
> - Intermediate score descriptions (2,3,4) had limited impact
> -- *llm-judge-design-choices.txt:13-15*

The practical implication: rubric construction effort should concentrate on (a) accurate reference answers and (b) clear descriptions of levels 1 and 5. Detailed prose for levels 2-4 is largely wasted effort. **Caveat**: this finding comes from a single empirical study; the source does not indicate whether it was tested across multiple task types or a single task type, so generalizability beyond the studied tasks is uncertain.

### Criteria Decomposition and Multi-Dimensional Evaluation

Holistic scoring should be avoided in favor of dimension-specific evaluation:

> Criteria Decomposition: break evaluation into specific dimensions rather than holistic scoring
> - Likert Scale Structures: 1-5 across predefined dimensions, dimension-specific scoring before overall
> -- *llm-judge-survey.txt:5-7*

Prometheus implements this through sequential single-criteria rubrics rather than a monolithic multi-criteria prompt:

> Multi-dimensional: focuses on single-criteria per rubric, multiple rubrics applied sequentially
> -- *prometheus-framework.txt:25*

### Step-by-Step Verification for Complex Judgments

G-Eval offers an alternative approach using chain-of-thought to decompose complex judgments:

> Step-by-Step Verification (G-Eval): decompose complex judgments into intermediate steps
> -- *llm-judge-survey.txt:6*

This contrasts with Prometheus's rubric-provision approach (see "LLM-as-Judge: Framework Comparison" below).

### Context-Dependent Rubric Calibration

> "reliability is context-dependent" - rubric and calibration choices should adapt to task complexity
> -- *llm-judge-survey.txt:25*

This is a qualitative guidance finding. No specific decision rules are provided in the sources for when to increase rubric complexity.

### Training a Judge on Rubric Feedback

> Trained on Feedback Collection dataset (kaist-ai on HuggingFace)
> - Learns to produce evaluations with detailed feedback + numeric score (1-5)
> -- *prometheus-framework.txt:11-12*

This approach -- fine-tuning a judge model on labeled rubric feedback -- represents an alternative to pure in-context rubric specification.

---

## Noise and Variance

### Subjectivity as an Irreducible Source of Variance

CaseReportBench provides empirical evidence that token-level scores do not always correspond to task utility:

> high token-level accuracy does not always translate to clinically actionable outputs
> -- *casereportbench.txt:28*

TSR was specifically chosen to handle this:

> Handles "variability in extracted spans caused by subjective clinical classifications"
> -- *casereportbench.txt:21*

### Formal Judge Parameter Estimation

The noisy hypothesis testing framework models judge quality through confusion matrix parameters estimated on human-labeled calibration data:

> True Positive Rate (TPR): probability judge flags response as unreliable when it is unreliable
> - False Positive Rate (FPR): probability judge incorrectly flags reliable response
> - Computed as simple proportions from confusion matrices on human-labeled data
> -- *noisy-hypothesis-testing.txt:7-9*

### Variance-Corrected Critical Threshold

Once TPR and FPR are estimated, the variance-corrected threshold formally accounts for all three sources of estimation uncertainty:

> Variance-Corrected Critical Threshold (Equation 6):
> c'_J = alpha' + phi^(-1)(zeta) x sqrt[variance terms]
> Combines: variance from judge-labeled data (nJ samples), variance from TPR estimate, variance from FPR estimate
> -- *noisy-hypothesis-testing.txt:11-13*

### Formal Type-I Error Bounds

The framework provides a closed-form bound on Type-I error that reveals how error scales with dataset sizes:

> Type-I error Pe(I) <= zeta + O(nJ^(-1/2) + nM1^(-1/2) + nM0^(-1/2))
> -- *noisy-hypothesis-testing.txt:16*

Here nJ is the judge-labeled test set size, nM1 and nM0 are positive and negative calibration set sizes respectively. Error decreases as the square root of each set's size.

### Ensemble and Multi-Source Variance Reduction

Beyond formal statistical methods, practical variance reduction strategies include:

> Variance Reduction:
> - List-wise comparisons using advanced ranking algorithms
> - Best-of-N Evaluation for test-time scenarios
> - Integrating Multi-Source Evaluation Results
> -- *llm-judge-survey.txt:20-23*

---

## Bias Mitigation

### Position Bias

> Position Bias: shuffle contents, reorder response pairs, randomize positions
> -- *llm-judge-survey.txt:16*

This is standard practice for pairwise evaluation prompts where response order can influence the judge.

### Length and Verbosity Bias

> Length/Verbosity Bias: prompt design emphasizing criteria over surface features
> -- *llm-judge-survey.txt:17*

Explicit rubric criteria are the primary countermeasure here, linking bias mitigation directly back to rubric design quality.

### Self-Enhancement Bias

> Self-Enhancement Bias: relative (pairwise) rather than absolute evaluation
> -- *llm-judge-survey.txt:18*

Models tend to favor outputs similar to their own generation style. Pairwise (rather than absolute) evaluation reduces this effect.

### Inherent LLM Randomness as a Bias Source

> Inter-rater reliability affected by inherent LLM generation randomness
> -- *llm-judge-survey.txt:13*

This is the source that motivates the sampling-plus-aggregation approach described in Scoring Metrics. The three biases above are structural; LLM randomness is stochastic. Both require distinct mitigations.

---

## Datasets and Benchmarks

### CaseReportBench: Dense Clinical Extraction

CaseReportBench targets a high-difficulty information extraction scenario -- clinical case reports:

> Final dataset: 138 case reports, 14 clinical categories
> -- *casereportbench.txt:9*

Annotation methodology used dual expert annotators with iterative reconciliation:

> Two rare disease specialists independently extracted using Prodigy annotation tool
> - Detailed annotation guidelines collaboratively designed
> - Iterative review + discussions to resolve discrepancies
> -- *casereportbench.txt:5-7*

Despite this rigorous process, 422 instances still required clarification:

> 422 problematic instances identified requiring clarification
> -- *casereportbench.txt:8*

### KILT and FEVER: Knowledge-Intensive Fact-Checking

KILT and FEVER are established benchmarks (KILT published 2020, FEVER earlier). They are included here as reference examples of benchmark design patterns, not as novel contributions.

> Benchmark for knowledge-intensive tasks grounded in single Wikipedia snapshot
> - Tasks: open-domain QA, fact checking, slot filling, entity linking
> -- *kilt-fever-benchmarks.txt:4-6*

FEVER within KILT provides large-scale structured fact-checking data:

> 185,441 claims generated by altering Wikipedia sentences
> - Classified as Supported, Refuted, or NotEnoughInfo
> - Annotators recorded sentence(s) forming necessary evidence
> -- *kilt-fever-benchmarks.txt:10-12*

KILT's structured data format is notable for its complete provenance specification:

> Data Format:
> - id, input (question/claim), output with answers and provenance
> - Provenance: Wikipedia IDs, titles, sections, paragraph positions, character offsets
> - Structured ground truth with exact source attribution
> -- *kilt-fever-benchmarks.txt:15-18*

---

## Partial Matching

### Token Set Ratio (TSR)

> Token Set Ratio (TSR%): measures token selection correctness (0-100), uses FuzzyWuzzy
> - TSR captures token-level overlap rather than demanding exact matches
> - Computes intersection and differences between token sets
> -- *casereportbench.txt:12,19-20*

TSR is implemented via the FuzzyWuzzy Python library and operates by computing token intersection/difference. The behavior described (set intersection and differences) is consistent with the `token_set_ratio` function, though the source does not explicitly name which FuzzyWuzzy ratio function is used. TSR tolerates reordering and minor additions, making it suitable for free-text extraction where exact match is too strict.

### Levenshtein Similarity

> Levenshtein Similarity: character-level edit distance (0-100)
> -- *casereportbench.txt:13*

Character-level edit distance complements token-level TSR by capturing situations where token boundaries differ but characters overlap significantly (e.g., plural vs. singular, abbreviated vs. expanded terms).

### Relationship Between Partial Matching and Subjectivity

The motivation for partial matching metrics is directly tied to the subjectivity findings: when ground truth annotations themselves have inter-annotator TSR as low as 42.5%, exact match scoring would be misleading. Partial matching calibrates scoring to the actual precision of the ground truth.

---

## LLM-as-Judge

### Prometheus Performance Benchmarks

> Pearson correlation 0.897 with human evaluators (45 customized rubrics)
> - On par with GPT-4 (0.882), far exceeds ChatGPT (0.392)
> -- *prometheus-framework.txt:16-17*

These figures are for Prometheus v1 (13B parameters, ICLR 2024). The 0.897 is the model's Pearson correlation with human evaluators. The 0.882 is GPT-4's correlation with the same human evaluators, provided for comparison. Prometheus v2 (8x7B MoE, May 2024) reports 0.6-0.7 correlation with GPT-4-1106 as the reference target -- a different evaluation protocol that is not directly comparable to the v1 human-correlation figure.

### Model Variants

> 13B parameter model (v1), 7B and 8x7B (v2, May 2024)
> -- *prometheus-framework.txt:13*

### Framework Comparison: Prometheus vs. G-Eval

Both frameworks use rubric-based scoring but differ fundamentally in rubric source:

> G-Eval: framework using GPT-3.5/4, generates rubric via CoT
> - Prometheus: fine-tuned LLM, rubric provided in prompt
> - Both emphasize rubric-based scoring
> -- *prometheus-framework.txt:21-23*

G-Eval generates rubrics dynamically from the evaluation prompt via chain-of-thought; Prometheus consumes user-provided rubrics. This creates a tradeoff between flexibility (G-Eval) and consistency/controllability (Prometheus).

### Input Requirements for Prometheus

> Users must provide: instruction, response, reference answer, score rubrics
> -- *prometheus-framework.txt:26*

The requirement for a reference answer aligns with the empirical finding that reference answers matter more than intermediate rubric level descriptions.

### Decoding Strategy for Judge Reliability

> Greedy decoding: zero score variance but poor human correlation (0.593-0.635)
> - Sampling-based: higher variance but better human alignment (0.641-0.666)
> -- *llm-judge-design-choices.txt:7-8*

Five sampling runs are the recommended minimum:

> 5 runs provides adequate sampling for reliable mean
> -- *llm-judge-design-choices.txt:25*

This is a practical recommendation from the study without an accompanying statistical power analysis. "Adequate" is not defined relative to a specific correlation target or variance threshold, so teams with stringent requirements may need more runs.

---

## Inter-Rater Reliability

### LLM Judge Consistency: Krippendorff's Alpha

> Consistency (Krippendorff's alpha across 5 runs):
> - With criteria + reference: alpha = 0.908
> - Without both: alpha = 0.896
> - Removing criteria causes noticeable drop
> -- *llm-judge-design-choices.txt:18-21*

This finding is confirmed by both scouts from the same source (high confidence). The source characterizes the drop from 0.908 to 0.896 (delta = 0.012) as "noticeable," though the absolute difference is small. The source does not provide statistical significance testing for this difference, so whether the delta is statistically meaningful beyond the source's characterization cannot be confirmed.

### Human Annotator Agreement in Clinical Extraction

CaseReportBench reveals extreme variability in human inter-rater agreement across clinical categories:

> Ranges from 42.5% to 98.5% TSR by category
> - Pairwise F1 scores: 0.0 to 0.57 across 14 categories
> - Low agreement in complex categories (History: 42.5%, Lab_Image: 54.9%)
> -- *casereportbench.txt:24-26*

F1 scores ranging from 0.0 to 0.57 indicate that for some clinical categories, even expert annotators achieve near-random agreement. This sets a practical ceiling on what any automated evaluation can be expected to achieve in those categories.

### Pairwise vs. Score-Based Evaluation Consistency

> Primary: alignment between LLM evaluations and human annotations
> - Pairwise comparisons have superior positional consistency vs score-based
> -- *llm-judge-survey.txt:11-12*

Pairwise (preference) evaluation is more consistent than absolute score-based evaluation, supporting the self-enhancement bias mitigation finding above.

---

## Calibration

### Two-Stage Calibration Procedure

> Two-stage procedure: 1) Judge calibration on small human-labeled set, 2) Variance-corrected testing on large judge-labeled set
> -- *noisy-hypothesis-testing.txt:22*

Stage 1 uses human labels to estimate TPR/FPR; Stage 2 uses the calibrated judge on a larger dataset with variance correction applied. This allows statistical rigor while minimizing expensive human annotation.

### Condition for Judge Adoption Over Direct Human Evaluation

The noisy hypothesis testing framework provides a formal condition for when using an LLM judge is statistically preferable to direct human evaluation:

> Noisy HT outperforms direct human evaluation only when:
> (TPR - FPR)^2 > [alpha^2 * TPR(1-TPR)/RM + (1-alpha)^2 * FPR(1-FPR)/(1-RM)] / [RM(1-RM)]
> -- *noisy-hypothesis-testing.txt:19-20*

This is a practical go/no-go criterion for LLM judge adoption. Teams should compute this inequality before committing to a judge-based evaluation pipeline.

### Sampling and Aggregation Recommendations

> Sampling-based decoding with mean aggregation over greedy
> -- *llm-judge-design-choices.txt:24*

> 5 runs provides adequate sampling for reliable mean
> -- *llm-judge-design-choices.txt:25*

These two findings together form the minimum viable calibration recipe: use sampling-based decoding, aggregate by mean, and use at least 5 runs.

---

## Cross-References

| Source A | Source B | Relationship | Notes |
|-|-|-|-|
| llm-judge-design-choices.txt | llm-judge-survey.txt | extends | Design choices study provides empirical data supporting survey-level recommendations |
| prometheus-framework.txt | llm-judge-survey.txt | documents | Prometheus is a case study instantiating the surveyed rubric-based evaluation paradigm |
| noisy-hypothesis-testing.txt | llm-judge-design-choices.txt | documents | Hypothesis testing framework formalizes variance handling discussed empirically in design choices |
| prometheus-framework.txt | llm-judge-design-choices.txt | documents | Prometheus five-point rubric is the evaluated format in the design choices study |
| casereportbench.txt | llm-judge-design-choices.txt | documents | CaseReportBench's TSR handles span variability analogous to LLM judge variance addressed in design choices |
| kilt-fever-benchmarks.txt | casereportbench.txt | documents | Both establish ground-truth annotation pipelines; KILT uses provenance, CaseReportBench uses clinical guidelines |

---

## Gaps and Open Questions

The following gaps were identified across both scouts (deduplicated):

1. **Acceptable noise thresholds**: No specific epsilon thresholds or practical bounds are provided for acceptable LLM judge noise levels. The formal error bound `Pe(I) <= zeta + O(nJ^(-1/2) + ...)` exists but the sources do not recommend concrete zeta values for typical benchmarking scenarios.

2. **Calibration set sizing guidance**: Beyond the general sample-size scaling law (`O(n^(-1/2))`), no practical guidance is provided on how large the human-labeled calibration set (nM1, nM0) should be for a given target precision.

3. **Extraction task type coverage**: No analysis of how different extraction task types (entity extraction, relation extraction, event detection, hierarchical schema extraction) affect the choice of scoring metric or rubric design. All sources treat IE as largely homogeneous.

4. **Subjective and ambiguous ground truth**: No guidance on handling extraction scenarios where ground truth is genuinely ambiguous (beyond the general observation that inter-rater agreement can be low). CaseReportBench acknowledges the problem but does not prescribe a solution.

5. **Rubric-based vs. similarity-based comparison**: No direct comparison of rubric-based LLM judge scoring against purely similarity-based alternatives (BERTScore, semantic cosine similarity, etc.).

6. **Multi-answer scenarios**: No coverage of how to score extraction tasks where multiple valid answers exist, or where the number of correct spans is variable per instance.

7. **Domain generalization**: CaseReportBench covers clinical extraction; KILT/FEVER covers Wikipedia fact-checking. No guidance on domain-specific scoring adjustments for other domains (financial, biomedical NER, legal text).

---

## Additional Notes

The following medium-relevance findings do not fit the primary sections but are preserved for completeness.

- **Prometheus v2 correlation range**: Prometheus 2 (8x7B) achieves 0.6-0.7 correlation with GPT-4-1106 (*prometheus-framework.txt:18*), substantially below the 0.897 headline figure. This difference is explained by two factors: (a) v2 8x7B is a different architecture from v1 13B, and (b) the comparison target differs -- v1's 0.897 measures correlation with human evaluators, while v2's 0.6-0.7 measures correlation with GPT-4-1106 as the reference. These represent different evaluation protocols and should not be directly compared.

- **Prometheus model variants**: v1 is a 13B parameter model; v2 offers 7B and 8x7B (mixture of experts) variants. The 8x7B variant offers improved flexibility at higher computational cost (*prometheus-framework.txt:13*).

- **G-Eval framework**: Uses GPT-3.5 or GPT-4 to dynamically generate rubric criteria via chain-of-thought before scoring. This provides flexibility when pre-defined rubrics are unavailable but introduces rubric consistency variance (*prometheus-framework.txt:21-23*).

- **Prometheus input interface**: Requires instruction, response, reference answer, and score rubrics as separate inputs. The reference answer field is a mandatory component, not optional (*prometheus-framework.txt:26*).

- **LLM randomness as inter-rater factor**: LLM generation randomness is a distinct source of inter-rater disagreement from systematic bias. It is reduced by sampling aggregation but not eliminated (*llm-judge-survey.txt:13*).

- **Prometheus training data**: The Feedback Collection dataset (kaist-ai on HuggingFace) is the training source for Prometheus's judge behavior. This dataset shapes what rubric formats and feedback styles the model has internalized (*prometheus-framework.txt:11-12*).

- **KILT/FEVER as established benchmarks**: KILT was published in 2020 (arxiv 2009.02252) and FEVER predates it. The scouts labeled these with claim_era "2025-2026" reflecting the cache document date, not the original publication date. All KILT/FEVER findings in this report represent established benchmark methodology, not novel contributions.

---

<!-- AUDIT LOG
Auditor: Opus
Scout JSONs verified: 2
Original sources spot-checked: 6 (all cached sources read and verified against scout excerpts)
Issues found and fixed:
- Prometheus version reconciliation: Clarified that 0.897 is v1 (13B) correlation with human evaluators and 0.6-0.7 is v2 (8x7B) correlation with GPT-4-1106 (different comparison target). Removed TEMPORAL TODO markers and replaced with inline explanatory text.
- Krippendorff alpha: Removed claim that the 0.012 delta is "statistically meaningful" -- source does not provide significance testing. Replaced with note that the source characterizes the drop as "noticeable" but the absolute difference is small and significance is unconfirmed.
- "Direct scoring beats CoT" condition: Confirmed that "when criteria are well-defined" IS explicitly stated in the source (llm-judge-design-choices.txt:27). Low-confidence flag resolved; the condition is source-stated, not analyst inference.
- Intermediate rubric level impact: Added caveat that this finding comes from a single study and task-type generalizability is uncertain.
- "5 runs adequate sampling": Added clarification that this is a practical recommendation without statistical power analysis and that "adequate" is not defined against a specific threshold.
- TSR FuzzyWuzzy function: Added note that the description is consistent with token_set_ratio but the source does not explicitly name the function.
- KILT/FEVER claim_era: Added note in Datasets section and Additional Notes that these are established benchmarks (2020 and earlier), not 2025 contributions. Scout claim_era labels reflect cache dates.
- Removed all TODO and TEMPORAL HTML comment markers (3 total).
Unresolved items:
- None. All review notes items resolved with source verification.
Verdict: PASS
-->
