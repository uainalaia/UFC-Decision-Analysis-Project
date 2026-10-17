"""Strict earlier-date profiles; no target-fight or current-career predictors."""

import numpy as np
import pandas as pd

from .config import FEATURE_VERSION, MIN_HISTORY
from .data import Dataset

PROFILE_FEATURES = [
    "sig_landed_pm",
    "sig_absorbed_pm",
    "sig_accuracy",
    "sig_defense",
    "td_landed_15",
    "td_defense",
    "sub_attempts_15",
    "win_rate",
    "log_experience",
    "inactivity_years",
]
FEATURES = ["diff_" + c for c in PROFILE_FEATURES]


def long_history(dataset: Dataset) -> pd.DataFrame:
    rows = []
    for fight in dataset.fights.itertuples():
        for side, fid, opp in [
            ("a", fight.fighter_a_id, fight.fighter_b_id),
            ("b", fight.fighter_b_id, fight.fighter_a_id),
        ]:
            rows.append(
                {
                    "fight_id": fight.fight_id,
                    "fighter_id": fid,
                    "opponent_id": opp,
                    "event_date": fight.event_date,
                    "weight_class": fight.weight_class,
                    "minutes": fight.duration_seconds / 60,
                    "won": int(fight.result == side + "_win"),
                }
            )
    history = pd.DataFrame(rows).merge(
        dataset.stats, on=["fight_id", "fighter_id"], validate="one_to_one"
    )
    opponent = dataset.stats[
        ["fight_id", "fighter_id", "sig_landed", "sig_attempted", "td_landed", "td_attempted"]
    ].rename(
        columns={
            "fighter_id": "opponent_id",
            **{c: "opp_" + c for c in ["sig_landed", "sig_attempted", "td_landed", "td_attempted"]},
        }
    )
    return history.merge(opponent, on=["fight_id", "opponent_id"], validate="one_to_one")


def rate(landed: float, attempted: float) -> float:
    """Observed ratios stay missing at 0/0; Laplace smoothing only with evidence."""
    return (landed + 1) / (attempted + 2) if attempted > 0 else np.nan


def _profile(history: pd.DataFrame, fighter_id: str, as_of_date) -> dict:
    cutoff = pd.Timestamp(as_of_date).normalize()
    prior = history[(history.fighter_id == fighter_id) & (history.event_date < cutoff)]
    n = len(prior)
    minutes = prior.minutes.sum()
    totals = prior.select_dtypes(include=["number"]).sum(min_count=1)

    def per_min(col):
        observed = prior[prior[col].notna()]
        exposure = observed.minutes.sum()
        return observed[col].sum() / exposure if exposure > 0 else np.nan

    result = {
        "fighter_id": fighter_id,
        "reference_date": str(cutoff.date()),
        "prior_fights": n,
        "wins": int(prior.won.sum()),
        "losses": n - int(prior.won.sum()),
        "observed_minutes": minutes,
        "last_fight": str(prior.event_date.max().date()) if n else None,
        "last_division": prior.sort_values("event_date").weight_class.iloc[-1] if n else None,
        "divisions": sorted(prior.weight_class.unique()),
        "sufficient_history": n >= MIN_HISTORY,
        "sig_landed_pm": per_min("sig_landed"),
        "sig_absorbed_pm": per_min("opp_sig_landed"),
        "sig_accuracy": rate(totals.get("sig_landed", np.nan), totals.get("sig_attempted", np.nan)),
        "sig_defense": rate(
            totals.get("opp_sig_attempted", np.nan) - totals.get("opp_sig_landed", np.nan),
            totals.get("opp_sig_attempted", np.nan),
        ),
        "td_landed_15": 15 * per_min("td_landed"),
        "td_attempts_15": 15 * per_min("td_attempted"),
        "td_accuracy": rate(totals.get("td_landed", np.nan), totals.get("td_attempted", np.nan)),
        "td_defense": rate(
            totals.get("opp_td_attempted", np.nan) - totals.get("opp_td_landed", np.nan),
            totals.get("opp_td_attempted", np.nan),
        ),
        "sub_attempts_15": 15 * per_min("submission_attempts"),
        "control_pm": per_min("control_seconds"),
        "win_rate": rate(int(prior.won.sum()), n),
        "log_experience": np.log1p(n),
        "inactivity_years": (cutoff - prior.event_date.max()).days / 365.25 if n else np.nan,
        "feature_version": FEATURE_VERSION,
    }
    for col in ["sig_landed", "sig_attempted", "td_landed", "td_attempted", "opp_td_attempted"]:
        result["total_" + col] = float(totals.get(col, np.nan))
    return result


