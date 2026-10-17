"""Freeze the actual GUI illustrative preset for the Spanish usage guide. No fitting."""

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))

import pandas as pd

from mma_decision_lab.analysis import analyze
from mma_decision_lab.data import load_dataset
from mma_decision_lab.forecasting import Baseline
from mma_decision_lab.persistence import load_numeric_model
from mma_decision_lab.reporting import clean, export_json
from mma_decision_lab.schemas import AnalysisContext, ScenarioConfig
from mma_decision_lab.sensitivity import one_way

folder=ROOT/'output/pdf/assets'
folder.mkdir(parents=True,exist_ok=True)
metadata=json.loads((ROOT/'models/baseline.json').read_text(encoding='utf-8'))
model,bootstraps=load_numeric_model(ROOT/'models/baseline.json')
baseline=Baseline(model,bootstraps,metadata['evaluation'],pd.read_csv(ROOT/'reports/generated/calibration.csv'),pd.read_csv(ROOT/'reports/generated/partitions.csv'),metadata['features'])
dataset=load_dataset()
context=AnalysisContext(fighter_a_id='032cc3922d871c7f',fighter_b_id='f4c49976c75c5ab2',reference_date='2018-10-06',weight_class='Lightweight',scheduled_rounds=5,draws=5000,seed=422)
config=ScenarioConfig(striking_effect=.35,grappling_effect=.5,counter_cost=.1,effect_half_width=.15,response_concentration=30)
result=analyze(dataset,context,config,baseline,modified_at='GUI illustrative preset; documented in usage guide')
neutral=analyze(dataset,context,ScenarioConfig(),baseline,modified_at='Neutral defaults; documented in usage guide')
custom,roots=one_way(result['baseline_probability'],config,'resistance',0,1)
payload={'guide_version':'v2-2026-10-16','mode':'Real historical profiles plus explicitly hypothetical GUI scenario','gui_preset':config.model_dump(mode='json'),'illustrative':json.loads(export_json(result)),'neutral':json.loads(export_json(neutral)),'custom_resistance_sweep':clean(custom),'custom_resistance_thresholds':clean(roots),'calibration':clean(baseline.calibration),'model_sha256':hashlib.sha256((ROOT/'models/baseline.json').read_bytes()).hexdigest()}
(folder/'guide_example.json').write_text(json.dumps(payload,indent=2,ensure_ascii=False,allow_nan=False),encoding='utf-8')
print(result['simulation']['summary'].to_string(index=False))
print(json.dumps(result['recommendation'],indent=2))
print('Resistance crossings:',roots)
