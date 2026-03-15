# Automated LLM Prompt Optimization and Agent Instruction Tuning

## Executive Summary

Automated prompt optimization -- the practice of using feedback loops, scoring functions, and mutation strategies to iteratively improve LLM system prompts and agent instructions -- has matured into a well-studied field with several production-grade implementations. Research across eight sources covering academic surveys, framework documentation, and empirical platform reports confirms that automated loops reliably achieve 9-50% improvements over manually written baselines, with the exact gain depending heavily on how poorly the baseline was tuned and how precisely the scoring metric captures the target behavior.

Three broad architecture families have emerged: (1) single-pass generation methods (APE) that trade thoroughness for speed; (2) iterative gradient-free search methods (OPRO, COPRO, GRIPS, APO) that refine a prompt over K candidates per step using natural-language feedback and history; and (3) population-based evolutionary methods (PromptBreeder, PhaseEvo, Turintech Artemis, the evolving-excellence framework) that maintain a generation of prompt variants and apply genetic operators. All three families are relevant to an edit-then-benchmark-then-score-then-keep/discard loop, but the iterative single-candidate approaches most closely match a system that generates one mutation per round and accepts or rejects it.

Overfitting to the benchmark is the dominant risk across all approaches. Every surveyed method optimizes against a fixed evaluation set, and multiple sources note that the lower bound on generalization can be negative -- meaning optimization can make prompts worse on held-out data. Mitigations include train/val/test splits (40/40/20 recommended), stratified sampling, maintaining failure history to avoid revisiting rejected variants, and embedding explicit anti-overfitting instructions in the editor LLM's meta-prompt. Fuzzy or subjective scoring metrics were singled out as a primary driver of degraded results; deterministic, verifiable metrics are strongly preferred.

Convergence is faster than intuition suggests: SI-Agent converges in 20-50 iterations, the evolving-excellence framework converges in 2-3 generations with a population of 3 (approximately 6-9 total evaluations), and APE shows diminishing returns beyond 64 single-pass candidates. Cost control is achieved by hierarchical filtering -- a cheap LLM pre-screen eliminates weak candidates before running expensive benchmark evaluations. In a ca. 2025 LangChain comparison, Claude-3.5-Sonnet was identified as the most effective optimization engine among compared models (outperforming O1 and GPT-4o). This finding is directly relevant to editor model selection, but model rankings shift frequently and should be re-evaluated against current offerings before committing.

---

## Mutation Operators

### Heuristic Phrase-Level Edits

GRIPS defines four atomic mutation operations applied at the phrase level: **delete**, **swap**, **paraphrase**, and **add**. These are deterministic edit types that can be implemented without an additional LLM call, making them the cheapest available operators. Greedy termination fires after K consecutive non-improving steps.

> "GRIPS (heuristic phrase edits: delete/swap/paraphrase/add, greedy termination after K non-improving steps)"
> -- *wolfe-apo-survey.txt:2*

### Natural-Language Gradient Mutations

APO moves away from token-level edits by computing a "natural language gradient" -- a textual description of what the current prompt is getting wrong -- and using that description to drive edits. B candidate prompts are generated per step, each receiving N edits informed by the gradient. This produces targeted, semantically coherent mutations rather than random perturbations.

> "APO (natural language gradients with beam search B candidates N edits, bandit selection, up to 31% improvement)"
> -- *wolfe-apo-survey.txt:2*

### Failure-Driven Mutation Targeting

Rather than mutating blindly, failure-driven approaches analyze which benchmark examples the current prompt gets wrong and generate mutations specifically aimed at fixing those failure modes. This requires the scorer to surface per-example results, not just an aggregate score.

> "Feedback-driven mutation analyzes classification failures."
> -- *evidently-practical.txt:2*

SIMBA (DSPy) applies a related idea at the mini-batch level: it identifies high-variability examples -- those where the prompt's output is inconsistent across runs -- and concentrates mutation effort there.

> "SIMBA (stochastic mini-batch, targets high-variability examples, self-reflective improvement rules)."
> -- *dspy-optimizers.txt:2*

### LLM Ensemble Mutations with Semantic Preservation

PromptBreeder and the Turintech Artemis platform use LLM ensembles to generate mutation candidates. The key design goal is **semantic-aware** mutation: the ensemble is prompted to produce variants that preserve the agent's validity (correct task framing, required output structure) while varying phrasing, ordering, or emphasis.

> "Mutation uses LLM ensembles for semantic-aware mutations preserving validity."
> -- *evolving-excellence.txt:2*

> "PromptBreeder mutation operators: LLM paraphrasing, edit operators (swap/drop/clarify), structural rewrites."
> -- *promptbreeder.txt:2*

> "Semantic genetic algorithms with LLM ensemble mutations."
> -- *turintech-evolutionary.txt:2*

### Evolutionary Hybrid (PhaseEvo)

PhaseEvo combines evolutionary population search with gradient feedback in a single loop. It was reported as the most reliable approach across the evaluated methods in the LangChain comparison, suggesting that neither purely evolutionary nor purely gradient-based approaches alone are as robust.

