# Supplied materials and research boundaries

The supplied development prompt and extensionless Word draft establish the implementation scope. The exact preliminary filename mentioned in the prompt, term-project guidelines and Clemen/Reilly chapters were absent. The supplied revised Word draft was inspected as the academic specification. It is not treated as executable mathematics or proof of tactical effects.

All four supplied PDFs were text-extracted for inspection. Relevant metadata and methodological sections establish these roles:

| Supplied publication | Role | Boundary |
|---|---|---|
| Holmes, McHale & Żychaluk (2023), IJF 39, 623–640; DOI 10.1016/j.ijforecast.2022.01.007 | Pre-fight skill estimation, probabilistic forecasting, Markov simulation and temporal testing precedent | Already uses stochastic simulation; this implementation does not reproduce its full Markov model or claim a compatible performance comparison |
| Miarka, Brito & Amtmann (2017); DOI 10.1080/24748668.2017.1360103 | Phase-specific technical/tactical measurement context | Observed associations do not identify assigned coaching effects |
| James et al. (2017), JSAMS 20, 296–301; DOI 10.1016/j.jsams.2016.08.001 | Interpretable performance indicators | A post-fight classification tree is different from a normative decision tree |
| Bueno et al. (2022), Sports 10, 80; DOI 10.3390/sports10060080 | Research heterogeneity and MMA performance context | No matchup-specific tactical treatment coefficients can be transferred from a broad review |

Publication titles/authors/DOIs above were checked against the supplied first pages. The Holmes publisher record was also accessible online. Gneiting/Raftery's proper-scoring reference is retained with its supplied DOI; its full paper was not supplied. No unprovided quotations, original-study numerical superiority claims or causal coefficients were invented.

The [community archive README](https://github.com/Greco1899/scrape_ufc_stats) explicitly offers published CSV downloads; its repository declares [GPL-3.0](https://github.com/Greco1899/scrape_ufc_stats/blob/main/LICENSE). The frozen commit and file hashes are recorded in `data/manifests/snapshot.json`. The software imports data files and does not execute upstream scraper code. Original UFCStats data rights are not independently established; data remain local and excluded from Git.

A direct primary-page cross-check for the default UFC 229 bout was attempted, but UFCStats returned a gateway error through the available research tool. Therefore the data pipeline claims **audited archive provenance and internal consistency**, not complete independent primary-source reconciliation. This is an outstanding research-quality check. The source fight URL is preserved for inspection when accessible.

Public observations support descriptive history and retrospective forecasting. They do not reveal intended pre-fight policies, establish feasible allocation proportions or identify counterfactual tactic effects. All such parameters are Category C assumptions with definitions, bounds, defaults and modification records in exports.
