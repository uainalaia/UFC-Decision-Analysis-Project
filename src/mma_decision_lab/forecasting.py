"""Symmetric logistic baseline with chronological selection and untouched testing."""

import logging
from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, brier_score_loss, log_loss, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .config import SEED, VERSION
from .features import FEATURES

logger = logging.getLogger(__name__)


def pipeline(c):
    # Mirroring makes training medians zero; no centering/intercept preserves p(x)=1-p(-x).
    return make_pipeline(
        SimpleImputer(strategy="constant", fill_value=0, keep_empty_features=True),
        StandardScaler(with_mean=False),
        LogisticRegression(C=c, fit_intercept=False, max_iter=2000, random_state=SEED),
    )


def fit_symmetric(model, x, y):
    return model.fit(np.vstack([x, -x]), np.concatenate([y, 1 - y]))


def scores(y, p) -> dict:
    p = np.clip(p, 1e-8, 1 - 1e-8)
    return {
        "brier": float(brier_score_loss(y, p)),
        "log_loss": float(log_loss(y, p, labels=[0, 1])),
        "accuracy": float(accuracy_score(y, p >= 0.5)),
        "auc": float(roc_auc_score(y, p)) if len(np.unique(y)) == 2 else None,
    }


def calibration_table(y, p, bins=8):
    frame = pd.DataFrame({"observed": y, "predicted": p})
    frame["bin"] = pd.cut(frame.predicted, bins=np.linspace(0, 1, bins + 1), include_lowest=True)
    result = (
        frame.groupby("bin", observed=True)
        .agg(predicted=("predicted", "mean"), observed=("observed", "mean"), n=("observed", "size"))
        .reset_index(drop=True)
    )
    # Wilson 95% intervals for observed proportions, one independent unit per bout.
    z = 1.96
    center = (result.observed + z * z / (2 * result.n)) / (1 + z * z / result.n)
    half = (
        z
        * np.sqrt(result.observed * (1 - result.observed) / result.n + z * z / (4 * result.n**2))
        / (1 + z * z / result.n)
    )
    result["lower"], result["upper"] = center - half, center + half
    return result


@dataclass
class Baseline:
    model: object
    bootstraps: list
    evaluation: dict
    calibration: pd.DataFrame
    partitions: pd.DataFrame
    features: list[str]

    def predict(self, x):
        return float(self.model.predict_proba(np.asarray(x).reshape(1, -1))[0, 1])

    def predict_draws(self, x):
        return np.array(
            [m.predict_proba(np.asarray(x).reshape(1, -1))[0, 1] for m in self.bootstraps]
        )


def train_baseline(table: pd.DataFrame, as_of_date, bootstrap_count=64, seed=SEED) -> Baseline:
    eligible = (
        table[table.eligible & (table.event_date < pd.Timestamp(as_of_date).normalize())]
        .sort_values(["event_date", "fight_id"])
        .copy()
    )
    dates = eligible.event_date.drop_duplicates().to_numpy()
    if len(eligible) < 180 or len(dates) < 30:
        raise ValueError(
            "At least 180 eligible earlier bouts on 30 dates are needed for temporal evaluation. Use scenario-only mode."
        )
    validation_start, test_start = dates[int(len(dates) * 0.65)], dates[int(len(dates) * 0.82)]
    eligible["partition"] = np.where(
        eligible.event_date < validation_start,
        "train",
        np.where(eligible.event_date < test_start, "validation", "test"),
    )
    blocks = {name: g for name, g in eligible.groupby("partition")}
    if min(map(len, blocks.values())) < 25:
        raise ValueError("Insufficient chronological partition sizes")
    xtrain, ytrain = blocks["train"][FEATURES].to_numpy(), blocks["train"].target.to_numpy()
    xval, yval = blocks["validation"][FEATURES].to_numpy(), blocks["validation"].target.to_numpy()
    selection = []
    for c in (0.1, 1.0, 10.0):
        fitted = fit_symmetric(pipeline(c), xtrain, ytrain)
        selection.append({"C": c, **scores(yval, fitted.predict_proba(xval)[:, 1])})
    best = min(selection, key=lambda s: s["log_loss"])["C"]
    dev = eligible[eligible.partition != "test"]
    xdev, ydev = dev[FEATURES].to_numpy(), dev.target.to_numpy()
    fitted = fit_symmetric(pipeline(best), xdev, ydev)
    test = blocks["test"]
    xtest, ytest = test[FEATURES].to_numpy(), test.target.to_numpy()
    ptest = fitted.predict_proba(xtest)[:, 1]
    naive = scores(ytest, np.full(len(ytest), 0.5))
    # Interpretable reference using only historical smoothed win-rate difference.
    win_index = FEATURES.index("diff_win_rate")
    reference = fit_symmetric(pipeline(1), xdev[:, [win_index]], ydev)
    reference_scores = scores(ytest, reference.predict_proba(xtest[:, [win_index]])[:, 1])
    empirical = scores(ytest, ptest)
    rng = np.random.default_rng(seed)
    differences = (ptest - ytest) ** 2 - (0.5 - ytest) ** 2
    boot_difference = np.array(
        [rng.choice(differences, len(differences), replace=True).mean() for _ in range(1000)]
    )
    interval = np.quantile(boot_difference, [0.025, 0.975]).tolist()
    # Conservative evidence gate: clear Brier advantage over 0.5 is required.
    supported = interval[1] < 0 and empirical["log_loss"] < naive["log_loss"]
    bootstraps = []
    for _ in range(bootstrap_count):
        sample = rng.integers(0, len(dev), len(dev))
        bootstraps.append(fit_symmetric(pipeline(best), xdev[sample], ydev[sample]))
    evaluation = {
        "model_version": VERSION,
        "feature_names": FEATURES,
        "reference_date": str(pd.Timestamp(as_of_date).date()),
        "selected_C": best,
        "selection": selection,
        "test": empirical,
        "coin_reference": naive,
        "winrate_reference": reference_scores,
        "brier_difference_vs_coin_95_interval": interval,
        "status": "Held-out evidence supports the baseline against the 0.5 reference; calibration remains descriptive."
        if supported
        else "Exploratory baseline: held-out evidence is insufficient against the 0.5 reference.",
        "supported": bool(supported),
        "bootstrap_models": bootstrap_count,
        "partition_summary": {
            k: {
                "n": len(v),
                "start": str(v.event_date.min().date()),
                "end": str(v.event_date.max().date()),
            }
            for k, v in blocks.items()
        },
        "training_latest_date": str(dev.event_date.max().date()),
        "scope": "Pooled divisions and 3/5-round formats; no individualized round-length or division effect is estimated.",
        "uncertainty": "Bout bootstrap, conditional on selected C and fixed historical feature design; excludes structural uncertainty. Serial fighter dependence is not captured by iid bout resampling.",
    }
    logger.info(
        "baseline %s", {"cutoff": str(as_of_date), "test_n": len(test), "brier": empirical["brier"]}
    )
    return Baseline(
        fitted,
        bootstraps,
        evaluation,
        calibration_table(ytest, ptest),
        eligible[["fight_id", "event_date", "partition"]],
        FEATURES,
    )
