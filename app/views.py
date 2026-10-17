"""Eight focused views; presentation orchestration over the existing research engines."""

import copy
import hashlib
import json
from datetime import datetime
from html import escape
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import streamlit as st

from app import resources, state, ui
from mma_decision_lab import charts
from mma_decision_lab.config import REFERENCES, ROOT
from mma_decision_lab.data import ingest
from mma_decision_lab.decision import POLICIES, decision_tree
from mma_decision_lab.reporting import export_bundle, export_json, html_report, safe_csv
from mma_decision_lab.schemas import ScenarioConfig
from mma_decision_lab.sensitivity import one_way, two_way


def fight_brief():
    ui.header("Fight brief")
    ui.matchup_hero()
    st.write("Compare earlier evidence, test tactical assumptions and document the decision.")
    ui.next_page("fighter_evidence", "Review evidence", primary=True)
    ui.next_page("outcome_analysis", "Continue to outcome analysis")
    if ui.environment()["error"]:
        st.warning(ui.environment()["error"])
    st.subheader("Three tactical alternatives")
    ui.policy_rows()
    with st.expander("What the starting probability represents"):
        ui.baseline_note()
        st.write(
            "Observed data describe earlier bouts. The baseline is estimated; the tactical allocations and effects are assumed. Expected utility and sensitivity are calculated from those inputs."
        )


def fighter_evidence():
    ui.header("Fighter evidence")
    e = ui.environment()
    st.write("**Observed data · strictly before the cutoff**")
    st.caption(
        "The same metrics and units for both fighters. Ratios are smoothed with one success and two attempts only when an observed denominator exists; 0/0 remains missing."
    )
    groups = {
        "Striking": [
            ("Significant strikes landed / minute", "sig_landed_pm", "rate"),
            ("Significant strikes absorbed / minute", "sig_absorbed_pm", "rate"),
            ("Smoothed striking accuracy", "sig_accuracy", "percent"),
            ("Smoothed striking defense", "sig_defense", "percent"),
        ],
        "Wrestling": [
            ("Takedowns landed / 15 minutes", "td_landed_15", "rate"),
            ("Takedown attempts / 15 minutes", "td_attempts_15", "rate"),
            ("Smoothed takedown accuracy", "td_accuracy", "percent"),
            ("Smoothed takedown defense", "td_defense", "percent"),
        ],
        "Grappling": [
            ("Submission attempts / 15 minutes", "sub_attempts_15", "rate"),
            ("Control seconds / observed minute", "control_pm", "rate"),
        ],
        "Experience": [
            ("Earlier bouts", "prior_fights", "count"),
            ("Wins / earlier bouts", "win_rate", "percent"),
            ("Observed exposure (minutes)", "observed_minutes", "rate"),
            ("Last earlier appearance", "last_fight", "text"),
            ("Last recorded division", "last_division", "text"),
            ("Inactivity (years)", "inactivity_years", "rate"),
        ],
    }

    def number(value, kind):
        if value is None or isinstance(value, (float, np.floating)) and not np.isfinite(value):
            return "No observations"
        return (
            format(value, ".1%")
            if kind == "percent"
            else format(value, ",.0f")
            if kind == "count"
            else format(value, ".2f")
            if kind == "rate"
            else str(value)
        )

    rows = []
    for group, metrics in groups.items():
        rows.append(f'<tr class="mdl-group"><th colspan="3" scope="colgroup">{group}</th></tr>')
        for label, key, kind in metrics:
            values = [number(p.get(key), kind) for p in e["profiles"]]
            # win_rate is the smoothed feature; the human label names its construction.
            if key == "win_rate":
                label = "Smoothed historical win fraction"
            rows.append(
                f'<tr><th scope="row">{label}</th><td>{escape(values[0])}</td><td>{escape(values[1])}</td></tr>'
            )
    ui.html(
        '<div class="mdl-table-scroll" tabindex="0" aria-label="Earlier-date fighter comparison"><table class="mdl-comparison"><caption>Earlier-date evidence · observed sample and derived rates</caption><thead><tr><th scope="col">Metric</th>'
        + "".join(f'<th scope="col">{escape(n)}</th>' for n in e["names"])
        + "</tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table></div>"
    )
    with st.expander("Compare rate profiles visually"):
        ui.chart(charts.fighter_rates(e["profiles"], e["names"]))
    with st.expander("Inspect contributing bouts and denominators"):
        names = e["dataset"].fighters.set_index("fighter_id").fighter_name.to_dict()
        frames = []
        for fid, name in zip(
            (e["context"].fighter_a_id, e["context"].fighter_b_id), e["names"], strict=True
        ):
            bouts = e["dataset"].fights
            bouts = bouts[
                ((bouts.fighter_a_id == fid) | (bouts.fighter_b_id == fid))
                & (bouts.event_date < pd.Timestamp(e["context"].reference_date))
            ].copy()
            bouts["Fighter"] = name
            bouts["Opponent"] = [
                names[b if a == fid else a]
                for a, b in zip(bouts.fighter_a_id, bouts.fighter_b_id, strict=True)
            ]
            bouts["Outcome"] = [
                ("Win" if outcome == ("a_win" if a == fid else "b_win") else "Loss")
                for a, outcome in zip(bouts.fighter_a_id, bouts.result, strict=True)
            ]
            frames.append(
                bouts[
                    [
                        "Fighter",
                        "event_date",
                        "Opponent",
                        "Outcome",
                        "weight_class",
                        "duration_seconds",
                        "source_identifier",
                    ]
                ]
            )
        frame = pd.concat(frames).rename(
            columns={
                "event_date": "Date",
                "weight_class": "Division",
                "duration_seconds": "Exposure (seconds)",
                "source_identifier": "Source",
            }
        )
        st.dataframe(
            frame,
            hide_index=True,
            width="stretch",
            column_config={
                "Source": st.column_config.LinkColumn("Source", display_text="UFCStats")
            },
        )
        st.download_button(
            "Download contributing bouts", safe_csv(frame), "earlier_bouts.csv", "text/csv"
        )
        ui.table(
            pd.DataFrame(
                [
                    {
                        "Fighter": name,
                        **{
                            key: value for key, value in profile.items() if key.startswith("total_")
                        },
                    }
                    for name, profile in zip(e["names"], e["profiles"], strict=True)
                ]
            )
        )
    ui.next_page("tactical_model", "Set tactical assumptions", primary=True)


