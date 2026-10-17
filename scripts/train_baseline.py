"""Fit/evaluate a historical baseline and save safe numeric JSON parameters."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mma_decision_lab.config import ROOT
from mma_decision_lab.data import load_dataset
from mma_decision_lab.features import build_feature_table
from mma_decision_lab.forecasting import train_baseline
from mma_decision_lab.persistence import save_numeric_model

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--as-of", default="2018-10-06")
args = parser.parse_args()
model = train_baseline(build_feature_table(load_dataset()), args.as_of)
save_numeric_model(model, ROOT / "models/baseline.json")
print(json.dumps(model.evaluation, indent=2))
