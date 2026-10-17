"""Presentation tokens and licensed local fonts. No analytical parameters live here."""

import base64
from pathlib import Path

TOKENS = {
    "workspace": "#F3F5F7",
    "surface": "#FFFFFF",
    "text": "#172126",
    "muted": "#59656F",
    "navigation": "#20282E",
    "nav_muted": "#AEB9C2",
    "brand": "#882A3A",
    "separator": "#D8DEE3",
    "control_border": "#7A8791",
    "warning": "#765415",
    "warning_bg": "#FFF5DF",
    "error": "#A32323",
}
POLICY_COLORS = {
    "Striking priority": "#2457A6",
    "Grappling priority": "#007A71",
    "Balanced priority": "#925A08",
    "No robust preference": "#6A737D",
}
PHASE_COLORS = {"Standing": "#46525C", "Clinch": "#7A8791", "Ground": "#BBC3CB"}


def font_css(embed=False):
    folder = Path(__file__).resolve().parents[2] / "app/static/fonts"
    variants = [
        ("IBM Plex Sans", "IBMPlexSans-Regular.woff2", 400),
        ("IBM Plex Sans", "IBMPlexSans-SemiBold.woff2", 600),
        ("IBM Plex Sans Condensed", "IBMPlexSansCondensed-Bold.woff2", 700),
    ]
    rules = []
    for family, name, weight in variants:
        path = folder / name
        if embed and path.exists():
            url = "data:font/woff2;base64," + base64.b64encode(path.read_bytes()).decode()
        else:
            url = "/app/static/fonts/" + name
        rules.append(
            f"@font-face{{font-family:'{family}';src:url('{url}') format('woff2');font-weight:{weight};font-style:normal;font-display:swap}}"
        )
    return "\n".join(rules)


