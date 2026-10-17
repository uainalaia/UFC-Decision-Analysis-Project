"""Explicit applied/draft/result state; independent of Streamlit widget lifetimes."""

import copy
import hashlib
import json

from mma_decision_lab.schemas import AnalysisContext, ScenarioConfig


def initialize(state, context, snapshot):
    if "applied_context" not in state:
        state["applied_context"] = AnalysisContext(**context).model_dump(mode="json")
        state["applied_scenario"] = ScenarioConfig().model_dump(mode="json")
        state["baseline_source"] = "Historical model"
        state["manual_probability"] = 0.5
        state["snapshot_token"] = snapshot
        state["analysis_records"] = {}
        state["last_record_id"] = None
        state["run_error"] = None
        state["running"] = False
        state["generated_report"] = None


def identity(state, model_identity):
    payload = {
        "context": state["applied_context"],
        "scenario": state["applied_scenario"],
        "snapshot": state["snapshot_token"],
        "baseline_source": state["baseline_source"],
        "manual_probability": state["manual_probability"]
        if state["baseline_source"] != "Historical model"
        else None,
        "model_identity": model_identity,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, allow_nan=False).encode()).hexdigest()


def apply_matchup(state, context, source, probability):
    validated = AnalysisContext(**context).model_dump(mode="json")
    if source not in ("Historical model", "Scenario-only") or not 0.01 <= probability <= 0.99:
        raise ValueError(
            "Choose a valid baseline source and an assumed probability from 1% to 99%."
        )
    state["applied_context"] = validated
    state["baseline_source"] = source
    state["manual_probability"] = probability
    state["run_error"] = None


def begin_scenario_edit(state):
    state.setdefault("scenario_draft", copy.deepcopy(state["applied_scenario"]))


def apply_scenario(state):
    validated = ScenarioConfig(**state["scenario_draft"]).model_dump(mode="json")
    state["applied_scenario"] = validated
    state["scenario_draft"] = copy.deepcopy(validated)
    state["run_error"] = None


def cancel_scenario(state):
    state["scenario_draft"] = copy.deepcopy(state["applied_scenario"])


def draft_dirty(state):
    return state.get("scenario_draft", state["applied_scenario"]) != state["applied_scenario"]


def result_state(state, signature):
    if state.get("running"):
        return "running"
    if state.get("run_error"):
        return "failed"
    if signature in state.get("analysis_records", {}):
        return "current"
    return "stale" if state.get("last_record_id") else "empty"


def current_result(state, signature):
    if state.get("run_error") or state.get("running"):
        return None
    return state.get("analysis_records", {}).get(signature)


def store_result(state, signature, result):
    result = copy.deepcopy(result)
    result["input_identity"] = signature
    result["analysis_id"] = signature
    records = dict(state.get("analysis_records", {}))
    records[signature] = result
    # Bounded session cache; returning to any of the four recent exact configurations recovers it.
    while len(records) > 4:
        del records[next(iter(records))]
    state["analysis_records"] = records
    state["last_record_id"] = signature
    state["run_error"] = None
    state["running"] = False


def replace_snapshot(state, token, default_context):
    state["snapshot_token"] = token
    state["applied_context"] = AnalysisContext(**default_context).model_dump(mode="json")
    state["analysis_records"] = {}
    state["last_record_id"] = None
    state["generated_report"] = None
    state["run_error"] = None
    state["prepared_models"] = {}
    state.pop("sensitivity_exploration", None)
    state.pop("matchup_draft", None)
    state["matchup_edit_open"] = False
    for key in list(state):
        if key.startswith(("edit_matchup_", "calculation_")):
            state.pop(key, None)
