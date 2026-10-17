"""Executable decision/chance/outcome tree under declared log-odds assumptions."""

import numpy as np
import pandas as pd
from scipy.special import expit, logit

from .schemas import ScenarioConfig, TacticalPolicy

POLICIES = (
    TacticalPolicy(
        policy_id="striking",
        name="Striking priority",
        description="Distance management and standing exchanges; limited intentional grappling.",
        allocation=(0.75, 0.15, 0.10),
    ),
    TacticalPolicy(
        policy_id="grappling",
        name="Grappling priority",
        description="Takedown entries, clinch pressure and ground offense.",
        allocation=(0.20, 0.30, 0.50),
    ),
    TacticalPolicy(
        policy_id="balanced",
        name="Balanced priority",
        description="Static combination of standing, clinch and ground emphasis.",
        allocation=(0.45, 0.25, 0.30),
    ),
)
RESPONSES = ("Lower resistance", "Expected resistance", "Stronger resistance")
RESPONSE_OFFSETS = np.array([-0.25, 0.0, 0.25])
# A fixed ENGINEERING reference, not a measured historical allocation or the balanced policy.
REFERENCE_ALLOCATION = np.array([0.5, 0.25, 0.25])
BOUNDS = {
    "striking_effect": (-1.5, 1.5),
    "grappling_effect": (-1.5, 1.5),
    "resistance": (0.0, 1.0),
    "counter_cost": (0.0, 1.0),
}


def adjustments(config: ScenarioConfig, policies=POLICIES, striking=None, grappling=None):
    """Shape (..., policies, responses); effects are C assumptions, not fitted values."""
    allocation = np.array([p.allocation for p in policies])
    standing = allocation[:, 0] - REFERENCE_ALLOCATION[0]
    pressure = allocation[:, 1] + allocation[:, 2] - sum(REFERENCE_ALLOCATION[1:])
    resistance = np.clip(config.resistance + RESPONSE_OFFSETS, 0, 1)
    s = np.asarray(config.striking_effect if striking is None else striking)
    g = np.asarray(config.grappling_effect if grappling is None else grappling)
    return (
        s[..., None, None] * standing[:, None]
        + g[..., None, None] * pressure[:, None] * (1 - 2 * resistance)
        - config.counter_cost * np.abs(pressure[:, None]) * resistance
    )


def conditional_probabilities(p0, config, policies=POLICIES):
    if not np.isfinite(p0) or not 0 < p0 < 1:
        raise ValueError("Baseline probability must be strictly between zero and one")
    return expit(logit(p0) + adjustments(config, policies))


def expected_utilities(p0, config, policies=POLICIES):
    return conditional_probabilities(p0, config, policies) @ np.asarray(config.response_weights)


def decision_tree(p0, config, policies=POLICIES):
    probs = conditional_probabilities(p0, config, policies)
    rows = []
    for i, policy in enumerate(policies):
        for j, response in enumerate(RESPONSES):
            weight = config.response_weights[j]
            for consequence, probability, utility in [
                ("Win", probs[i, j], 1),
                ("Loss", 1 - probs[i, j], 0),
            ]:
                rows.append(
                    {
                        "policy": policy.name,
                        "response": response,
                        "response_probability": weight,
                        "conditional_outcome_probability": probability,
                        "outcome": consequence,
                        "utility": utility,
                        "joint_probability": weight * probability,
                        "utility_contribution": weight * probability * utility,
                    }
                )
    return pd.DataFrame(rows)


def feasibility(profile_a, profile_b, division):
    warnings = []
    for label, profile in [("Fighter A", profile_a), ("Fighter B", profile_b)]:
        if not profile["sufficient_history"]:
            warnings.append(
                f"{label} has fewer than two eligible earlier bouts: empirical prediction is disabled."
            )
        if profile["inactivity_years"] > 2:
            warnings.append(
                f"{label} has over two years of inactivity; transport of historical rates is uncertain."
            )
        if profile["last_division"] != division:
            warnings.append(
                f"{label}'s last recorded division differs from the selected context; empirical prediction is disabled."
            )
    if profile_a.get("total_td_attempted", 0) < 5:
        warnings.append(
            "Fighter A has fewer than five recorded takedown attempts. Grappling feasibility is unestablished; allocation remains an assumption."
        )
    warnings.append(
        "All policy allocations are engineering presets; execution feasibility has not been established by coaching evidence."
    )
    return warnings