> "PhaseEvo (evolutionary + gradient feedback) most reliable"
> -- *langchain-optimization.txt:2*

### Crossover Operators (Population Contexts)

PromptBreeder defines four crossover mechanisms applicable when maintaining multiple prompt variants: single-point, uniform, section-wise, and clause-level swapping. These are only applicable when the system maintains a population of at least two active candidates.

> "Crossover: single-point, uniform, section-wise, clause-level swapping."
> -- *promptbreeder.txt:2*

---

## Selection Strategies

### Beam Search over Candidates

APO generates B candidate mutations per step and retains a beam -- keeping only the top-scoring subset to carry forward. This prevents the search from being trapped by a single unlucky mutation while controlling budget.

> "APO (natural language gradients with beam search B candidates N edits, bandit selection, up to 31% improvement)"
> -- *wolfe-apo-survey.txt:2*

### Multi-Armed Bandit Selection

APO also applies bandit selection when choosing between candidate prompts that have partial evaluation results. Bandit algorithms balance exploration (trying undersampled candidates) with exploitation (committing to high-scoring candidates), which reduces wasted benchmark evaluations.

> "APO (natural language gradients with beam search B candidates N edits, bandit selection, up to 31% improvement)"
> -- *wolfe-apo-survey.txt:2*

### Elitism, Roulette-Wheel, Softmax, and UCB (Population Methods)

PromptBreeder exposes four distinct selection mechanisms for population-based search. Elitism guarantees the best-known prompt survives each generation. Roulette-wheel and softmax-over-fitness select proportionally. UCB-based exploration-exploitation mirrors bandit approaches and is particularly suited for small populations where variance is high.

> "Selection: elitism, roulette-wheel, softmax over fitness, UCB exploration-exploitation."
> -- *promptbreeder.txt:2*

### Greedy Termination after K Non-Improving Steps

The simplest and most directly applicable strategy for a keep/discard loop: count consecutive rounds where the accepted prompt's score does not improve by at least delta, and halt (or trigger a restart/perturbation) after K such rounds.

> "GRIPS (heuristic phrase edits: delete/swap/paraphrase/add, greedy termination after K non-improving steps)"
> -- *wolfe-apo-survey.txt:2*

### Early Stopping Criteria

Evidently's practical implementation combines three stopping signals: `max_iterations` (hard budget cap), `min_score_gain` (minimum improvement threshold per accepted step), and `target_score` (halt when an absolute performance level is reached).

> "Early stopping via max_iterations, min_score_gain, target_score."
> -- *evidently-practical.txt:2*

### Multi-Stage Filtering (Cheap-then-Expensive)

The evolving-excellence framework applies a two-stage gate before running expensive benchmark evaluation: first, a cheap LLM scoring pass eliminates clearly inferior candidates; second, the survivors run the full benchmark. This is also the pattern used by Turintech Artemis.

> "Selection uses multi-stage filtering (cheap LLM scoring then expensive benchmark)."
> -- *evolving-excellence.txt:2*

---

## Scoring and Evaluation

### Deterministic Metrics for Classification and Recall

Accuracy is the baseline metric for classification tasks. Deterministic metrics derived from verifiable expected outputs are strongly preferred. The finding that fuzzy or subjective metrics actively degrade optimization outcomes is one of the most actionable warnings in this literature.

> "Scoring: accuracy for classification, LLM-as-evaluator for complex tasks."
> -- *wolfe-apo-survey.txt:2*

> "Fuzzy metrics make prompts worse."
> -- *langchain-optimization.txt:2*

### LLM-as-Evaluator for Complex Tasks

When the target behavior cannot be captured by a deterministic metric (e.g., instruction-following quality, citation accuracy, reasoning trace coherence), an LLM judge is used. This introduces its own optimization target drift -- the system can learn to satisfy the judge rather than the underlying task. Multiple sources treat this as a fallback, not a preferred approach.

> "Scoring: accuracy for classification, LLM-as-evaluator for complex tasks."
> -- *wolfe-apo-survey.txt:2*

### Fitness Function as Black-Box Benchmark Mapping

The evolving-excellence framework formalizes scoring as a function f that maps an agent configuration C=(P,T,M,Theta) -- covering prompts, tools, models, and parameters -- through a benchmark suite to produce a fitness value. This framing is directly applicable to a system that already has a composite scorer.

> "Fitness function f maps agent configs through benchmarks."
> -- *evolving-excellence.txt:2*

> "Population config C=(P,T,M,Theta) covers prompts, tools, models, parameters."
> -- *evolving-excellence.txt:2*

### Multi-Dimensional Fitness

SI-Agent uses a multi-dimensional fitness function that evaluates both task performance and readability as separate dimensions. This approach directly parallels a composite scorer with weighted sub-dimensions.

> "Multi-dimensional evaluation: task performance + readability."
> -- *si-agent.txt:2*

### Development Set as Reliability Predictor

