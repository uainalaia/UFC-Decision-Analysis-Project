# Scientific communication and research-record audit

Audit date: 2026-10-16. Bounded review of the initial interface, analytical services, reporting code, model card, methodology, validation, limitations and reproducibility documentation against the v2 designer brief. No analytical source, dataset, fitted model or scientific parameter was changed. No retraining or browser inspection was performed in this review.

## Demonstrated issues and supported presentation repairs

1. **Exact ties acquire arbitrary individual leaders in prose and tornado labels.** `src/mma_decision_lab/sensitivity.py:125–146` selects the last sorted mean; line 102 selects the first `argmax` for tornado. A read-only fixture with `p0=.6`, neutral `ScenarioConfig`, seed 422 and 1,000 draws produced all three mean utilities `.6`, equal rank-first shares `1/3`, `highest_mean="Balanced priority"`, prose saying Balanced has the highest mean, and a tornado measuring Striking as the current leader. The no-robust-preference headline itself is correct. Preserve all numerical outputs and the declared robustness criteria; communicate equality explicitly and label any tied-policy tornado as an inspected alternative, or ask which tied alternative to inspect. Do not imply a unique tactical leader.

2. **The scenario-only HTML baseline is mislabeled as bootstrap evidence.** `analysis.py:46–53` constructs a single fixed assumed probability; `reporting.py:85` always labels its interval “Conditional bootstrap parameter interval.” A read-only real-profile run with manual `.6` returned `[.6,.6]`, draw count `1`, and that bootstrap label in HTML. For scenario-only mode say assumed/fixed baseline and no empirical baseline interval. Historical mode can retain the conditional bootstrap terminology and its limitations.

3. **Explored sensitivity scope and research-record scope are different.** Initial `app/main.py:568–610` computes selected one-way and two-way axes/ranges as local views, while `analysis.py:72–87` and `reporting.py:63–66` export the default grappling-effect/resistance analysis. Downloads of individual displayed grids exist, but the Research report does not identify that the user's currently explored sensitivity is omitted. Either label the report's default scope unambiguously or retain an immutable sensitivity record with axes, ranges, resolution and its corresponding results. Keep the existing recommendation's default robustness grid unchanged.

4. **Record creation time is not fixed across exports.** Initial `reporting.py:59` assigns the current time every time HTML is built; the JSON record has no analysis creation timestamp. Standalone HTML and ZIP HTML can therefore identify the same analysis with different “Created” times. Add a fixed record timestamp when an analysis completes, then reuse it across HTML/JSON/ZIP. An optional export-generation timestamp should have its own clear meaning. This is presentation metadata only.

5. **Neutral wording omits the uncertainty condition.** Initial `app/main.py:741` says neutral `s=g=c=0` preserves the baseline under every policy; `docs/METHODOLOGY.md` correctly additionally requires zero effect uncertainty. Nonzero triangular width means the effects are not identically zero. Carry the documented zero-width condition into the interface help.

## Checks that support the existing scientific boundaries

- The stored default historical baseline is `0.6858367292839322`; loading the saved numeric model and applying the exported profile differences reproduced it exactly without fitting. The exported record and saved model contain 64 bootstrap models/draws.
- The default held-out test has 527 bouts. Its Brier-difference interval is `[-0.016199116670441584, +0.0007691930678525138]`, and `supported=false`, consistent with the model card's exploratory status. An audit or redesign does not establish calibration or tactical causal validity.
- Simulation shares exact ties equally, uses common draws, integrates fight outcomes analytically, and describes separate empirical/scenario SDs as controlled comparisons rather than additive variance components.
- Earlier-date exclusions, static Balanced allocation, assumed allocations/effects/response weights, pooled divisions/formats, lack of opponent-strength adjustment and iid bout-bootstrap dependence limits are explicitly documented. These are declared scientific limitations, not missing implemented functionality to conceal through redesign.
- HTML includes Plotly inline and tables; structured exports preserve summary, pairwise comparisons, convergence, tree and default sensitivity. The HTML could expose paired diagnostics more directly, but their absence from HTML does not imply that the engine or ZIP lacks them.
- The source fingerprint exists at nested `snapshot.implementation_sha256`, populated by `data.py:129–142`. An initial top-level-only inspection wrongly suggested it was absent; that finding was retracted after checking the nested record.

## Scope of this evidence

This review verifies the issues and numeric comparisons above, not full scientific validation, external source reconciliation, formal accessibility, browser layout, every data case or all integration tests. Root review owns those checks and the redesign. Initial line references may shift during implementation.
