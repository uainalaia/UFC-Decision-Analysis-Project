"""Audited local ingestion; all exclusions remain inspectable."""

import hashlib
import io
import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from .config import ROOT, VERSION
from .schemas import Event, Fight, Fighter

logger = logging.getLogger(__name__)
COUNT_PAIRS = {
    "SIG.STR.": "sig",
    "TD": "td",
    "DISTANCE": "distance",
    "CLINCH": "clinch",
    "GROUND": "ground",
}


def division_label(value: str) -> str:
    for label in (
        "Women's Strawweight",
        "Women's Flyweight",
        "Women's Bantamweight",
        "Women's Featherweight",
        "Super Heavyweight",
        "Light Heavyweight",
        "Heavyweight",
        "Middleweight",
        "Welterweight",
        "Lightweight",
        "Featherweight",
        "Bantamweight",
        "Flyweight",
        "Catch Weight",
        "Open Weight",
    ):
        if label in value:
            return label
    return value


@dataclass
class Dataset:
    fighters: pd.DataFrame
    events: pd.DataFrame
    fights: pd.DataFrame
    stats: pd.DataFrame
    rounds: pd.DataFrame
    exclusions: pd.DataFrame
    manifest: dict
    quality: dict


def pair(value) -> tuple[float, float]:
    if pd.isna(value) or str(value).strip() in ("", "--", "---"):
        return np.nan, np.nan
    match = re.fullmatch(r"\s*(\d+)\s+of\s+(\d+)\s*", str(value))
    if not match:
        raise ValueError(f"Malformed landed/attempted field: {value!r}")
    landed, attempts = map(int, match.groups())
    if landed > attempts:
        raise ValueError("Landed actions exceed attempts")
    return landed, attempts


def seconds(value) -> float:
    if pd.isna(value) or str(value).strip() in ("", "--", "---"):
        return np.nan
    match = re.fullmatch(r"\s*(\d+):(\d{2})\s*", str(value))
    if not match or int(match[2]) >= 60:
        raise ValueError(f"Malformed time: {value!r}")
    return int(match[1]) * 60 + int(match[2])


def read_csv_bytes(payload: bytes, required: set[str], max_bytes=12_000_000) -> pd.DataFrame:
    """Parse data bytes only; never accept paths, pickle or executable model uploads."""
    if len(payload) > max_bytes:
        raise ValueError("CSV exceeds the 12 MB per-file limit")
    frame = pd.read_csv(io.BytesIO(payload))
    if not required <= set(frame.columns):
        raise ValueError(f"Missing CSV fields: {sorted(required - set(frame.columns))}")
    if len(frame) > 200000:
        raise ValueError("CSV exceeds the row limit")
    for col in frame.select_dtypes(include=["object"]):
        frame[col] = frame[col].str.strip()
    return frame