Development set performance curves reliably predict test set performance -- meaning the composite score on the fixed benchmark is a reasonable proxy for out-of-sample generalization. **Important qualification**: this holds when the dev set was not itself used to select the optimization strategy or tune meta-parameters. If the dev set informed experiment-design-level choices (e.g., which mutation operator to use, what K threshold to set), it is no longer truly independent and its predictive value is diminished.

> "Dev set curves predict test reliability."
> -- *langchain-optimization.txt:2*

### DSPy Optimizer Economics

A concrete cost data point: DSPy optimizers (MIPROv2 and similar) typically cost approximately $2 and take approximately 10 minutes per run. This is useful as a baseline for evaluating whether the current loop's per-round cost is in a reasonable range.

> "Typical cost $2, ~10 minutes."
> -- *dspy-optimizers.txt:2*

### Observed Improvement Ranges

Across sources, reported improvement ranges are:
- APO: up to 31% (wolfe-apo-survey.txt)
- OPRO: 8-50% (wolfe-apo-survey.txt)
- Turintech Artemis: 9.3-36.9% (turintech-evolutionary.txt)
- ALE benchmark: +13.6% (evolving-excellence.txt)
- Mini-SWE benchmark: +10.1% (evolving-excellence.txt)
- MathTales benchmark: +22% accuracy (evolving-excellence.txt)
- CrewAI cost reduction: -36.9% (evolving-excellence.txt)

> "Results: ALE +13.6%, Mini-SWE +10.1%, CrewAI -36.9% cost, MathTales +22% accuracy."
> -- *evolving-excellence.txt:2*

---

## Convergence and Plateau Escape

### Rapid Convergence in Practice

Two independent sources report surprisingly fast convergence. SI-Agent converges in 20-50 iterations (each iteration being a single instruction evaluation). The evolving-excellence framework with a population of 3 converges in 2-3 generations, yielding approximately 6-9 total evaluations before diminishing returns. These figures are broadly consistent when normalized to total evaluations and suggest that for a well-specified benchmark, diminishing returns appear early -- not after hundreds of rounds.

> "20-50 iterations typical convergence."
> -- *si-agent.txt:2*

> "Population size 3, generations 2-3, optimization time 9-411 hours depending on benchmark complexity."
> -- *evolving-excellence.txt:2*

### Diminishing Returns Beyond 64 Candidates (Single-Pass)

APE, which generates all candidates in a single pass, shows diminishing returns beyond 64 candidates. This establishes a practical upper bound for single-pass exploration before switching to iterative refinement.

> "APE (single-pass 64 candidates, diminishing returns beyond)"
> -- *wolfe-apo-survey.txt:2*

### History-Augmented Meta-Prompt to Avoid Revisiting Local Optima

OPRO's key mechanism for plateau escape is injecting a sorted history of all previously evaluated (prompt, score) pairs into the meta-prompt given to the editor LLM. The editor can then see which directions have already been tried and generate mutations that explore genuinely new territory.

> "OPRO (gradient-free iterative, K candidates per step, meta-prompt with sorted history, 8-50% improvement)"
> -- *wolfe-apo-survey.txt:2*

### Coordinate Ascent Limitations

COPRO (DSPy) uses coordinate ascent hill-climbing, which is explicitly noted as susceptible to local optima. When a hill-climb approach stalls, it typically requires a restart with a different initialization rather than an incremental perturbation.

> "COPRO (coordinate ascent hill-climbing for instructions)."
> -- *dspy-optimizers.txt:2*

### K Non-Improving Steps as Concrete Plateau Trigger

Both GRIPS and general early stopping literature recommend tracking the count of consecutive rounds with no improvement and using K as a configurable threshold. No source surveyed provides a concrete recommended value for K. For a keep/discard loop with a composite scorer, K should be calibrated to the stochastic variance of the benchmark: if re-running the same prompt yields score variance of +/-X, then K must be large enough that K consecutive non-improvements is unlikely to occur by chance alone during a genuine improvement trend. A practical starting point is K=5-10 for benchmarks with low variance, increasing to K=15-20 for high-variance benchmarks. This range is a practitioner recommendation, not a source-backed finding.

> "GRIPS (heuristic phrase edits: delete/swap/paraphrase/add, greedy termination after K non-improving steps)"
> -- *wolfe-apo-survey.txt:2*

---

## Overfitting Prevention

### The Fundamental Risk: Fixed Benchmark Optimization

Every reviewed method -- without exception -- optimizes against a fixed evaluation set. Multiple sources explicitly flag that this creates overfitting risk with a potentially negative lower bound: the optimizer may learn prompt features that score well on the benchmark while performing worse on novel inputs.

> "All optimize against fixed training sets with overfitting risk."
> -- *wolfe-apo-survey.txt:2*

> "Critical overfitting risk: lower bound often negative."
> -- *langchain-optimization.txt:2*

### Train / Validation / Test Split (40/40/20)