def tactical_model():
    ui.header("Tactical model")
    st.write("**Assumed · static opportunity allocations**")
    ui.policy_rows()
    st.caption(
        "Reference allocation: 50% standing / 25% clinch / 25% ground. Each policy is compared with this reference in the existing log-odds model."
    )
    state.begin_scenario_edit(st.session_state)

    def preset(illustrative):
        draft = (
            ScenarioConfig(
                striking_effect=0.35,
                grappling_effect=0.5,
                counter_cost=0.1,
                effect_half_width=0.15,
                response_concentration=30,
            ).model_dump(mode="json")
            if illustrative
            else ScenarioConfig().model_dump(mode="json")
        )
        st.session_state["scenario_draft"] = draft
        ui.clear_scenario_widgets()

    st.subheader("Edit assumptions")
    left, right = st.columns(2)
    left.button("Use neutral assumptions", on_click=preset, args=(False,))
    right.button(
        "Use illustrative assumptions",
        on_click=preset,
        args=(True,),
        help="Hypothetical scenario, not fitted tactical effects.",
    )
    left, right = st.columns(2)
    with left:
        ui.scenario_number("Striking effect (log-odds)", "striking_effect", -1.5, 1.5)
        ui.scenario_number(
            "Opponent resistance index",
            "resistance",
            0.0,
            1.0,
            help="Scenario index, not an observed takedown-defense rate.",
        )
    with right:
        ui.scenario_number("Grappling effect (log-odds)", "grappling_effect", -1.5, 1.5)
        ui.scenario_number("Counter-exposure cost (log-odds)", "counter_cost", 0.0, 1.0)
    with st.expander(
        "Opponent response and uncertainty", expanded=state.draft_dirty(st.session_state)
    ):
        st.caption("Response probabilities must sum to 1. They are not automatically normalized.")
        columns = st.columns(3)
        for i, (column, label) in enumerate(
            zip(
                columns,
                [
                    "Lower response probability",
                    "Expected response probability",
                    "Stronger response probability",
                ],
                strict=True,
            )
        ):
            key = "edit_scenario_weight_" + str(i)
            st.session_state.setdefault(
                key, float(st.session_state["scenario_draft"]["response_weights"][i])
            )
            column.number_input(
                label,
                min_value=0.0,
                max_value=1.0,
                step=0.05,
                key=key,
                on_change=ui.update_draft,
                args=("response_weights", key, i),
            )
        st.caption(
            f"Response sum: {sum(st.session_state['scenario_draft']['response_weights']):.3f}"
        )
        ui.scenario_number(
            "Effect uncertainty half-width (log-odds)", "effect_half_width", 0.0, 1.0
        )
        key = "edit_scenario_uncertain_response"
        st.session_state.setdefault(
            key, st.session_state["scenario_draft"]["response_concentration"] is not None
        )

        def toggle_response():
            st.session_state["scenario_draft"]["response_concentration"] = (
                30.0 if st.session_state[key] else None
            )
            st.session_state.pop("edit_scenario_response_concentration", None)

        st.checkbox(
            "Model uncertainty in response probabilities", key=key, on_change=toggle_response
        )
        if st.session_state[key]:
            ui.scenario_number(
                "Response concentration", "response_concentration", 3.0, 1000.0, step=1.0
            )
        st.caption(
            "Independent triangular tactical-effect distributions; optional Dirichlet response weights. Bounds must stay inside the model limits."
        )
    dirty = state.draft_dirty(st.session_state)
    if dirty:
        st.info("Unapplied changes · all views continue using the last applied assumptions.")
        changes = [
            {
                "Assumption": key.replace("_", " ").capitalize(),
                "Applied": str(st.session_state["applied_scenario"][key]),
                "Draft": str(value),
            }
            for key, value in st.session_state["scenario_draft"].items()
            if value != st.session_state["applied_scenario"][key]
        ]
        ui.table(pd.DataFrame(changes))
    left, right = st.columns(2)
    if left.button("Apply assumptions", type="primary", disabled=not dirty):
        try:
            state.apply_scenario(st.session_state)
            st.session_state["scenario_modified_at"] = datetime.now(
                ZoneInfo("America/Lima")
            ).isoformat(timespec="seconds")
            st.rerun()
        except ValueError as exc:
            st.error("Assumptions were not applied. " + str(exc))

    def cancel():
        state.cancel_scenario(st.session_state)
        ui.clear_scenario_widgets()

    right.button("Cancel assumption edits", on_click=cancel, disabled=not dirty)
    e = ui.environment()
    st.subheader("Applied decision tree")
    if e["p0"] is None:
        st.info(
            "A baseline is required to calculate the tree. Choose Scenario-only or prepare the historical baseline in Outcome analysis."
        )
    else:
        policy = st.selectbox("Tree alternative", [p.name for p in POLICIES], key="tree_policy")
        tree = decision_tree(e["p0"], e["config"])
        ui.chart(charts.tree_chart(tree, policy))
        with st.expander("Inspect all terminal branches and the calculation"):
            ui.table(tree[tree.policy == policy])
            st.latex(r"U(a)=\sum_r w_r\,\mathrm{logistic}\{\mathrm{logit}(p_0)+\Delta(a,r)\}")
            st.write(
                "The tree has three opponent responses and two binary outcomes for each static policy. Branch weights sum to one; win has utility 1 and loss utility 0."
            )
    ui.next_page("outcome_analysis", "Continue to outcome analysis", primary=True)


