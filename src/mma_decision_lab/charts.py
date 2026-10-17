"""Presentation-only Plotly views of the unchanged analytical outputs."""

from collections.abc import Mapping

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .decision import POLICIES
from .theme import POLICY_COLORS, TOKENS

TEXT = TOKENS["text"]
MUTED = TOKENS["muted"]
GRID = TOKENS["separator"]
SURFACE = TOKENS["surface"]
SYMBOLS = ("circle", "square", "diamond")
DASHES = ("solid", "dash", "dot")
PARAMETER_LABELS = {
    "striking_effect": "Striking effect (log-odds)",
    "grappling_effect": "Grappling effect (log-odds)",
    "resistance": "Opponent resistance index",
    "counter_cost": "Counter-exposure cost (log-odds)",
}
SHORT_POLICIES = ("Striking", "Grappling", "Balanced")
REGION_LABELS = (*SHORT_POLICIES, "No preference")
REGION_CODES = ("S", "G", "B", "=")


def parameter_label(parameter):
    return PARAMETER_LABELS.get(parameter, parameter.replace("_", " ").capitalize())


def styled(fig, title, x_title=None, y_title=None):
    fig.update_layout(
        template="plotly_white",
        title={"text": title, "font": {"size": 16}, "automargin": True, "x": 0, "xanchor": "left"},
        font={"family": "IBM Plex Sans, sans-serif", "color": TEXT, "size": 12},
        paper_bgcolor=SURFACE,
        plot_bgcolor=SURFACE,
        margin={"l": 42, "r": 18, "t": 64, "b": 64},
        legend={
            "title_text": "",
            "orientation": "h",
            "x": 0,
            "y": -0.22,
            "xanchor": "left",
            "yanchor": "top",
            "font": {"size": 11},
            "bgcolor": "rgba(255,255,255,0)",
        },
        hoverlabel={"font": {"family": "IBM Plex Sans, sans-serif", "size": 12}, "align": "left"},
        hovermode="closest",
        autosize=True,
    )
    fig.update_xaxes(
        automargin=True, gridcolor=GRID, zerolinecolor=GRID, tickfont={"color": MUTED, "size": 11}
    )
    fig.update_yaxes(
        automargin=True, gridcolor=GRID, zerolinecolor=GRID, tickfont={"color": MUTED, "size": 11}
    )
    if x_title:
        fig.update_xaxes(title={"text": x_title, "font": {"size": 12}, "standoff": 12})
    if y_title:
        fig.update_yaxes(title={"text": y_title, "font": {"size": 12}, "standoff": 10})
    return fig


def utility_intervals(summary, baseline=None):
    """Means and the supplied central bands; optional point baseline is a reference."""
    fig = go.Figure()
    for i, row in enumerate(summary.itertuples()):
        color = POLICY_COLORS[row.policy]
        fig.add_trace(
            go.Scatter(
                x=[row.expected_utility],
                y=[row.policy],
                mode="markers",
                marker={
                    "color": color,
                    "size": 12,
                    "symbol": SYMBOLS[i % len(SYMBOLS)],
                    "line": {"color": "white", "width": 1},
                },
                error_x={
                    "type": "data",
                    "array": [row.upper_95 - row.expected_utility],
                    "arrayminus": [row.expected_utility - row.lower_95],
                    "color": color,
                    "thickness": 3,
                    "width": 5,
                },
                customdata=[[row.lower_95, row.upper_95]],
                name=row.policy,
                hovertemplate="%{y}<br>Mean utility: %{x:.2%}<br>Central 95% band: %{customdata[0]:.2%}–%{customdata[1]:.2%}<extra></extra>",
            )
        )
    endpoints = [float(summary.lower_95.min()), float(summary.upper_95.max())]
    if baseline is not None and np.isfinite(baseline):
        endpoints.append(float(baseline))
        fig.add_vline(x=float(baseline), line_dash="dot", line_color=MUTED, line_width=1.5)
        fig.add_annotation(
            x=float(baseline),
            y=1.05,
            yref="paper",
            text=f"Baseline {baseline:.1%}",
            showarrow=False,
            font={"size": 11, "color": MUTED},
        )
    padding = max(0.012, (max(endpoints) - min(endpoints)) * 0.12)
    fig.update_xaxes(
        tickformat=".1%",
        nticks=6,
        range=[max(0, min(endpoints) - padding), min(1, max(endpoints) + padding)],
    )
    fig.update_yaxes(
        categoryorder="array",
        categoryarray=summary.policy.tolist(),
        autorange="reversed",
        showgrid=False,
    )
    fig.update_layout(showlegend=False, height=330)
    return styled(fig, "Expected utility · central 95% bands", "Modeled probability of winning")