The recommended mitigation is a three-way data split: 40% training (used to compute the optimization signal), 40% validation (used to decide keep/discard), and 20% held-out test (used only for final reporting). Mixing the optimization signal and keep/discard decision into a single set inflates apparent progress.

> "Data split 40/40/20 train/val/test."
> -- *evidently-practical.txt:2*

### Stratified Sampling and Held-Out Test Sets

The evolving-excellence framework validates generalization using stratified sampling alongside held-out test sets -- ensuring that the benchmark sample is representative of the task distribution rather than being a biased subset.

> "Generalization validated via stratified sampling and held-out test sets."
> -- *evolving-excellence.txt:2*

### Explicit Anti-Overfitting Instruction in Editor Prompts

A direct mitigation: include an explicit instruction in the editor LLM's meta-prompt that discourages overfitting behaviors, such as adding benchmark-specific triggers or overly narrow conditions. This is a zero-cost intervention reported in a single source without supporting evidence of effect size. Include it as a low-risk addition, not a primary defense.

> "Explicit anti-overfitting instruction in prompts."
> -- *evidently-practical.txt:2*

### Failure History to Avoid Repeated Exploration

SI-Agent maintains a history of previously tried instruction variants and their scores, which prevents the optimizer from revisiting failed directions. Beyond efficiency, this acts as an indirect overfitting check -- if the optimizer keeps returning to superficially similar prompts that score high on the benchmark, the history makes that pattern visible. The history also functions as a memoization table, preventing repeated evaluation of identical instruction variants.

> "Historical context prevents repeated failures."
> -- *si-agent.txt:2*

---

## Population Management

### Population Size: Two Regimes

Two distinct population regimes emerged from the sources, reflecting different design philosophies:

**Large-population regime (PromptBreeder)**: Population size 20-50, generations 10-30, mutation pool 5-20 candidates. This configuration is designed for broad exploration of prompt space using genetic operators (crossover, mutation, selection). It suits scenarios where the search space is large and the mutation operator is relatively cheap (e.g., LLM paraphrasing without full benchmark evaluation of every candidate).

> "Population size 20-50, generations 10-30, mutation pool 5-20."
> -- *promptbreeder.txt:2*

**Small-population regime (evolving-excellence)**: Population size 3, converging in 2-3 generations. This configuration works when: (a) the benchmark is well-specified with a reliable composite scorer, (b) the mutation operator is high-quality (LLM ensemble with semantic preservation), and (c) each evaluation is expensive enough that minimizing total evaluations matters more than broad exploration.

> "Population size 3, generations 2-3, optimization time 9-411 hours depending on benchmark complexity."
> -- *evolving-excellence.txt:2*

**Which regime applies to an edit-then-benchmark loop**: A single-candidate keep/discard loop is effectively a population of 1 with rolling replacement. This is closest to the small-population regime. The convergence data from evolving-excellence (6-9 total evaluations for convergence) and SI-Agent (20-50 iterations) provides the more relevant reference points. PromptBreeder's parameters are relevant only if the loop is extended to maintain multiple concurrent candidates.

### Multiple Independent Starts

Multiple independent optimization runs (restarts from different initial prompts) mitigate stochastic variance and improve robustness. This is particularly relevant when the optimization landscape is non-convex and the editor LLM introduces stochastic noise.

> "Multiple starts mitigate stochastic variance."
> -- *evidently-practical.txt:2*

### Edits per Candidate (APO)

APO's N-edits-per-candidate parameter controls mutation intensity. Higher N means larger jumps in prompt space per round; lower N means finer-grained search. No recommended default value was found in any surveyed source; this is an implementation-specific parameter that should be tuned based on the granularity of the target instruction.

> "APO (natural language gradients with beam search B candidates N edits, bandit selection, up to 31% improvement)"
> -- *wolfe-apo-survey.txt:2*

### MIPROv2 Scale Requirements