def outcome_analysis():
    ui.header("Outcome analysis")
    e = ui.environment()
    ui.scenario_summary(e["config"])
    ui.baseline_note()
    if e["source"] == "Historical model" and e["eligible"] and e["model"] is None:
        if st.button("Prepare historical baseline", type="primary"):
            try:
                with st.spinner(
                    "Preparing the existing chronological baseline procedure…", show_time=True
                ):
                    model = resources.prepare_baseline(
                        e["dataset"], e["token"], str(e["context"].reference_date)
                    )
                prepared = dict(st.session_state.get("prepared_models", {}))
                prepared[(e["token"], str(e["context"].reference_date))] = model
                st.session_state["prepared_models"] = prepared
                st.rerun()
            except ValueError as exc:
                st.error(
                    "Baseline preparation failed: "
                    + str(exc)
                    + ". Choose a later cutoff or Scenario-only."
                )
    with st.expander("Calculation settings"):

        def setting(field, key):
            st.session_state["applied_context"][field] = st.session_state[key]
            st.session_state["run_error"] = None

        for label, field, lower, upper in [
            ("Integration draws", "draws", 100, 100000),
            ("Random seed", "seed", 0, 2**32 - 1),
        ]:
            key = "calculation_" + field
            st.session_state.setdefault(key, int(st.session_state["applied_context"][field]))
            st.number_input(
                label,
                min_value=lower,
                max_value=upper,
                step=100 if field == "draws" else 1,
                key=key,
                on_change=setting,
                args=(field, key),
            )
        st.caption(
            "Draws integrate uncertainty; they are not additional historical fights. A fixed seed reproduces the calculation."
        )
    status = ui.result_status()
    ui.run_control()
    result = e["result"]
    if result is None:
        if status == "empty":
            st.info(
                "No completed result for this configuration. Run analysis to compare the alternatives with uncertainty."
            )
        else:
            ui.show_previous()
        return
    ui.decision_panel(result)
    ui.chart(
        charts.utility_intervals(
            result["simulation"]["summary"], baseline=result["baseline_probability"]
        )
    )
    st.caption(
        "Calculated · means and central 95% integration bands. Bands combine the available baseline parameter approximation and the explicitly assumed tactical uncertainty; they are not causal confidence intervals. The dotted line is the baseline point estimate."
    )
    ui.table(ui.policy_result_table(result))
    st.caption(
        "Difference uses a paired simulated baseline, so its mean can differ slightly from a subtraction of the baseline point estimate. Exact ties split rank-first mass equally; rank-first share is conditional on this assumed model."
    )
    ui.next_page("sensitivity", "Explore sensitivity", primary=True)
    ui.next_page("research_report", "Prepare research report")
    with st.expander("Paired comparisons and regret"):
        ui.table(ui.paired_result_table(result))
        st.write(
            "Expected regret is the expected utility lost relative to the best alternative within the same draw. Pairwise differences use the same draws, not independent simulations."
        )
    with st.expander("Uncertainty distributions and controlled comparisons"):
        ui.chart(charts.distributions(result["simulation"]))
        ui.table(ui.uncertainty_table(result))
        st.caption(
            "Controlled standard deviations describe separate sensitivity runs. They do not form an additive variance decomposition. A fixed assumed baseline has no empirical baseline uncertainty."
        )
    with st.expander("Convergence and reproducibility"):
        ui.chart(charts.convergence_chart(result["simulation"]["convergence"]))
        st.caption(ui.metadata_label(result))
        st.json(
            {
                "analysis_id": result.get("analysis_id"),
                "context": result["context"],
                "scenario": result["scenario"],
            }
        )


