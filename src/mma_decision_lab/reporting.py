"""Standalone HTML, safe CSV, strict JSON, and a reproducibility ZIP."""

import io
import json
import math
import zipfile
from datetime import date, datetime
from html import escape

import numpy as np
import pandas as pd

from .charts import decision_regions, sensitivity_lines, utility_intervals
from .config import REFERENCES
from .decision import POLICIES
from .theme import font_css, shared_styles


def clean(value):
    if isinstance(value, pd.DataFrame):
        return [clean(r) for r in value.to_dict("records")]
    if isinstance(value, np.ndarray):
        return clean(value.tolist())
    if isinstance(value, (np.integer, np.floating, np.bool_)):
        return clean(value.item())
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [clean(v) for v in value]
    if isinstance(value, (date, datetime, pd.Timestamp)):
        return value.isoformat()
    return value


def export_json(result):
    compact = {k: v for k, v in result.items() if k != "simulation"}
    compact["simulation"] = {k: v for k, v in result["simulation"].items() if k != "utilities"}
    compact["policies"] = [p.model_dump(mode="json") for p in POLICIES]
    compact["references"] = REFERENCES
    return json.dumps(clean(compact), indent=2, ensure_ascii=False, allow_nan=False)


def safe_csv(frame):
    frame = frame.copy()
    for col in frame.select_dtypes(include=["object"]):
        frame[col] = frame[col].map(
            lambda v: (
                "'" + v if isinstance(v, str) and v.lstrip().startswith(("=", "+", "-", "@")) else v
            )
        )
    return frame.to_csv(index=False).encode("utf-8-sig")


def _table(frame, caption, formatters=None):
    rendered = frame.to_html(
        index=False,
        escape=True,
        na_rep="Not observed",
        border=0,
        classes="record-table",
        formatters=formatters,
    )
    rendered = rendered.replace("<thead>", f"<caption>{escape(caption)}</caption><thead>", 1)
    return f'<div class="table-scroll" tabindex="0" aria-label="{escape(caption, quote=True)}">{rendered}</div>'


def _details(label, value):
    return (
        '<details class="technical-details"><summary>'
        + escape(label)
        + "</summary><pre>"
        + escape(json.dumps(clean(value), indent=2, ensure_ascii=False))
        + "</pre></details>"
    )


def _number(value, style="rate"):
    if value is None or (isinstance(value, (float, np.floating)) and not np.isfinite(value)):
        return "Not observed"
    if style == "count":
        return f"{value:,.0f}"
    if style == "percent":
        return f"{value:.1%}"
    if style == "text":
        return str(value)
    return f"{value:.2f}"


def _profile_table(result):
    metrics = [
        ("Experience", "Earlier eligible bouts", "prior_fights", "count"),
        ("Experience", "Observed exposure (min)", "observed_minutes", "rate"),
        ("Experience", "Last earlier appearance", "last_fight", "text"),
        ("Experience", "Last earlier division", "last_division", "text"),
        ("Experience", "Inactivity (years)", "inactivity_years", "rate"),
        ("Striking", "Significant strikes landed / min", "sig_landed_pm", "rate"),
        ("Striking", "Significant strikes absorbed / min", "sig_absorbed_pm", "rate"),
        ("Striking", "Smoothed striking accuracy", "sig_accuracy", "percent"),
        ("Striking", "Smoothed striking defense", "sig_defense", "percent"),
        ("Wrestling", "Takedowns landed / 15 min", "td_landed_15", "rate"),
        ("Wrestling", "Takedown attempts / 15 min", "td_attempts_15", "rate"),
        ("Wrestling", "Smoothed takedown accuracy", "td_accuracy", "percent"),
        ("Wrestling", "Smoothed takedown defense", "td_defense", "percent"),
        ("Grappling", "Submission attempts / 15 min", "sub_attempts_15", "rate"),
        ("Grappling", "Control seconds / observed min", "control_pm", "rate"),
    ]
    denominators = {
        "sig_accuracy": "total_sig_attempted",
        "td_accuracy": "total_td_attempted",
        "td_defense": "total_opp_td_attempted",
    }
    rows = []
    for group, label, key, style in metrics:
        row = {"Group": group, "Metric": label}
        for side, name in zip(("a", "b"), result["names"], strict=True):
            profile = result["profiles"][side]
            value = _number(profile.get(key), style)
            if key in denominators and profile.get(denominators[key]) == 0:
                value = "No observations"
            row[name] = value
        rows.append(row)
    return _table(pd.DataFrame(rows), "Earlier-date fighter evidence; common metrics and units")


