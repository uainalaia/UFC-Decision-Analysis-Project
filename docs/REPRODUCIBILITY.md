# Reproducibility

## Frozen inputs

The tracked `data/manifests/snapshot.json` identifies commit `5e38ebeb9bb854c9ab4359f8f6f5b444328c555c` and SHA-256 hashes for the published source CSVs, README and upstream license. The fetch command honors this commit by default. Raw and processed data are intentionally excluded from Git. Existing authorized local copies must match the recorded hashes; uploads become a separately labeled in-memory snapshot.

`requirements.lock` pins dependencies with hashes. The validated environment uses Python 3.12.14 on Windows. `uv pip sync requirements.lock` and `uv pip install --no-deps -e .` reconstruct the application environment. Analysis JSON records Python/package versions and the SHA-256 fingerprint of analytical source files.

## Historical example

```powershell
.venv/Scripts/python.exe scripts/run_example_analysis.py
```

This selects Khabib Nurmagomedov (source ID `032cc3922d871c7f`) against Conor McGregor (`f4c49976c75c5ab2`), before 2018-10-06, Lightweight, five scheduled rounds, seed 422, 5,000 draws, neutral effects. Both profiles have ten retained earlier bouts. All target-date information is excluded from feature generation/training.

For an explicitly hypothetical nonneutral example:

```powershell
.venv/Scripts/python.exe scripts/run_example_analysis.py --illustrative
```

This uses the documented illustrative tactical assumptions, **not** estimated intervention effects. Outputs go to `reports/generated/`: offline report, JSON record, result CSV, reproducibility ZIP, calibration, partitions and benchmark. Numeric model parameters are saved to `models/baseline.json`.

Reproduce an exported record:

```powershell
.venv/Scripts/python.exe scripts/run_example_analysis.py --config reports/generated/analysis.json --output reports/generated/reproduced
```

The CLI refuses a snapshot-version mismatch. Same versions, inputs, context, assumptions and seed reproduce analytical numeric outputs within 1e-12 in the tested environment. Created timestamps and Plotly HTML element IDs may differ; HTML byte identity is not promised. The command does not deserialize the exported JSON as Python code or model objects.

## Classroom path (3–5 minutes)

1. Open Overview with the default historical bout; note the date cutoff and exploratory forecast status.
2. Inspect Fighter Comparison and sample sizes.
3. Open Decision Model: neutral effects give identical policy utilities. Examine the computational tree.
4. Deliberately apply the **Illustrative effects (hypothetical)** preset.
5. Run Monte Carlo Analysis; distinguish parameter bands, scenario uncertainty and numerical error.
6. Open Sensitivity Analysis and inspect the switching conditions/decision map.
7. Generate the Research Report and download the JSON/ZIP.

No live API is used after initial installation. The worked notebook verifies the utility arithmetic with explicitly mathematical fixtures; it contains no fictitious UFC observations.
