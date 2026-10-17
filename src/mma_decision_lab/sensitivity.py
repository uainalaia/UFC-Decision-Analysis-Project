"""Deterministic sensitivity; numerical roots only where a top-ranking crossing exists."""

import itertools

import numpy as np
import pandas as pd
from scipy.optimize import brentq

from .decision import BOUNDS, POLICIES, expected_utilities


def validate_range(config, parameter, low, high, steps):
    if parameter not in BOUNDS or not np.isfinite([low, high]).all():
        raise ValueError("Unsupported sensitivity parameter")
    if not BOUNDS[parameter][0] <= low < high <= BOUNDS[parameter][1] or not 3 <= steps <= 151:
        raise ValueError("Invalid bounds or grid resolution")
    config.changed(**{parameter: low})
    config.changed(**{parameter: high})


def preference(values, tolerance=0.01):
    order = np.argsort(values)
    return int(order[-1]) if values[order[-1]] - values[order[-2]] > tolerance else 3


def one_way(p0, config, parameter, low, high, steps=61):
    validate_range(config, parameter, low, high, steps)
    xs = np.linspace(low, high, steps)
    values = np.array([expected_utilities(p0, config.changed(**{parameter: float(x)})) for x in xs])
    frame = pd.DataFrame(values, columns=[p.name for p in POLICIES])
    frame.insert(0, parameter, xs)
    roots = []
    for i, j in itertools.combinations(range(3), 2):
        difference = values[:, i] - values[:, j]
        candidates = []
        for k in range(steps - 1):
            if difference[k] * difference[k + 1] < 0:

                def fun(x, first=i, second=j):
                    values = expected_utilities(p0, config.changed(**{parameter: float(x)}))
                    return values[first] - values[second]

                candidates.append(brentq(fun, xs[k], xs[k + 1], xtol=1e-10))
        for k in range(1, steps - 1):
            if abs(difference[k]) < 1e-12 and difference[k - 1] * difference[k + 1] < 0:
                candidates.append(xs[k])
        for root in candidates:
            eps = min((high - low) * 1e-5, root - low, high - root) / 2
            if eps <= 0:
                continue
            before = expected_utilities(p0, config.changed(**{parameter: float(root - eps)}))
            after = expected_utilities(p0, config.changed(**{parameter: float(root + eps)}))
            if np.argmax(before) != np.argmax(after) and {
                int(np.argmax(before)),
                int(np.argmax(after)),
            } == {i, j}:
                if not any(abs(root - r["value"]) < 1e-7 for r in roots):
                    roots.append(
                        {
                            "parameter": parameter,
                            "value": float(root),
                            "from_policy": POLICIES[int(np.argmax(before))].name,
                            "to_policy": POLICIES[int(np.argmax(after))].name,
                        }
                    )
    return frame, roots


def two_way(p0, config, x_param, x_bounds, y_param, y_bounds, steps=31, tolerance=0.01):
    if x_param == y_param:
        raise ValueError("Select different parameters for the two axes")
    validate_range(config, x_param, *x_bounds, steps)
    validate_range(config, y_param, *y_bounds, steps)
    records = []
    for y in np.linspace(*y_bounds, steps):
        for x in np.linspace(*x_bounds, steps):
            values = expected_utilities(
                p0, config.changed(**{x_param: float(x), y_param: float(y)})
            )
            winner = preference(values, tolerance)
            ordered = np.sort(values)
            records.append(
                {
                    x_param: x,
                    y_param: y,
                    "region": winner,
                    "decision": POLICIES[winner].name if winner < 3 else "No robust preference",
                    "margin": ordered[-1] - ordered[-2],
                    **{p.name: values[i] for i, p in enumerate(POLICIES)},
                }
            )
    return pd.DataFrame(records)


def tornado(p0, config, ranges=None):
    ranges = ranges or {
        "striking_effect": (-1, 1),
        "grappling_effect": (-1, 1),
        "resistance": (0, 1),
        "counter_cost": (0, 0.5),
    }
    leader = int(np.argmax(expected_utilities(p0, config)))
    rows = []
    for param, (low, high) in ranges.items():
        endpoints = []
        for x in (low, high):
            values = expected_utilities(p0, config.changed(**{param: x}))
            endpoints.append(values[leader] - np.max(np.delete(values, leader)))
        rows.append(
            {
                "parameter": param,
                "low_margin": endpoints[0],
                "high_margin": endpoints[1],
                "swing": abs(endpoints[1] - endpoints[0]),
                "measured_policy": POLICIES[leader].name,
                "low": low,
                "high": high,
            }
        )
    return pd.DataFrame(rows).sort_values("swing", ascending=False)


def recommendation(simulation, region, baseline_supported, tolerance=0.01):
    summary = simulation["summary"]
    order = np.argsort(summary.expected_utility.to_numpy())
    best = int(order[-1])
    draws = simulation["utilities"]
    differences = draws[:, [best]] - np.delete(draws, best, axis=1)
    paired_lower = float(np.quantile(differences, 0.025, axis=0).min())
    paired_error = float((differences.std(axis=0, ddof=1) / np.sqrt(len(draws))).max())
    survives = bool((region.region == best).all())
    robust = bool(
        baseline_supported and paired_lower > tolerance + 1.96 * paired_error and survives
    )
    name = summary.policy.iloc[best]
    leaders = summary.loc[
        np.isclose(summary.expected_utility, summary.expected_utility.max(), atol=1e-12, rtol=0),
        "policy",
    ].tolist()
    return {
        "robust": robust,
        "headline": f"Conditional preferred strategy: {name}"
        if robust
        else "No robust tactical preference under the tested assumptions.",
        "highest_mean": name,
        "mean_leaders": leaders,
        "paired_lower_95": paired_lower,
        "paired_mc_standard_error": paired_error,
        "stable_across_tested_grid": survives,
        "tolerance": tolerance,
        "explanation": (
            "All three alternatives have equal modeled mean utility. "
            if len(leaders) == 3
            else "The highest modeled mean is shared by " + ", ".join(leaders) + ". "
            if len(leaders) > 1
            else f"{name} has the highest modeled mean utility. "
        )
        + (
            "Its paired advantage exceeds the declared 1-point margin and survives the tested two-parameter grid. "
            if robust
            else "A preference requires supported baseline evidence, a positive paired 95% advantage above the declared margin, and stability throughout the tested grid. "
        )
        + "Tactical effects remain assumptions; this is not causal evidence of an optimal real-world strategy.",
    }