def sensitivity():
    ui.header("Sensitivity")
    e = ui.environment()
    if e["p0"] is None:
        st.info("A valid baseline is required before exploring sensitivity.")
        ui.next_page("outcome_analysis", "Prepare baseline in Outcome analysis", primary=True)
        return
    st.write("**Calculated · deterministic stress tests of assumed effects**")
    st.caption(
        "These grids vary explicit assumptions around the baseline point estimate. They are separate from Monte Carlo uncertainty and do not estimate tactical treatment effects."
    )
    params = ["striking_effect", "grappling_effect", "resistance", "counter_cost"]
    defaults = {
        "one_param": "grappling_effect",
        "one_low": -min(1.0, 1.5 - e["config"].effect_half_width),
        "one_high": min(1.0, 1.5 - e["config"].effect_half_width),
        "x_param": "grappling_effect",
        "x_low": -min(1.0, 1.5 - e["config"].effect_half_width),
        "x_high": min(1.0, 1.5 - e["config"].effect_half_width),
        "y_param": "resistance",
        "y_low": 0.0,
        "y_high": 1.0,
        "steps": 25,
    }
    settings = st.session_state.setdefault("sensitivity_settings", defaults)
    with st.form("one_way_controls"):
        st.subheader("One assumption at a time")
        param = st.selectbox(
            "One-way parameter",
            params,
            index=params.index(settings["one_param"]),
            format_func=charts.parameter_label,
        )
        left, right = st.columns(2)
        low = left.number_input("One-way minimum", value=float(settings["one_low"]), step=0.05)
        high = right.number_input("One-way maximum", value=float(settings["one_high"]), step=0.05)
        submit = st.form_submit_button("Apply one-way range")
    st.caption(
        "Only submitted ranges are stored. Leaving this form before submission discards its unsent widget edits; the last valid exploration remains available."
    )
    if submit:
        try:
            frame, roots = one_way(e["p0"], e["config"], param, low, high)
            st.session_state.setdefault("sensitivity_exploration", {})["one"] = {
                "signature": e["signature"],
                "frame": frame,
                "roots": roots,
                "parameter": param,
            }
            settings.update(one_param=param, one_low=low, one_high=high)
        except ValueError as exc:
            st.error(
                f"One-way range was not applied: {exc}. Use ordered bounds within the parameter limits and the applied uncertainty width."
            )
    explored = st.session_state.get("sensitivity_exploration", {})
    one = explored.get("one")
    if one and one["signature"] == e["signature"]:
        ui.chart(charts.sensitivity_lines(one["frame"], one["parameter"], e["config"].model_dump()))
        if one["roots"]:
            ui.table(
                pd.DataFrame(one["roots"]).rename(
                    columns={
                        "value": "Crossing value",
                        "from_policy": "Before crossing",
                        "to_policy": "After crossing",
                        "parameter": "Parameter",
                    }
                )
            )
        else:
            st.caption(
                "No top-ranking crossover was found within this tested range. Equality without a ranking change is not a crossover."
            )
        with st.expander("One-way values and download"):
            ui.table(one["frame"])
            st.download_button(
                "Download one-way values", safe_csv(one["frame"]), "one_way.csv", "text/csv"
            )
    else:
        st.info(
            "Apply a range to calculate the current one-way exploration."
            if one is None
            else "The saved exploration belongs to previous inputs. Apply a range to update it."
        )
    with st.form("two_way_controls"):
        st.subheader("Decision regions")
        left, right = st.columns(2)
        with left:
            xp = st.selectbox(
                "Horizontal assumption",
                params,
                index=params.index(settings["x_param"]),
                format_func=charts.parameter_label,
            )
            xl = st.number_input("Horizontal minimum", value=float(settings["x_low"]), step=0.05)
            xh = st.number_input("Horizontal maximum", value=float(settings["x_high"]), step=0.05)
        with right:
            yp = st.selectbox(
                "Vertical assumption",
                params,
                index=params.index(settings["y_param"]),
                format_func=charts.parameter_label,
            )
            yl = st.number_input("Vertical minimum", value=float(settings["y_low"]), step=0.05)
            yh = st.number_input("Vertical maximum", value=float(settings["y_high"]), step=0.05)
        steps = st.select_slider(
            "Grid points per axis", options=[15, 25, 31, 51], value=settings["steps"]
        )
        submit = st.form_submit_button("Apply decision-region ranges")
    if submit:
        try:
            grid = two_way(e["p0"], e["config"], xp, (xl, xh), yp, (yl, yh), steps=steps)
            st.session_state.setdefault("sensitivity_exploration", {})["two"] = {
                "signature": e["signature"],
                "frame": grid,
                "x": xp,
                "y": yp,
            }
            settings.update(
                x_param=xp, x_low=xl, x_high=xh, y_param=yp, y_low=yl, y_high=yh, steps=steps
            )
        except ValueError as exc:
            st.error(
                f"Decision-region ranges were not applied: {exc}. Choose different axes and valid ordered bounds."
            )
    two = st.session_state.get("sensitivity_exploration", {}).get("two")
    if two and two["signature"] == e["signature"]:
        ui.chart(
            charts.decision_regions(two["frame"], two["x"], two["y"], e["config"].model_dump())
        )
        st.caption(
            "A named region means its deterministic utility exceeds the second alternative by more than 1 percentage point at that grid point. Gray (=) means no such preference; a colored region alone does not satisfy the full robust recommendation criterion."
        )
        with st.expander("Decision-region values and download"):
            ui.table(two["frame"])
            st.download_button(
                "Download region values", safe_csv(two["frame"]), "decision_regions.csv", "text/csv"
            )
    else:
        st.info(
            "Apply decision-region ranges to calculate the current grid."
            if two is None
            else "The saved region grid belongs to previous inputs. Apply ranges to update it."
        )
    if e["result"] is not None:
        with st.expander("Reference-policy sensitivity in the analysis record"):
            ui.chart(charts.tornado_chart(e["result"]["tornado"]))
            st.caption(
                "The reference policy is selected deterministically by the engine. If means tie, its selection does not establish a tactical leader. This chart uses the analysis record’s default stress ranges."
            )
            ui.table(e["result"]["tornado"])
    st.caption(
        "Research reports preserve the engine’s declared default robustness ranges. The custom explorations on this page have their own CSV downloads and do not silently replace that scope."
    )
    ui.next_page("research_report", "Prepare research report", primary=True)


