"""Research-record semantics and offline export invariants."""

import io
import json
import re
import zipfile
from copy import deepcopy

import pandas as pd
import pytest

from mma_decision_lab.analysis import analyze
from mma_decision_lab.reporting import export_bundle, export_json, html_report
from mma_decision_lab.schemas import AnalysisContext, ScenarioConfig


@pytest.fixture
def assumed_record(synthetic_dataset):
    context = AnalysisContext(
        fighter_a_id="alpha",
        fighter_b_id="beta",
        reference_date="2021-01-01",
        weight_class="Lightweight",
        draws=1000,
        seed=422,
    )
    result = analyze(synthetic_dataset, context, ScenarioConfig(), manual_p0=0.6)
    result["analysis_created_at"] = "2026-10-16T09:45:00-05:00"
    result["analysis_id"] = "fixed-test-analysis-identity"
    return result


def test_assumed_neutral_record_has_faithful_labels_and_unchanged_values(assumed_record):
    result = assumed_record
    before = deepcopy(result["simulation"]["summary"])
    report = html_report(result)
    assert "There is no unique highest-mean alternative" in report
    assert "Fixed user assumption; no empirical baseline interval" in report
    assert "Conditional bootstrap parameter interval:" not in report
    assert "No observations" in report
    assert "1,000 integration draws · Seed 422" in report
    assert "Default sensitivity and robustness" in report
    assert "are not substituted into this report" in report
    pd.testing.assert_frame_equal(before, result["simulation"]["summary"])
    decoded = json.loads(export_json(result))
    assert [row["expected_utility"] for row in decoded["simulation"]["summary"]] == pytest.approx(
        [0.6, 0.6, 0.6], abs=1e-12
    )
    assert [row["rank_first_share"] for row in decoded["simulation"]["summary"]] == pytest.approx(
        [1 / 3, 1 / 3, 1 / 3], abs=1e-12
    )


def test_record_timestamp_identity_and_metadata_align_across_exports(assumed_record):
    result = assumed_record
    report = html_report(result)
    bundle = zipfile.ZipFile(io.BytesIO(export_bundle(result)))
    zipped_report = bundle.read("report.html").decode()
    decoded = json.loads(bundle.read("analysis.json"))
    for html in (report, zipped_report):
        assert "Analysis created 2026-10-16T09:45:00-05:00" in html
        assert "Analysis identity: fixed-test-analysis-identity" in html
    assert decoded["analysis_created_at"] == result["analysis_created_at"]
    assert decoded["analysis_id"] == result["analysis_id"]
    assert decoded["context"] == result["context"]
    assert decoded["scenario"] == result["scenario"]
    expected_csv = pd.read_csv(io.BytesIO(bundle.read("policy_results.csv")))
    pd.testing.assert_frame_equal(expected_csv, result["simulation"]["summary"], check_exact=False)
    legacy = result.copy()
    legacy.pop("analysis_created_at")
    legacy.pop("analysis_id")
    assert "Analysis created Not recorded (legacy analysis)" in html_report(legacy)


def test_html_embeds_resources_and_escapes_matchup_content(assumed_record):
    result = assumed_record
    result["names"] = ["A <img src=x onerror=alert(1)>", "An unusually long opponent name"]
    report = html_report(result)
    assert "<img src=x onerror=alert(1)>" not in report
    assert "A &lt;img src=x onerror=alert(1)&gt;" in report
    assert "An unusually long opponent name" in report
    assert "data:font/woff2;base64," in report
    assert not re.search(r"<script[^>]+src=", report, flags=re.IGNORECASE)
    assert not re.search(r"url\(['\"]?https?://", report, flags=re.IGNORECASE)
    assert "@page{size:A4" in report
    assert "filter:grayscale(1)" in report