def ingest(files: dict[str, bytes], manifest: dict) -> Dataset:
    required = {
        "ufc_event_details.csv": {"EVENT", "URL", "DATE", "LOCATION"},
        "ufc_fighter_details.csv": {"FIRST", "LAST", "URL"},
        "ufc_fight_results.csv": {
            "EVENT",
            "BOUT",
            "OUTCOME",
            "WEIGHTCLASS",
            "METHOD",
            "ROUND",
            "TIME",
            "TIME FORMAT",
            "URL",
        },
        "ufc_fight_stats.csv": {
            "EVENT",
            "BOUT",
            "ROUND",
            "FIGHTER",
            "KD",
            "SIG.STR.",
            "TD",
            "SUB.ATT",
            "CTRL",
            "DISTANCE",
            "CLINCH",
            "GROUND",
        },
    }
    tables = {name: read_csv_bytes(files[name], cols) for name, cols in required.items()}
    source_root = Path(__file__).parent
    code_hash = hashlib.sha256(
        b"".join(p.name.encode() + p.read_bytes() for p in sorted(source_root.glob("*.py")))
    ).hexdigest()
    manifest = manifest | {
        "original_field_names": {name: list(table.columns) for name, table in tables.items()},
        "transformations": [
            "Trim surrounding string whitespace; map source URLs to stable entity IDs.",
            "Reject every ambiguous duplicate fight and ambiguous fighter-name identity.",
            "Retain binary non-DQ 3/5-round bouts with complete essential round counts; log all exclusions.",
            "Normalize title/non-title division labels; convert mm:ss to seconds; aggregate competitor-round counts.",
            "Preserve partial metric missingness; strictly earlier-date historical feature generation.",
        ],
        "missing_value_rules": "Missing is not zero. Essential strike/takedown counts are required. Optional partial totals remain missing. 0/0 ratios are missing; forecast differences are imputed to zero inside the pipeline.",
        "implementation_sha256": code_hash,
    }
    fighters_raw = tables["ufc_fighter_details.csv"]
    fighters = pd.DataFrame(
        [
            Fighter(
                fighter_id=str(r.URL).rsplit("/", 1)[-1],
                fighter_name=" ".join(str(v) for v in [r.FIRST, r.LAST] if pd.notna(v)),
                source_identifier=r.URL,
            ).model_dump()
            for r in fighters_raw.itertuples()
        ]
    )
    if fighters.fighter_id.duplicated().any() or fighters.fighter_id.eq("").any():
        raise ValueError("Duplicate or empty fighter identifiers")
    ambiguous = set(fighters.loc[fighters.fighter_name.duplicated(False), "fighter_name"])
    names = (
        fighters[~fighters.fighter_name.isin(ambiguous)]
        .set_index("fighter_name")
        .fighter_id.to_dict()
    )
    events_raw = tables["ufc_event_details.csv"]
    events = pd.DataFrame(
        [
            Event(
                event_id=r.URL.rsplit("/", 1)[-1],
                event_name=r.EVENT,
                event_date=pd.to_datetime(r.DATE).date(),
                location=r.LOCATION if pd.notna(r.LOCATION) else None,
                source_identifier=r.URL,
            ).model_dump()
            for r in events_raw.itertuples()
        ]
    )
    events.event_date = pd.to_datetime(events.event_date)
    if events.event_id.duplicated().any() or events.event_name.duplicated().any():
        raise ValueError("Event identifiers/names must be unique for an unambiguous join")
    event_map = events.set_index("event_name").to_dict("index")
    results = tables["ufc_fight_results.csv"]
    duplicate_ids = set(results.loc[results.URL.duplicated(False), "URL"])
    duplicate_keys = set(
        map(
            tuple,
            results.loc[results.duplicated(["EVENT", "BOUT"], False), ["EVENT", "BOUT"]].to_numpy(),
        )
    )
    stat_groups = {
        key: group
        for key, group in tables["ufc_fight_stats.csv"].groupby(["EVENT", "BOUT"], sort=False)
    }
    fights, round_rows, excluded = [], [], []
    for _, result in results.iterrows():
        fight_id = str(result.URL).rsplit("/", 1)[-1]
        try:
            if result.URL in duplicate_ids or (result.EVENT, result.BOUT) in duplicate_keys:
                raise ValueError(
                    "Ambiguous duplicate source ID or event/bout key; all copies excluded"
                )
            competitors = str(result.BOUT).split(" vs. ")
            if len(competitors) != 2 or any(c not in names for c in competitors):
                raise ValueError("Missing or ambiguous fighter source identity")
            if result.OUTCOME not in ("W/L", "L/W"):
                raise ValueError("Excluded nonbinary outcome")
            if str(result.METHOD).upper().startswith(("DQ", "DISQUAL")):
                raise ValueError("Excluded disqualification")
            fmt = re.fullmatch(r"([35]) Rnd \((?:5-){2,4}5\)", str(result["TIME FORMAT"]))
            if not fmt:
                raise ValueError("Unsupported round format")
            scheduled = int(fmt[1])
            if str(result["TIME FORMAT"]).count("5") - (1 if scheduled == 5 else 0) != scheduled:
                raise ValueError("Inconsistent round format")
            event = event_map[result.EVENT]
            ids = [names[n] for n in competitors]
            a, b = sorted(ids)  # Canonical ordering does not use the result.
            winner = ids[0 if result.OUTCOME == "W/L" else 1]
            fight = Fight(
                fight_id=fight_id,
                event_id=event["event_id"],
                fighter_a_id=a,
                fighter_b_id=b,
                weight_class=division_label(result.WEIGHTCLASS),
                scheduled_rounds=scheduled,
                completed_rounds=int(result.ROUND),
                result="a_win" if winner == a else "b_win",
                victory_method=result.METHOD,
                finish_time=int(seconds(result.TIME)),
                source_identifier=result.URL,
            ).model_dump()
            group = stat_groups.get((result.EVENT, result.BOUT))
            if group is None:
                raise ValueError("No recorded round statistics")
            rows = []
            for _, row in group.iterrows():
                if row.FIGHTER not in competitors:
                    raise ValueError("Round competitor differs from fight roster")
                rnd = int(re.fullmatch(r"Round (\d+)", row.ROUND)[1])
                if not 1 <= rnd <= fight["completed_rounds"]:
                    raise ValueError("Round number outside completed fight")
                duration = 300 if rnd < fight["completed_rounds"] else fight["finish_time"]
                record = {
                    "fight_id": fight_id,
                    "fighter_id": names[row.FIGHTER],
                    "round_number": rnd,
                    "round_seconds": duration,
                }
                for original, prefix in COUNT_PAIRS.items():
                    record[prefix + "_landed"], record[prefix + "_attempted"] = pair(row[original])
                for original, canonical in [
                    ("KD", "knockdowns"),
                    ("SUB.ATT", "submission_attempts"),
                ]:
                    value = pd.to_numeric(row[original], errors="coerce")
                    if pd.notna(value) and (value < 0 or value % 1):
                        raise ValueError("Action counts must be nonnegative integers")
                    record[canonical] = value
                record["control_seconds"] = seconds(row.CTRL)
                if pd.notna(record["control_seconds"]) and record["control_seconds"] > duration:
                    raise ValueError("Control time exceeds round exposure")
                rows.append(record)
            keys = {(r["fighter_id"], r["round_number"]) for r in rows}
            if len(keys) != len(rows) or len(rows) != 2 * fight["completed_rounds"]:
                raise ValueError("Duplicate or missing competitor-round records")
            if any(
                pd.isna(r[k])
                for r in rows
                for k in ("sig_landed", "sig_attempted", "td_landed", "td_attempted")
            ):
                raise ValueError(
                    "Missing essential strike/takedown counts; exposure cannot be reconstructed"
                )
            fights.append(
                fight
                | {
                    "event_date": event["event_date"],
                    "event_name": result.EVENT,
                    "duration_seconds": (fight["completed_rounds"] - 1) * 300
                    + fight["finish_time"],
                }
            )
            round_rows.extend(rows)
        except (ValueError, KeyError, TypeError, IndexError) as exc:
            excluded.append(
                {
                    "fight_id": fight_id,
                    "event": result.EVENT,
                    "bout": result.BOUT,
                    "reason": str(exc),
                }
            )
    if not fights:
        raise ValueError("No eligible historical fights remain after validation")
    fights = pd.DataFrame(fights).sort_values(["event_date", "fight_id"]).reset_index(drop=True)
    rounds = pd.DataFrame(round_rows)
    numeric = [
        c for c in rounds if c not in ("fight_id", "fighter_id", "round_number", "round_seconds")
    ]
    # Preserve missingness if any round in a fighter/fight is missing that metric.
    stats = (
        rounds.groupby(["fight_id", "fighter_id"])[numeric]
        .agg(lambda s: s.sum() if s.notna().all() else np.nan)
        .reset_index()
    )
    quality = {
        "input_fights": len(results),
        "retained_fights": len(fights),
        "excluded_fights": len(excluded),
        "exclusion_rate": len(excluded) / len(results),
        "round_rows": len(rounds),
        "fighter_count": len(fighters),
        "ambiguous_names": sorted(ambiguous),
        "first_date": str(fights.event_date.min().date()),
        "last_date": str(fights.event_date.max().date()),
        "missing_fraction": stats[numeric].isna().mean().to_dict(),
        "exclusion_reasons": pd.Series([r["reason"] for r in excluded]).value_counts().to_dict(),
        "transform_version": VERSION,
    }
    logger.info(
        "ingestion %s",
        {k: quality[k] for k in ("input_fights", "retained_fights", "excluded_fights")},
    )
    return Dataset(
        fighters, events, fights, stats, rounds, pd.DataFrame(excluded), manifest, quality
    )