def validation():
    ui.header("Validation")
    e = ui.environment()
    forecast, data, technical = st.tabs(["Forecast evidence", "Data quality", "Technical checks"])
    with forecast:
        if e["model"] is None:
            st.info(
                "No historical baseline is prepared for this cutoff. Scenario-only assumptions carry no empirical validation."
            )
            ui.next_page("outcome_analysis", "Prepare historical baseline")
        else:
            evaluation = e["model"].evaluation
            ui.html(ui.baseline_badge())
            st.write(evaluation.get("status", "Held-out chronological evaluation"))
            st.caption(
                "Held-out outcomes assess this baseline forecasting procedure. They do not validate the assumed tactical effects."
            )
            metrics = evaluation["test"]
            left, middle, right = st.columns(3)
            left.metric("Brier score", f"{metrics['brier']:.4f}")
            middle.metric("Log loss", f"{metrics['log_loss']:.4f}")
            right.metric("Accuracy", f"{metrics['accuracy']:.1%}")
            st.caption(
                "Lower Brier score and log loss are better. Accuracy is a secondary threshold metric; it does not establish calibration."
            )
            partition = evaluation["partition_summary"]["test"]
            st.write(
                f"Held-out test: **{partition['n']:,} bouts** · {partition['start']} to {partition['end']}"
            )
            interval = evaluation["brier_difference_vs_coin_95_interval"]
            st.write(
                f"Brier difference against the 0.5 reference: **{interval[0]:+.5f} to {interval[1]:+.5f}** (95% resampling interval). "
                + (
                    "The interval includes zero; the support criterion is not met."
                    if interval[0] <= 0 <= interval[1]
                    else "Interpret this alongside the declared support criterion and sampling limitations."
                )
            )
            ui.table(
                pd.DataFrame(
                    [
                        {
                            "Forecast": label,
                            "Brier score": f"{evaluation[key]['brier']:.4f}",
                            "Log loss": f"{evaluation[key]['log_loss']:.4f}",
                            "Accuracy": f"{evaluation[key]['accuracy']:.1%}",
                            "ROC AUC": f"{evaluation[key]['auc']:.3f}",
                        }
                        for key, label in [
                            ("test", "Logistic baseline"),
                            ("coin_reference", "Fixed 0.5 reference"),
                            ("winrate_reference", "Historical win-fraction reference"),
                        ]
                    ]
                )
            )
            ui.chart(charts.calibration_chart(e["model"].calibration))
            st.caption(
                "Each point pools held-out predictions; bars are Wilson 95% intervals for observed fractions. Bin counts matter, particularly at the extremes. This plot describes calibration and cannot certify it."
            )
            ui.table(
                e["model"].calibration.rename(
                    columns={
                        "predicted": "Mean forecast",
                        "observed": "Observed win fraction",
                        "n": "Bouts",
                        "lower": "Wilson lower 95%",
                        "upper": "Wilson upper 95%",
                    }
                )
            )
            with st.expander("Chronological partitions and evaluation details"):
                ui.table(e["model"].partitions)
                st.download_button(
                    "Download partition audit",
                    safe_csv(e["model"].partitions),
                    "partitions.csv",
                    "text/csv",
                )
                st.json(evaluation)
    with data:
        q = e["dataset"].quality
        st.write(
            f"**{q['retained_fights']:,} retained bouts** from {q['input_fights']:,} raw records · {q['excluded_fights']:,} exclusions"
        )
        st.caption(
            f"Snapshot {e['dataset'].manifest['dataset_version']} · {q['first_date']} to {q['last_date']}. This is a frozen source archive, not a live feed."
        )
        ui.table(
            pd.DataFrame(
                [
                    {"Reason": reason, "Excluded bouts": n}
                    for reason, n in q["exclusion_reasons"].items()
                ]
            )
        )
        with st.expander("Missingness and exclusion records"):
            ui.table(
                pd.DataFrame(
                    [
                        {"Field": key, "Missing fraction": value}
                        for key, value in q["missing_fraction"].items()
                    ]
                )
            )
            ui.table(e["dataset"].exclusions)
            st.download_button(
                "Download exclusions",
                safe_csv(e["dataset"].exclusions),
                "exclusions.csv",
                "text/csv",
            )
        with st.expander("Import a compatible research snapshot"):
            st.caption(
                "Four CSV files, at most 12 MB each. Source identity, schemas and exclusions are checked before replacing the applied snapshot. Existing analyses and exports are cleared only after a valid import."
            )
            required = [
                "ufc_event_details.csv",
                "ufc_fighter_details.csv",
                "ufc_fight_results.csv",
                "ufc_fight_stats.csv",
            ]
            st.code("\n".join(required), language=None)
            files = st.file_uploader(
                "Snapshot CSV files", type=["csv"], accept_multiple_files=True, key="snapshot_files"
            )
            label = st.text_input("Snapshot label", value="Local research snapshot")
            if st.button("Validate and apply snapshot", disabled=not files):
                try:
                    if sorted(f.name for f in files) != sorted(required):
                        raise ValueError(
                            "Provide each of the four required filenames exactly once."
                        )
                    payload = {f.name: f.getvalue() for f in files}
                    manifest = {
                        "dataset_version": "local-"
                        + hashlib.sha256(b"".join(payload[k] for k in sorted(payload))).hexdigest()[
                            :12
                        ],
                        "source": label,
                        "files": [
                            {"name": k, "sha256": hashlib.sha256(v).hexdigest()}
                            for k, v in payload.items()
                        ],
                    }
                    imported = ingest(payload, manifest)
                    if imported.fights.empty:
                        raise ValueError("No eligible bouts remain in this snapshot.")
                    st.session_state["uploaded_dataset"] = imported
                    state.replace_snapshot(
                        st.session_state,
                        resources.snapshot_token(imported),
                        resources.default_context(imported),
                    )
                    st.rerun()
                except (ValueError, KeyError, pd.errors.ParserError) as exc:
                    st.error("Snapshot was not applied: " + str(exc))
            if "uploaded_dataset" in st.session_state and st.button(
                "Restore frozen research snapshot"
            ):
                original = resources.frozen_dataset(e["frozen_token"])
                st.session_state.pop("uploaded_dataset")
                state.replace_snapshot(
                    st.session_state,
                    resources.snapshot_token(original),
                    resources.default_context(original),
                )
                st.rerun()
    with technical:
        st.write(
            "The redesign preserves the existing equations, source snapshot, persisted model, policies and scientific thresholds."
        )
        path = ROOT / "reports/audit_v2/numbers.json"
        if path.exists():
            audit = json.loads(path.read_text(encoding="utf-8"))
            st.write(
                "Independent numerical reproduction: **"
                + ("passed" if audit.get("numeric_audit_passed") else "see recorded checks")
                + "**"
            )
            st.caption(
                "This audit is scoped to the documented frozen snapshot and reference analysis; it is not a guarantee for future datasets."
            )
            with st.expander("Inspect numerical audit evidence"):
                st.json(audit)
        st.caption(
            "Functional, browser and accessibility checks are documented in the repository review record. Statistical support remains a separate question."
        )


