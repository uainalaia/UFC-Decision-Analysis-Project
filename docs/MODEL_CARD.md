# Baseline model card

**Version:** 0.1.0; strict-date feature design v1. Intended use: educational retrospective pre-fight probability estimation, providing an empirical anchor for transparent hypothetical decision analysis. Unsupported: betting, causal tactic optimization, injury/fatigue advice, real-time coaching or claims of replicating the reference Markov model.

## Data and eligible population

Frozen archive: `greco-5e38ebeb9bb8`, full upstream commit `5e38ebeb9bb854c9ab4359f8f6f5b444328c555c`. There are 8,962 raw result rows, 8,420 retained binary non-DQ standard-format bouts, 40,068 competitor-round records and 4,628 source identities. Missing/ambiguous identity, duplicate, nonbinary and unsupported-format cases are excluded; only the retained history contributes to profiles. Original-source reconciliation and reuse rights are not fully established. Raw data remain local.

The default historical decision is Khabib Nurmagomedov vs. Conor McGregor before 2018-10-06. Each profile has ten retained earlier UFC bouts. This does not equal the fighters' complete professional histories. No outcome/statistics on or after the target date enter features or training.

## Chronological evaluation for the default cutoff

| Partition | Dates | Bouts |
|---|---|---:|
| Train | 2000-09-22–2015-01-31 | 1,257 |
| Validation | 2015-02-14–2016-11-12 | 493 |
| Untouched test | 2016-11-19–2018-09-22 | 527 |

The selected regularization C is 0.1. Final coefficients/scales are fitted to train+validation only. The test period is not used for tuning or refitting the target forecast.

| Model | Brier ↓ | Log loss ↓ | Accuracy | AUC |
|---|---:|---:|---:|---:|
| Full logistic baseline | 0.24252 | 0.67808 | 57.12% | 0.60080 |
| 50/50 reference | 0.25000 | 0.69315 | 50.09% | 0.50000 |
| Win-rate-only logistic | 0.24400 | 0.68107 | 54.27% | 0.58878 |

The 95% iid bout-bootstrap interval for the Brier difference against 50/50 is approximately **[-0.01620, +0.00077]**. It includes zero. The application therefore labels this baseline **exploratory** and withholds robust tactical recommendations for the default example. A modest point-score improvement does not establish well-calibrated probabilities or superiority to Holmes et al. Calibration is reported descriptively with bin sizes and Wilson intervals; no recalibration stage is claimed.

## Uncertainty, fairness of ordering and limitations

Mirrored development observations, zero imputation, scaling without centering and no intercept preserve complementary predictions under fighter reversal. All mirrored representations remain in the same bout-level chronological partition. Conditional uncertainty comes from 64 development-bout bootstrap models with fixed C and fixed historical features. This omits dependence among repeated fighter appearances, feature-estimation uncertainty, model-selection uncertainty and structural misspecification.

Features pool divisions and formats and do not adjust for opponent strength, changing form or unpublished camp information. The two-bout minimum does not guarantee adequate individual evidence. Division change and inactivity limit transportability. Modern source revisions may alter historical outcomes or fields, so this is not a verified as-was information backtest.

The model has no protected-person decision-making use. Its relevant biases are selection of recorded UFC athletes, unequal histories, survivorship, era drift, and conservative exclusions of ambiguous identities. Predictive evaluation does not validate the assumed tactic-to-outcome relationship.