def load_dataset(root: Path = ROOT) -> Dataset:
    manifest = json.loads((root / "data/manifests/snapshot.json").read_text(encoding="utf-8"))
    files = {}
    for entry in manifest["files"]:
        # Only the known leaf names from the contract can be read.
        name = entry["file"]
        if name not in {
            "ufc_event_details.csv",
            "ufc_fighter_details.csv",
            "ufc_fight_results.csv",
            "ufc_fight_stats.csv",
            "LICENSE",
            "README.md",
        }:
            raise ValueError("Unexpected file in snapshot manifest")
        payload = (root / "data/raw" / name).read_bytes()
        if hashlib.sha256(payload).hexdigest() != entry["sha256"]:
            raise ValueError(f"Snapshot hash mismatch for {name}")
        files[name] = payload
    return ingest(files, manifest)


def save_processed(dataset: Dataset, root: Path = ROOT):
    path = root / "data/processed"
    path.mkdir(parents=True, exist_ok=True)
    for name in ("fighters", "events", "fights", "stats", "rounds", "exclusions"):
        getattr(dataset, name).to_csv(path / f"{name}.csv", index=False)
    (path / "quality.json").write_text(json.dumps(dataset.quality, indent=2), encoding="utf-8")
    (path / "provenance.json").write_text(json.dumps(dataset.manifest, indent=2), encoding="utf-8")