def distributions(simulation):
    utilities = np.asarray(simulation["utilities"])
    coincident = all(
        np.array_equal(utilities[:, 0], utilities[:, i]) for i in range(1, utilities.shape[1])
    )
    fig = go.Figure()
    if coincident:
        values = utilities[:, 0]
        trace = go.Histogram(
            x=values,
            name="All strategies · shared distribution",
            histnorm="probability",
            nbinsx=45,
            marker_color=POLICY_COLORS["No robust preference"],
            opacity=0.85,
            hovertemplate="Utility: %{x:.2%}<br>Fraction of draws: %{y:.1%}<extra>All strategies</extra>",
        )
        if np.ptp(values) == 0:
            trace.update(
                xbins={"start": values[0] - 0.001, "end": values[0] + 0.001, "size": 0.002}
            )
        fig.add_trace(trace)
        fig.add_annotation(
            x=0,
            y=1.08,
            xref="paper",
            yref="paper",
            xanchor="left",
            text="All strategies coincide under these assumptions.",
            showarrow=False,
            font={"size": 11, "color": MUTED},
        )
    else:
        for i, policy in enumerate(POLICIES):
            fig.add_trace(
                go.Histogram(
                    x=utilities[:, i],
                    name=policy.name,
                    opacity=0.48,
                    histnorm="probability",
                    nbinsx=45,
                    marker_color=POLICY_COLORS[policy.name],
                    hovertemplate="Utility: %{x:.2%}<br>Fraction of draws: %{y:.1%}<extra>%{fullData.name}</extra>",
                )
            )
    fig.update_layout(barmode="overlay", height=410)
    fig.update_xaxes(tickformat=".1%", nticks=6)
    fig.update_yaxes(tickformat=".0%")
    return styled(
        fig,
        "Uncertainty in expected utility",
        "Modeled probability of winning",
        "Fraction of integration draws",
    )


def sensitivity_lines(frame, parameter, current=None):
    fig = go.Figure()
    for i, policy in enumerate(POLICIES):
        fig.add_trace(
            go.Scatter(
                x=frame[parameter],
                y=frame[policy.name],
                mode="lines",
                name=policy.name,
                line={"color": POLICY_COLORS[policy.name], "width": 2.5, "dash": DASHES[i]},
                hovertemplate=parameter_label(parameter)
                + ": %{x:.3f}<br>Expected utility: %{y:.2%}<extra>%{fullData.name}</extra>",
            )
        )
    if isinstance(current, Mapping):
        current = current.get(parameter)
    if (
        current is not None
        and np.isfinite(current)
        and frame[parameter].min() <= current <= frame[parameter].max()
    ):
        fig.add_vline(x=float(current), line_dash="dashdot", line_color=TEXT, line_width=1.5)
        fig.add_annotation(
            x=float(current),
            y=1.05,
            yref="paper",
            text=f"Current {current:g}",
            showarrow=False,
            font={"size": 11, "color": MUTED},
        )
    probabilities = frame[[p.name for p in POLICIES]].to_numpy()
    low, high = float(probabilities.min()), float(probabilities.max())
    padding = max(0.005, (high - low) * 0.08)
    fig.update_yaxes(
        tickformat=".1%", nticks=6, range=[max(0, low - padding), min(1, high + padding)]
    )
    fig.update_layout(height=420)
    return styled(
        fig, "Sensitivity to one assumption", parameter_label(parameter), "Expected utility"
    )


