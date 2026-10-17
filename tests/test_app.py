import copy
from unittest.mock import patch

import numpy as np
import pytest
from streamlit.testing.v1 import AppTest

from mma_decision_lab.config import ROOT

pytestmark = pytest.mark.skipif(
    not (ROOT / "data/raw/ufc_fight_results.csv").exists(),
    reason="Requires documented local snapshot",
)


def boot():
    app = AppTest.from_file(str(ROOT / "app/main.py"), default_timeout=90).run()
    assert not app.exception
    return app


def page(app, name):
    app.switch_page("screens/" + name + ".py").run()
    assert not app.exception
    return app


def button(app, label):
    return next(b for b in app.button if b.label == label)


@pytest.mark.parametrize("view", ["sensitivity", "outcome_analysis", "research_report"])
def test_cold_deep_link_initializes_shell_context_and_actions(view):
    app = AppTest.from_file(str(ROOT / "app/main.py"), default_timeout=90)
    app.switch_page("screens/" + view + ".py").run()
    assert not app.exception
    assert app.session_state["applied_context"]["reference_date"] == "2018-10-06"
    assert len(app.session_state["_pages"]) == 8


def test_unavailable_research_resources_have_a_recovery_state():
    with patch("app.resources.frozen_dataset", side_effect=ValueError("Snapshot hash mismatch")):
        app = AppTest.from_file(str(ROOT / "app/main.py"), default_timeout=90).run()
    assert not app.exception
    assert app.title[0].value == "Research resources unavailable"
    assert any("could not be loaded" in error.value for error in app.error)
    assert not any(b.label == "Run analysis" for b in app.button)


def test_complete_historical_app_workflow():
    app = boot()
    context = copy.deepcopy(app.session_state["applied_context"])
    assert context["reference_date"] == "2018-10-06"
    page(app, "fighter_evidence")
    assert len(app.dataframe) >= 2
    page(app, "tactical_model")
    button(app, "Use illustrative assumptions").click().run()
    assert app.session_state["scenario_draft"]["grappling_effect"] == 0.5
    assert app.session_state["applied_scenario"]["grappling_effect"] == 0
    # Navigation must preserve explicit draft, despite native widget cleanup.
    page(app, "fighter_evidence")
    page(app, "tactical_model")
    assert app.number_input(key="edit_scenario_grappling_effect").value == 0.5
    button(app, "Apply assumptions").click().run()
    assert not app.exception
    assert app.session_state["applied_scenario"]["striking_effect"] == 0.35
    page(app, "outcome_analysis")
    button(app, "Run analysis").click().run()
    assert not app.exception
    signature = app.session_state["_environment"]["signature"]
    record = copy.deepcopy(app.session_state["analysis_records"][signature])
    assert record["analysis_id"] == signature
    assert len(record["tree"]) == 18
    for view in ["sensitivity", "validation", "methodology", "research_report", "fight_brief"]:
        page(app, view)
        assert app.session_state["applied_context"] == context
        assert app.session_state["_environment"]["signature"] == signature
    page(app, "sensitivity")
    button(app, "Apply one-way range").click().run()
    button(app, "Apply decision-region ranges").click().run()
    assert not app.exception
    assert len(app.session_state["sensitivity_exploration"]["two"]["frame"]) == 625
    page(app, "research_report")
    button(app, "Generate research report").click().run()
    assert not app.exception
    assert len(app.get("download_button")) == 4
    generated = app.session_state["generated_report"]
    assert generated["signature"] == signature
    assert record["analysis_created_at"] in generated["html"]
    assert np.array_equal(
        record["simulation"]["utilities"],
        app.session_state["analysis_records"][signature]["simulation"]["utilities"],
    )


def test_stale_failed_recovered_and_invalid_edits():
    app = boot()
    page(app, "outcome_analysis")
    button(app, "Run analysis").click().run()
    original_signature = app.session_state["_environment"]["signature"]
    original = app.session_state["analysis_records"][original_signature]
    means = original["simulation"]["summary"].expected_utility.to_numpy()
    assert np.ptp(means) == 0
    assert np.allclose(original["simulation"]["summary"].rank_first_share, 1 / 3)
    assert original["recommendation"]["robust"] is False
    app.number_input(key="calculation_seed").set_value(1234).run()
    assert any("previous analysis" in w.value for w in app.warning)
    assert app.session_state["_environment"]["result"] is None
    with patch("app.ui.analyze", side_effect=RuntimeError("test integration failure")):
        button(app, "Run analysis").click().run()
    assert any("test integration failure" in err.value for err in app.error)
    assert app.session_state["last_record_id"] == original_signature
    app.number_input(key="calculation_seed").set_value(422).run()
    assert app.session_state["_environment"]["result"] is not None
    assert not app.error
    page(app, "tactical_model")
    valid = copy.deepcopy(app.session_state["applied_scenario"])
    app.number_input(key="edit_scenario_weight_0").set_value(0.9).run()
    button(app, "Apply assumptions").click().run()
    assert app.error and app.session_state["applied_scenario"] == valid
    button(app, "Cancel assumption edits").click().run()
    assert not app.exception
    assert app.session_state["scenario_draft"] == valid


def test_matchup_apply_cancel_and_unsupported_context():
    app = boot()
    context = copy.deepcopy(app.session_state["applied_context"])
    button(app, "Change matchup").click().run()
    app.selectbox(key="edit_matchup_mode").set_value("Custom matchup").run()
    app.date_input(key="edit_matchup_date").set_value("1999-07-16").run()
    page(app, "fighter_evidence")
    assert app.session_state["matchup_draft"]["reference_date"].isoformat() == "1999-07-16"
    button(app, "Cancel matchup edits").click().run()
    assert app.session_state["applied_context"] == context
    button(app, "Change matchup").click().run()
    app.selectbox(key="edit_matchup_mode").set_value("Custom matchup").run()
    app.date_input(key="edit_matchup_date").set_value("1999-07-16").run()
    button(app, "Apply matchup").click().run()
    page(app, "outcome_analysis")
    assert not app.exception
    assert button(app, "Run analysis").disabled
    assert any("two retained earlier bouts" in w.value for w in app.warning)