def research_report():
    ui.header("Research report")
    e = ui.environment()
    status = ui.result_status()
    result = e["result"]
    if result is None:
        st.info("Run the applied configuration before generating its research record.")
        ui.next_page("outcome_analysis", "Run analysis in Outcome analysis", primary=True)
        if status != "empty":
            ui.show_previous()
    else:
        ui.decision_panel(result)
        ui.chart(
            charts.utility_intervals(
                result["simulation"]["summary"], result["baseline_probability"]
            )
        )
        ui.table(ui.policy_result_table(result))
        st.caption(ui.metadata_label(result))
        with st.expander("Applied assumptions and limitations"):
            ui.scenario_summary(ScenarioConfig(**result["scenario"]))
            st.write(
                "Tactical effects are scenario assumptions. The baseline remains exploratory when its held-out support criterion is not met. The report uses the declared default sensitivity grid, not custom page explorations."
            )
        if st.button("Generate research report", type="primary"):
            record = copy.deepcopy(result)
            with st.spinner("Preparing the complete offline record…"):
                st.session_state["generated_report"] = {
                    "signature": e["signature"],
                    "names": record["names"],
                    "context": record["context"],
                    "snapshot": record["snapshot"]["dataset_version"],
                    "created": record["analysis_created_at"],
                    "html": html_report(record),
                    "json": export_json(record),
                    "csv": safe_csv(record["simulation"]["summary"]),
                    "zip": export_bundle(record),
                }
    generated = st.session_state.get("generated_report")
    if generated:
        previous = generated["signature"] != e["signature"] or status == "failed"
        st.subheader("Previous research record" if previous else "Research record ready")
        if previous:
            st.warning(
                "These downloads belong to the previous completed configuration shown below. Generate a new report after running the current configuration."
            )
        st.write(
            f"**{generated['names'][0]} vs {generated['names'][1]}** · before {generated['context']['reference_date']}"
        )
        st.caption(
            f"{generated['snapshot']} · {generated['context']['draws']:,} draws · seed {generated['context']['seed']} · created {generated['created']}"
        )
        left, right = st.columns(2)
        left.download_button(
            "Download offline HTML",
            generated["html"],
            "mma_research_report.html",
            "text/html",
            width="stretch",
        )
        right.download_button(
            "Download reproducibility ZIP",
            generated["zip"],
            "mma_research_record.zip",
            "application/zip",
            width="stretch",
        )
        left.download_button(
            "Download results CSV", generated["csv"], "mma_results.csv", "text/csv", width="stretch"
        )
        right.download_button(
            "Download analysis JSON",
            generated["json"],
            "mma_analysis.json",
            "application/json",
            width="stretch",
        )
        st.caption(
            "HTML includes Plotly and local fonts, with readable tables and a print layout. JSON and ZIP retain the record’s original context and reproducibility metadata."
        )


