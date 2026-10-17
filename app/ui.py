"""Reusable presentation and native controls; all model equations remain in src."""

import copy
from html import escape
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

from app import state
from mma_decision_lab.analysis import analyze
from mma_decision_lab.decision import POLICIES
from mma_decision_lab.theme import PHASE_COLORS, shared_styles


def environment():
    return st.session_state["_environment"]


def install_styles():
    css = (Path(__file__).parent / "styles.css").read_text(encoding="utf-8")
    st.markdown("<style>" + shared_styles() + css + "</style>", unsafe_allow_html=True)


def html(value):
    st.markdown(value, unsafe_allow_html=True)


def pretty_date(value):
    return pd.Timestamp(value).strftime("%d %b %Y").lstrip("0")


def table(frame):
    st.dataframe(frame, hide_index=True, width="stretch")


def chart(fig):
    st.plotly_chart(
        fig,
        width="stretch",
        theme=None,
        config={
            "displaylogo": False,
            "responsive": True,
            "toImageButtonOptions": {"format": "png", "scale": 2},
        },
    )


def next_page(key, label, primary=False):
    if primary:
        with st.container(key="primary_link"):
            st.page_link(st.session_state["_pages"][key], label=label)
    else:
        st.page_link(st.session_state["_pages"][key], label=label)


def header(title):
    e = environment()
    ctx = e["context"]
    with st.container(key="context_bar"):
        left, right = st.columns([4, 1], vertical_alignment="center")
        with left:
            st.title(title)
        with right:
            if st.button("Change matchup", key="change_matchup", width="stretch"):
                st.session_state["matchup_edit_open"] = not st.session_state.get(
                    "matchup_edit_open", False
                )
        if title != "Fight brief":
            st.write(f"**{e['names'][0]}** vs **{e['names'][1]}**")
        html(
            f'<div class="mdl-context"><span>Cutoff <strong>{pretty_date(ctx.reference_date)}</strong></span><span><strong>{escape(ctx.weight_class)}</strong></span><span><strong>{ctx.scheduled_rounds} scheduled rounds</strong></span><span>Focal fighter: <strong>{escape(e["names"][0])}</strong></span></div>'
        )
    if st.session_state.get("matchup_edit_open"):
        matchup_editor()
    if state.draft_dirty(st.session_state) and title != "Tactical model":
        st.info(
            "Unapplied tactical edits are saved in Tactical model. This page uses the applied assumptions."
        )


def baseline_badge():
    e = environment()
    if e["source"] != "Historical model":
        return '<span class="mdl-badge neutral">Assumed baseline</span>'
    if e["p0"] is None:
        return '<span class="mdl-badge neutral">Baseline unavailable</span>'
    if not e["model"].evaluation["supported"]:
        return '<span class="mdl-badge">Exploratory baseline</span>'
    return '<span class="mdl-badge neutral">Held-out baseline evidence</span>'


def baseline_note():
    e = environment()
    if e["error"]:
        st.warning(e["error"])
    elif e["source"] == "Historical model":
        html(
            baseline_badge()
            + '<span class="mdl-unit">Estimated from earlier fight histories. Calibration remains descriptive.</span>'
        )
        next_page("validation", "Review forecasting evidence")
    else:
        html(
            baseline_badge()
            + '<span class="mdl-unit">User-entered probability; no empirical forecast validation attaches to it.</span>'
        )


def matchup_hero():
    e = environment()
    a, b = e["profiles"]
    value = f"{e['p0']:.1%}" if e["p0"] is not None else "Unavailable"
    fighters = []
    for name, profile, role in zip(
        e["names"], [a, b], ["Fighter A · focal fighter", "Opponent"], strict=True
    ):
        fighters.append(
            f'<div><p class="mdl-role">{role}</p><h2 class="mdl-fighter-name">{escape(name)}</h2><p class="mdl-meta">{profile["prior_fights"]} earlier bouts · {profile["wins"]} {"win" if profile["wins"] == 1 else "wins"} / {profile["losses"]} {"loss" if profile["losses"] == 1 else "losses"}</p></div>'
        )
    html(
        '<section class="mdl-matchup" aria-label="Applied matchup"><div class="mdl-fighters">'
        + fighters[0]
        + '<span class="mdl-versus">versus</span>'
        + fighters[1]
        + f'</div><div class="mdl-baseline"><div><span class="mdl-unit">Baseline modeled win probability · Fighter A</span><span class="mdl-baseline-value">{value}</span></div><div>{baseline_badge()}<span class="mdl-unit">'
        + (
            "A forecast estimate, not an established tactical effect."
            if e["source"] == "Historical model"
            else "An explicit scenario assumption."
        )
        + "</span></div></div></section>"
    )


