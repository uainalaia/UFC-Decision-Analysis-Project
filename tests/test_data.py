import io

import numpy as np
import pandas as pd
import pytest
from pydantic import ValidationError

from mma_decision_lab.data import division_label, ingest, pair, read_csv_bytes, seconds
from mma_decision_lab.schemas import Fight


def test_valid_round_ingestion_preserves_identifiers_and_denominators(raw_source):
    d = ingest(raw_source, {"dataset_version": "SYNTHETIC"})
    assert d.fights.iloc[0].fighter_a_id == "alpha"
    assert d.fights.iloc[0].weight_class == "Lightweight"
    assert d.fights.iloc[0].duration_seconds == 60
    assert len(d.stats) == 2 and len(d.rounds) == 2
    assert d.stats.td_attempted.eq(0).all()


@pytest.mark.parametrize("value", ["-1 of 3", "4 of 3", "junk", "1 / 2"])
def test_invalid_counts_rejected(value):
    with pytest.raises(ValueError):
        pair(value)


def test_missing_not_zero():
    assert all(np.isnan(x) for x in pair("---"))
    assert pair("0 of 0") == (0, 0)


@pytest.mark.parametrize("value", ["1:60", "bad", "-1:20"])
def test_malformed_time_rejected(value):
    with pytest.raises(ValueError):
        seconds(value)


def test_csv_contract_and_size_limit():
    with pytest.raises(ValueError):
        read_csv_bytes(b"bad\n1", {"fight_id"})
    with pytest.raises(ValueError):
        read_csv_bytes(b"id\n1", {"id"}, max_bytes=2)


@pytest.mark.parametrize(
    "column,value",
    [("OUTCOME", "NC/NC"), ("METHOD", "DQ"), ("TIME FORMAT", "1 Rnd (10)"), ("ROUND", 4)],
)
def test_unsupported_fights_cannot_become_losses(raw_source, column, value):
    results = pd.read_csv(io.BytesIO(raw_source["ufc_fight_results.csv"]))
    results[column] = value
    raw_source["ufc_fight_results.csv"] = results.to_csv(index=False).encode()
    with pytest.raises(ValueError, match="No eligible"):
        ingest(raw_source, {})


def test_duplicate_fights_detected_and_all_copies_excluded(raw_source):
    f = pd.read_csv(io.BytesIO(raw_source["ufc_fight_results.csv"]))
    other = f.copy()
    other.URL = "https://example.invalid/fights/f2"
    other.BOUT = "Test Beta vs. Test Alpha"
    # Keep a separate valid fight to inspect the exclusion report.
    all_results = pd.concat([f, f, other], ignore_index=True)
    raw_source["ufc_fight_results.csv"] = all_results.to_csv(index=False).encode()
    stats = pd.read_csv(io.BytesIO(raw_source["ufc_fight_stats.csv"]))
    alternate = stats.copy()
    alternate.BOUT = "Test Beta vs. Test Alpha"
    raw_source["ufc_fight_stats.csv"] = pd.concat([stats, alternate]).to_csv(index=False).encode()
    d = ingest(raw_source, {})
    assert len(d.fights) == 1 and len(d.exclusions) == 2
    assert d.exclusions.reason.str.contains("duplicate").all()


def test_round_control_cannot_exceed_duration(raw_source):
    raw_source["ufc_fight_stats.csv"] = raw_source["ufc_fight_stats.csv"].replace(
        b"0:00", b"1:01", 1
    )
    with pytest.raises(ValueError, match="No eligible"):
        ingest(raw_source, {})


def test_canonical_fight_rejects_same_competitor():
    with pytest.raises(ValidationError):
        Fight(
            fight_id="x",
            event_id="e",
            fighter_a_id="a",
            fighter_b_id="a",
            weight_class="Lightweight",
            scheduled_rounds=3,
            completed_rounds=1,
            result="a_win",
            victory_method="KO",
            finish_time=60,
            source_identifier="synthetic",
        )


def test_title_and_non_title_divisions_are_comparable():
    assert division_label("UFC Interim Lightweight Title Bout") == division_label(
        "Lightweight Bout"
    )
    assert division_label("Women's Flyweight Bout") == "Women's Flyweight"
