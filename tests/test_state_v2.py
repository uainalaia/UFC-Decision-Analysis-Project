"""Configuration binding, atomic editing and failure/snapshot invalidation."""

from copy import deepcopy

import pytest

from app import state


@pytest.fixture
def session():
    session = {}
    state.initialize(
        session,
        {
            "fighter_a_id": "a",
            "fighter_b_id": "b",
            "reference_date": "2020-01-01",
            "weight_class": "Lightweight",
            "seed": 422,
            "draws": 5000,
            "scheduled_rounds": 5,
        },
        "snapshot-A",
    )
    return session


def test_identity_tracks_all_analytical_dimensions_and_recovers(session):
    initial = state.identity(session, "model-A")
    state.store_result(
        session, initial, {"names": ["A", "B"], "context": deepcopy(session["applied_context"])}
    )
    for section, key, value in [
        ("applied_context", "fighter_a_id", "other"),
        ("applied_context", "fighter_b_id", "other"),
        ("applied_context", "reference_date", "2020-02-01"),
        ("applied_context", "weight_class", "Welterweight"),
        ("applied_context", "seed", 1234),
        ("applied_context", "draws", 1000),
        ("applied_context", "scheduled_rounds", 3),
        ("applied_scenario", "striking_effect", 0.2),
        ("applied_scenario", "effect_half_width", 0.1),
        ("applied_scenario", "response_weights", [0.2, 0.5, 0.3]),
        ("applied_scenario", "response_concentration", 30.0),
    ]:
        changed = deepcopy(session)
        changed[section][key] = value
        identity = state.identity(changed, "model-A")
        assert identity != initial
        assert state.result_state(changed, identity) == "stale"
        assert state.current_result(changed, identity) is None
    assert state.identity(session, "model-B") != initial
    session["visual_choice"] = "some presentation preference"
    session["manual_probability"] = 0.8  # irrelevant while using the historical model
    assert state.identity(session, "model-A") == initial
    assert state.result_state(session, initial) == "current"
    session["baseline_source"] = "Scenario-only"
    assumed = state.identity(session, "assumed")
    session["manual_probability"] = 0.7
    assert state.identity(session, "assumed") != assumed


def test_invalid_draft_cannot_overwrite_valid_configuration(session):
    before = deepcopy(session["applied_scenario"])
    state.begin_scenario_edit(session)
    session["scenario_draft"]["response_weights"] = [0.8, 0.5, 0.25]
    with pytest.raises(ValueError):
        state.apply_scenario(session)
    assert session["applied_scenario"] == before
    state.cancel_scenario(session)
    assert not state.draft_dirty(session)
    session["scenario_draft"]["striking_effect"] = 1.4
    session["scenario_draft"]["effect_half_width"] = 0.2
    with pytest.raises(ValueError):
        state.apply_scenario(session)
    assert session["applied_scenario"] == before


def test_failed_current_run_and_snapshot_clear_bindings(session):
    identity = state.identity(session, "model-A")
    record = {"names": ["A", "B"], "context": deepcopy(session["applied_context"])}
    state.store_result(session, identity, record)
    record["names"][0] = "Changed external object"
    assert state.current_result(session, identity)["names"] == ["A", "B"]
    session["run_error"] = "Failed retry"
    assert state.result_state(session, identity) == "failed"
    assert state.current_result(session, identity) is None
    assert session["analysis_records"][identity]["names"] == ["A", "B"]
    session.update(
        generated_report={"signature": identity},
        prepared_models={"old": "model"},
        sensitivity_exploration={"old": "grid"},
        calculation_seed=1234,
        edit_matchup_date="2020-01-01",
    )
    state.replace_snapshot(session, "snapshot-B", session["applied_context"])
    assert not session["analysis_records"] and session["generated_report"] is None
    assert not session["prepared_models"] and "sensitivity_exploration" not in session
    assert "calculation_seed" not in session and "edit_matchup_date" not in session
    assert state.result_state(session, state.identity(session, "model-A")) == "empty"


def test_two_equal_highest_means_are_communicated_as_shared():
    import numpy as np
    import pandas as pd

    from mma_decision_lab.sensitivity import recommendation

    policies = ["Striking priority", "Grappling priority", "Balanced priority"]
    simulation = {
        "summary": pd.DataFrame({"policy": policies, "expected_utility": [0.6, 0.6, 0.5]}),
        "utilities": np.tile([0.6, 0.6, 0.5], (100, 1)),
    }
    result = recommendation(simulation, pd.DataFrame({"region": [3, 3]}), False)
    assert result["mean_leaders"] == policies[:2]
    assert "shared by Striking priority, Grappling priority" in result["explanation"]
    assert result["robust"] is False
