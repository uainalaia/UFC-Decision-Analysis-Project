"""The redesign must preserve the real pre-redesign reference, without any fitting."""

import json

import numpy as np
import pandas as pd
import pytest

from mma_decision_lab.analysis import analyze
from mma_decision_lab.config import ROOT
from mma_decision_lab.data import load_dataset
from mma_decision_lab.forecasting import Baseline
from mma_decision_lab.persistence import load_numeric_model
from mma_decision_lab.schemas import AnalysisContext, ScenarioConfig


@pytest.mark.skipif(
    not (ROOT / "reports/audit_v2/reference_before.json").exists()
    or not (ROOT / "models/baseline.json").exists(),
    reason="Requires recorded local reference and numeric baseline",
)
def test_historical_reference_is_numerically_unchanged():
    old = json.loads((ROOT / "reports/audit_v2/reference_before.json").read_text(encoding="utf-8"))
    metadata = json.loads((ROOT / "models/baseline.json").read_text(encoding="utf-8"))
    model, bootstraps = load_numeric_model(ROOT / "models/baseline.json")
    baseline = Baseline(
        model,
        bootstraps,
        metadata["evaluation"],
        pd.read_csv(ROOT / "reports/generated/calibration.csv"),
        pd.read_csv(ROOT / "reports/generated/partitions.csv"),
        metadata["features"],
    )
    current = analyze(
        load_dataset(),
        AnalysisContext(**old["context"]),
        ScenarioConfig(**old["scenario"]),
        baseline,
    )
    for key in ["baseline_probability", "baseline_parameter_interval", "deterministic_utilities"]:
        np.testing.assert_allclose(current[key], old[key], atol=1e-12, rtol=0)
    for key in ["tree", "one_way", "two_way", "tornado"]:
        pd.testing.assert_frame_equal(
            current[key].reset_index(drop=True),
            pd.DataFrame(old[key]).reset_index(drop=True),
            check_dtype=False,
            atol=1e-12,
            rtol=0,
        )
    for key in ["summary", "pairwise", "convergence"]:
        pd.testing.assert_frame_equal(
            current["simulation"][key],
            pd.DataFrame(old["simulation"][key]),
            check_dtype=False,
            atol=1e-12,
            rtol=0,
        )
    assert current["baseline_evaluation"] == old["baseline_evaluation"]
    assert current["recommendation"]["robust"] == old["recommendation"]["robust"]
    assert current["snapshot"]["dataset_version"] == old["snapshot"]["dataset_version"]