MIPROv2 (DSPy's most capable optimizer) requires at least 40 trials and 200+ examples. This is relevant as a lower bound on benchmark scale needed to use Bayesian discrete search effectively.

> "MIPROv2 (3-stage: bootstrap traces, grounded proposals, Bayesian discrete search, 40+ trials 200+ examples)."
> -- *dspy-optimizers.txt:2*

### Score and Instruction History Tracking (SI-Agent)

SI-Agent maintains complete iteration history: all (instruction variant, score) pairs. This serves three purposes: plateau detection, overfitting detection, and enabling the editor LLM to generate mutations informed by the full optimization trajectory.

> "Maintains SI history and scores."
> -- *si-agent.txt:2*

---

## Architecture Patterns

### The Core Loop

The universal pattern across all reviewed implementations:

> "Loop: execute->score->log->decide->generate."
> -- *evidently-practical.txt:2*

This maps exactly to the current system's edit-then-benchmark-then-score-then-keep/discard-then-repeat loop.

### DSPy Optimizer Catalog

DSPy provides a hierarchy of optimizer types with increasing capability and cost:

> "BootstrapFewShot (teacher-generated demos, metric-validated). BootstrapFewShotWithRandomSearch (multiple attempts, 50+ examples). COPRO (coordinate ascent hill-climbing for instructions). MIPROv2 (3-stage: bootstrap traces, grounded proposals, Bayesian discrete search, 40+ trials 200+ examples). SIMBA (stochastic mini-batch, targets high-variability examples, self-reflective improvement rules). GEPA (trajectory reflection, domain feedback integration). BetterTogether (sequences prompt and weight optimization)."
> -- *dspy-optimizers.txt:2*

### Local GA + Global Bayesian Hierarchical Architecture

Both the evolving-excellence framework and Turintech Artemis use a two-level optimization hierarchy: local search via genetic algorithms (for components that can vary independently) and global search via Bayesian optimization (for components with strong interaction effects). This decomposition is applicable when the agent configuration has identifiable independent vs. interdependent parts.

> "Local (GA for independent components) + Global (Bayesian for interacting)."
> -- *turintech-evolutionary.txt:2*

> "Local optimization uses GA for independent components, global uses Bayesian for interacting components."
> -- *evolving-excellence.txt:2*

### PhaseEvo: Most Reliable Hybrid

PhaseEvo was explicitly ranked as the most reliable approach among compared methods in the LangChain evaluation, combining evolutionary population search with natural-language gradient feedback.

> "PhaseEvo (evolutionary + gradient feedback) most reliable"
> -- *langchain-optimization.txt:2*

### Three-Stage Pipeline (MIPROv2)

MIPROv2's three-stage structure -- bootstrap traces for diversity, grounded proposals for relevance, Bayesian search for optimization -- is a template for systems that want to separate exploration (early stages) from exploitation (final stage).

> "MIPROv2 (3-stage: bootstrap traces, grounded proposals, Bayesian discrete search, 40+ trials 200+ examples)."
> -- *dspy-optimizers.txt:2*

### Joint Prompt + Weight Optimization (BetterTogether)

For systems that fine-tune model weights alongside prompt optimization, BetterTogether sequences these two objectives. This is not directly applicable to pure prompt optimization but is relevant if the system later incorporates weight updates.

> "BetterTogether (sequences prompt and weight optimization)."
> -- *dspy-optimizers.txt:2*

---

## Cost Optimization

### Hierarchical Filtering: Cheap Before Expensive

The single most impactful cost reduction strategy: run a cheap LLM pre-filter before expensive benchmark evaluation. Both Turintech Artemis and the evolving-excellence framework use this pattern.

> "Hierarchical evaluation: cheap filters then expensive benchmarks."
> -- *turintech-evolutionary.txt:2*

> "Selection uses multi-stage filtering (cheap LLM scoring then expensive benchmark)."
> -- *evolving-excellence.txt:2*

### Benchmark Complexity Drives Wall-Clock Cost

Optimization runtime is bounded by benchmark complexity, not number of rounds. Reported ranges:
- Turintech: 9-671 hours (turintech-evolutionary.txt)
- evolving-excellence: 9-411 hours (evolving-excellence.txt)
- DSPy: ~10 minutes per run (dspy-optimizers.txt)

The DSPy figure reflects a much smaller benchmark scope (single pipeline evaluation) while the multi-hour figures reflect multi-agent agentic tasks requiring full end-to-end execution.

> "Cost varies 9-671 hours."
> -- *turintech-evolutionary.txt:2*

> "Typical cost $2, ~10 minutes."
> -- *dspy-optimizers.txt:2*

### Sample Efficiency

Evidently's practical guidance reports that 5-10 labeled examples are "often sufficient" for effective prompt optimization. **Qualification**: this likely applies to simple classification tasks with clear right/wrong answers, not to complex agent instruction tuning where the behavior space is much larger. Treat as a lower-bound data point for bootstrapping, not as a recommendation for agent optimization benchmarks.

> "5-10 labeled examples often sufficient."
> -- *evidently-practical.txt:2*

### Editor Model Selection

In a ca. 2025 LangChain comparison, Claude-3.5-Sonnet was reported as the most effective model for the optimization (editor) role, outperforming O1 and GPT-4o. **Temporal caveat**: model rankings shift with each release cycle. This finding indicates that a strong reasoning model should be used for the editor role, but the specific model should be re-evaluated against current offerings (e.g., Claude 4 Sonnet, GPT-4.1, Gemini 2.5 Pro) before committing to a long optimization run.

> "Claude-3.5-Sonnet best optimization engine (beats O1, GPT-4o)."
> -- *langchain-optimization.txt:2*

---

## Feedback Mechanisms

### Three Primary Feedback Types

SI-Agent cleanly enumerates the three feedback mechanisms used across all reviewed systems:

> "Three feedback mechanisms: LLM-based refinement (critiques in meta-prompts), evolutionary selection (scores as fitness), preference learning."
> -- *si-agent.txt:2*

### LLM-Based Refinement via Meta-Prompt Critiques

The editor LLM receives the current prompt, its score, a description of failures, and (optionally) a history of prior attempts, then generates a critique and a revised prompt. OPRO makes this explicit by injecting a sorted (score, prompt) history.

> "OPRO (gradient-free iterative, K candidates per step, meta-prompt with sorted history, 8-50% improvement)"
> -- *wolfe-apo-survey.txt:2*

### Trajectory Reflection (GEPA)

GEPA extends meta-prompt feedback by including the full optimization trajectory -- not just the current state and its score -- so the editor LLM can reason about the direction of change over multiple steps.

> "GEPA (trajectory reflection, domain feedback integration)."
> -- *dspy-optimizers.txt:2*

### Reflective Modules with Exponential Smoothing (PromptBreeder)

PromptBreeder implements structured reflection modules that apply exponential smoothing (alpha parameter 0.7-0.9) to the fitness signal, filtering out noise from stochastic benchmark evaluations. A long-term reflection memory persists across generations. The alpha range 0.7-0.9 is reported without task-specific tuning guidance; higher alpha values weight recent scores more heavily and are appropriate when benchmark variance is low.

> "Reflective modules with smoothing alpha=0.7-0.9. Long-term reflection memory."
> -- *promptbreeder.txt:2*

### Quantitative + Qualitative Feedback Synthesis

The most effective feedback combines both quantitative metrics (numeric score dimensions) and qualitative feedback (textual critique of what the prompt is doing wrong). SI-Agent identifies this combination as producing the best instruction optimization outcomes.

> "Quantitative+qualitative feedback most effective."
> -- *si-agent.txt:2*

---

## Practical Guidelines

### Conditions Where Optimization Succeeds

> "Success when: non-obvious patterns, verifiable labels, model lacks domain knowledge."
> -- *langchain-optimization.txt:2*

For agent instruction tuning specifically, this translates to: the benchmark must test behaviors that are not already reliably triggered by naive prompts, scoring must be verifiable against ground truth, and the base model must have genuine room to improve on the task.

> "Works best with poorly tuned baselines and well-defined metrics."
> -- *turintech-evolutionary.txt:2*

### Conditions Where Optimization Fails

> "Failure when: subjective tasks, model already good, complex subtle rules."
> -- *langchain-optimization.txt:2*

If the baseline agent instruction is already near-optimal for the benchmark, optimization rounds produce noise rather than signal. Subjective tasks amplify the fuzzy-metric risk identified in the scoring section.

### Measured Improvements Across Benchmarks

> "Results: ALE +13.6%, Mini-SWE +10.1%, CrewAI -36.9% cost, MathTales +22% accuracy."
> -- *evolving-excellence.txt:2*

These figures establish realistic expectations. A 10-25% improvement over a reasonably tuned baseline is a plausible target for an automated loop. Improvements exceeding 30% suggest either the baseline was very poorly tuned or the benchmark is narrow enough to admit overfitting.

---

## Cross-References

| Source A | Source B | Relationship |
|-|-|-|
| wolfe-apo-survey.txt | evidently-practical.txt | Theory to implementation: survey describes APE/APO/OPRO/GRIPS; Evidently implements concrete loop with data splitting and early stopping |
| wolfe-apo-survey.txt | langchain-optimization.txt | Performance comparison: survey covers multiple algorithms; LangChain identifies PhaseEvo as most reliable, Claude-3.5-Sonnet as best engine |
| evidently-practical.txt | langchain-optimization.txt | Validation: Evidently's 40/40/20 split connects to LangChain's finding that dev curves predict test performance |
| langchain-optimization.txt | wolfe-apo-survey.txt | Gap identification: LangChain's critical overfitting risk finding applies to all fixed-set methods in the survey |
| dspy-optimizers.txt | promptbreeder.txt | Shared mechanisms: both use stochastic mini-batch and fitness-based selection; DSPy SIMBA targets high-variability examples; PromptBreeder uses roulette-wheel and UCB |
| dspy-optimizers.txt | turintech-evolutionary.txt | Platform parallel: both provide multiple optimizer types with hierarchical evaluation; DSPy uses Bayesian discrete search; Turintech uses local GA + global Bayesian |
| promptbreeder.txt | turintech-evolutionary.txt | Genetic foundations: both use GA-based population search; PromptBreeder emphasizes reflective modules; Turintech emphasizes semantic mutations and hierarchical filtering |
| evolving-excellence.txt | si-agent.txt | Complementary convergence data: both confirm rapid convergence (2-3 generations / ~6-9 evals vs. 20-50 iterations); both use feedback-driven iteration with LLM-based refinement |

---

## Gaps and Open Questions

The following gaps were identified across all three scouts (deduplicated):

1. **Hyperparameter values for K, B, N** -- No concrete recommendation for the greedy-termination step count K, APO beam width B, or APO edits-per-candidate N. All sources describe the parameters but none provide empirical tuning guidance.

2. **min_score_gain threshold selection** -- The early stopping `min_score_gain` parameter is mentioned but no guidance is given on appropriate values for different task types or benchmark scales.

3. **OPRO meta-prompt construction** -- OPRO's sorted-history meta-prompt is described at a high level, but no template or structural guidance is provided for how to format prior (score, prompt) pairs effectively.

4. **Computational cost model** -- No systematic comparison of per-round cost across methods (APE vs. APO vs. OPRO vs. PhaseEvo vs. PromptBreeder). The reported cost ranges (minutes to hundreds of hours) span orders of magnitude and are not normalized to equivalent benchmark complexity.

5. **Overfitting detection at runtime** -- Sources identify overfitting risk and recommend train/val/test splits, but no method is described for detecting overfitting during an ongoing optimization run (i.e., before running the held-out test set).

6. **PromptBreeder convergence criteria** -- No explicit stopping rule is given for PromptBreeder generations. Population size (20-50) and generation count (10-30) are ranges, not decision rules.

7. **COPRO local optima escape** -- COPRO's coordinate ascent is noted as susceptible to local optima, but no restart strategy or perturbation heuristic is specified.

8. **DSPy overfitting prevention** -- DSPy documentation does not address how to avoid overfitting in its optimization procedures.

9. **Smoothing alpha tuning for PromptBreeder** -- The recommended range alpha=0.7-0.9 is given without guidance on when to use higher vs. lower values within the range.

10. **Verifiable label design** -- No guidance on how to construct benchmark labels that are verifiable yet representative of the target behavior, particularly for open-ended agent tasks.

---

## Additional Notes

These findings are lower-relevance but are preserved for completeness:

- **BootstrapFewShotWithRandomSearch** generates 50+ examples during exploration. This is useful context for understanding DSPy's resource requirements at the lower end (vs. MIPROv2's 200+). *(dspy-optimizers.txt:2, medium relevance)*