def shared_styles():
    return """
    :root{--mdl-bg:#F3F5F7;--mdl-surface:#FFFFFF;--mdl-text:#172126;--mdl-muted:#59656F;--mdl-action:#882A3A;--mdl-line:#D8DEE3}
    .mdl-matchup{background:#fff;border-radius:10px;padding:32px;margin:8px 0 24px}
    .mdl-fighters{display:grid;grid-template-columns:minmax(0,1fr) 64px minmax(0,1fr);gap:24px;align-items:center}
    .mdl-role,.mdl-meta{color:#59656F;font-size:14px;line-height:1.6;margin:0 0 8px}
    .mdl-fighter-name{font-family:'IBM Plex Sans Condensed','Arial Narrow',sans-serif;font-size:48px;line-height:1.05;letter-spacing:-.5px;margin:0 0 12px;overflow-wrap:anywhere;font-weight:700}
    .mdl-versus{font-size:15px;text-align:center;color:#59656F}
    .mdl-context{display:flex;gap:12px 24px;flex-wrap:wrap;font-size:14px;color:#59656F;margin-bottom:16px}
    .mdl-context strong{color:#172126;font-weight:600}
    .mdl-baseline{display:flex;gap:16px;flex-wrap:wrap;align-items:center;background:#F3F5F7;padding:16px 20px;border-radius:8px;margin-top:24px}
    .mdl-baseline-value{font-size:28px;line-height:1.2;font-variant-numeric:tabular-nums;font-weight:600}
    .mdl-badge{display:inline-block;border-radius:5px;padding:4px 8px;background:#FFF5DF;color:#765415;font-size:13px;line-height:1.4;font-weight:600;vertical-align:middle}
    .mdl-badge.neutral{background:#E8EDF1;color:#46525C}
    .mdl-badge.current{background:#E8EDF1;color:#172126}
    .mdl-copy{max-width:76ch;color:#59656F;line-height:1.65}
    .mdl-policy{display:grid;grid-template-columns:minmax(170px,1fr) minmax(240px,1.4fr);gap:16px 32px;align-items:center;padding:20px 0;border-bottom:1px solid #D8DEE3}
    .mdl-policy:last-child{border-bottom:0}
    .mdl-policy h3{margin:0 0 6px;font-size:18px;font-weight:600}
    .mdl-policy p{margin:0;color:#59656F;font-size:14px;line-height:1.5}
    .mdl-phasebar{display:flex;width:100%;height:12px;border-radius:3px;overflow:hidden;margin:8px 0 10px}
    .mdl-phaselabels{display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap;font-size:13px;color:#59656F;font-variant-numeric:tabular-nums}
    .mdl-legend{display:flex;gap:12px 24px;flex-wrap:wrap;font-size:13px;color:#59656F}
    .mdl-swatch{display:inline-block;width:12px;height:12px;margin-right:6px;vertical-align:-1px;border-radius:2px}
    .mdl-comparison{width:100%;border-collapse:collapse;font-variant-numeric:tabular-nums;font-size:15px}
    .mdl-comparison th,.mdl-comparison td{padding:14px 16px;border-bottom:1px solid #D8DEE3;text-align:right;vertical-align:middle}
    .mdl-comparison th:first-child,.mdl-comparison td:first-child{text-align:left;max-width:340px}
    .mdl-comparison thead th{font-weight:600;color:#172126;background:#F3F5F7}
    .mdl-comparison .mdl-group td{background:#F3F5F7;text-align:left;font-weight:600;color:#172126;padding-top:20px}
    .mdl-unit{display:block;color:#59656F;font-size:13px;font-weight:400;margin-top:3px}
    .mdl-decision{background:#fff;border-radius:10px;padding:24px 28px;margin:16px 0 24px;border-left:4px solid #737B85}
    .mdl-decision h2{font-size:22px;margin:8px 0 12px;line-height:1.3}
    .mdl-decision p{max-width:80ch;font-size:15px;line-height:1.65;margin:8px 0;color:#59656F}
    .mdl-snapshot{font-size:13px;color:#59656F;overflow-wrap:anywhere}
    .mdl-inline-values{display:flex;gap:16px 32px;flex-wrap:wrap;padding:16px 0;font-size:14px;color:#59656F}
    .mdl-inline-values strong{color:#172126;font-variant-numeric:tabular-nums;font-weight:600}
    .mdl-table-scroll{overflow:auto;max-width:100%;border-radius:8px;background:#fff}
    .mdl-empty{background:#fff;border-radius:10px;padding:24px;margin:16px 0}
    .mdl-mark{width:32px;height:32px;display:inline-flex;align-items:center;justify-content:center;background:#882A3A;color:white;border-radius:6px;font-weight:600;flex:0 0 32px}
    .mdl-brand{display:flex;gap:10px;align-items:center;margin:0 0 12px;font-size:19px;line-height:1.1;font-weight:600}
    .mdl-sidebar-context{color:#fff;border-top:1px solid #46525C;padding-top:20px;margin-top:20px;font-size:14px;line-height:1.6}
    .mdl-sidebar-context small{color:#AEB9C2;font-size:13px}
    .mdl-sidebar-context p{margin:6px 0 12px}
    .mdl-report-metrics{display:flex;gap:24px;flex-wrap:wrap;margin:16px 0}
    @media(max-width:600px){.mdl-matchup{padding:20px}.mdl-fighters{grid-template-columns:minmax(0,1fr);gap:12px}.mdl-fighter-name{font-size:34px;line-height:1.1}.mdl-versus{text-align:left;font-size:13px}.mdl-baseline{padding:16px}.mdl-policy{grid-template-columns:minmax(0,1fr);gap:8px}.mdl-comparison{font-size:14px}.mdl-comparison th,.mdl-comparison td{padding:10px 8px}.mdl-decision{padding:20px}.mdl-phaselabels{font-size:12px}}
    @media(prefers-reduced-motion:reduce){*,*::before,*::after{animation-duration:0.01ms!important;transition-duration:0.01ms!important;scroll-behavior:auto!important}}
    """
