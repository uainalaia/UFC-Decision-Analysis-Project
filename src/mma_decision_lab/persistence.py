"""Portable JSON numeric model persistence; no pickle deserialization."""

import json
from pathlib import Path

import numpy as np
from scipy.special import expit

from .features import FEATURES


class NumericLogistic:
    def __init__(self, coefficients, scales):
        self.coefficients = np.asarray(coefficients, dtype=float)
        self.scales = np.asarray(scales, dtype=float)
        if self.coefficients.shape != (len(FEATURES),) or self.scales.shape != (len(FEATURES),):
            raise ValueError("Persisted model dimension mismatch")
        if (
            not np.isfinite(self.coefficients).all()
            or not np.isfinite(self.scales).all()
            or (self.scales <= 0).any()
        ):
            raise ValueError("Invalid numeric model parameters")

    def predict_proba(self, x):
        x = np.asarray(x, dtype=float)
        p = expit(np.nan_to_num(x, nan=0) / self.scales @ self.coefficients)
        return np.column_stack([1 - p, p])


def save_numeric_model(baseline, path: Path):
    def encode(model):
        return {"coefficients": model[-1].coef_[0].tolist(), "scales": model[-2].scale_.tolist()}

    payload = {
        "features": FEATURES,
        "model": encode(baseline.model),
        "bootstraps": [encode(m) for m in baseline.bootstraps],
        "evaluation": baseline.evaluation,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_numeric_model(path: Path):
    if path.stat().st_size > 10_000_000:
        raise ValueError("Numeric model file exceeds size limit")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload["features"] != FEATURES:
        raise ValueError("Persisted feature order mismatch")
    return NumericLogistic(**payload["model"]), [
        NumericLogistic(**m) for m in payload["bootstraps"]
    ]
