# Mathematical methodology

## Decision and evidence

The focal fighter and coaching team choose a **static** pre-fight opportunity priority. Utility is 1 for a win and 0 for a loss. Draws, no-contests, disqualifications and unsupported formats are excluded and logged; they are never recoded as losses. Current archive revisions prevent a strict claim of an as-was publication backtest.

- A — observed: dates, outcomes and competitor-round counts in the published archive.
- B — estimated: earlier-date smoothed profiles, baseline forecast, bootstrap parameters.
- C — assumed: all allocations, tactical effects, response probabilities, uncertainty widths and robustness margins.
- D — computed: conditional utilities, simulated parameter bands, regret and sensitivity regions.

## Historical profiles

Only events with `event_date < reference_date` contribute. Profiles contain counts, observed exposure, aggregate rates, last division and inactivity. Significant strikes and takedowns are summed over recorded rounds, and rates use total corresponding exposure (not an unweighted mean of per-fight percentages). Submission/control rates use exposure only where that metric is observed. A partial optional total stays missing. Smoothed success/defense ratios are `(successes+1)/(attempts+2)` **only when attempts > 0**. At 0/0 the displayed estimate remains missing. These are simple engineering priors, not individualized posterior skill models.

Two earlier eligible fights are required for each empirical matchup. This is an eligibility rule, not a guarantee of precision. Division switching and long inactivity are disclosed. There is no opponent-strength adjustment, current-career statistic, ranking, injury, camp or post-target feature.

## Forecasting baseline

Predictors are differences A−B in significant strikes landed/absorbed per minute, smoothed striking accuracy/defense, takedowns per 15 minutes, takedown defense, submission attempts per 15 minutes, smoothed win fraction, log(1+prior bouts), and inactivity in years.

The model pools divisions and 3/5-round formats. Bout format and agreed division define the decision context and eligibility; **individualized format/division effects are not estimated**. Unknown differences are imputed to zero (neutral difference) in the pipeline. Training uses `(x,y)` and `(-x,1-y)` together, scaling without centering and logistic regression without an intercept. Consequently `p(x)+p(-x)=1`. There are no labels tied to source corner order or winner-first order: competitor source IDs establish canonical ordering independently of outcome.

Eligible earlier event dates establish chronological boundaries at 65% and 82% of distinct dates. C ∈ {0.1,1,10} is selected by validation log loss. Scaling and coefficients are then refitted on train+validation only. The final test block remains excluded from the model applied to the selected target matchup. This sacrifices some recency in return for an auditable held-out evaluation.

Report Brier score, log loss, AUC and secondary accuracy; compare 50/50 and a win-rate-only model. Calibration bins have Wilson intervals with bout counts. No calibration transform was fitted: modest data and the prototype scope do not justify an additional tuning stage. A conservative support gate requires log loss better than 50/50 and an upper 95% bout-bootstrap bound below zero for `Brier(model)−Brier(50/50)`. This is an engineering evidence criterion, not proof of general predictive validity. Repeated-fighter dependence is not captured by the iid bout bootstrap.

## Tactical policies and response model

| Policy | Standing | Clinch | Ground |
|---|---:|---:|---:|
| Striking priority | 0.75 | 0.15 | 0.10 |
| Grappling priority | 0.20 | 0.30 | 0.50 |
| Balanced priority | 0.45 | 0.25 | 0.30 |

Each allocation sums to one. They describe **planned opportunity emphasis**, not guaranteed realized combat time. These presets are not empirical strategy labels and their execution feasibility is not established. The reference allocation `(0.50,0.25,0.25)` is an explicit engineering origin, **not** an observed historical profile or the balanced policy.

Let `z_a = q_clinch + q_ground − 0.5` and `d_a = q_standing − 0.5`. Opponent-response resistance indices are `R_r = clip(R + {-0.25,0,+0.25},0,1)`, ordered lower/expected/stronger. Weights default to `(0.25,0.50,0.25)`. They are assumed exogenous to the selected policy, not empirically estimated opponent reactions.

`Δ(a,r) = s*d_a + g*z_a*(1−2R_r) − c*abs(z_a)*R_r`

`p(a,r) = sigmoid(logit(p0) + Δ(a,r))`

`V(a) = Σ_r w_r*p(a,r)`

