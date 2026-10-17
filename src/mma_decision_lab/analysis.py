"""Framework-independent end-to-end analysis service."""

import hashlib
import json
import platform
from datetime import datetime
from importlib.metadata import version
from zoneinfo import ZoneInfo

import numpy as np

from .config import VERSION
from .decision import decision_tree, expected_utilities, feasibility
from .features import build_fighter_profile, matchup_features
from .schemas import AnalysisContext, ScenarioConfig
from .sensitivity import one_way, recommendation, tornado, two_way
from .simulation import simulate


def fingerprint(
    context: AnalysisContext, config: ScenarioConfig, snapshot: str, mode: str, manual_p0: float
):
    payload = {
        "context": context.model_dump(mode="json"),
        "scenario": config.model_dump(),
        "snapshot": snapshot,
        "mode": mode,
        "manual_p0": manual_p0,
        "model_version": VERSION,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def analyze(
    dataset,
    context,
    config,
    baseline=None,
    manual_p0=None,
    modified_at="Initial defaults or CLI configuration",
):
    a = build_fighter_profile(dataset, context.fighter_a_id, context.reference_date)
    b = build_fighter_profile(dataset, context.fighter_b_id, context.reference_date)
    warnings = feasibility(a, b, context.weight_class)
    empirically_eligible = all(
        p["sufficient_history"] and p["last_division"] == context.weight_class for p in (a, b)
    )
    if manual_p0 is not None:
        if not 0.01 <= manual_p0 <= 0.99:
            raise ValueError("Scenario-only baseline must be in [0.01,0.99]")
        p0 = manual_p0
        samples = np.array([p0])
        mode = "Scenario-only; user-assumed baseline"
        evaluation = {
            "supported": False,
            "status": "No empirical validation attaches to a user-entered baseline.",
        }
    else:
        if not empirically_eligible:
            raise ValueError(
                "Historical forecast requires two retained earlier bouts in total for each fighter and a matching last recorded division. Use scenario-only mode or a supported matchup."
            )
        if baseline is None or baseline.evaluation["reference_date"] != str(context.reference_date):
            raise ValueError("A baseline evaluated strictly before this reference date is required")
        x = matchup_features(a, b)
        p0 = baseline.predict(x)
        samples = baseline.predict_draws(x)
        if samples.size == 0:
            samples = np.array([p0])
        mode = "Historical research"
        evaluation = baseline.evaluation
    simulation = simulate(p0, samples, config, draws=context.draws, seed=context.seed)
    effect_limit = 1.5 - config.effect_half_width
    ranges = {
        "striking_effect": (-min(1, effect_limit), min(1, effect_limit)),
        "grappling_effect": (-min(1, effect_limit), min(1, effect_limit)),
        "resistance": (0, 1),
        "counter_cost": (0, 0.5),
    }
    line, thresholds = one_way(p0, config, "grappling_effect", *ranges["grappling_effect"])
    region = two_way(
        p0,
        config,
        "grappling_effect",
        ranges["grappling_effect"],
        "resistance",
        ranges["resistance"],
        steps=25,
    )
    result = {
        "analysis_created_at": datetime.now(ZoneInfo("America/Lima")).isoformat(timespec="seconds"),
        "context": context.model_dump(mode="json"),
        "scenario": config.model_dump(mode="json"),
        "profiles": {"a": a, "b": b},
        "names": dataset.fighters.set_index("fighter_id")
        .fighter_name.loc[[context.fighter_a_id, context.fighter_b_id]]
        .tolist(),
        "baseline_probability": p0,
        "baseline_parameter_interval": np.quantile(samples, [0.025, 0.975]).tolist(),
        "baseline_draw_count": len(samples),
        "baseline_evaluation": evaluation,
        "mode": mode,
        "snapshot": dataset.manifest,
        "quality": dataset.quality,
        "model_version": VERSION,
        "runtime": {
            "python": platform.python_version(),
            "packages": {
                name: version(name)
                for name in (
                    "numpy",
                    "pandas",
                    "scipy",
                    "scikit-learn",
                    "plotly",
                    "streamlit",
                    "pydantic",
                )
            },
        },
        "parameter_provenance": parameter_provenance(config, modified_at),
        "warnings": warnings,
        "tree": decision_tree(p0, config),
        "deterministic_utilities": expected_utilities(p0, config).tolist(),
        "simulation": simulation,
        "one_way": line,
        "thresholds": thresholds,
        "two_way": region,
        "tornado": tornado(p0, config, ranges),
        "sensitivity_ranges": ranges,
    }
    result["recommendation"] = recommendation(simulation, region, evaluation["supported"])
    return result


def parameter_provenance(config, modified_at):
    definitions = {
        "striking_effect": ("Standing opportunity effect coefficient", "log-odds", [-1.5, 1.5]),
        "grappling_effect": (
            "Grappling opportunity effect coefficient, modulated by opponent resistance",
            "log-odds",
            [-1.5, 1.5],
        ),
        "resistance": (
            "Central resistance index; not an observed defense percentage",
            "dimensionless",
            [0, 1],
        ),
        "counter_cost": (
            "Counter-exposure cost per absolute grappling allocation difference",
            "log-odds",
            [0, 1],
        ),
        "response_weights": (
            "Lower/expected/stronger opponent-response probabilities",
            "simplex",
            [0, 1],
        ),
        "effect_half_width": (
            "Independent triangular tactical-effect half-width; bounds must remain within [-1.5,1.5]",
            "log-odds",
            [0, 1],
        ),
        "response_concentration": (
            "Optional Dirichlet concentration; None fixes the response probabilities",
            "dimensionless",
            [3, 1000],
        ),
    }
    defaults = ScenarioConfig().model_dump()
    return [
        {
            "name": name,
            "definition": definitions[name][0],
            "unit": definitions[name][1],
            "value": value,
            "default": defaults[name],
            "admissible_range": definitions[name][2],
            "classification": "C — scenario assumption",
            "source": "Engineering/user scenario; not estimated from intervention data",
            "last_modified": modified_at,
            "model_version": VERSION,
        }
        for name, value in config.model_dump().items()
    ]
