"""Vectorized integration; shared parameter draws and integrated fight outcomes."""

import numpy as np
import pandas as pd
from scipy.special import expit, logit

from .decision import POLICIES, adjustments


def simulate(p0, baseline_samples, config, draws=5000, seed=422, policies=POLICIES):
    if not 100 <= draws <= 100000:
        raise ValueError("Use 100 to 100,000 integration draws")
    if not 0 < p0 < 1 or not np.isfinite(p0):
        raise ValueError("Invalid baseline probability")
    samples = np.asarray(baseline_samples, dtype=float)
    if (
        samples.size == 0
        or not np.isfinite(samples).all()
        or ((samples <= 0) | (samples >= 1)).any()
    ):
        raise ValueError(
            "Bootstrap probabilities must be finite, nonempty and strictly within (0,1)"
        )
    # Independent RNG streams: changing an uncertainty setting preserves other common draws.
    streams = [np.random.default_rng(s) for s in np.random.SeedSequence(seed).spawn(4)]
    baseline = streams[0].choice(samples, size=draws)
    w = config.effect_half_width
    striking = (
        streams[1].triangular(
            config.striking_effect - w,
            config.striking_effect,
            config.striking_effect + w,
            size=draws,
        )
        if w
        else np.full(draws, config.striking_effect)
    )
    grappling = (
        streams[2].triangular(
            config.grappling_effect - w,
            config.grappling_effect,
            config.grappling_effect + w,
            size=draws,
        )
        if w
        else np.full(draws, config.grappling_effect)
    )
    weights = (
        streams[3].dirichlet(
            np.asarray(config.response_weights) * config.response_concentration, size=draws
        )
        if config.response_concentration
        else np.broadcast_to(config.response_weights, (draws, 3))
    )
    delta = adjustments(config, policies, striking, grappling)
    conditional = expit(logit(baseline)[:, None, None] + delta)
    utilities = np.sum(conditional * weights[:, None, :], axis=2)
    # Fight-level win/loss randomness is analytically integrated, not falsely labeled parameter spread.
    empirical_only = expit(
        logit(baseline)[:, None, None] + adjustments(config, policies)
    ) @ np.asarray(config.response_weights)
    structural_only = np.sum(expit(logit(p0) + delta) * weights[:, None, :], axis=2)
    maxima = utilities.max(axis=1, keepdims=True)
    ties = np.isclose(utilities, maxima, atol=1e-12, rtol=0)
    rank_share = (ties / ties.sum(axis=1, keepdims=True)).mean(axis=0)
    summary = pd.DataFrame(
        {
            "policy": [p.name for p in policies],
            "expected_utility": utilities.mean(axis=0),
            "lower_95": np.quantile(utilities, 0.025, axis=0),
            "upper_95": np.quantile(utilities, 0.975, axis=0),
            "difference_from_baseline": (utilities - baseline[:, None]).mean(axis=0),
            "mc_standard_error": utilities.std(axis=0, ddof=1) / np.sqrt(draws),
            "rank_first_share": rank_share,
            "expected_regret": (maxima - utilities).mean(axis=0),
            "empirical_parameter_sd": empirical_only.std(axis=0, ddof=1),
            "scenario_assumption_sd": structural_only.std(axis=0, ddof=1),
        }
    )
    pairwise = []
    for i in range(len(policies)):
        for j in range(i + 1, len(policies)):
            difference = utilities[:, i] - utilities[:, j]
            pairwise.append(
                {
                    "policy_a": policies[i].name,
                    "policy_b": policies[j].name,
                    "mean_difference": float(difference.mean()),
                    "lower_95": float(np.quantile(difference, 0.025)),
                    "upper_95": float(np.quantile(difference, 0.975)),
                    "mc_standard_error": float(difference.std(ddof=1) / np.sqrt(draws)),
                }
            )
    checkpoints = sorted({max(100, draws // 10), draws // 2, draws})
    convergence = pd.DataFrame(
        [
            {
                "draws": n,
                "policy": p.name,
                "mean": utilities[:n, i].mean(),
                "mc_standard_error": utilities[:n, i].std(ddof=1) / np.sqrt(n),
            }
            for n in checkpoints
            for i, p in enumerate(policies)
        ]
    )
    return {
        "summary": summary,
        "utilities": utilities,
        "pairwise": pd.DataFrame(pairwise),
        "convergence": convergence,
    }
