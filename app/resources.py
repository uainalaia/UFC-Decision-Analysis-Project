"""Immutable snapshot resources and explicit model preparation."""

import hashlib
import json

import pandas as pd
import streamlit as st

from mma_decision_lab.config import ROOT
from mma_decision_lab.data import load_dataset
from mma_decision_lab.features import build_feature_table
from mma_decision_lab.forecasting import Baseline, train_baseline
from mma_decision_lab.persistence import load_numeric_model


@st.cache_resource(show_spinner="Checking the frozen research snapshot…")
def frozen_dataset(token):
    return load_dataset()


@st.cache_data(show_spinner=False)
def historical_features(_dataset, token):
    return build_feature_table(_dataset)


@st.cache_resource(show_spinner=False)
def existing_baseline(model_hash):
    path = ROOT / "models/baseline.json"
    model, bootstraps = load_numeric_model(path)
    metadata = json.loads(path.read_text(encoding="utf-8"))
    calibration = pd.read_csv(ROOT / "reports/generated/calibration.csv")
    partitions = pd.read_csv(ROOT / "reports/generated/partitions.csv", parse_dates=["event_date"])
    return Baseline(
        model, bootstraps, metadata["evaluation"], calibration, partitions, metadata["features"]
    )


@st.cache_resource(show_spinner=False, max_entries=6)
def prepare_baseline(_dataset, token, cutoff):
    return train_baseline(historical_features(_dataset, token), cutoff)


def default_context(dataset):
    names = dataset.fighters.set_index("fighter_id").fighter_name.to_dict()
    eligible = dataset.fights
    first = next((fid for fid, name in names.items() if name == "Khabib Nurmagomedov"), None)
    second = next((fid for fid, name in names.items() if name == "Conor McGregor"), None)
    matches = eligible[
        (eligible.fighter_a_id.isin([first, second]))
        & (eligible.fighter_b_id.isin([first, second]))
    ]
    row = matches.iloc[0] if len(matches) else eligible.iloc[-1]
    return {
        "fighter_a_id": first if len(matches) else row.fighter_a_id,
        "fighter_b_id": second if len(matches) else row.fighter_b_id,
        "reference_date": str(row.event_date.date()),
        "weight_class": row.weight_class,
        "scheduled_rounds": int(row.scheduled_rounds),
        "draws": 5000,
        "seed": 422,
    }


def snapshot_token(dataset):
    payload = {
        "version": dataset.manifest["dataset_version"],
        "files": dataset.manifest.get("files", []),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def numeric_model_identity(baseline):
    """Bind prepared results to every actual numeric coefficient and bootstrap scale."""

    def parameters(model):
        if hasattr(model, "coefficients"):
            return {"coefficients": model.coefficients.tolist(), "scales": model.scales.tolist()}
        return {"coefficients": model[-1].coef_[0].tolist(), "scales": model[-2].scale_.tolist()}

    payload = {
        "model": parameters(baseline.model),
        "bootstraps": [parameters(model) for model in baseline.bootstraps],
        "evaluation": baseline.evaluation,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, allow_nan=False).encode()).hexdigest()
