"""Presentation contracts: unchanged evidence, visible references and honest ties."""

import numpy as np
import pandas as pd

from mma_decision_lab.charts import (
    calibration_chart,
    convergence_chart,
    decision_regions,
    distributions,
    fighter_rates,
    sensitivity_lines,
    tornado_chart,
    utility_intervals,
)
from mma_decision_lab.decision import POLICIES
from mma_decision_lab.schemas import ScenarioConfig
from mma_decision_lab.sensitivity import two_way


def test_utility_chart_keeps_means_bands_and_exposes_baseline():
    summary = pd.DataFrame(
        {
            "policy": [p.name for p in POLICIES],
            "expected_utility": [0.51, 0.52, 0.53],
            "lower_95": [0.49, 0.50, 0.51],
            "upper_95": [0.54, 0.55, 0.56],
        }
    )
    fig = utility_intervals(summary, baseline=0.505)
    np.testing.assert_allclose([trace.x[0] for trace in fig.data], summary.expected_utility)
    np.testing.assert_allclose(
        [trace.x[0] - trace.error_x.arrayminus[0] for trace in fig.data], summary.lower_95
    )
    np.testing.assert_allclose(
        [trace.x[0] + trace.error_x.array[0] for trace in fig.data], summary.upper_95
    )
    assert len({trace.marker.symbol for trace in fig.data}) == 3
    assert fig.layout.shapes[0].x0 == fig.layout.shapes[0].x1 == 0.505
    assert fig.layout.xaxis.tickformat == ".1%"
    assert fig.layout.paper_bgcolor == "#FFFFFF"


def test_neutral_distribution_uses_one_faithful_histogram_only_for_actual_ties():
    values = np.linspace(0.3, 0.7, 100)
    utilities = np.column_stack([values, values, values])
    fig = distributions({"utilities": utilities})
    assert len(fig.data) == 1
    np.testing.assert_array_equal(fig.data[0].x, values)
    assert any("coincide" in a.text for a in fig.layout.annotations)
    utilities[:, 2] += 1e-8
    assert len(distributions({"utilities": utilities}).data) == 3


def test_sensitivity_current_reference_is_in_range_and_lines_remain_distinct():
    frame = pd.DataFrame(
        {"grappling_effect": [-1.0, 0.0, 1.0], **{p.name: [0.4, 0.5, 0.6] for p in POLICIES}}
    )
    fig = sensitivity_lines(frame, "grappling_effect", current=0.35)
    assert fig.layout.shapes[0].x0 == 0.35
    assert len({trace.line.dash for trace in fig.data}) == 3
    assert fig.layout.xaxis.title.text == "Grappling effect (log-odds)"
    for trace in fig.data:
        np.testing.assert_array_equal(trace.x, frame.grappling_effect)
        np.testing.assert_array_equal(trace.y, frame[trace.name])
    assert not sensitivity_lines(frame, "grappling_effect", current=2.0).layout.shapes


def test_region_codes_utilities_and_exact_current_coordinates_are_preserved():
    frame = two_way(
        0.6,
        ScenarioConfig(striking_effect=0.3),
        "grappling_effect",
        (-1, 1),
        "resistance",
        (0, 1),
        steps=5,
    )
    fig = decision_regions(frame, current={"grappling_effect": 0.37, "resistance": 0.43})
    heatmap = fig.data[0]
    np.testing.assert_array_equal(heatmap.z, frame.region.to_numpy().reshape(5, 5))
    assert set(np.asarray(heatmap.text).ravel()) <= {"S", "G", "B", "="}
    np.testing.assert_array_equal(
        np.asarray(heatmap.customdata)[:, :, :3],
        frame[[p.name for p in POLICIES]].to_numpy().reshape(5, 5, 3),
    )
    current = next(trace for trace in fig.data if trace.name == "Current scenario")
    assert list(current.x) == [0.37] and list(current.y) == [0.43]
    assert not heatmap.showscale
    assert fig.layout.legend.orientation == "h"
    assert fig.layout.legend.entrywidthmode == "fraction"
    outside = decision_regions(frame, current=(1.1, 0.43))
    assert not any(trace.name == "Current scenario" for trace in outside.data)


def test_tornado_does_not_claim_a_unique_leader():
    frame = pd.DataFrame(
        {
            "parameter": ["resistance"],
            "low_margin": [-0.02],
            "high_margin": [0.0],
            "measured_policy": [POLICIES[0].name],
            "low": [0.0],
            "high": [1.0],
        }
    )
    fig = tornado_chart(frame)
    assert "reference policy" in fig.layout.title.text.lower()
    assert "leader" not in fig.layout.title.text.lower()
    np.testing.assert_array_equal(fig.data[0].x, [-0.02, 0.0])


def test_calibration_and_convergence_keep_uncertainty_and_sample_counts():
    frame = pd.DataFrame(
        {
            "predicted": [0.3, 0.6],
            "observed": [0.25, 0.55],
            "n": [4, 20],
            "lower": [0.1, 0.35],
            "upper": [0.65, 0.75],
        }
    )
    trace = calibration_chart(frame).data[0]
    np.testing.assert_array_equal(trace.customdata, frame.n)
    np.testing.assert_allclose(
        np.asarray(trace.y) - np.asarray(trace.error_y.arrayminus), frame.lower
    )
    np.testing.assert_allclose(np.asarray(trace.y) + np.asarray(trace.error_y.array), frame.upper)
    checkpoint = pd.DataFrame(
        [
            {"policy": p.name, "draws": n, "mean": 0.5 + i * 0.01, "mc_standard_error": 0.001}
            for n in [100, 500, 1000]
            for i, p in enumerate(POLICIES)
        ]
    )
    for curve in convergence_chart(checkpoint).data:
        expected = checkpoint[checkpoint.policy.eq(curve.name)]
        np.testing.assert_array_equal(curve.x, expected.draws)
        np.testing.assert_array_equal(curve.y, expected["mean"])
        np.testing.assert_array_equal(curve.customdata, expected.mc_standard_error)


def test_fighter_rate_charts_stack_units_and_keep_missing_evidence_visible():
    profiles = [
        {"sig_landed_pm": 4.2, "td_landed_15": 2.1, "sub_attempts_15": np.nan},
        {"sig_landed_pm": 3.3, "td_landed_15": 1.2, "sub_attempts_15": 0.0},
    ]
    fig = fighter_rates(profiles, ["Alpha", "Beta"])
    assert len(fig.data) == 6
    assert {trace.xaxis for trace in fig.data} == {"x", "x2", "x3"}
    assert fig.layout.yaxis.domain[0] > fig.layout.yaxis2.domain[1]
    assert fig.layout.yaxis2.domain[0] > fig.layout.yaxis3.domain[1]
    assert fig.data[4].x[0] is None and fig.data[5].x[0] == 0
    assert any(annotation.text == "Not observed" for annotation in fig.layout.annotations)