def _summary_table(summary):
    rows = []
    for r in summary.itertuples():
        rows.append(
            {
                "Tactical priority": r.policy,
                "Mean modeled P(win)": f"{r.expected_utility:.3%}",
                "Central 95% band": f"{r.lower_95:.3%}–{r.upper_95:.3%}",
                "Change from paired baseline (pp)": f"{100 * r.difference_from_baseline:+.3f}",
                "Rank-first share": f"{r.rank_first_share:.1%}",
                "Expected regret (pp)": f"{100 * r.expected_regret:.3f}",
                "MC standard error (pp)": f"{100 * r.mc_standard_error:.4f}",
            }
        )
    return _table(pd.DataFrame(rows), "Calculated policy outcomes; pp = percentage points")


def _conclusion(result):
    recommendation = result["recommendation"]
    means = result["simulation"]["summary"]
    tied = means.loc[
        np.isclose(means.expected_utility, means.expected_utility.max(), atol=1e-12, rtol=0),
        "policy",
    ].tolist()
    if len(tied) > 1:
        explanation = (
            "The highest modeled mean is shared by "
            + ", ".join(tied)
            + ". There is no unique highest-mean alternative. Exact ties share rank-first mass equally. "
            "A robust preference still requires supported baseline evidence, the declared paired "
            "uncertainty margin and stability throughout the default tested grid. Tactical effects "
            "remain assumptions; these calculations do not identify an optimal real-world strategy."
        )
    else:
        explanation = recommendation["explanation"]
    return escape(recommendation["headline"]), escape(explanation)