def methodology():
    ui.header("Methodology")
    st.subheader("What decision does the lab examine?")
    st.write(
        "For one focal fighter and one opponent, compare three static allocations of planned standing, clinch and ground opportunities. Utilities are conditional modeled win probabilities under explicit assumptions."
    )
    ui.table(
        pd.DataFrame(
            [
                {
                    "Origin": "Observed data",
                    "Meaning": "Retained earlier bouts, action counts, exposure and source identity.",
                },
                {
                    "Origin": "Estimated",
                    "Meaning": "Regularized logistic baseline fitted to strict earlier-date profile differences; conditional bootstrap approximation.",
                },
                {
                    "Origin": "Assumed",
                    "Meaning": "Static allocations, tactical coefficients, resistance, exposure cost, response weights and their uncertainty.",
                },
                {
                    "Origin": "Calculated",
                    "Meaning": "Decision tree, expected utilities, paired Monte Carlo comparisons, regret and sensitivity grids.",
                },
            ]
        )
    )
    st.subheader("What does the evidence support?")
    st.write(
        "The baseline uses chronological train, validation and test partitions. The interface reports proper probability scores and calibration with sample counts. A support criterion and a robust decision criterion are separate; a plausible-looking chart does not establish either."
    )
    st.write(
        "Neutral means zero striking effect, zero grappling effect, zero exposure cost and zero effect uncertainty half-width. In that case every policy shares the baseline in each draw, with equal rank-first shares."
    )
    st.write(
        "Balanced priority is a fixed allocation, not an adaptive learned policy. The archive does not identify interventions or causal tactical effects. Scenario-only mode uses an explicit user assumption with no empirical forecast validation."
    )
    with st.expander("Model equations and robustness criteria"):
        st.latex(
            r"p(a,r)=\mathrm{logistic}[\mathrm{logit}(p_0)+\Delta(a,r)],\quad U(a)=\sum_r w_r p(a,r)"
        )
        st.write(
            "The engine applies its existing log-odds tactical shift relative to the reference allocation. A robust preference requires supported baseline evidence, a paired 95% advantage above 1 percentage point plus the Monte Carlo error allowance, and stability throughout the declared default two-parameter grid."
        )
        st.write(
            "Monte Carlo integrates uncertainty using a fixed seed. The bands summarize the parameter and scenario distributions supplied to this model; they are not causal intervals or individual-fight guarantees."
        )
    with st.expander("Earlier-date rules, missing data and exclusions"):
        st.write(
            "Profiles exclude the target fight and every observation on its calendar date. Eligibility requires at least two retained earlier bouts in total per fighter and a matching last recorded division. Missing denominators remain missing; the fitted pipeline handles predictor missingness using its existing preprocessing."
        )
        st.write(
            "The frozen source includes only retained binary outcomes and supported three/five-round formats after identity and consistency checks. Validation provides exclusions and missingness without replacing absent observations with convenient zeros."
        )
    st.subheader("Research and provenance")
    st.write(
        "Holmes and colleagues already use simulation in their Markov forecasting study. This implementation uses its own regularized logistic baseline; it does not implement that paper’s complete Markov model. The lab’s contribution is to formulate and examine explicit tactical alternatives and their sensitivity."
    )
    for ref in REFERENCES:
        st.markdown(f"[{ref['title']}]({ref['url']})")
    with st.expander("Snapshot, software and parameter provenance"):
        e = ui.environment()
        st.json(e["dataset"].manifest)
        if e["result"]:
            provenance = pd.DataFrame(e["result"]["parameter_provenance"])
            # Scalar/tuple/None assumptions share these presentation columns.
            # Explicit JSON text avoids Arrow's automatic mixed-type repair.
            for column in ("value", "default", "admissible_range"):
                provenance[column] = provenance[column].map(
                    lambda value: json.dumps(value, ensure_ascii=False)
                )
            ui.table(provenance)
            st.json(e["result"]["runtime"])
        else:
            st.caption(
                "Run analysis to record the exact runtime and parameter modification metadata."
            )
    st.caption(
        "Independent academic prototype. Cited authors, institutions, data providers and products have not endorsed or evaluated this application."
    )
