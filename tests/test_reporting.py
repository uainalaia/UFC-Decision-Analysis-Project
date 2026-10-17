import io
import json
import zipfile

import numpy as np
import pandas as pd

from mma_decision_lab.analysis import analyze
from mma_decision_lab.reporting import clean, export_bundle, export_json, html_report, safe_csv
from mma_decision_lab.schemas import AnalysisContext, ScenarioConfig


def test_scenario_analysis_exports_are_strict_and_complete(synthetic_dataset):
    d = synthetic_dataset
    d.manifest["files"] = []
    context = AnalysisContext(
        fighter_a_id="alpha",
        fighter_b_id="beta",
        reference_date="2021-01-01",
        weight_class="Lightweight",
        draws=1000,
    )
    result = analyze(d, context, ScenarioConfig(), manual_p0=0.6)
    encoded = export_json(result)
    decoded = json.loads(encoded, parse_constant=lambda v: (_ for _ in ()).throw(ValueError(v)))
    assert decoded["mode"].startswith("Scenario-only")
    assert decoded["profiles"]["a"]["td_accuracy"] is None
    assert "utilities" not in decoded["simulation"]
    assert len(decoded["tree"]) == 18 and len(decoded["two_way"]) == 625
    report = html_report(result)
    assert '<html lang="en">' in report and "plotly.js" in report
    assert (
        "cdn.plot.ly" not in report.split("<script src=")[-1] if "<script src=" in report else True
    )
    bundle = zipfile.ZipFile(io.BytesIO(export_bundle(result)))
    assert {
        "report.html",
        "analysis.json",
        "policy_results.csv",
        "decision_tree.csv",
        "one_way.csv",
        "two_way.csv",
        "convergence.csv",
    } <= set(bundle.namelist())


def test_nonfinite_numbers_and_csv_formula_injection():
    assert clean({"a": np.nan, "b": np.float64(np.inf)}) == {"a": None, "b": None}
    payload = safe_csv(pd.DataFrame({"name": ["=cmd()", " +SUM(1)", "Normal"]})).decode("utf-8-sig")
    assert "'=cmd()" in payload and "' +SUM(1)" in payload