def build_fighter_profile(dataset: Dataset, fighter_id: str, as_of_date, history=None) -> dict:
    if fighter_id not in set(dataset.fighters.fighter_id):
        raise ValueError("Unknown fighter ID")
    return _profile(long_history(dataset) if history is None else history, fighter_id, as_of_date)


def matchup_features(a: dict, b: dict) -> np.ndarray:
    return np.array([a[c] - b[c] for c in PROFILE_FEATURES], dtype=float)


def build_feature_table(dataset: Dataset) -> pd.DataFrame:
    history = long_history(dataset)
    history["prior_fights"] = 1
    history["sub_exposure"] = history.minutes.where(history.submission_attempts.notna(), 0)
    count_cols = [
        "prior_fights",
        "won",
        "minutes",
        "sub_exposure",
        "sig_landed",
        "sig_attempted",
        "opp_sig_landed",
        "opp_sig_attempted",
        "td_landed",
        "td_attempted",
        "opp_td_landed",
        "opp_td_attempted",
        "submission_attempts",
    ]
    daily = (
        history.groupby(["fighter_id", "event_date"], as_index=False)[count_cols]
        .sum()
        .sort_values(["fighter_id", "event_date"])
    )
    # Aggregate all observations on the same day BEFORE shifting cumulative totals.
    previous = daily.copy()
    previous[count_cols] = daily.groupby("fighter_id")[count_cols].cumsum() - daily[count_cols]
    previous["last_date"] = daily.groupby("fighter_id").event_date.shift()
    p = previous
    minutes = p.minutes.replace(0, np.nan)

    def smooth(numerator, denominator):
        return ((numerator + 1) / (denominator + 2)).where(denominator > 0)

    p["sig_landed_pm"] = p.sig_landed / minutes
    p["sig_absorbed_pm"] = p.opp_sig_landed / minutes
    p["sig_accuracy"] = smooth(p.sig_landed, p.sig_attempted)
    p["sig_defense"] = smooth(p.opp_sig_attempted - p.opp_sig_landed, p.opp_sig_attempted)
    p["td_landed_15"] = 15 * p.td_landed / minutes
    p["td_defense"] = smooth(p.opp_td_attempted - p.opp_td_landed, p.opp_td_attempted)
    p["sub_attempts_15"] = 15 * p.submission_attempts / p.sub_exposure.replace(0, np.nan)
    p["win_rate"] = smooth(p.won, p.prior_fights)
    p["log_experience"] = np.log1p(p.prior_fights)
    p["inactivity_years"] = (p.event_date - p.last_date).dt.days / 365.25
    table = dataset.fights[
        [
            "fight_id",
            "event_date",
            "fighter_a_id",
            "fighter_b_id",
            "weight_class",
            "scheduled_rounds",
            "result",
        ]
    ].copy()
    cols = ["fighter_id", "event_date", "prior_fights", *PROFILE_FEATURES]
    for side in ("a", "b"):
        right = p[cols].rename(columns={c: side + "_" + c for c in cols if c != "event_date"})
        table = table.merge(
            right,
            left_on=["fighter_" + side + "_id", "event_date"],
            right_on=[side + "_fighter_id", "event_date"],
            validate="many_to_one",
        )
    for col in PROFILE_FEATURES:
        table["diff_" + col] = table["a_" + col] - table["b_" + col]
    table["target"] = table.result.eq("a_win").astype(int)
    table["eligible"] = table.a_prior_fights.ge(MIN_HISTORY) & table.b_prior_fights.ge(MIN_HISTORY)
    return table[
        [
            "fight_id",
            "event_date",
            "fighter_a_id",
            "fighter_b_id",
            "weight_class",
            "scheduled_rounds",
            "target",
            "eligible",
            *FEATURES,
        ]
    ]
