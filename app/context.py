"""Bind every native-navigation rerun to one complete applied environment."""

import hashlib
import json

import streamlit as st

from app import resources, state
from mma_decision_lab.config import ROOT
from mma_decision_lab.features import build_fighter_profile, long_history, matchup_features
from mma_decision_lab.schemas import AnalysisContext, ScenarioConfig


def refresh():
    manifest_path = ROOT / "data/manifests/snapshot.json"
    frozen_token = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    dataset = st.session_state.get("uploaded_dataset")
    if dataset is None:
        dataset = resources.frozen_dataset(frozen_token)
    token = resources.snapshot_token(dataset)
    state.initialize(st.session_state, resources.default_context(dataset), token)
    context = AnalysisContext(**st.session_state["applied_context"])
    config = ScenarioConfig(**st.session_state["applied_scenario"])

    # Reuse the immutable joined history without retraining or simulating on navigation.
    @st.cache_data(show_spinner=False)
    def joined_history(_dataset, token):
        return long_history(_dataset)

    history = joined_history(dataset, token)
    profiles = [
        build_fighter_profile(dataset, fid, context.reference_date, history)
        for fid in (context.fighter_a_id, context.fighter_b_id)
    ]
    names = (
        dataset.fighters.set_index("fighter_id")
        .fighter_name.loc[[context.fighter_a_id, context.fighter_b_id]]
        .tolist()
    )
    source = st.session_state["baseline_source"]
    eligible = all(
        p["sufficient_history"] and p["last_division"] == context.weight_class for p in profiles
    )
    model, error = None, None
    model_id = "user-assumed-v1"
    p0 = st.session_state["manual_probability"] if source == "Scenario-only" else None
    if source == "Historical model":
        model = st.session_state.get("prepared_models", {}).get(
            (token, str(context.reference_date))
        )
        saved = ROOT / "models/baseline.json"
        if model is None and "uploaded_dataset" not in st.session_state and saved.exists():
            metadata = json.loads(saved.read_text(encoding="utf-8"))
            if metadata["evaluation"]["reference_date"] == str(context.reference_date):
                model_hash = hashlib.sha256(saved.read_bytes()).hexdigest()
                model = resources.existing_baseline(model_hash)
                model_id = model_hash
        if model is not None and model_id == "user-assumed-v1":
            model_id = resources.numeric_model_identity(model)
        if not eligible:
            error = "Historical forecast unavailable: each fighter needs at least two retained earlier bouts in total and a matching last recorded division. Change the matchup or select Scenario-only."
        elif model is None:
            error = "No baseline is prepared for this snapshot and cutoff. Prepare it explicitly in Outcome analysis, or select Scenario-only."
            model_id = "unprepared:" + token + str(context.reference_date)
        else:
            p0 = model.predict(matchup_features(*profiles))
    signature = state.identity(st.session_state, model_id)
    environment = dict(
        dataset=dataset,
        frozen_token=frozen_token,
        token=token,
        context=context,
        config=config,
        source=source,
        model=model,
        model_id=model_id,
        p0=p0,
        eligible=eligible,
        error=error,
        names=names,
        profiles=profiles,
        signature=signature,
        result=state.current_result(st.session_state, signature),
    )

    st.session_state["_environment"] = environment
    return environment