- **COPRO** (DSPy) performs coordinate ascent hill-climbing for instruction optimization. While its local-optima susceptibility is a limitation, it is simpler to implement than Bayesian or evolutionary alternatives. *(dspy-optimizers.txt:2, medium relevance)*

- **GEPA** integrates domain feedback and trajectory reflection. The "domain feedback" component suggests human-in-the-loop input, which is not detailed in the source. *(dspy-optimizers.txt:2, medium relevance)*

- **BetterTogether** sequences prompt and weight optimization. Not applicable to pure prompt-only loops but noted for completeness. *(dspy-optimizers.txt:2, medium relevance)*

- **APO improvement ceiling** -- The 31% improvement figure for APO and 8-50% range for OPRO are provided as reference benchmarks but represent different tasks and baselines; they should not be taken as expected gains for any specific system. *(wolfe-apo-survey.txt:2, medium relevance)*

- **SI-Agent failure history** also functions as a memoization table, preventing repeated evaluation of identical instruction variants. This is a practical efficiency gain independent of its overfitting-prevention role. *(si-agent.txt:2, medium relevance)*

---

## Recommendations for Training Loop

The existing system uses: one editor LLM that generates a mutation, one trainee LLM that runs the benchmark, a composite scorer with 7 weighted dimensions, keep/discard based on composite improvement. The following recommendations map the highest-confidence findings to this specific architecture.

