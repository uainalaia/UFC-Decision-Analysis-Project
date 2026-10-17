# MMA Decision Lab — v2 interface brief

## Baseline and audit

The real project is this repository; `app/main.py` serves the existing local application. The initial 48 tests and Ruff checks pass. Reference inputs/results are frozen in `reports/audit_v2/reference_before.json`; screenshots in `reports/review_v2/before/` record 1440×900, 1280×800 and 390×844 states. No source snapshot, exclusions, numerical model, policy, distribution, utility equation, robustness threshold or scientific version is changed for the redesign.

Observed friction: generic introductory blocks displace the matchup; long sidebar combines navigation and all controls; separate athlete tables impede row comparison; raw variables/decimal proportions dominate; visible radio navigation feels like a form; form drafts and stale/exported states lack a clear identity; neutral utilities can receive an arbitrary leader narrative. Calibration remains exploratory, not “perfect”.

## Concrete direction

The matchup is the principal visual element: two full names with focal/opponent roles, cutoff and division, a modest baseline estimate/status and a useful next action. A dark 236px navigation supports light research surfaces. Tactical allocations use neutral labeled phase segments; policy outcomes use stable blue/teal/ochre plus distinct symbols and dashes. Brand burgundy belongs to primary actions. IBM Plex Sans/Condensed files are local, with their original OFL license; no athlete imagery or remote assets are needed.

Shared tokens: workspace #F3F5F7, surface #FFFFFF, text #172126, muted #59656F, navigation #20282E, nav muted #AEB9C2, action #882A3A, separator #D8DEE3, control border #7A8791. Policy colors: #2457A6, #007A71, #925A08; no-preference #6A737D (darkened after contrast measurement). Spacing 4/8/12/16/24/32/48. Names 48px desktop, 34px narrow; page titles 30px; section headings 22px; body 16px, supporting text 14px.

```text
Fight brief
  Compact navigation | Applied date/division                  Change matchup
                     | Khabib Nurmagomedov    vs    Conor McGregor
                     | Focal fighter                Opponent
                     | Earlier bouts   Baseline + status   Earlier bouts
                     | Review fighter evidence       Review current result
                     | Three tactical priorities with labeled phase allocations

Fighter evidence
  Matchup context    | Striking / Wrestling / Grappling / Experience
                     | Metric + unit          Fighter A       Opponent
                     | Shared comparison rows and small unit-specific plots
                     | Audit contributing bouts (expand)     Review tactical model

Outcome analysis
  Matchup context    | Applied assumptions + computation settings
                     | Run analysis / explicit current or previous state
                     | Conditional conclusion + intervals + baseline reference
                     | Paired differences / uncertainty details (expand)
                     | Explore sensitivity / Generate research report
```

## Navigation mapping

| Existing function | New label | Group / URL |
|---|---|---|
| Overview | Fight brief | Research / root |
| Fighter Comparison | Fighter evidence | Research / fighter_evidence |
| Decision Model | Tactical model | Decision analysis / tactical_model |
| Monte Carlo Analysis | Outcome analysis | Decision analysis / outcome_analysis |
| Sensitivity Analysis | Sensitivity | Decision analysis / sensitivity |
| Model Validation | Validation | Research record / validation |
| Research Report | Research report | Research record / research_report |
| Methodology & Sources | Methodology | Research record / methodology |

Old views had no distinct URLs. Native Streamlit navigation adds real destinations rather than duplicate form controls.

## State contract

Applied matchup, baseline source, tactical assumptions and computation settings live independently of page widgets. Editors use an explicit persistent draft received by the backend on widget changes. Apply validates atomically; Cancel discards the draft. Leaving an editor preserves the draft with an explicit notice; it never changes applied calculations. Closing the matchup editor leaves applied state unchanged.

Results have an input identity including dataset content hashes, model numeric identity, fighter order, reference date/division/rounds, relevant baseline input, complete scenario, seed and draws. Navigation and visual formatting are excluded. Returning to the exact input values recovers the existing current result. Other changes mark the previous record as previous, without mixing its numbers with the new matchup. Failures preserve the last completed result as previous. Snapshot changes invalidate model/result/export bindings from the old source.

Only Run analysis integrates the complete decision model. The default existing numeric baseline is loaded from JSON, not refitted for style/navigation. A different cutoff requires an explicit Prepare historical baseline action; the existing forecasting procedure is unchanged. Report generation freezes HTML/CSV/JSON/ZIP from one complete result; downloads never silently regenerate against new controls. Sensitivity explorations have their own scope/identity and download; the main research record labels its default robustness grid separately.

## Verification plan

Audit independent values and calibration first, then implement shell/evidence, analytical editors/states, validation/methodology and report. Recheck unchanged numerical reference and neutral invariant. Test persistent navigation, apply/cancel, invalid weights, stale/current restoration, snapshot invalidation and failed runs. Inspect all eight views plus 1440×900, 1280×800, 1024×768, 768×1024 and 390×844; review contrast, keyboard focus, 200% text zoom/reflow and offline report print presentation. Record verified scope and limits rather than a global perfection claim.

## References and skills

Applied local Data validation skill and its deep-review/analysis-quality guidance. Consulted the public [Anthropic frontend-design guidance](https://github.com/anthropics/skills/blob/main/skills/frontend-design/SKILL.md) and [Vercel web-interface guidelines](https://github.com/vercel-labs/web-interface-guidelines/blob/main/command.md) as references; neither was installed. Reviewed [Linear](https://linear.app/now/behind-the-latest-design-refresh), [Geist typography](https://vercel.com/geist/typography), [Carbon categorical/continuous palettes](https://www.carbondesignsystem.com/building-blocks/data-visualization/color-palettes), [WCAG 2.2](https://www.w3.org/TR/WCAG22/) and [OpenAI frontend guidance](https://developers.openai.com/api/docs/guides/frontend-prompt). Their principles inform the implementation, not a certification or affiliation.

Native Streamlit 1.66 signatures/config definitions were inspected for navigation, dialogs, containers, stable widget keys and local fonts; current [font](https://docs.streamlit.io/develop/concepts/configuration/theming-customize-fonts), [navigation](https://docs.streamlit.io/develop/concepts/multipage-apps/page-and-navigation) and [widget state](https://docs.streamlit.io/develop/concepts/architecture/widget-behavior) documentation was checked. User sentence-case and scientific constraints override conflicting reference preferences.
