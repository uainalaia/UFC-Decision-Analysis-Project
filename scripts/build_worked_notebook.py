"""Build the small tutorial notebook with notebook-safe tooling."""

from pathlib import Path

import nbformat as nbf

ROOT = Path(__file__).resolve().parents[1]
nb = nbf.v4.new_notebook()
nb.metadata = {
    "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
    "language_info": {"name": "python", "version": "3.12"},
}
markdown = nbf.v4.new_markdown_cell
code = nbf.v4.new_code_cell
nb.cells = [
    markdown(
        "# MMA Decision Lab: a worked decision-tree calculation\n\n## Goal\nVerify how one tactical policy's terminal branches produce expected utility. These are **mathematical teaching inputs**, not observed UFC probabilities or invented fight records. The real historical workflow is separate."
    ),
    markdown(
        "## Setup\nInstall the repository's locked environment. Run from the repository root or `notebooks/`. The neutral baseline is assumed to be 0.60; win utility is 1 and loss utility is 0. No source dataset is required for this arithmetic example."
    ),
    code(
        "from pathlib import Path\nimport sys\nimport numpy as np\nimport pandas as pd\nfrom scipy.special import expit, logit\n\nroot = Path.cwd() if (Path.cwd() / 'src').exists() else Path.cwd().parent\nsys.path.insert(0, str(root / 'src'))\nfrom mma_decision_lab.schemas import ScenarioConfig\nfrom mma_decision_lab.decision import POLICIES, decision_tree, expected_utilities\npd.set_option('display.precision', 6)\np0 = 0.60\nchosen = POLICIES[1]  # Grappling priority; static allocation, not guaranteed fight time.\n"
    ),
    markdown(
        "## Steps\n### 1. Inspect the neutral terminal branches\nResponse weights are 0.25 / 0.50 / 0.25. All tactical effects are zero. Each response has a win and a loss terminal consequence."
    ),
    code(
        "neutral = ScenarioConfig()\nbranches = decision_tree(p0, neutral)\nselected = branches[branches.policy == chosen.name]\nselected[['response', 'response_probability', 'outcome', 'conditional_outcome_probability', 'utility', 'joint_probability', 'utility_contribution']]"
    ),
    markdown(
        "### 2. Check the utility by hand\nThe win contributions are `0.25×0.60 + 0.50×0.60 + 0.25×0.60 = 0.60`. Loss contributions are zero. This is an exact expectation, not a simulation estimate."
    ),
    code(
        "manual_neutral = 0.25 * 0.60 + 0.50 * 0.60 + 0.25 * 0.60\nengine_neutral = selected.utility_contribution.sum()\nassert np.isclose(selected.joint_probability.sum(), 1.0)\nassert np.isclose(engine_neutral, manual_neutral)\nassert np.allclose(expected_utilities(p0, neutral), p0)\nprint(f'Hand calculation: {manual_neutral:.6f}; engine: {engine_neutral:.6f}')"
    ),
    markdown(
        "### 3. Make the assumed tactical effect explicit\nFor this second **hypothetical** arithmetic example, use `s=.4, g=.2, R=.25, c=.1`. The policy allocation is fixed at standing/clinch/ground = .20/.30/.50. The response index is `clip(R + offset, 0, 1)`, with offsets −.25 / 0 / +.25. Calculate delta, conditional P(win), and branch contribution separately. These coefficients are assumptions, not paper estimates."
    ),
    code(
        "assumed = ScenarioConfig(striking_effect=.4, grappling_effect=.2, resistance=.25, counter_cost=.1)\ndistance_difference = chosen.allocation[0] - .5\ngrappling_difference = chosen.allocation[1] + chosen.allocation[2] - .5\nrows = []\nfor label, offset, weight in zip(['Lower', 'Expected', 'Stronger'], [-.25, 0, .25], assumed.response_weights):\n    response_index = np.clip(assumed.resistance + offset, 0, 1)\n    delta = (.4 * distance_difference + .2 * grappling_difference * (1 - 2 * response_index)\n             - .1 * abs(grappling_difference) * response_index)\n    conditional = expit(logit(p0) + delta)\n    rows.append({'Response': label, 'Weight': weight, 'Resistance index': response_index,\n                 'Assumed delta': delta, 'Conditional P(win)': conditional,\n                 'Expected utility contribution': weight * conditional})\nworked = pd.DataFrame(rows)\nworked"
    ),
    markdown(
        "## Checks\nSum the displayed branch contributions and compare with the production engine. The result concerns this one assumed policy/scenario model; no empirical policy recommendation follows."
    ),
    code(
        "manual_value = worked['Expected utility contribution'].sum()\nengine_value = expected_utilities(p0, assumed)[1]\nassert np.isclose(manual_value, engine_value, atol=1e-12)\nassert 0 < engine_value < 1\nprint(f'Hypothetical grappling policy expected utility: {engine_value:.6f}')\nprint('All probability-mass, neutral-invariant and hand-calculation checks passed.')"
    ),
    markdown(
        "## Next steps\nRun `python scripts/run_example_analysis.py` from the repository root for the real historical example, or use `--illustrative` to deliberately enable hypothetical nonneutral assumptions. Read `docs/METHODOLOGY.md` and `docs/MODEL_CARD.md` before interpreting the research outputs. The historical model is exploratory at the default cutoff, and public observations do not identify tactical causal effects.\n\nThe tutorial intentionally uses small branch tables rather than charts: its purpose is to audit a single expected-utility calculation. The full application and standalone research report contain the uncertainty and sensitivity visualizations."
    ),
]
nbf.validate(nb)
path = ROOT / "notebooks/worked_example.ipynb"
path.parent.mkdir(parents=True, exist_ok=True)
nbf.write(nb, path)
print(path)
