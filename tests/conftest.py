"""SYNTHETIC fixtures; these never enter the historical app dataset."""

from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import pytest

from mma_decision_lab.data import Dataset
from mma_decision_lab.features import FEATURES


@pytest.fixture
def synthetic_dataset():
    fighters = pd.DataFrame(
        [
            {
                "fighter_id": fid,
                "fighter_name": "Test " + fid,
                "source_identifier": "synthetic:" + fid,
            }
            for fid in ("alpha", "beta", "gamma")
        ]
    )
    fights = []
    stats = []
    for i, (a, b) in enumerate(
        [
            ("alpha", "beta"),
            ("alpha", "gamma"),
            ("beta", "gamma"),
            ("alpha", "beta"),
            ("alpha", "gamma"),
            ("beta", "gamma"),
        ]
    ):
        fights.append(
            {
                "fight_id": f"test-{i}",
                "event_id": f"event-{i}",
                "fighter_a_id": a,
                "fighter_b_id": b,
                "event_date": pd.Timestamp(datetime(2020, 1, 1) + timedelta(days=i * 30)),
                "event_name": f"SYNTHETIC event {i}",
                "weight_class": "Lightweight",
                "scheduled_rounds": 3,
                "completed_rounds": 1,
                "finish_time": 300,
                "duration_seconds": 300,
                "result": "a_win" if i % 2 else "b_win",
                "victory_method": "Synthetic",
                "source_identifier": "synthetic",
            }
        )
        for side, fid in enumerate([a, b]):
            stats.append(
                {
                    "fight_id": f"test-{i}",
                    "fighter_id": fid,
                    "sig_landed": 10 + i + side,
                    "sig_attempted": 30 + i,
                    "td_landed": 0,
                    "td_attempted": 0,
                    "submission_attempts": side,
                    "control_seconds": np.nan if i == 1 else 30,
                }
            )
    return Dataset(
        fighters,
        pd.DataFrame(),
        pd.DataFrame(fights),
        pd.DataFrame(stats),
        pd.DataFrame(),
        pd.DataFrame(),
        {"dataset_version": "SYNTHETIC-test-only"},
        {},
    )


@pytest.fixture
def synthetic_features():
    rng = np.random.default_rng(83)
    x = rng.normal(size=(420, len(FEATURES)))
    y = (rng.random(420) < 1 / (1 + np.exp(-x[:, 0]))).astype(int)
    frame = pd.DataFrame(x, columns=FEATURES)
    frame["fight_id"] = [f"synthetic-{i}" for i in range(420)]
    frame["event_date"] = pd.date_range("2010-01-01", periods=420, freq="7D")
    frame["eligible"] = True
    frame["target"] = y
    return frame


@pytest.fixture
def raw_source():
    return {
        "ufc_event_details.csv": b'EVENT,URL,DATE,LOCATION\nTest Event,https://example.invalid/events/e1,"January 01, 2020",Test City\n',
        "ufc_fighter_details.csv": b"FIRST,LAST,URL\nTest,Alpha,https://example.invalid/fighters/alpha\nTest,Beta,https://example.invalid/fighters/beta\n",
        "ufc_fight_results.csv": b"EVENT,BOUT,OUTCOME,WEIGHTCLASS,METHOD,ROUND,TIME,TIME FORMAT,URL\nTest Event,Test Alpha vs. Test Beta,W/L,Lightweight Title Bout,KO/TKO,1,1:00,3 Rnd (5-5-5),https://example.invalid/fights/f1\n",
        "ufc_fight_stats.csv": b"EVENT,BOUT,ROUND,FIGHTER,KD,SIG.STR.,TD,SUB.ATT,CTRL,DISTANCE,CLINCH,GROUND\nTest Event,Test Alpha vs. Test Beta,Round 1,Test Alpha,1,10 of 20,0 of 0,0,0:00,10 of 20,0 of 0,0 of 0\nTest Event,Test Alpha vs. Test Beta,Round 1,Test Beta,0,5 of 10,0 of 0,0,0:00,5 of 10,0 of 0,0 of 0\n",
    }
