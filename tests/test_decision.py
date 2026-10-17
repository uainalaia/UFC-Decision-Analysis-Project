import numpy as np
import pytest
from pydantic import ValidationError

from mma_decision_lab.decision import POLICIES, decision_tree, expected_utilities
from mma_decision_lab.schemas import AnalysisContext, ScenarioConfig, TacticalPolicy
from mma_decision_lab.sensitivity import one_way, recommendation, two_way
from mma_decision_lab.simulation import simulate


@pytest.mark.parametrize("p0", [0.01, 0.2, 0.5, 0.9, 0.99])
def test_neutral_effect_invariant_and_hand_calculated_tree(p0):
    config = ScenarioConfig()
    np.testing.assert_allclose(expected_utilities(p0, config), p0, atol=1e-15)
    tree = decision_tree(p0, config)
    np.testing.assert_allclose(tree.groupby("policy").joint_probability.sum(), 1)
    np.testing.assert_allclose(tree.groupby("policy").utility_contribution.sum(), p0)
    assert len(tree) == 18


def test_invalid_assumptions_and_policies_rejected():
    for values in (
        {"response_weights": (0.2, 0.2, 0.2)},
        {"resistance": 1.1},
        {"striking_effect": 1.5, "effect_half_width": 0.2},
        {"response_weights": (0, 0.5, 0.5), "response_concentration": 30},
    ):
        with pytest.raises(ValidationError):
            ScenarioConfig(**values)
    with pytest.raises(ValidationError):
        TacticalPolicy(
            policy_id="bad", name="bad", description="Synthetic", allocation=(0.7, 0.2, 0.2)
        )
    with pytest.raises(ValidationError):
        AnalysisContext(
            fighter_a_id="a",
            fighter_b_id="a",
            reference_date="2020-01-01",
            weight_class="Lightweight",
        )


def test_identical_policies_share_draws_and_tie_mass():
    policy = POLICIES[0]
    config = ScenarioConfig(striking_effect=0.4, effect_half_width=0.2, response_concentration=30)
    result = simulate(0.6, [0.55, 0.6, 0.65], config, policies=(policy, policy, policy), seed=3)
    np.testing.assert_array_equal(result["utilities"][:, 0], result["utilities"][:, 1])
    np.testing.assert_allclose(result["summary"].rank_first_share, 1 / 3)


def test_seed_reproducibility_bounds_and_analytic_integration():
    c = ScenarioConfig(striking_effect=0.4, grappling_effect=0.3, resistance=0.4)
    a = simulate(0.6, [0.6], c, seed=422)
    b = simulate(0.6, [0.6], c, seed=422)
    np.testing.assert_array_equal(a["utilities"], b["utilities"])
    np.testing.assert_allclose(
        a["summary"].expected_utility, expected_utilities(0.6, c), atol=1e-12
    )
    assert np.isfinite(a["utilities"]).all() and ((a["utilities"] > 0) & (a["utilities"] < 1)).all()


def test_monte_carlo_converges_and_distinguishes_uncertainties():
    c = ScenarioConfig()
    samples = np.linspace(0.2, 0.8, 101)
    small = simulate(0.5, samples, c, draws=1000, seed=9)
    large = simulate(0.5, samples, c, draws=100000, seed=9)
    assert (
        large["summary"].mc_standard_error.iloc[0] < small["summary"].mc_standard_error.iloc[0] / 8
    )
    assert abs(large["summary"].expected_utility.iloc[0] - 0.5) < 0.003
    np.testing.assert_allclose(large["summary"].scenario_assumption_sd, 0, atol=1e-12)
    assert large["summary"].empirical_parameter_sd.iloc[0] > 0.1


@pytest.mark.parametrize("samples", [[], [np.nan], [1.0], [-0.1]])
def test_invalid_mc_inputs(samples):
    with pytest.raises(ValueError):
        simulate(0.5, samples, ScenarioConfig())


def test_one_way_matches_direct_values_and_preserves_config():
    c = ScenarioConfig(striking_effect=0.2, resistance=0.25)
    frame, _ = one_way(0.6, c, "grappling_effect", -1, 1, 31)
    for row in frame.itertuples(index=False, name=None):
        np.testing.assert_allclose(
            row[1:], expected_utilities(0.6, c.changed(grappling_effect=row[0]))
        )
    assert c.grappling_effect == 0


def test_switching_root_known_from_hand_equation():
    # At R=0 all response offsets have no effect because weights=(1,0,0).
    # Delta=(standing-.5)*s+(pressure-.5)*g; the ranking reverses at g=s=.4.
    c = ScenarioConfig(striking_effect=0.4, resistance=0, response_weights=(1, 0, 0))
    _, roots = one_way(0.5, c, "grappling_effect", -1, 1, 60)
    assert len(roots) == 1 and abs(roots[0]["value"] - 0.4) < 1e-8


def test_no_fabricated_threshold_and_near_ties():
    c = ScenarioConfig()
    _, roots = one_way(0.5, c, "resistance", 0, 1)
    assert roots == []
    grid = two_way(0.5, c, "resistance", (0, 1), "counter_cost", (0, 0.001), steps=11)
    assert len(grid) == 121 and grid.region.eq(3).all()
    simulation = simulate(0.5, [0.5], c)
    assert not recommendation(simulation, grid, True)["robust"]


def test_invalid_sensitivity_ranges():
    with pytest.raises(ValueError):
        one_way(0.5, ScenarioConfig(), "resistance", 1, 0)
    with pytest.raises(ValueError):
        two_way(0.5, ScenarioConfig(), "resistance", (0, 1), "resistance", (0, 1))
