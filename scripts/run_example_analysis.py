"""Reproduce a real historical matchup or an exported analysis configuration."""

import argparse
import json
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mma_decision_lab.analysis import analyze
from mma_decision_lab.config import ROOT
from mma_decision_lab.data import load_dataset, save_processed
from mma_decision_lab.features import build_feature_table
from mma_decision_lab.forecasting import train_baseline
from mma_decision_lab.persistence import save_numeric_model
from mma_decision_lab.reporting import export_bundle, export_json, html_report, safe_csv
from mma_decision_lab.schemas import AnalysisContext, ScenarioConfig


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config", type=Path, help="JSON record previously exported by MMA Decision Lab"
    )
    parser.add_argument(
        "--illustrative",
        action="store_true",
        help="Use explicitly hypothetical nonneutral tactical assumptions",
    )
    parser.add_argument("--output", type=Path, default=ROOT / "reports/generated")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    start = time.perf_counter()
    dataset = load_dataset()
    save_processed(dataset)
    if args.config:
        exported = json.loads(args.config.read_text(encoding="utf-8"))
        if exported["snapshot"]["dataset_version"] != dataset.manifest["dataset_version"]:
            raise ValueError(
                "Snapshot mismatch: fetch the commit recorded in the exported JSON before reproducing"
            )
        context = AnalysisContext(**exported["context"])
        config = ScenarioConfig(**exported["scenario"])
        manual = (
            exported["baseline_probability"]
            if exported["mode"].startswith("Scenario-only")
            else None
        )
    else:
        names = dataset.fighters.set_index("fighter_name").fighter_id
        context = AnalysisContext(
            fighter_a_id=names["Khabib Nurmagomedov"],
            fighter_b_id=names["Conor McGregor"],
            reference_date="2018-10-06",
            weight_class="Lightweight",
            scheduled_rounds=5,
        )
        config = (
            ScenarioConfig(
                striking_effect=0.35,
                grappling_effect=0.5,
                resistance=0.4,
                counter_cost=0.15,
                effect_half_width=0.3,
                response_concentration=30,
            )
            if args.illustrative
            else ScenarioConfig()
        )
        manual = None
    feature_start = time.perf_counter()
    features = build_feature_table(dataset)
    baseline = train_baseline(features, context.reference_date) if manual is None else None
    fit_seconds = time.perf_counter() - feature_start
    analysis_start = time.perf_counter()
    result = analyze(dataset, context, config, baseline, manual)
    analysis_seconds = time.perf_counter() - analysis_start
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "report.html").write_text(html_report(result), encoding="utf-8")
    (args.output / "analysis.json").write_text(export_json(result), encoding="utf-8")
    (args.output / "research_bundle.zip").write_bytes(export_bundle(result))
    (args.output / "policy_results.csv").write_bytes(safe_csv(result["simulation"]["summary"]))
    if baseline:
        save_numeric_model(baseline, ROOT / "models/baseline.json")
        (args.output / "calibration.csv").write_bytes(safe_csv(baseline.calibration))
        (args.output / "partitions.csv").write_bytes(safe_csv(baseline.partitions))
    runtime = {
        "feature_and_model_seconds": fit_seconds,
        "simulation_and_sensitivity_seconds": analysis_seconds,
        "total_seconds": time.perf_counter() - start,
        "draws": context.draws,
    }
    (args.output / "benchmark.json").write_text(json.dumps(runtime, indent=2), encoding="utf-8")
    print(result["simulation"]["summary"].to_string(index=False))
    print(result["recommendation"]["headline"])
    print(runtime)


if __name__ == "__main__":
    main()
