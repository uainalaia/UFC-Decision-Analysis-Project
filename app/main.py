"""MMA Decision Lab: native navigation around one applied research context."""

import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for folder in (ROOT, ROOT / "src"):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

import streamlit as st

from app import ui
from app.context import refresh

st.set_page_config(page_title="MMA Decision Lab", layout="wide", initial_sidebar_state="auto")
ui.install_styles()
st.logo(
    str(ROOT / "app/static/brand.svg"),
    icon_image=str(ROOT / "app/static/brand_icon.svg"),
    size="large",
)
try:
    e = refresh()
except (OSError, ValueError, KeyError) as exc:
    logging.getLogger(__name__).exception("Research resources could not be loaded")
    st.title("Research resources unavailable")
    st.error(
        "The research snapshot or saved baseline could not be loaded. Check the documented local resource files and reload the application."
    )
    st.info(
        "For a missing archive, run `.venv/Scripts/python.exe scripts/fetch_snapshot.py` as documented in README. Restore an invalid saved baseline from a trusted local copy; the application will not silently replace it."
    )
    st.caption(
        f"Resource check: {type(exc).__name__}. Detailed diagnostics remain in the local application logs."
    )
    st.stop()
context, dataset, names = e["context"], e["dataset"], e["names"]
labels = {
    "fight_brief": "Fight brief",
    "fighter_evidence": "Fighter evidence",
    "tactical_model": "Tactical model",
    "outcome_analysis": "Outcome analysis",
    "sensitivity": "Sensitivity",
    "validation": "Validation",
    "research_report": "Research report",
    "methodology": "Methodology",
}
pages = {
    key: st.Page("screens/" + key + ".py", title=label, default=key == "fight_brief")
    for key, label in labels.items()
}
st.session_state["_pages"] = pages
page = st.navigation(
    {
        "Research": [pages[k] for k in ("fight_brief", "fighter_evidence")],
        "Decision analysis": [
            pages[k] for k in ("tactical_model", "outcome_analysis", "sensitivity")
        ],
        "Research record": [pages[k] for k in ("validation", "research_report", "methodology")],
    },
    position="sidebar",
    expanded=True,
)
with st.sidebar:
    st.caption("APPLIED CONTEXT")
    st.write(f"**{names[0]}**\n\nvs **{names[1]}**")
    st.caption(
        f"Before {ui.pretty_date(context.reference_date)} · {context.weight_class}\n\n{context.scheduled_rounds} scheduled rounds"
    )
    st.divider()
    st.caption("Independent academic prototype\n\nTactical effects are explicit assumptions.")
page.run()
st.divider()
st.caption(
    f"Frozen snapshot {dataset.manifest['dataset_version']} · strictly earlier-date evidence · research prototype"
)
