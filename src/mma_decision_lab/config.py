from pathlib import Path

from .theme import POLICY_COLORS

ROOT = Path(__file__).resolve().parents[2]
VERSION = "0.1.0"
FEATURE_VERSION = "strict-date-v1"
MIN_HISTORY = 2
SEED = 422
DEFAULT_DRAWS = 5000
# Backward-compatible alias; all presentation colors share one token source.
COLORS = POLICY_COLORS
REFERENCES = [
    {
        "title": "Holmes, McHale & Żychaluk (2023). A Markov chain model for forecasting results of mixed martial arts contests.",
        "url": "https://doi.org/10.1016/j.ijforecast.2022.01.007",
    },
    {
        "title": "Miarka, Brito & Amtmann (2017). Performance probabilities and outcome effects in technical–tactical factors with bout phase changes of mixed martial arts.",
        "url": "https://doi.org/10.1080/24748668.2017.1360103",
    },
    {
        "title": "James et al. (2017). Identifying the performance characteristics of a winning outcome in elite mixed martial arts competition.",
        "url": "https://doi.org/10.1016/j.jsams.2016.08.001",
    },
    {
        "title": "Bueno et al. (2022). Exploratory systematic review of mixed martial arts.",
        "url": "https://doi.org/10.3390/sports10060080",
    },
    {
        "title": "Gneiting & Raftery (2007). Strictly proper scoring rules, prediction, and estimation.",
        "url": "https://doi.org/10.1198/016214506000001437",
    },
    {
        "title": "Greco1899. Published UFCStats community CSV archive (GPL-3.0 declared).",
        "url": "https://github.com/Greco1899/scrape_ufc_stats",
    },
]