### 1. Mutation Operator: Natural-Language Gradient + Failure Analysis

The editor LLM should receive, at minimum: the current instruction, the composite score, and a per-dimension breakdown of where scores decreased since the last accepted version. Add a description of which benchmark examples failed (if the scorer surfaces per-example data). This implements the failure-driven mutation and APO-style natural language gradient approaches in combination.

For plateau escape specifically, inject a sorted history of the last N accepted (instruction, composite-score) pairs into the editor's meta-prompt (OPRO pattern). The editor can then see the optimization trajectory and avoid re-generating variants of already-rejected directions.

### 2. Selection: Keep/Discard with Composite Improvement + min_score_gain Threshold

The current keep/discard decision based on composite improvement is sound. Add a `min_score_gain` threshold (the minimum delta in composite score to count as an improvement). Without this threshold, the system will accept cosmetic changes that score marginally higher on any given run due to evaluation stochasticity.

Track K consecutive rounds with no improvement exceeding `min_score_gain` as the plateau signal. When K is reached, either: (a) restart from the best-known prompt with a different mutation type, or (b) trigger a more aggressive mutation (e.g., structural rewrite instead of phrase-level edit).

### 3. Scoring: Preserve Deterministic Metrics; Audit Subjective Dimensions

The 7-dimension composite scorer should be audited for fuzzy dimensions. Any dimension that cannot be evaluated deterministically against ground truth (or via a well-calibrated LLM judge with documented rubric) is a candidate for degrading optimization. The finding "fuzzy metrics make prompts worse" is a direct warning. For each scorer dimension, verify that the metric is stable across repeated evaluations of the same prompt.