`s,g` are assumed effect coefficients in log-odds units; `c` is an assumed counter-exposure cost. `R` is an index, **not** the fighter's observed takedown-defense percentage. This form is an inspectable scenario relationship, not a fitted physical law or a causal intervention model. With `s=g=c=0` and zero effect uncertainty, every policy equals `p0`. With nonzero uncertainty width around a zero center, effects are no longer identically neutral.

Every policy/response branch terminates in win/loss, with joint probabilities `w_r*p(a,r)` and `w_r*(1−p(a,r))`. Terminal utilities are 1 and 0. The engine actually sums terminal contributions; the diagram and branch table use those computed values.

### Defaults and bounds

| Parameter | Default | Bounds / meaning |
|---|---:|---|
| `striking_effect`, `grappling_effect` | 0 | [-1.5,1.5] log-odds coefficients |
| `resistance` | 0.5 | [0,1], dimensionless |
| `counter_cost` | 0 | [0,1], log-odds coefficient |
| `response_weights` | .25/.50/.25 | Nonnegative simplex; positive for Dirichlet sampling |
| `effect_half_width` | 0 | [0,1]; both triangular supports must remain within [-1.5,1.5] |
| `response_concentration` | None | Fixed weights by default; otherwise [3,1000] |
| seed / integration draws | 422 / 5,000 | UI: 1,000 / 5,000 / 10,000; engine: 100–100,000 |

The optional illustrative preset is `s=.35,g=.50,R=.40,c=.15,half_width=.30,concentration=30`. It is entirely hypothetical. It is never an estimated tactic advantage.

## Uncertainty and simulation

1. **Empirical parameter uncertainty:** refit 64 bout-bootstrap logistic models on the development block, conditional on the chosen C and fixed historical feature design. Resample their target probabilities with replacement. This is a finite conditional bootstrap approximation, not a complete predictive confidence interval.
2. **Structural/scenario uncertainty:** sample independent symmetric triangular distributions for s and g, with the declared center and half-width. Optionally sample the response simplex using Dirichlet(`concentration × weights`). Dependence among simplex components is retained; s, g, the baseline and response simplex are otherwise assumed independent.
3. **Future fight performance:** win/loss randomness and conditional opponent responses are integrated analytically when evaluating utility, rather than sampled into a misleading binary utility histogram. The bands show uncertainty in expected utility, not frequencies of possible win/loss observations.

Separate random streams preserve common draws across policies. Report mean utility, central 95% bands, change relative to the paired baseline draw, paired differences, empirical-only SD, structural-only SD, numerical MC standard error, expected regret and rank-first share. Exact ties share mass equally. These SD components are controlled comparisons, not an additive variance decomposition.

Numerical convergence compares prefixes at approximately 10%, 50% and 100% of the same draw stream; it does not create independent experiments. More draws reduce integration error, not structural uncertainty.

## Sensitivity and conditional recommendations

One-way analysis varies one parameter and holds other central assumptions constant. Sign-changing pairwise intersections are refined with Brent's method; a switching root is reported only if the top-ranked alternative changes across the root inside the tested range. Ties over intervals do not imply a unique threshold.

The default two-way grid varies grappling effect over [-1,1] (narrowed if required by uncertainty bounds) and resistance over [0,1], at 25×25 points. UI axes, ranges and one-way resolution are selectable. A cell receives a pointwise strategy label only when the leading central utility gap exceeds 0.01; otherwise it is a no-preference region. Codes and accessible tables supplement color.

The tornado measures the central leader's utility minus its best competitor at each parameter's endpoints, rather than an undefined performance score. Default ranges also include striking effect [-1,1] and counter cost [0,.5]. These are declared stress ranges, not elicited expert judgments.

A **conditional preferred strategy** requires supported baseline evidence, the lowest paired 2.5% utility-difference quantile against every competitor above 0.01 plus a numerical-error allowance, and the same leader throughout the default two-way grid. Otherwise report **no robust preference**. Stability is limited to the tested model and parameter ranges; it is never a universal optimality claim.

## Hand-checkable example

For neutral policies with `p0=.6`, the three response win contributions are `.25×.6=.15`, `.5×.6=.30`, `.25×.6=.15`. Their sum is `.60`, with loss utility contributions zero. For a single hypothetical branch with delta=.2, `sigmoid(logit(.6)+.2)=.646906...`. See the worked notebook and unit tests.