def html_report(result):
    """Render one immutable analysis record; never invent an analysis timestamp."""
    names = [escape(n) for n in result["names"]]
    context = result["context"]
    evaluation = result["baseline_evaluation"]
    snapshot = result["snapshot"]
    scenario = result["scenario"]
    summary = result["simulation"]["summary"]
    timestamp = escape(str(result.get("analysis_created_at") or "Not recorded (legacy analysis)"))
    record_id = escape(str(result.get("analysis_id") or "Not recorded (legacy analysis)"))
    assumed = result["mode"].startswith("Scenario-only")
    evidence_state = (
        "Assumed baseline"
        if assumed
        else "Baseline support criterion met"
        if evaluation.get("supported")
        else "Exploratory baseline"
    )
    headline, explanation = _conclusion(result)
    interval = result["baseline_parameter_interval"]
    baseline_note = (
        "Fixed user assumption; no empirical baseline interval is available."
        if assumed
        else (
            f"Conditional bootstrap parameter interval: {interval[0]:.3%}–{interval[1]:.3%}; "
            f"{result['baseline_draw_count']} fitted bootstrap models. This is a conditional "
            "parameter approximation, not a complete predictive confidence interval."
        )
    )
    interval_fig = utility_intervals(summary, baseline=result["baseline_probability"])
    chart1 = interval_fig.to_html(
        full_html=False, include_plotlyjs=True, config={"responsive": True, "displaylogo": False}
    )
    chart2 = sensitivity_lines(result["one_way"], "grappling_effect").to_html(
        full_html=False, include_plotlyjs=False, config={"responsive": True, "displaylogo": False}
    )
    chart3 = decision_regions(result["two_way"]).to_html(
        full_html=False, include_plotlyjs=False, config={"responsive": True, "displaylogo": False}
    )
    policies = _table(
        pd.DataFrame(
            [
                {
                    "Tactical priority": p.name,
                    "Planned opportunity emphasis": p.description,
                    "Standing": f"{p.allocation[0]:.0%}",
                    "Clinch": f"{p.allocation[1]:.0%}",
                    "Ground": f"{p.allocation[2]:.0%}",
                }
                for p in POLICIES
            ]
        ),
        "Assumed static allocations; planned opportunities, not observed fight time",
    )
    parameter_labels = {
        "striking_effect": ("Assumed striking effect", "log-odds"),
        "grappling_effect": ("Assumed grappling effect", "log-odds"),
        "resistance": ("Opponent resistance index", "dimensionless"),
        "counter_cost": ("Counter-exposure cost", "log-odds"),
        "response_weights": ("Lower / expected / stronger response weights", "probabilities"),
        "effect_half_width": ("Triangular effect half-width", "log-odds"),
        "response_concentration": ("Dirichlet response concentration", "dimensionless"),
    }
    assumption_rows = []
    for key, value in scenario.items():
        label, unit = parameter_labels.get(key, (key.replace("_", " "), ""))
        if key == "response_weights":
            display = " / ".join(format(v, ".6g") for v in value)
        else:
            display = "Fixed response weights" if value is None else format(value, ".12g")
        assumption_rows.append({"Assumed parameter": label, "Applied value": display, "Unit": unit})
    assumptions = _table(
        pd.DataFrame(assumption_rows), "Applied tactical and uncertainty assumptions"
    )
    uncertainty = _table(
        summary[["policy", "empirical_parameter_sd", "scenario_assumption_sd"]].rename(
            columns={
                "policy": "Tactical priority",
                "empirical_parameter_sd": "Empirical-only SD (pp)",
                "scenario_assumption_sd": "Scenario-only SD (pp)",
            }
        ),
        "Controlled uncertainty comparisons; these SDs are not additive variance components",
        {
            "Empirical-only SD (pp)": lambda v: f"{100 * v:.3f}",
            "Scenario-only SD (pp)": lambda v: f"{100 * v:.3f}",
        },
    )
    pairwise = result["simulation"]["pairwise"].rename(
        columns={
            "policy_a": "Priority A",
            "policy_b": "Priority B",
            "mean_difference": "Mean A − B (pp)",
            "lower_95": "2.5% quantile (pp)",
            "upper_95": "97.5% quantile (pp)",
            "mc_standard_error": "MC standard error (pp)",
        }
    )
    pairwise_table = _table(
        pairwise,
        "Paired utility differences from the same integration draws",
        {col: lambda v: f"{100 * v:+.4f}" for col in pairwise.columns[2:]},
    )
    ranges = _table(
        pd.DataFrame(
            [
                {
                    "Parameter": parameter_labels.get(k, (k, ""))[0],
                    "Minimum": f"{v[0]:.6g}",
                    "Maximum": f"{v[1]:.6g}",
                }
                for k, v in result["sensitivity_ranges"].items()
            ]
        ),
        "Declared default stress ranges in this record",
    )
    thresholds = (
        _table(pd.DataFrame(result["thresholds"]), "Calculated top-ranking switching thresholds")
        if result["thresholds"]
        else "<p>No unique top-ranking switching threshold was found within the recorded one-way range.</p>"
    )
    recommendation = result["recommendation"]
    robustness = _table(
        pd.DataFrame(
            [
                {
                    "Recorded criterion or diagnostic": "Held-out baseline support criterion met",
                    "Value": "Yes" if evaluation.get("supported") else "No",
                },
                {
                    "Recorded criterion or diagnostic": "Lowest paired 2.5% advantage (pp)",
                    "Value": f"{100 * recommendation['paired_lower_95']:+.4f}",
                },
                {
                    "Recorded criterion or diagnostic": "Maximum paired MC standard error (pp)",
                    "Value": f"{100 * recommendation['paired_mc_standard_error']:.4f}",
                },
                {
                    "Recorded criterion or diagnostic": "Same leader throughout default tested grid",
                    "Value": "Yes" if recommendation["stable_across_tested_grid"] else "No",
                },
                {
                    "Recorded criterion or diagnostic": "Declared utility margin (pp)",
                    "Value": f"{100 * recommendation['tolerance']:.2f}",
                },
            ]
        ),
        "Recorded robustness criteria and paired diagnostics",
    )
    validation = "<p>No empirical forecasting evaluation attaches to this assumed baseline.</p>"
    if not assumed and "test" in evaluation:
        validation_frame = pd.DataFrame(
            {
                "Logistic baseline": evaluation["test"],
                "50/50 reference": evaluation["coin_reference"],
                "Win-rate-only reference": evaluation["winrate_reference"],
            }
        ).T.reset_index(names="Model")
        validation_frame = validation_frame.rename(
            columns={
                "brier": "Brier score ↓",
                "log_loss": "Log loss ↓",
                "accuracy": "Accuracy",
                "auc": "AUC",
            }
        )
        validation = _table(
            validation_frame,
            "Untouched chronological test; accuracy is a secondary measure",
            {
                "Brier score ↓": lambda v: f"{v:.5f}",
                "Log loss ↓": lambda v: f"{v:.5f}",
                "Accuracy": lambda v: f"{v:.1%}",
                "AUC": lambda v: _number(v, "rate"),
            },
        )
        partitions = pd.DataFrame(evaluation.get("partition_summary", {})).T.reset_index(
            names="Partition"
        )
        validation += _table(
            partitions.rename(columns={"n": "Bouts", "start": "First date", "end": "Last date"}),
            "Chronological evaluation partitions",
        )
        ci = evaluation.get("brier_difference_vs_coin_95_interval")
        if ci:
            validation += f"<p>95% iid bout-bootstrap interval for Brier(model) − Brier(50/50): <strong>{ci[0]:+.5f} to {ci[1]:+.5f}</strong>. Calibration remains descriptive; repeated-fighter dependence is not captured.</p>"
    quality_keys = {
        "input_fights": "Source result rows",
        "retained_fights": "Retained eligible bouts",
        "excluded_fights": "Excluded source rows",
        "round_rows": "Competitor-round records",
        "fighter_count": "Source fighter identities",
        "first_date": "First retained date",
        "last_date": "Last retained date",
    }
    quality = _table(
        pd.DataFrame(
            [
                {
                    "Snapshot measure": label,
                    "Value": _number(result["quality"][key], "text" if "date" in key else "count"),
                }
                for key, label in quality_keys.items()
                if key in result["quality"]
            ],
            columns=["Snapshot measure", "Value"],
        ),
        "Observed snapshot coverage and ingestion counts",
    )
    source_files = snapshot.get("files", [])
    file_hashes = _table(
        pd.DataFrame(
            [
                {
                    "Source file": f.get("file", "Not recorded"),
                    "SHA-256": f.get("sha256", "Not recorded"),
                }
                for f in source_files
            ],
            columns=["Source file", "SHA-256"],
        ),
        "Frozen input file hashes",
    )
    refs = "".join(
        f'<li><a href="{escape(r["url"], quote=True)}">{escape(r["title"])}</a></li>'
        for r in REFERENCES
    )
    limitations = list(result["warnings"]) + [
        "Tactical effects, allocations, opponent responses and uncertainty distributions are assumptions; no causal tactic effect is identified. Balanced is static, not a learned adaptive policy.",
        "This implementation uses a logistic baseline, not the full state-transition Markov model of Holmes et al. The reference research already uses simulation.",
        "Current archival records may contain later corrections; strict event dates do not establish an as-was publication-time backtest.",
        "Retained earlier bouts are not complete professional career records. Nonbinary, DQ and unsupported-format bouts are excluded. Full primary-source reconciliation and reuse rights remain outstanding.",
        "The baseline pools divisions and 3/5-round formats and does not estimate individualized division, bout-length, opponent-strength, injury, preparation or changing-form effects.",
        "Bout bootstrap ignores repeated-fighter dependence and conditions on the selected regularization and fixed historical features. Structural and empirical draws are assumed independent; the displayed components do not add to total variance.",
        "Pointwise sensitivity regions use central assumptions. Robustness is limited to the declared paired criterion and finite default grid, not all possible tactics, models or parameter ranges.",
    ]
    limitations_html = "".join(f"<li>{escape(w)}</li>" for w in dict.fromkeys(limitations))
    tree = result["tree"].rename(
        columns={
            "policy": "Priority",
            "response": "Opponent response",
            "response_probability": "Response probability",
            "conditional_outcome_probability": "Conditional outcome probability",
            "outcome": "Outcome",
            "utility": "Utility",
            "joint_probability": "Joint probability",
            "utility_contribution": "Utility contribution",
        }
    )
    tree_table = _table(
        tree,
        "Calculated decision → response → outcome → utility branches",
        {
            c: lambda v: f"{v:.6f}"
            for c in tree.columns
            if "probability" in c.lower() or c == "Utility contribution"
        },
    )
    provenance = _details("Full source provenance and implementation fingerprint", snapshot)
    technical = (
        _details("Full baseline evaluation record", evaluation)
        + _details(
            "Parameter definitions, bounds, defaults and modification record",
            result["parameter_provenance"],
        )
        + _details("Raw earlier-date profile record", result["profiles"])
        + _details("Full data-quality record", result["quality"])
        + _details("Runtime and dependency versions", result.get("runtime", {}))
    )
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MMA Decision Lab — {names[0]} vs {names[1]}</title><style>
    {font_css(embed=True)}
    {shared_styles()}
    *{{box-sizing:border-box}}body{{margin:0;background:#F3F5F7;color:#172126;font:15px/1.6 'IBM Plex Sans',Arial,sans-serif;font-variant-numeric:tabular-nums}}main{{max-width:1180px;margin:auto;padding:40px 32px 56px}}h1,h2,h3{{color:#172126;line-height:1.2}}h1{{font-family:'IBM Plex Sans Condensed','Arial Narrow',sans-serif;font-size:48px;margin:8px 0;overflow-wrap:anywhere}}h2{{font-size:24px;margin:0 0 16px}}h3{{font-size:18px;margin:24px 0 12px}}p{{margin:8px 0 16px}}a{{color:#882A3A;text-underline-offset:3px}}a:focus-visible,summary:focus-visible,.table-scroll:focus-visible{{outline:3px solid #2457A6;outline-offset:4px}}.brand{{font-weight:600;font-size:16px;color:#882A3A}}.record-type,.muted{{color:#59656F;font-size:13px}}.matchup{{display:grid;grid-template-columns:minmax(0,1fr) auto minmax(0,1fr);gap:24px;align-items:center;margin:24px 0}}.fighter-role{{color:#59656F;font-size:13px}}.versus{{font-size:16px;color:#59656F}}.context-line{{padding:12px 0;border-top:1px solid #D8DEE3;border-bottom:1px solid #D8DEE3}}.status{{display:inline-block;padding:4px 10px;border:1px solid #7A8791;border-radius:6px;font-size:13px;margin:0 0 12px}}section{{background:white;border-radius:8px;padding:28px 32px;margin:24px 0}}.decision{{border-left:4px solid #737B85}}.baseline{{font-size:24px;font-weight:600;margin:4px 0}}.baseline small{{font-size:13px;color:#59656F;font-weight:400}}.table-scroll{{overflow:auto;width:100%;margin:16px 0}}table{{width:100%;border-collapse:collapse;font-size:13px;text-align:left}}caption{{text-align:left;color:#59656F;font-size:13px;padding:0 0 10px}}th,td{{padding:10px 12px;border-bottom:1px solid #D8DEE3;vertical-align:top}}th{{font-weight:600;background:#F3F5F7}}td{{overflow-wrap:anywhere}}tbody tr:last-child td{{border-bottom:0}}details{{margin:16px 0;border-top:1px solid #D8DEE3;padding-top:12px}}summary{{cursor:pointer;font-weight:600}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;background:#F3F5F7;padding:16px;border-radius:6px;font-size:12px}}.chart{{width:100%;min-width:0;margin:16px 0}}.plotly-graph-div{{max-width:100%}}.record-id{{overflow-wrap:anywhere}}footer{{padding:8px 0;color:#59656F;font-size:13px}}li{{margin:8px 0}}@media(max-width:650px){{main{{padding:24px 16px}}section{{padding:20px 16px}}.matchup{{grid-template-columns:1fr;gap:8px}}h1{{font-size:34px}}h2{{font-size:22px}}.versus{{margin:4px 0}}}}@page{{size:A4;margin:15mm}}@media print{{html,body{{background:white!important;color:#111!important;font-size:10pt}}main{{max-width:none;padding:0}}section{{padding:14px 0;border-radius:0;margin:18px 0;border-top:1px solid #999}}h1{{font-size:28pt}}h2{{font-size:17pt;break-after:avoid}}h3,caption{{break-after:avoid}}.brand,.status,a{{color:#111!important}}.matchup{{gap:12px}}.decision{{border-left:3px solid #555;padding-left:12px}}table{{font-size:8pt;table-layout:fixed}}th,td{{padding:5px;overflow-wrap:anywhere}}thead{{display:table-header-group}}tr{{break-inside:avoid}}.table-scroll{{overflow:visible}}.chart,.plotly-graph-div{{break-inside:avoid;max-width:100%}}.plotly .main-svg{{filter:grayscale(1)}}.modebar{{display:none!important}}.technical-details{{display:none}}a{{text-decoration:underline}}footer{{break-inside:avoid}}p,li{{orphans:3;widows:3}}}}
    </style></head><body><main>
    <header><div class="brand">MMA Decision Lab</div><div class="record-type">Research record · {escape(evidence_state)}</div><div class="matchup"><div><div class="fighter-role">Focal fighter · Fighter A</div><h1>{names[0]}</h1></div><div class="versus">vs</div><div><div class="fighter-role">Opponent</div><h1>{names[1]}</h1></div></div><p class="context-line">Before <strong>{escape(context["reference_date"])}</strong> · {escape(context["weight_class"])} · {context["scheduled_rounds"]} scheduled rounds<br>Snapshot {escape(snapshot["dataset_version"])} · Model {escape(result["model_version"])} · Analysis created {timestamp}</p><p class="record-id muted">Analysis identity: {record_id}</p></header>
    <section class="decision"><span class="status">{escape(evidence_state)}</span><h2>{headline}</h2><p>{explanation}</p><p class="muted">Baseline source: {escape(result["mode"])}. Historical forecasts and hypothetical tactical effects have different evidential status.</p></section>
    <section><h2>Decision and applied assumptions</h2><p>The focal fighter and coaching team examine static pre-fight priorities. Within this binary model U(win)=1 and U(loss)=0, so expected utility equals modeled win probability. These allocations do not guarantee execution or time in a fight state.</p>{policies}<p class="muted">Reference allocation: Standing 50% / Clinch 25% / Ground 25%. This engineering origin is separate from Balanced priority and from observed historical profiles.</p>{assumptions}<p class="muted">All applied effects, resistance, response weights and uncertainty settings are assumed (Category C), not fitted interventions. Lower / expected / stronger resistance offsets are −0.25 / 0 / +0.25, clipped to [0,1]. Response weights are exogenous to policy. Identically neutral effects require s=g=c=0 and effect half-width=0.</p></section>
    <section><h2>Earlier-date evidence and baseline</h2><div class="baseline">{result["baseline_probability"]:.3%} <small>{"Assumed" if assumed else "Estimated"} P(Fighter A wins)</small></div><p>{escape(baseline_note)}</p><p>{escape(evaluation["status"])}</p>{_profile_table(result)}<p class="muted">Only observations strictly before {escape(context["reference_date"])} contribute. Rates are estimated from retained history; displayed ratios use the documented smoothing. Missing observations remain missing. Descriptive differences do not establish tactical advantages; a higher absorbed-strike rate is not automatically favorable.</p><h3>Forecasting evidence</h3>{validation}</section>
    <section><h2>Modeled outcomes and uncertainty</h2><div class="chart">{chart1}</div>{_summary_table(summary)}<p>Central 95% bands describe the specified parameter and assumption distribution, not uncertainty in a causal effect or the frequency of future win/loss observations. The dotted baseline is the central reference estimate; change from baseline uses paired baseline draws.</p>{uncertainty}<h3>Paired comparisons</h3>{pairwise_table}<p class="muted">Rank-first shares are conditional on this uncertainty model; exact ties share mass equally. Expected regret compares each policy with the best within the same common parameter draw. Future fight outcome randomness is integrated analytically.</p><p><strong>{context["draws"]:,} integration draws · Seed {context["seed"]}</strong>. Draw count is computational; increasing it reduces numerical error and adds no historical evidence.</p>{_details("Numerical convergence prefixes from the same draw stream", result["simulation"]["convergence"])}</section>
    <section><h2>Decision-tree calculation</h2><p>Decision: tactical priority → Chance: opponent response → Outcome: win/loss → Utility: 1/0. Expected utility is the sum of the calculated terminal contributions below; the tree uses central assumptions.</p>{tree_table}</section>
    <section><h2>Default sensitivity and robustness</h2><p>This record includes the engine's default grappling-effect one-way sweep and grappling-effect × resistance decision grid. Sensitivity grids explored separately in the interface are separate records and are not substituted into this report or its robustness criterion.</p>{ranges}<div class="chart">{chart2}</div>{thresholds}<div class="chart">{chart3}</div><p>Pointwise regions require a leading central utility gap above 0.01. S = Striking, G = Grappling, B = Balanced; the code <code>=</code> means no pointwise preference. Pointwise preference is distinct from full uncertainty robustness.</p><p>A conditional preferred strategy additionally requires supported held-out baseline evidence, a paired 2.5% advantage against every competitor above the declared 0.01 margin plus its numerical-error allowance, and the same leader throughout the default tested grid. These are engineering criteria, not universal scientific thresholds.</p>{robustness}{_details("Full default sensitivity and robustness diagnostics", {"recommendation": result["recommendation"], "tornado": result["tornado"], "thresholds": result["thresholds"]})}</section>
    <section><h2>Limitations and interpretation</h2><ul>{limitations_html}</ul></section>
    <section><h2>Data quality and provenance</h2>{quality}<p>Source: {escape(str(snapshot.get("source", "Not recorded")))}<br>Reuse / license status: {escape(str(snapshot.get("license", "Not independently established")))}</p>{file_hashes}<p class="muted record-id">Analytical implementation SHA-256: {escape(str(snapshot.get("implementation_sha256", "Not recorded")))}</p>{provenance}{technical}</section>
    <section><h2>Research foundations</h2><ul>{refs}</ul><p class="muted">References provide context; they do not imply endorsement or validate this implementation.</p></section>
    <footer>Independent academic research prototype. Not affiliated with or endorsed by UFC. Educational decision analysis; no wagering functionality. This HTML embeds its fonts and plotting runtime for offline reading. Structured JSON and CSV retain the numerical analysis record.</footer>
    </main></body></html>"""


def export_bundle(result):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("report.html", html_report(result))
        z.writestr("analysis.json", export_json(result))
        for name, frame in {
            "policy_results": result["simulation"]["summary"],
            "pairwise_differences": result["simulation"]["pairwise"],
            "convergence": result["simulation"]["convergence"],
            "decision_tree": result["tree"],
            "one_way": result["one_way"],
            "two_way": result["two_way"],
            "tornado": result["tornado"],
        }.items():
            z.writestr(name + ".csv", safe_csv(frame))
    return stream.getvalue()