def decision_regions(frame, x="grappling_effect", y="resistance", current=None):
    xs, ys = np.sort(frame[x].unique()), np.sort(frame[y].unique())
    grid = frame.sort_values([y, x])
    policies = [policy.name for policy in POLICIES]
    colors = [POLICY_COLORS[label] for label in [*policies, "No robust preference"]]
    scale = [(stop, color) for i, color in enumerate(colors) for stop in (i / 4, (i + 1) / 4)]
    custom = grid[[*policies, "margin"]].to_numpy().reshape(len(ys), len(xs), 4)
    z = grid.region.to_numpy().reshape(len(ys), len(xs))
    text = np.asarray(REGION_CODES)[z]
    fig = go.Figure(
        go.Heatmap(
            x=xs,
            y=ys,
            z=z,
            zmin=-0.5,
            zmax=3.5,
            colorscale=scale,
            customdata=custom,
            text=text,
            showscale=False,
            hovertemplate=parameter_label(x)
            + ": %{x:.3f}<br>"
            + parameter_label(y)
            + ": %{y:.3f}<br>Region code: %{text}<br>Striking utility: %{customdata[0]:.2%}<br>Grappling utility: %{customdata[1]:.2%}<br>Balanced utility: %{customdata[2]:.2%}<br>Leading gap: %{customdata[3]:.2%}<extra></extra>",
        )
    )
    for i, label in enumerate(REGION_LABELS):
        fig.add_trace(
            go.Scatter(
                x=[None],
                y=[None],
                mode="markers",
                marker={"symbol": "square", "size": 10, "color": colors[i]},
                name=f"{REGION_CODES[i]} · {label}",
                hoverinfo="skip",
            )
        )
    for iy in range(0, len(ys), max(1, int(np.ceil(len(ys) / 7)))):
        for ix in range(0, len(xs), max(1, int(np.ceil(len(xs) / 7)))):
            fig.add_annotation(
                x=xs[ix],
                y=ys[iy],
                text=REGION_CODES[z[iy, ix]],
                showarrow=False,
                font={"size": 10, "color": "white"},
            )
    if isinstance(current, Mapping):
        point = (current.get(x), current.get(y))
    elif current is not None:
        point = tuple(current)
    else:
        point = (None, None)
    if (
        len(point) == 2
        and all(value is not None and np.isfinite(value) for value in point)
        and xs.min() <= point[0] <= xs.max()
        and ys.min() <= point[1] <= ys.max()
    ):
        fig.add_trace(
            go.Scatter(
                x=[float(point[0])],
                y=[float(point[1])],
                mode="markers",
                marker={
                    "symbol": "circle",
                    "size": 14,
                    "color": "white",
                    "line": {"color": TEXT, "width": 2.5},
                },
                name="Current scenario",
                showlegend=False,
                cliponaxis=False,
                hovertemplate="Current assumptions<br>"
                + parameter_label(x)
                + ": %{x:.3f}<br>"
                + parameter_label(y)
                + ": %{y:.3f}<extra></extra>",
            )
        )
        fig.add_annotation(
            x=0,
            y=1.06,
            xref="paper",
            yref="paper",
            xanchor="left",
            text="○ Current scenario",
            showarrow=False,
            font={"size": 11, "color": MUTED},
        )
    styled(fig, "Decision regions · tested assumptions", parameter_label(x), parameter_label(y))
    fig.update_layout(
        height=490,
        legend={"orientation": "h", "entrywidth": 0.5, "entrywidthmode": "fraction", "y": -0.24},
        margin={"b": 105},
    )
    return fig


def tornado_chart(frame):
    fig = go.Figure()
    for row in frame.itertuples():
        fig.add_trace(
            go.Scatter(
                x=[row.low_margin, row.high_margin],
                y=[parameter_label(row.parameter)] * 2,
                mode="lines+markers",
                line={"width": 9, "color": POLICY_COLORS[row.measured_policy]},
                marker={"symbol": "circle", "size": 9},
                name=parameter_label(row.parameter),
                customdata=[[row.low, row.measured_policy], [row.high, row.measured_policy]],
                hovertemplate="%{y}<br>Assumption value: %{customdata[0]:.3f}<br>Reference policy: %{customdata[1]}<br>Utility margin: %{x:.2%}<extra></extra>",
            )
        )
    fig.add_vline(x=0, line_dash="dot", line_color=MUTED)
    fig.update_layout(showlegend=False, height=360)
    fig.update_xaxes(tickformat=".1%", nticks=5)
    return styled(fig, "Sensitivity of the reference policy", "Reference policy − best competitor")


def calibration_chart(frame):
    fig = go.Figure(
        go.Scatter(
            x=frame.predicted,
            y=frame.observed,
            mode="lines+markers",
            error_y={
                "array": frame.upper - frame.observed,
                "arrayminus": frame.observed - frame.lower,
                "thickness": 1.5,
                "width": 4,
            },
            customdata=frame.n,
            hovertemplate="Predicted: %{x:.2%}<br>Observed: %{y:.2%}<br>Bouts: %{customdata}<extra></extra>",
            name="Held-out bouts",
            line={"color": POLICY_COLORS["Grappling priority"], "width": 2},
            marker={"symbol": "circle", "size": 9},
        )
    )
    fig.add_trace(
        go.Scatter(
            x=[0, 1],
            y=[0, 1],
            mode="lines",
            line={"dash": "dot", "color": MUTED},
            name="Ideal calibration",
        )
    )
    fig.update_xaxes(range=[0, 1], tickformat=".0%", nticks=6)
    fig.update_yaxes(range=[0, 1], tickformat=".0%", nticks=6)
    fig.update_layout(height=430)
    return styled(
        fig,
        "Held-out calibration · Wilson 95% intervals",
        "Mean forecast probability",
        "Observed win fraction",
    )


