import copy

import numpy as np
import pandas as pd

from mma_decision_lab.features import (
    FEATURES,
    PROFILE_FEATURES,
    build_feature_table,
    build_fighter_profile,
    matchup_features,
    rate,
)


def test_future_and_same_day_fights_do_not_change_earlier_profile(synthetic_dataset):
    d = synthetic_dataset
    cutoff = "2020-04-01"
    before = build_fighter_profile(d, "alpha", cutoff)
    changed = copy.deepcopy(d)
    extra = d.fights.iloc[0].copy()
    extra.fight_id = "future-synthetic"
    extra.event_date = pd.Timestamp(cutoff)
    changed.fights = pd.concat([changed.fights, pd.DataFrame([extra])], ignore_index=True)
    stats = d.stats[d.stats.fight_id == "test-0"].copy()
    stats.fight_id = extra.fight_id
    stats.sig_landed = 99999
    stats.sig_attempted = 100000
    changed.stats = pd.concat([changed.stats, stats], ignore_index=True)
    after = build_fighter_profile(changed, "alpha", cutoff)
    for key in before:
        if isinstance(before[key], float) and np.isnan(before[key]):
            assert np.isnan(after[key])
        else:
            assert before[key] == after[key]


def test_vectorized_features_match_strict_profile_api(synthetic_dataset):
    d = synthetic_dataset
    table = build_feature_table(d)
    for row in table.itertuples():
        a = build_fighter_profile(d, row.fighter_a_id, row.event_date)
        b = build_fighter_profile(d, row.fighter_b_id, row.event_date)
        np.testing.assert_allclose(
            table.loc[table.fight_id == row.fight_id, FEATURES].to_numpy()[0],
            matchup_features(a, b),
            equal_nan=True,
            atol=1e-12,
        )


def test_same_date_multiple_bouts_excluded_as_a_group(synthetic_dataset):
    d = synthetic_dataset
    d.fights.loc[1, "event_date"] = d.fights.loc[0, "event_date"]
    table = build_feature_table(d)
    for row in table.iloc[:2].itertuples():
        a = build_fighter_profile(d, row.fighter_a_id, row.event_date)
        b = build_fighter_profile(d, row.fighter_b_id, row.event_date)
        assert a["prior_fights"] == b["prior_fights"] == 0
        np.testing.assert_allclose(
            table.loc[table.fight_id == row.fight_id, FEATURES].to_numpy()[0],
            matchup_features(a, b),
            equal_nan=True,
        )


def test_no_attempt_denominator_is_not_measured_zero(synthetic_dataset):
    profile = build_fighter_profile(synthetic_dataset, "alpha", "2021-01-01")
    assert np.isnan(profile["td_accuracy"])
    assert np.isnan(profile["td_defense"])
    assert np.isnan(rate(0, 0))
    assert set(PROFILE_FEATURES) <= set(profile)


def test_sparse_history_is_explicit(synthetic_dataset):
    profile = build_fighter_profile(synthetic_dataset, "alpha", "2020-01-01")
    assert profile["prior_fights"] == 0 and not profile["sufficient_history"]
    assert np.isnan(profile["sig_landed_pm"])
