"""Read-only numerical audit. Run: .venv/Scripts/python reports/audit_v2/audit_numbers.py.

Does not fit or persist any model. Only writes its companion numbers.json.
The independent history implementation uses cumulative prefix arrays and a
left search per date, and checks every saved feature vector.
"""

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit, logit
from scipy.stats import rankdata

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from mma_decision_lab.data import load_dataset
from mma_decision_lab.decision import decision_tree, expected_utilities
from mma_decision_lab.features import FEATURES, PROFILE_FEATURES
from mma_decision_lab.schemas import ScenarioConfig
from mma_decision_lab.sensitivity import one_way, two_way
from mma_decision_lab.simulation import simulate


def difference(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    return float(np.nanmax(np.abs(a - b))) if np.isfinite(a - b).any() else 0.0


def smooth(n, d):
    return (n + 1) / (d + 2) if d > 0 else np.nan


def metrics(y, p):
    n1, n0 = y.sum(), (1 - y).sum()
    auc = (rankdata(p)[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)
    return {
        "brier": float(np.mean((p - y) ** 2)),
        "log_loss": float(-np.mean(y * np.log(p) + (1 - y) * np.log1p(-p))),
        "accuracy": float(np.mean((p >= 0.5) == y)),
        "auc": float(auc),
    }


def main():
    immutable = [ROOT / "models/baseline.json", ROOT / "data/processed/features.csv"]
    immutable += list((ROOT / "data/raw").glob("*"))
    before = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in immutable}
    saved = json.loads((ROOT / "reports/generated/analysis.json").read_text(encoding="utf-8"))
    payload = json.loads((ROOT / "models/baseline.json").read_text(encoding="utf-8"))
    dataset = load_dataset()
    feat = pd.read_csv(ROOT / "data/processed/features.csv", parse_dates=["event_date"])
    parts = pd.read_csv(ROOT / "reports/generated/partitions.csv", parse_dates=["event_date"])
    result = {
        "scope": "All existing raw snapshot hashes; 8420 persisted feature vectors; unchanged persisted model; example tree, Monte Carlo, calibration and partitions. No fitting.",
        "data_quality": dataset.quality,
        "checks": {},
    }
    checks = result["checks"]
    # Join counts by known opponent ID, independently of the feature constructor.
    side_rows = []
    for side, other in [("a", "b"), ("b", "a")]:
        frame = dataset.fights[["fight_id", "event_date", "duration_seconds", "weight_class", "result", f"fighter_{side}_id", f"fighter_{other}_id"]].copy()
        frame = frame.rename(columns={f"fighter_{side}_id": "fighter_id", f"fighter_{other}_id": "opponent_id"})
        frame["won"] = frame.result.eq(side + "_win").astype(int)
        side_rows.append(frame)
    history = pd.concat(side_rows, ignore_index=True).merge(dataset.stats, on=["fight_id", "fighter_id"], validate="one_to_one")
    opp = dataset.stats[["fight_id", "fighter_id", "sig_landed", "sig_attempted", "td_landed", "td_attempted"]].rename(columns={"fighter_id": "opponent_id", **{c: "opp_" + c for c in ["sig_landed", "sig_attempted", "td_landed", "td_attempted"]}})
    history = history.merge(opp, on=["fight_id", "opponent_id"], validate="one_to_one")
    history["minutes"] = history.duration_seconds / 60
    groups = {fid: g.sort_values(["event_date", "fight_id"]) for fid, g in history.groupby("fighter_id")}
    prefix = {}
    cols = ["minutes", "won", "sig_landed", "sig_attempted", "opp_sig_landed", "opp_sig_attempted", "td_landed", "td_attempted", "opp_td_landed", "opp_td_attempted", "submission_attempts", "control_seconds"]
    for fid, frame in groups.items():
        arrays = {col: np.r_[0.0, np.nancumsum(frame[col].to_numpy(float))] for col in cols}
        arrays["sub_exposure"] = np.r_[0.0, np.cumsum(frame.minutes.where(frame.submission_attempts.notna(), 0))]
        arrays["control_exposure"] = np.r_[0.0, np.cumsum(frame.minutes.where(frame.control_seconds.notna(), 0))]
        arrays["dates"] = frame.event_date.to_numpy()
        arrays["divisions"] = frame.weight_class.to_numpy()
        prefix[fid] = arrays

    def independent_profile(fid, cutoff):
        h = prefix.get(fid)
        if h is None:
            return np.full(len(PROFILE_FEATURES), np.nan), {}
        idx = int(np.searchsorted(h["dates"], np.datetime64(cutoff), side="left"))
        t = {c: h[c][idx] for c in cols}
        minutes = t["minutes"]
        values = [
            t["sig_landed"] / minutes if minutes else np.nan,
            t["opp_sig_landed"] / minutes if minutes else np.nan,
            smooth(t["sig_landed"], t["sig_attempted"]),
            smooth(t["opp_sig_attempted"] - t["opp_sig_landed"], t["opp_sig_attempted"]),
            15 * t["td_landed"] / minutes if minutes else np.nan,
            smooth(t["opp_td_attempted"] - t["opp_td_landed"], t["opp_td_attempted"]),
            15 * t["submission_attempts"] / h["sub_exposure"][idx] if h["sub_exposure"][idx] else np.nan,
            smooth(t["won"], idx),
            np.log1p(idx),
            (pd.Timestamp(cutoff) - pd.Timestamp(h["dates"][idx-1])).days / 365.25 if idx else np.nan,
        ]
        return np.array(values), {"prior_fights": idx, "wins": int(t["won"]), "observed_minutes": minutes, "strike_attempts": t["sig_attempted"], "td_attempts": t["td_attempted"], "sub_exposure_minutes": h["sub_exposure"][idx], "control_exposure_minutes": h["control_exposure"][idx]}

    recomputed = []
    for row in feat.itertuples():
        a, _ = independent_profile(row.fighter_a_id, row.event_date)
        b, _ = independent_profile(row.fighter_b_id, row.event_date)
        recomputed.append(a - b)
    recomputed = np.asarray(recomputed)
    old = feat[FEATURES].to_numpy()
    checks["all_historical_features"] = {"rows": len(feat), "features": len(FEATURES), "max_absolute_error": difference(old, recomputed), "nan_pattern_identical": bool(np.array_equal(np.isnan(old), np.isnan(recomputed)))}
    checks["example_profiles"] = {}
    for side in ("a", "b"):
        profile = saved["profiles"][side]
        values, exposure = independent_profile(profile["fighter_id"], profile["reference_date"])
        checks["example_profiles"][side] = {"name": saved["names"][0 if side == "a" else 1], "denominators": exposure, "max_feature_error": difference(values, [profile[c] for c in PROFILE_FEATURES])}
    # Reconcile the example directly with original source CSV text, independently
    # of ingest()'s parsing, duration and fighter-side aggregation implementation.
    source_results = pd.read_csv(ROOT / "data/raw/ufc_fight_results.csv")
    source_stats = pd.read_csv(ROOT / "data/raw/ufc_fight_stats.csv")
    for col in source_results.select_dtypes("object"):
        source_results[col] = source_results[col].str.strip()
    for col in source_stats.select_dtypes("object"):
        source_stats[col] = source_stats[col].str.strip()
    source_results["fight_id"] = source_results.URL.str.rsplit("/", n=1).str[-1]
    checks["example_raw_csv_reconciliation"] = {}
    for side, name in zip(("a", "b"), saved["names"]):
        profile = saved["profiles"][side]
        historical = dataset.fights[(dataset.fights.fighter_a_id.eq(profile["fighter_id"]) | dataset.fights.fighter_b_id.eq(profile["fighter_id"])) & dataset.fights.event_date.lt(profile["reference_date"])]
        own_counts = {"sig_landed":0,"sig_attempted":0,"td_landed":0,"td_attempted":0}
        raw_minutes, raw_wins, raw_round_rows = 0.0, 0, 0
        for fight in historical.itertuples():
            raw = source_results[source_results.fight_id.eq(fight.fight_id)].iloc[0]
            minute, second = (int(v) for v in raw.TIME.split(":"))
            raw_minutes += ((int(raw.ROUND)-1)*300 + minute*60 + second)/60
            competitors = raw.BOUT.split(" vs. ")
            raw_wins += int(competitors[0 if raw.OUTCOME == "W/L" else 1] == name)
            rnds = source_stats[source_stats.EVENT.eq(raw.EVENT) & source_stats.BOUT.eq(raw.BOUT) & source_stats.FIGHTER.eq(name)]
            raw_round_rows += len(rnds)
            for source_col, prefix_name in [("SIG.STR.","sig"),("TD","td")]:
                counts = rnds[source_col].str.extract(r"^(\d+)\s+of\s+(\d+)$").astype(int)
                own_counts[prefix_name+"_landed"] += int(counts[0].sum())
                own_counts[prefix_name+"_attempted"] += int(counts[1].sum())
        checks["example_raw_csv_reconciliation"][side] = {"name":name,"bout_count":len(historical),"raw_round_rows":raw_round_rows,"raw_minutes":raw_minutes,"raw_wins":raw_wins,"raw_counts":own_counts,"all_counts_equal_saved_profile":all(own_counts[k] == profile["total_"+k] for k in own_counts),"minutes_absolute_error":abs(raw_minutes-profile["observed_minutes"]),"wins_equal_saved":raw_wins == profile["wins"]}
    checks["features_ids_match_retained_bouts"] = set(feat.fight_id) == set(dataset.fights.fight_id)
    checks["target_matches_source_outcome"] = bool((feat.set_index("fight_id").target.sort_index() == dataset.fights.set_index("fight_id").result.eq("a_win").astype(int).sort_index()).all())
    # Temporal membership and persisted-model test evaluation; no model fitting.
    evaluation = payload["evaluation"]
    merged = parts.merge(feat, on=["fight_id", "event_date"], validate="one_to_one")
    limits = {k: {"n": len(v), "start": str(v.event_date.min().date()), "end": str(v.event_date.max().date())} for k, v in parts.groupby("partition")}
    ordered = [parts[parts.partition.eq(k)].event_date for k in ("train", "validation", "test")]
    eligible = feat[feat.eligible & feat.event_date.lt(evaluation["reference_date"])].sort_values(["event_date", "fight_id"])
    dates = eligible.event_date.drop_duplicates().to_numpy()
    validation_start, test_start = dates[int(len(dates) * .65)], dates[int(len(dates) * .82)]
    expected_parts = np.where(eligible.event_date < validation_start, "train", np.where(eligible.event_date < test_start, "validation", "test"))
    checks["partitions"] = {"summary": limits, "matches_saved_summary": limits == evaluation["partition_summary"], "unique_fights": not parts.fight_id.duplicated().any(), "all_strictly_before_cutoff": bool(parts.event_date.lt(evaluation["reference_date"]).all()), "date_blocks_do_not_overlap": bool(ordered[0].max() < ordered[1].min() and ordered[1].max() < ordered[2].min()), "exact_expected_membership": bool(eligible.fight_id.tolist() == parts.fight_id.tolist() and np.array_equal(expected_parts, parts.partition.to_numpy()))}
    test = merged[merged.partition.eq("test")]
    x = np.nan_to_num(test[FEATURES].to_numpy(float), nan=0.0)
    p = expit(x / np.asarray(payload["model"]["scales"]) @ np.asarray(payload["model"]["coefficients"]))
    y = test.target.to_numpy()
    test_metrics = metrics(y, p)
    coin_metrics = metrics(y, np.full(len(y), .5))
    rng = np.random.default_rng(422)
    diff = (p - y) ** 2 - (.5 - y) ** 2
    interval = np.quantile([rng.choice(diff, len(diff), replace=True).mean() for _ in range(1000)], [.025, .975])
    checks["test_metrics"] = {"independent": test_metrics, "max_error": max(abs(test_metrics[k] - evaluation["test"][k]) for k in test_metrics), "coin_max_error": max(abs(coin_metrics[k] - evaluation["coin_reference"][k]) for k in coin_metrics), "brier_difference_95_interval": interval.tolist(), "interval_max_error": difference(interval, evaluation["brier_difference_vs_coin_95_interval"]), "supported": bool(interval[1] < 0 and test_metrics["log_loss"] < coin_metrics["log_loss"])}
    # Independent binning and Wilson calculation rather than app calibration helper.
    bins = np.minimum(np.ceil(p * 8).astype(int) - 1, 7)
    cal = []
    for b in sorted(set(bins)):
        use = bins == b
        n, observed, predicted = int(use.sum()), y[use].mean(), p[use].mean()
        z = 1.96
        center = (observed + z*z/(2*n)) / (1 + z*z/n)
        half = z*np.sqrt(observed*(1-observed)/n + z*z/(4*n*n))/(1+z*z/n)
        cal.append([predicted, observed, n, center-half, center+half])
    old_cal = pd.read_csv(ROOT / "reports/generated/calibration.csv")
    checks["calibration"] = {"bins": len(cal), "n": int(sum(v[2] for v in cal)), "max_absolute_error": difference(cal, old_cal.to_numpy()), "sparse_bins": [int(v[2]) for v in cal if v[2] < 25], "limitation": "Descriptive observed proportions from held-out bouts; small bins and serial fighter dependence preclude a guarantee of calibration."}
    # Logistic prediction and bootstrap interval for the worked example.
    a, _ = independent_profile(saved["context"]["fighter_a_id"], saved["context"]["reference_date"])
    b, _ = independent_profile(saved["context"]["fighter_b_id"], saved["context"]["reference_date"])
    x = np.nan_to_num(a-b, nan=0.0)
    predict = lambda m: float(expit(x / np.asarray(m["scales"]) @ np.asarray(m["coefficients"])))
    p0 = predict(payload["model"])
    samples = np.array([predict(m) for m in payload["bootstraps"]])
    checks["baseline"] = {"probability": p0, "absolute_error": abs(p0-saved["baseline_probability"]), "bootstrap_models": len(samples), "interval_max_error": difference(np.quantile(samples,[.025,.975]), saved["baseline_parameter_interval"]), "swap_complement_error": abs(p0+float(expit(-x / np.asarray(payload["model"]["scales"]) @ np.asarray(payload["model"]["coefficients"]))) - 1)}
    # Manual allocation equation, independent of adjustments() or tree helpers.
    s = saved["scenario"]
    allocations = np.array([v["allocation"] for v in saved["policies"]])
    standing = allocations[:, 0] - .5
    pressure = allocations[:, 1:].sum(axis=1) - .5
    resistance = np.clip(s["resistance"] + np.array([-.25, 0, .25]), 0, 1)
    delta = s["striking_effect"]*standing[:,None] + s["grappling_effect"]*pressure[:,None]*(1-2*resistance) - s["counter_cost"]*np.abs(pressure[:,None])*resistance
    deterministic = expit(logit(p0) + delta) @ np.asarray(s["response_weights"])
    c = ScenarioConfig(**s)
    tree = decision_tree(p0,c)
    checks["decision_tree"] = {"terminal_rows": len(tree), "max_error_vs_independent_equation": difference(deterministic, saved["deterministic_utilities"]), "max_error_api": difference(deterministic, expected_utilities(p0,c)), "joint_mass_error": difference(tree.groupby("policy",sort=False).joint_probability.sum(), 1), "tree_utility_error": difference(tree.groupby("policy",sort=False).utility_contribution.sum(), deterministic)}
    mc = simulate(p0,samples,c,draws=saved["context"]["draws"],seed=saved["context"]["seed"])
    checks["simulation"] = {k: {"rows": len(mc[k]), "max_numeric_error": difference(mc[k].select_dtypes("number").to_numpy(), pd.DataFrame(saved["simulation"][k]).select_dtypes("number").to_numpy())} for k in ("summary","pairwise","convergence")}
    u = mc["utilities"]
    # Independent draw construction and summary reduction from the documented
    # four streams. This also detects a stable bug in the simulation routine.
    n = saved["context"]["draws"]
    streams = [np.random.default_rng(seed) for seed in np.random.SeedSequence(saved["context"]["seed"]).spawn(4)]
    bd = streams[0].choice(samples, size=n)
    w = s["effect_half_width"]
    sd = streams[1].triangular(s["striking_effect"]-w,s["striking_effect"],s["striking_effect"]+w,n) if w else np.full(n,s["striking_effect"])
    gd = streams[2].triangular(s["grappling_effect"]-w,s["grappling_effect"],s["grappling_effect"]+w,n) if w else np.full(n,s["grappling_effect"])
    wd = streams[3].dirichlet(np.asarray(s["response_weights"])*s["response_concentration"],n) if s["response_concentration"] else np.broadcast_to(s["response_weights"],(n,3))
    dd = sd[:,None,None]*standing[None,:,None] + gd[:,None,None]*pressure[None,:,None]*(1-2*resistance[None,None,:]) - s["counter_cost"]*abs(pressure[None,:,None])*resistance[None,None,:]
    independent_u = (expit(logit(bd)[:,None,None]+dd)*wd[:,None,:]).sum(axis=2)
    mx = independent_u.max(axis=1,keepdims=True)
    ties = abs(independent_u-mx) <= 1e-12
    empirical = expit(logit(bd)[:,None,None]+delta) @ np.asarray(s["response_weights"])
    structural = (expit(logit(p0)+dd)*wd[:,None,:]).sum(axis=2)
    independent_summary = np.column_stack([
        independent_u.mean(axis=0),np.quantile(independent_u,.025,axis=0),np.quantile(independent_u,.975,axis=0),
        (independent_u-bd[:,None]).mean(axis=0),independent_u.std(axis=0,ddof=1)/np.sqrt(n),
        (ties/ties.sum(axis=1,keepdims=True)).mean(axis=0),(mx-independent_u).mean(axis=0),
        empirical.std(axis=0,ddof=1),structural.std(axis=0,ddof=1),
    ])
    checks["simulation"]["independent_equation"] = {"all_draws_max_error":difference(u,independent_u),"summary_max_error":difference(independent_summary,mc["summary"].select_dtypes("number").to_numpy())}
    checks["simulation"]["invariants"] = {"finite_and_strict_probability_bounds": bool(np.isfinite(u).all() and (u>0).all() and (u<1).all()), "rank_share_sum_error": abs(float(mc["summary"].rank_first_share.sum())-1), "all_regrets_nonnegative": bool((mc["summary"].expected_regret>=0).all())}
    # Entire saved sensitivity surface checked against manual equation at each node.
    def manual_eu(g, r):
        resistance = np.clip(r + np.array([-.25,0,.25]),0,1)
        delta = s["striking_effect"]*standing[:,None] + g*pressure[:,None]*(1-2*resistance)-s["counter_cost"]*np.abs(pressure[:,None])*resistance
        return expit(logit(p0)+delta)@np.array(s["response_weights"])
    for key in ("one_way","two_way"):
        frame = pd.DataFrame(saved[key])
        vals = np.array([manual_eu(row["grappling_effect"],row.get("resistance",s["resistance"])) for row in saved[key]])
        checks[key] = {"nodes": len(frame), "max_error_vs_independent_equation": difference(vals,frame[[v["name"] for v in saved["policies"]]].to_numpy())}
    # Reproduce both threshold and region routines, with no fitting or result overwrite.
    ranges = saved["sensitivity_ranges"]
    _, thresholds = one_way(p0,c,"grappling_effect",*ranges["grappling_effect"])
    grid = two_way(p0,c,"grappling_effect",ranges["grappling_effect"],"resistance",ranges["resistance"],steps=25)
    checks["sensitivity_labels"] = {"thresholds_equal": thresholds == saved["thresholds"], "all_region_labels_equal": grid.region.tolist() == pd.DataFrame(saved["two_way"]).region.tolist()}
    after = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in immutable}
    checks["raw_model_and_feature_bytes_unchanged"] = before == after
    result["scientific_limitations"] = [
        {"severity":"material limitation", "finding":"No demonstrated Brier improvement over 0.5 at 95% confidence; supported=false is correct.", "evidence":checks["test_metrics"], "remedy":"Keep exploratory status visible. Further validation/model development is separate scientific work and would change analytical results."},
        {"severity":"material limitation", "finding":"Pooled division and scheduled-round contexts are not predictors; all profiles count retained bouts across prior divisions.", "evidence":"forecasting.py evaluation.scope; features.py PROFILE_FEATURES; worked example B has historical Featherweight, Lightweight and Welterweight bouts.", "remedy":"Clarify context selectors and retained-bout scope in presentation; do not imply contextual effects have been estimated."},
        {"severity":"material limitation", "finding":"Tactical effects, allocations and opponent response distribution are engineering assumptions; bands and rank shares are conditional on those assumptions.", "evidence":"decision.py adjustments; simulation.py shared baseline and independent triangular/Dirichlet streams.", "remedy":"Retain explicit assumption and uncertainty labels; no causal/optimal strategy claim."},
        {"severity":"limitation", "finding":"Bout bootstrap and Wilson bands ignore serial fighter dependence, and historical archival data are a modern snapshot rather than records frozen as-of the reference date.", "remedy":"Keep current limitations. Clustered temporal validation and as-was archive require separately authorized scientific changes."},
    ]
    result["demonstrated_defects"] = [{"severity":"low / wording", "file":"src/mma_decision_lab/analysis.py", "line":59, "finding":"Historical forecast error text implies two earlier bouts in the selected last division. Actual eligibility requires two retained earlier bouts overall and the selected division to equal the last recorded division.", "remedy":"Clarify eligibility wording without changing calculations, predictions, versions or scientific scope."}]
    result["numeric_audit_passed"] = bool(
        checks["all_historical_features"]["max_absolute_error"] < 1e-9
        and checks["all_historical_features"]["nan_pattern_identical"]
        and checks["partitions"]["exact_expected_membership"]
        and checks["test_metrics"]["max_error"] < 1e-12
        and checks["calibration"]["max_absolute_error"] < 1e-12
        and checks["baseline"]["absolute_error"] < 1e-12
        and checks["decision_tree"]["max_error_vs_independent_equation"] < 1e-12
        and all(checks["simulation"][k]["max_numeric_error"] < 1e-12 for k in ("summary", "pairwise", "convergence"))
        and checks["simulation"]["independent_equation"]["all_draws_max_error"] < 1e-12
        and checks["simulation"]["independent_equation"]["summary_max_error"] < 1e-12
        and checks["one_way"]["max_error_vs_independent_equation"] < 1e-12
        and checks["two_way"]["max_error_vs_independent_equation"] < 1e-12
        and all(v["all_counts_equal_saved_profile"] and v["minutes_absolute_error"] < 1e-12 and v["wins_equal_saved"] for v in checks["example_raw_csv_reconciliation"].values())
        and checks["raw_model_and_feature_bytes_unchanged"]
    )
    result["artifact_hashes"] = before
    (Path(__file__).parent / "numbers.json").write_text(json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False),encoding="utf-8")
    print(json.dumps(checks,indent=2,ensure_ascii=False,allow_nan=False))
    if not result["numeric_audit_passed"]:
        raise SystemExit("Numerical audit failed; inspect numbers.json.")


if __name__ == "__main__":
    main()
