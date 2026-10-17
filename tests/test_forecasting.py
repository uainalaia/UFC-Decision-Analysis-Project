import numpy as np
import pytest

from mma_decision_lab.features import FEATURES
from mma_decision_lab.forecasting import train_baseline
from mma_decision_lab.persistence import load_numeric_model, save_numeric_model


def test_temporal_partition_symmetry_and_safe_serialization(synthetic_features, tmp_path):
    model = train_baseline(synthetic_features, "2020-01-01", bootstrap_count=8)
    x = synthetic_features[FEATURES].iloc[42].to_numpy()
    assert 0 < model.predict(x) < 1
    assert abs(model.predict(x) + model.predict(-x) - 1) < 1e-12
    parts = model.partitions
    assert not parts.fight_id.duplicated().any()
    assert (
        parts[parts.partition == "train"].event_date.max()
        < parts[parts.partition == "validation"].event_date.min()
    )
    assert (
        parts[parts.partition == "validation"].event_date.max()
        < parts[parts.partition == "test"].event_date.min()
    )
    path = tmp_path / "model.json"
    save_numeric_model(model, path)
    restored, boots = load_numeric_model(path)
    np.testing.assert_allclose(
        restored.predict_proba(x.reshape(1, -1))[0, 1], model.predict(x), atol=1e-12
    )
    np.testing.assert_allclose(
        [m.predict_proba(x.reshape(1, -1))[0, 1] for m in boots], model.predict_draws(x)
    )


def test_test_set_never_changes_selection_or_training(synthetic_features):
    a = train_baseline(synthetic_features, "2020-01-01", bootstrap_count=3)
    altered = synthetic_features.copy()
    test_ids = a.partitions.loc[a.partitions.partition == "test", "fight_id"]
    altered.loc[altered.fight_id.isin(test_ids), FEATURES] *= 1000
    altered.loc[altered.fight_id.isin(test_ids), "target"] = (
        1 - altered.loc[altered.fight_id.isin(test_ids), "target"]
    )
    b = train_baseline(altered, "2020-01-01", bootstrap_count=3)
    assert a.evaluation["selected_C"] == b.evaluation["selected_C"]
    np.testing.assert_array_equal(a.model[-1].coef_, b.model[-1].coef_)
    np.testing.assert_array_equal(a.model[-2].scale_, b.model[-2].scale_)


def test_future_training_rows_are_ignored(synthetic_features):
    cutoff = synthetic_features.event_date.iloc[350]
    a = train_baseline(synthetic_features, cutoff, bootstrap_count=2)
    changed = synthetic_features.copy()
    changed.loc[changed.event_date >= cutoff, FEATURES] = 999
    b = train_baseline(changed, cutoff, bootstrap_count=2)
    np.testing.assert_array_equal(a.model[-1].coef_, b.model[-1].coef_)
    assert (a.partitions.event_date < cutoff).all()


def test_insufficient_history_is_rejected(synthetic_features):
    with pytest.raises(ValueError, match="180"):
        train_baseline(synthetic_features.iloc[:50], "2020-01-01")