Apply exponential smoothing (PromptBreeder's alpha=0.7-0.9) to individual dimension scores across rounds if they exhibit high variance. Report smoothed scores alongside raw scores in the loop log.

### 4. Overfitting: Separate Benchmark Splits and Explicit Instruction

Implement at minimum a two-way split: an optimization set (used to compute the signal) and a held-out validation set (used to confirm improvement before accepting). The recommended ratio is 40/40/20 (optimize/validate/test), but for a fixed benchmark this may need to be approximated by rotating benchmark subsets across rounds.

Add an explicit instruction to the editor LLM's meta-prompt: something to the effect of "avoid adding benchmark-specific triggers or narrow conditions that only apply to the evaluation examples; the instruction must generalize." This is a zero-cost addition with unverified effectiveness -- include it but do not rely on it as a primary defense.

Maintain a log of all (instruction, composite-score) pairs. If the composite score on the optimization set continues to rise while scores on any held-out subset plateau or decline, flag the run for review.

### 5. Convergence: Expect 20-50 Rounds; Plan a Restart Budget

Based on SI-Agent and the evolving-excellence data, expect meaningful convergence within 20-50 accepted rounds for a well-specified benchmark. If the loop has not shown improvement after 50 rounds, the benchmark may be saturated, the editor may be stuck in a local optimum, or the baseline instruction was already near-optimal.

Allocate a restart budget: after K consecutive non-improving rounds, restart from the best-known prompt using a different mutation class (e.g., switch from phrase-level edits to full structural rewrite). No source provides a concrete K value; start with K=5 for low-variance benchmarks (where re-running the same prompt produces consistent scores) and K=10-15 for high-variance benchmarks. Monitor and adjust based on observed score stability.

### 6. Cost Control: Cheap Pre-Screen Before Benchmark

If the editor generates multiple mutation candidates per round (even 2-3), implement a cheap LLM pre-screen before running the expensive benchmark. The pre-screen prompt asks: "Given the current instruction and this candidate mutation, is this mutation likely to improve performance? Reason briefly." Accept only candidates that pass the pre-screen for full benchmark evaluation. This implements the hierarchical filtering pattern from evolving-excellence and Turintech.

### 7. History and State Management

Maintain a persistent log of all attempted instruction variants, their composite scores, per-dimension scores, and the round in which they were tried. Pass this log (or a sorted subset of the top and bottom performers) into the editor LLM's meta-prompt each round. This enables the editor to avoid re-generating failed variants and to identify which instruction features correlate with higher scores across the history (OPRO pattern + SI history tracking).

### 8. Editor Model Selection

The evidence supports using a strong reasoning model for the editor role. In a ca. 2025 comparison, Claude-3.5-Sonnet outperformed O1 and GPT-4o for this purpose. Given that model capabilities have advanced since that comparison, re-evaluate current models (Claude 4 Sonnet, GPT-4.1, Gemini 2.5 Pro, etc.) before committing. The trainee model's identity should be kept constant across all rounds; changing the trainee model mid-run invalidates score comparisons.

---

<!-- AUDIT LOG
Auditor: Opus
Scout JSONs verified: 3
Original sources spot-checked: 0 (WebFetch denied; all claims verified against cache files which are the scouts' actual source material)
Issues found and fixed:
- Resolved TODO marker for K threshold: replaced placeholder with practitioner-derived reasoning (calibrate K to benchmark variance; start K=5 low-variance, K=10-15 high-variance). Clearly labeled as not source-backed.
- Resolved TODO marker for APO N parameter: replaced placeholder with explicit "no recommended default found" statement.
- Resolved TEMPORAL markers for Claude-3.5-Sonnet: added explicit "ca. 2025" dating, named current-generation alternatives, reframed recommendation as "use a strong reasoning model" rather than a specific model name.
- Resolved population size contradiction (20-50 vs 3): restructured Population Management section into "Two Regimes" with explanation of when each applies and which is relevant to a keep/discard loop.
- Resolved convergence window contradiction (20-50 iterations vs 2-3 generations): added normalization note that pop=3 x gen=2-3 yields ~6-9 total evaluations, making the two figures broadly consistent.
- Added qualification to "dev set curves predict test reliability" per review notes: documented independence requirement.
- Added qualification to "5-10 labeled examples" per review notes: narrowed scope to simple classification, not agent instruction tuning.
- Downgraded "explicit anti-overfitting instruction" confidence per review notes: flagged as single-source, no effect size evidence.
- Added note on smoothing alpha range (0.7-0.9) lacking task-specific tuning guidance.
- Merged SI-Agent memoization note into the Failure History subsection to avoid duplication.
- Fixed cross-reference table entry for evolving-excellence/si-agent to include normalized evaluation counts.
Unresolved items:
- Could not spot-check original web sources (WebFetch denied). All verification was against cache files, which contain orchestrator-generated summaries rather than full article text. Numerical claims (ALE +13.6%, APO 31%, etc.) are verified against cache but not against the original papers.
- PromptBreeder smoothing alpha=0.7-0.9: no task-specific tuning guidance available in sources.
- Anti-overfitting instruction effectiveness: no effect size data available.
Verdict: PASS WITH WARNINGS
-->