def policy_rows():
    rows = []
    for policy in POLICIES:
        segments = "".join(
            f'<span style="width:{q * 100}%;background:{color}" aria-hidden="true"></span>'
            for q, color in zip(policy.allocation, PHASE_COLORS.values(), strict=True)
        )
        labels = "".join(
            f"<span>{label} <strong>{q:.0%}</strong></span>"
            for label, q in zip(PHASE_COLORS, policy.allocation, strict=True)
        )
        rows.append(
            f'<div class="mdl-policy"><div><h3>{policy.name}</h3><p>{escape(policy.description)}</p></div><div><div class="mdl-phasebar">{segments}</div><div class="mdl-phaselabels">{labels}</div></div></div>'
        )
    html(
        '<section aria-label="Assumed tactical opportunity allocations">'
        + "".join(rows)
        + "</section>"
    )
    st.caption(
        "Assumed planned opportunities, not observed fight time. Balanced priority is a fixed, static allocation."
    )


def decision_panel(result, previous=False):
    summary = result["simulation"]["summary"]
    tied = np.ptp(summary.expected_utility.to_numpy()) <= 1e-12
    text = (
        "The three alternatives have equal modeled expected utility under the applied assumptions. Their shared parameter distribution is shown below; there is no unique tactical leader."
        if tied
        else result["recommendation"]["explanation"]
    )
    badge = "Previous analysis" if previous else "Calculated · current analysis"
    html(
        f'<section class="mdl-decision" aria-label="Decision interpretation"><span class="mdl-badge neutral">{badge}</span><h2>{escape(result["recommendation"]["headline"])}</h2><p>{escape(text)}</p><p>Tactical effects are assumptions. This analysis does not establish a causal advantage.</p></section>'
    )


def result_status():
    e = environment()
    status = state.result_state(st.session_state, e["signature"])
    if status == "stale":
        st.warning(
            "Inputs changed. The previous analysis belongs to another configuration; run the applied configuration to update the result."
        )
    elif status == "failed":
        st.error(st.session_state["run_error"])
        st.caption(
            "The last completed record is preserved as a previous analysis. It is not shown as a successful current run."
        )
    return status


def show_previous():
    record = st.session_state.get("analysis_records", {}).get(
        st.session_state.get("last_record_id")
    )
    if record:
        with st.expander("Inspect previous analysis record"):
            st.write(
                f"**{record['names'][0]} vs {record['names'][1]}** · before {record['context']['reference_date']}"
            )
            st.caption(
                f"Snapshot {record['snapshot']['dataset_version']} · seed {record['context']['seed']} · {record['context']['draws']:,} draws. Every value below belongs to this previous record."
            )
            decision_panel(record, previous=True)
            table(policy_result_table(record))
            st.json({"context": record["context"], "scenario": record["scenario"]})


def run_control():
    e = environment()
    slot = st.empty()
    if slot.button(
        "Run analysis",
        type="primary",
        disabled=e["error"] is not None or st.session_state.get("running", False),
        key="run_analysis",
    ):
        st.session_state["running"] = True
        slot.empty()
        slot.button("Analysis running…", disabled=True, key="running_analysis")
        try:
            with st.spinner(
                "Integrating uncertainty and checking the applied assumptions…", show_time=True
            ):
                result = analyze(
                    e["dataset"],
                    e["context"],
                    e["config"],
                    e["model"],
                    st.session_state["manual_probability"]
                    if e["source"] != "Historical model"
                    else None,
                    modified_at=st.session_state.get(
                        "scenario_modified_at", "Initial neutral defaults"
                    ),
                )
                state.store_result(st.session_state, e["signature"], result)
        except (ValueError, ArithmeticError, RuntimeError) as exc:
            st.session_state["run_error"] = (
                f"Analysis could not complete: {exc}. Check the applied inputs and retry."
            )
        finally:
            st.session_state["running"] = False
        st.rerun()


def policy_result_table(result):
    s = result["simulation"]["summary"]
    return pd.DataFrame(
        {
            "Tactical priority": s.policy,
            "Modeled win probability": s.expected_utility.map(lambda v: f"{v:.2%}"),
            "Central 95% band": [
                f"{a:.2%}–{b:.2%}" for a, b in zip(s.lower_95, s.upper_95, strict=True)
            ],
            "Difference from paired baseline": s.difference_from_baseline.map(
                lambda v: f"{v * 100:+.2f} pp"
            ),
            "Rank-first share (assumed model)": s.rank_first_share.map(lambda v: f"{v:.1%}"),
            "Expected regret (pp)": s.expected_regret.map(lambda v: f"{v * 100:.3f}"),
        }
    )