def convergence_chart(frame):
    fig = go.Figure()
    for i, policy in enumerate(POLICIES):
        values = frame[frame.policy.eq(policy.name)]
        fig.add_trace(
            go.Scatter(
                x=values.draws,
                y=values["mean"],
                mode="lines+markers",
                name=policy.name,
                line={"color": POLICY_COLORS[policy.name], "dash": DASHES[i], "width": 2},
                marker={"symbol": SYMBOLS[i], "size": 7},
                customdata=values.mc_standard_error,
                hovertemplate="Draws: %{x:,}<br>Mean utility: %{y:.3%}<br>MC standard error: %{customdata:.4%}<extra>%{fullData.name}</extra>",
            )
        )
    low, high = float(frame["mean"].min()), float(frame["mean"].max())
    padding = max(0.0005, (high - low) * 0.08)
    fig.update_yaxes(
        tickformat=".2%", nticks=6, range=[max(0, low - padding), min(1, high + padding)]
    )
    fig.update_layout(height=420)
    return styled(
        fig, "Convergence within one draw stream", "Integration draws", "Mean modeled utility"
    )


def fighter_rates(profiles, names):
    metrics = [
        ("sig_landed_pm", "Significant strikes landed / minute"),
        ("td_landed_15", "Takedowns landed / 15 minutes"),
        ("sub_attempts_15", "Submission attempts / 15 minutes"),
    ]
    fig = make_subplots(
        rows=3, cols=1, subplot_titles=[m[1] for m in metrics], vertical_spacing=0.19
    )
    for i, (key, _) in enumerate(metrics):
        for j, (profile, name) in enumerate(zip(profiles, names, strict=True)):
            value = profile[key]
            missing = value is None or not np.isfinite(value)
            fig.add_trace(
                go.Bar(
                    x=[None if missing else value],
                    y=[f"Fighter {'AB'[j]}"],
                    orientation="h",
                    name=f"{'AB'[j]} · {name}",
                    legendgroup=name,
                    showlegend=i == 0,
                    marker_color=[
                        POLICY_COLORS["Striking priority"],
                        POLICY_COLORS["Grappling priority"],
                    ][j],
                    customdata=[name],
                    text=["Not observed" if missing else f"{value:.2f}"],
                    textposition="auto",
                    hovertemplate="%{customdata}<br>Rate: %{x:.3f}<extra></extra>",
                ),
                row=i + 1,
                col=1,
            )
            if missing:
                fig.add_annotation(
                    x=0,
                    y=f"Fighter {'AB'[j]}",
                    text="Not observed",
                    showarrow=False,
                    xanchor="left",
                    font={"color": MUTED, "size": 11},
                    row=i + 1,
                    col=1,
                )
        fig.update_xaxes(rangemode="tozero", row=i + 1, col=1)
        fig.update_yaxes(autorange="reversed", showgrid=False, row=i + 1, col=1)
    styled(fig, "Historical rates · separate units")
    fig.update_annotations(font={"family": "IBM Plex Sans, sans-serif", "size": 12})
    fig.update_layout(
        height=680, barmode="group", legend={"orientation": "h", "y": -0.1}, margin={"b": 110}
    )
    return fig


def tree_chart(tree, policy_name):
    branches = tree[tree.policy == policy_name]
    response_names = branches.response.drop_duplicates().tolist()
    labels = [policy_name, *response_names, "Win · utility 1", "Loss · utility 0"]
    sources, targets, values = [], [], []
    for j, response in enumerate(response_names):
        rows = branches[branches.response == response]
        sources.append(0)
        targets.append(j + 1)
        values.append(rows.response_probability.iloc[0])
        for row in rows.itertuples():
            sources.append(j + 1)
            targets.append(4 if row.outcome == "Win" else 5)
            values.append(row.joint_probability)
    fig = go.Figure(
        go.Sankey(
            node={
                "label": labels,
                "color": [
                    POLICY_COLORS[policy_name],
                    "#AAB4BC",
                    "#AAB4BC",
                    "#AAB4BC",
                    POLICY_COLORS["Grappling priority"],
                    "#B23D3D",
                ],
                "pad": 20,
            },
            link={
                "source": sources,
                "target": targets,
                "value": values,
                "color": "rgba(89,101,111,.20)",
            },
            valueformat=".3f",
        )
    )
    fig.update_layout(height=390)
    return styled(fig, "Response and outcome branches<br>" + policy_name)
