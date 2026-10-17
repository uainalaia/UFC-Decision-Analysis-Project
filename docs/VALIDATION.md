# Validation and acceptance status — 2026-10-16

**Release classification: functional local research beta with exploratory forecasting.** The software workflow is implemented and tested; this is not an empirically established tactical intervention system. The default baseline fails the declared support gate and correctly returns no robust tactical preference.

## Executed checks

- `python -m pytest -q --junitxml=reports/test_results.xml`: **48 passed**, 35.88 seconds in the final full-suite run. Local-socket permission was required by the Windows execution sandbox for Streamlit AppTest, not by the application on an ordinary local installation.
- `ruff check src app scripts tests`: passed. `ruff format --check src app scripts tests`: passed.
- `compileall -q src app scripts`: passed.
- `uv pip check`: all 88 installed packages compatible, after notebook tools were added.
- Editable project installation: completed successfully in the documented `.venv`.
- Historical CLI example: executed with real earlier-date records and the explicitly illustrative scenario. JSON, CSV, ZIP, offline HTML, numeric model, calibration, partition and benchmark files were produced.
- Exported-configuration replay: utilities matched at absolute tolerance 1e-12; profiles, scenario configuration and the full two-way grid matched exactly.
- Notebook: format validated, all five code cells executed top-to-bottom, saved outputs contain no error records, exported HTML visually inspected. Neutral expected utility = 0.600000; the second explicitly hypothetical worked policy value = 0.576375.
- Browser QA: Overview, Decision Model, Monte Carlo results and sensitivity views inspected at 1280×720; sensitivity curves/decision regions inspected at 1024×768. No whole-page horizontal overflow at 1024 pixels. Sidebars and data tables may scroll within their own containers. Exported HTML report and notebook HTML were inspected for legibility, valid charts and saved results. Keyboard-semantic controls and non-color heatmap codes/table are present; a complete formal WCAG audit was not performed.

The first preview encountered a stale Python-module import during live development after adding a new chart function. Restarting the preview loaded the final module. Full tests and browser checks above use the corrected version.

## Test coverage

Data tests cover identity/count/time validation, missing ratios, invalid schemas and size limits, duplicates, nonbinary/DQ/unsupported cases, duration/control bounds and division normalization. Temporal tests cover future and same-date invariance, grouped same-day exclusion, vectorized/API agreement and sparse histories. Forecast tests cover ordered-feature prediction, complementary probabilities, chronological partitions, test-data isolation, future-row exclusion and numeric JSON round trips.

Decision/simulation tests cover probability mass, hand-calculated terminal utility, neutral effects at multiple baselines, invalid assumptions, identical-policy common draws/tie sharing, fixed seeds, bounded finite probabilities, exact integration for fixed parameters, decreasing MC error and separated uncertainty components. Sensitivity tests cover direct-evaluation agreement, a switching root with a known mathematical value, absent roots, ties, grid dimensions and rejected ranges. Reporting tests cover strict finite JSON, complete bundle contents, embedded offline plotting and CSV formula protection.

Streamlit integration traverses all eight views, loads the supported historical matchup, applies hypothetical assumptions, runs simulation, opens sensitivity/validation, and generates four export controls. A second workflow verifies stale-result invalidation and graceful handling of insufficient historical context.

## Historical-data audit

| Check | Result |
|---|---:|
| Raw result rows | 8,962 |
| Retained eligible bouts | 8,420 |
| Excluded input rows | 542 (6.05%) |
| Competitor-round records | 40,068 |
| Source fighter identities | 4,628 |
| Retained coverage | 1999-07-16–2026-10-10 |

Exclusions: 251 unsupported formats; 150 nonbinary outcomes; 63 missing/ambiguous fighter identities; 52 ambiguous duplicate source/event-bout rows; 24 disqualifications; 2 unresolved event references. The row-level log and optional-field missingness are available in the UI and `data/processed`. No excluded nonbinary outcome is silently classified as a loss.

## Acceptance assessment

| Area | Status | Evidence / boundary |
|---|---|---|
| Frozen historical ingestion and provenance | Implemented/tested; primary reconciliation partial | Recorded commit/hashes, schemas, transformations, exclusions; full UFCStats cross-check outstanding |
| Earlier-date profiles and leakage prevention | Passed | Future/same-day tests, vectorized/API agreement, training cutoff tests |
| Baseline forecasting and chronological evaluation | Implemented/evaluated; exploratory | Brier 0.24252, log loss 0.67808 on 527 test bouts; Brier difference interval includes zero |
| Three static policies and expected utility | Passed | Validated simplex, terminal branches, probability-mass and neutral/hand-calculation tests |
| Shared-draw Monte Carlo and diagnostics | Passed | Fixed seed, numerical bounds, paired differences, regret, rank-first ties, convergence and separate uncertainty summaries |
| One-way/two-way/tornado sensitivity | Passed | Numerical root fixture, no fabricated threshold, selectable UI ranges and accessible decision grids |
| Conditional/no-preference behavior | Passed within declared model | Gate checks held-out support, paired uncertainty against all competitors and default-grid stability |
| Interface and exports | Passed supported workflow | Eight-view AppTest, browser inspection, HTML/CSV/JSON/ZIP generation and replay |
| Dependency/runtime reproducibility | Passed tested Windows environment | Hashed lock, successful installation, package compatibility and recorded versions |
| Research notebook | Passed | Executed saved cells, validated structure and reviewed HTML |
| Tactical causal validation | Unsupported by available observational data | Clearly labeled assumptions; no causal optimum claimed |
| Full primary-source reconciliation / as-was archive | Incomplete | UFCStats primary page lookup failed; current records may contain later revisions |
| Public deployment / production hardening | Deferred by scope | Local beta; deployment optional in the supplied requirements |

## Measured performance

Final illustrative CLI benchmark on the available Windows environment: **20.77 seconds total**, dominated by fresh CSV ingestion/validation; **0.51 seconds** for feature generation plus 64-bootstrap baseline evaluation; **0.27 seconds** for 5,000-draw simulation and default sensitivity calculations. Cached ordinary navigation avoids ingestion/model refitting. These measurements are not a cross-device latency guarantee.

## Research conclusions

The default model's modest held-out point-score improvement does not establish reliable superiority to 50/50 under the declared interval criterion, and no comparison with Holmes et al. is numerically justified. Tactical rankings change under scenario assumptions, and the illustrative run has no robust preference. Source rights/reconciliation, stronger forecast validation, dependence-aware uncertainty and defensible elicitation of tactic/feasibility assumptions remain future research work. All relevant components are labeled accordingly; launching the interface alone is not treated as scientific completion.