def paired_result_table(result):
    frame = result["simulation"]["pairwise"].copy()
    labels = {
        "policy_a": "Priority A",
        "policy_b": "Priority B",
        "mean_difference": "Mean A − B (pp)",
        "lower_95": "Central 95% lower (pp)",
        "upper_95": "Central 95% upper (pp)",
        "mc_standard_error": "MC standard error (pp)",
    }
    for col in frame.select_dtypes(include=["number"]):
        frame[col] = frame[col].map(lambda value: f"{100 * value:+.4f}")
    return frame.rename(columns=labels)


def uncertainty_table(result):
    frame = result["simulation"]["summary"][
        ["policy", "empirical_parameter_sd", "scenario_assumption_sd"]
    ].copy()
    for col in ["empirical_parameter_sd", "scenario_assumption_sd"]:
        frame[col] = frame[col].map(lambda value: f"{100 * value:.3f}")
    return frame.rename(
        columns={
            "policy": "Tactical priority",
            "empirical_parameter_sd": "Empirical-only SD (pp)",
            "scenario_assumption_sd": "Scenario-only SD (pp)",
        }
    )


def scenario_summary(config):
    neutral = (
        config.striking_effect
        == config.grappling_effect
        == config.counter_cost
        == config.effect_half_width
        == 0
    )
    st.write("**Neutral effects**" if neutral else "**Explicit tactical scenario assumptions**")
    html(
        f'<div class="mdl-inline-values"><span>Striking effect <strong>{config.striking_effect:+.2f}</strong></span><span>Grappling effect <strong>{config.grappling_effect:+.2f}</strong></span><span>Resistance <strong>{config.resistance:.2f}</strong></span><span>Exposure cost <strong>{config.counter_cost:.2f}</strong></span></div>'
    )
    st.caption(
        f"Effects/cost use log-odds coefficients. Effect uncertainty half-width {config.effect_half_width:.2f}; response weights "
        + " / ".join(f"{v:.0%}" for v in config.response_weights)
        + (
            "; Dirichlet concentration " + str(config.response_concentration)
            if config.response_concentration
            else "; fixed response weights"
        )
    )


def update_draft(field, key, index=None):
    value = st.session_state[key]
    draft = copy.deepcopy(st.session_state["scenario_draft"])
    if index is None:
        draft[field] = value
    else:
        values = list(draft[field])
        values[index] = value
        draft[field] = values
    st.session_state["scenario_draft"] = draft


def scenario_number(label, field, lower, upper, step=0.05, help=None):
    key = "edit_scenario_" + field
    if key not in st.session_state:
        st.session_state[key] = float(st.session_state["scenario_draft"][field])
    st.number_input(
        label,
        min_value=lower,
        max_value=upper,
        step=step,
        key=key,
        on_change=update_draft,
        args=(field, key),
        help=help,
    )


def clear_scenario_widgets():
    for key in list(st.session_state):
        if key.startswith("edit_scenario_"):
            del st.session_state[key]


def matchup_editor():
    e = environment()
    d = e["dataset"]
    names = d.fighters.set_index("fighter_id").fighter_name.to_dict()
    applied = st.session_state["applied_context"]
    if "matchup_draft" not in st.session_state:
        st.session_state["matchup_draft"] = {
            **copy.deepcopy(applied),
            "source": st.session_state["baseline_source"],
            "manual": st.session_state["manual_probability"],
            "mode": "Historical bout",
        }
    draft = st.session_state["matchup_draft"]

    def remember(field, key):
        st.session_state["matchup_draft"][field] = st.session_state[key]

    with st.expander("Edit matchup · changes are not applied yet", expanded=True):
        st.caption(
            "Draft values persist while you navigate. Apply matchup commits them together; Cancel keeps the current applied context."
        )
        mode = st.selectbox(
            "Matchup selection",
            ["Historical bout", "Custom matchup"],
            index=["Historical bout", "Custom matchup"].index(draft["mode"]),
            key="edit_matchup_mode",
            on_change=remember,
            args=("mode", "edit_matchup_mode"),
        )
        if mode == "Historical bout":
            fights = d.fights.sort_values("event_date", ascending=False).set_index("fight_id")
            selected = fights[
                (fights.fighter_a_id.isin([draft["fighter_a_id"], draft["fighter_b_id"]]))
                & (fights.fighter_b_id.isin([draft["fighter_a_id"], draft["fighter_b_id"]]))
            ]
            fallback = selected.index[0] if len(selected) else fights.index[0]
            ids = fights.index.tolist()
            bid = st.selectbox(
                "Search historical bouts",
                ids,
                index=ids.index(draft.get("bout_id", fallback))
                if draft.get("bout_id", fallback) in ids
                else 0,
                format_func=lambda fid: (
                    f"{fights.loc[fid, 'event_date'].date()} · {names[fights.loc[fid, 'fighter_a_id']]} vs {names[fights.loc[fid, 'fighter_b_id']]}"
                ),
                key="edit_matchup_bout",
                on_change=remember,
                args=("bout_id", "edit_matchup_bout"),
            )
            fight = fights.loc[bid]
            competitors = [fight.fighter_a_id, fight.fighter_b_id]
            focal = st.selectbox(
                "Focal fighter",
                competitors,
                index=competitors.index(draft["fighter_a_id"])
                if draft["fighter_a_id"] in competitors
                else 0,
                format_func=lambda fid: names[fid],
                key="edit_matchup_focal",
                on_change=remember,
                args=("fighter_a_id", "edit_matchup_focal"),
            )
            candidate = {
                **applied,
                "fighter_a_id": focal,
                "fighter_b_id": next(v for v in competitors if v != focal),
                "reference_date": str(fight.event_date.date()),
                "weight_class": fight.weight_class,
                "scheduled_rounds": int(fight.scheduled_rounds),
            }
            st.caption(
                f"Applied only after confirmation: before {candidate['reference_date']}; {candidate['weight_class']}; {candidate['scheduled_rounds']} rounds. Same-day observations are excluded."
            )
        else:
            ids = sorted(
                set(d.fights.fighter_a_id) | set(d.fights.fighter_b_id),
                key=lambda fid: (names[fid], fid),
            )
            c1, c2 = st.columns(2)
            a = c1.selectbox(
                "Fighter A",
                ids,
                index=ids.index(draft["fighter_a_id"]) if draft["fighter_a_id"] in ids else 0,
                format_func=lambda fid: names[fid],
                key="edit_matchup_a",
                on_change=remember,
                args=("fighter_a_id", "edit_matchup_a"),
            )
            others = [fid for fid in ids if fid != a]
            b = c2.selectbox(
                "Opponent",
                others,
                index=others.index(draft["fighter_b_id"]) if draft["fighter_b_id"] in others else 0,
                format_func=lambda fid: names[fid],
                key="edit_matchup_b",
                on_change=remember,
                args=("fighter_b_id", "edit_matchup_b"),
            )
            c1, c2, c3 = st.columns(3)
            cutoff = c1.date_input(
                "Information cutoff",
                value=pd.Timestamp(draft["reference_date"]).date(),
                min_value=d.fights.event_date.min().date(),
                key="edit_matchup_date",
                on_change=remember,
                args=("reference_date", "edit_matchup_date"),
            )
            divisions = sorted(d.fights.weight_class.unique())
            division = c2.selectbox(
                "Agreed division",
                divisions,
                index=divisions.index(draft["weight_class"])
                if draft["weight_class"] in divisions
                else 0,
                key="edit_matchup_division",
                on_change=remember,
                args=("weight_class", "edit_matchup_division"),
            )
            rounds = c3.selectbox(
                "Scheduled rounds",
                [3, 5],
                index=[3, 5].index(draft["scheduled_rounds"]),
                key="edit_matchup_rounds",
                on_change=remember,
                args=("scheduled_rounds", "edit_matchup_rounds"),
            )
            candidate = {
                **applied,
                "fighter_a_id": a,
                "fighter_b_id": b,
                "reference_date": str(cutoff),
                "weight_class": division,
                "scheduled_rounds": rounds,
            }
        source = st.selectbox(
            "Baseline source",
            ["Historical model", "Scenario-only"],
            index=["Historical model", "Scenario-only"].index(draft["source"]),
            key="edit_matchup_source",
            on_change=remember,
            args=("source", "edit_matchup_source"),
        )
        probability = st.number_input(
            "Assumed baseline probability",
            min_value=0.01,
            max_value=0.99,
            value=float(draft["manual"]),
            step=0.01,
            disabled=source == "Historical model",
            key="edit_matchup_probability",
            on_change=remember,
            args=("manual", "edit_matchup_probability"),
            help="Used only in scenario-only mode. It is an assumption, not a forecast.",
        )
        left, right = st.columns(2)
        if left.button("Apply matchup", type="primary", key="apply_matchup"):
            try:
                state.apply_matchup(st.session_state, candidate, source, probability)
                st.session_state["matchup_edit_open"] = False
                st.session_state.pop("matchup_draft", None)
                for key in list(st.session_state):
                    if key.startswith("edit_matchup_"):
                        del st.session_state[key]
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))
        if right.button("Cancel matchup edits", key="cancel_matchup"):
            st.session_state["matchup_edit_open"] = False
            st.session_state.pop("matchup_draft", None)
            for key in list(st.session_state):
                if key.startswith("edit_matchup_"):
                    del st.session_state[key]
            st.rerun()


def metadata_label(result):
    ctx = result["context"]
    return f"{result['snapshot']['dataset_version']} · Model {result['model_version']} · {ctx['draws']:,} draws · seed {ctx['seed']} · Created {result.get('analysis_created_at', 'Not recorded (legacy analysis)')}"
