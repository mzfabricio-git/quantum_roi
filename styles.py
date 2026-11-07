"""Identidade visual e formatadores do QUANTUM ROI."""
import math
from html import escape

MIDNIGHT = "#0F172A"
SAPPHIRE = "#2563EB"
GOLD = "#D97706"
GREEN = "#059669"
AMBER = "#D97706"
RUBY = "#E11D48"
SLATE = "#64748B"
BORDER = "#E2E8F0"
BG = "#F8FAFC"

LOGO_SVG = """<svg width="{s}" height="{s}" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">
<rect width="64" height="64" rx="14" fill="#0F172A"/>
<rect x="11" y="40" width="5" height="12" rx="1.5" fill="#2563EB"/>
<rect x="19" y="30" width="5" height="22" rx="1.5" fill="#2563EB"/>
<rect x="27" y="18" width="5" height="34" rx="1.5" fill="#D97706"/>
<rect x="35" y="22" width="5" height="30" rx="1.5" fill="#D97706"/>
<rect x="43" y="34" width="5" height="18" rx="1.5" fill="#2563EB"/>
<path d="M6 50 C 18 50, 20 12, 31 12 S 44 50, 58 50" stroke="#F8FAFC" stroke-width="2.4" fill="none" stroke-linecap="round"/>
</svg>"""


def logo(size=44):
    return LOGO_SVG.replace("{s}", str(size))


CSS = """
<style>
html, body, [class*="css"], .stApp { font-family: 'IBM Plex Sans', sans-serif; }
.stApp { background: #F8FAFC; color: #0F172A; }
section[data-testid="stSidebar"] { background: #FFFFFF; border-right: 1px solid #E2E8F0; }
.block-container { padding-top: 1.6rem; padding-bottom: 3rem; max-width: 1400px; }
h1, h2, h3, h4 { color: #0F172A; letter-spacing: -0.01em; }
.qr-top { display:flex; align-items:center; gap:16px; background:#0F172A; border-radius:14px; padding:16px 22px; margin-bottom:18px; }
.qr-top .t { color:#F8FAFC; font-weight:700; font-size:1.35rem; letter-spacing:0.14em; }
.qr-top .t span { color:#D97706; }
.qr-top .s { color:#94A3B8; font-size:0.86rem; margin-top:2px; }
.qr-top .tag { margin-left:auto; font-family:'IBM Plex Mono',monospace; color:#CBD5E1; font-size:0.74rem; text-align:right; line-height:1.5; }
.qr-side { display:flex; align-items:center; gap:10px; margin-bottom:6px; }
.qr-side b { font-size:1rem; letter-spacing:0.12em; color:#0F172A; }
.qr-side small { display:block; color:#64748B; font-size:0.7rem; letter-spacing:0.04em; }
.qr-card { background:#FFFFFF; border:1px solid #E2E8F0; border-radius:14px; padding:14px 16px; height:100%; box-shadow:0 2px 8px #0F172A05; }
.qr-card .l { font-size:0.7rem; text-transform:uppercase; letter-spacing:0.09em; color:#64748B; font-weight:600; }
.qr-card .v { font-family:'IBM Plex Mono',monospace; font-size:1.22rem; font-weight:600; color:#0F172A; margin-top:4px; overflow-wrap:anywhere; }
.qr-card .h { font-size:0.74rem; color:#64748B; margin-top:2px; }
.qr-card.g { border-left:4px solid #059669; } .qr-card.a { border-left:4px solid #D97706; } .qr-card.r { border-left:4px solid #E11D48; } .qr-card.b { border-left:4px solid #2563EB; }
.qr-sec { font-weight:700; font-size:0.95rem; color:#0F172A; margin:18px 0 2px 0; display:flex; align-items:center; gap:8px; }
.qr-sec:before { content:''; width:4px; height:16px; background:#D97706; border-radius:2px; display:inline-block; }
.qr-sub { color:#64748B; font-size:0.8rem; margin-bottom:4px; }
.qr-pill { display:inline-block; font-family:'IBM Plex Mono',monospace; font-size:0.72rem; padding:3px 9px; border-radius:999px; border:1px solid #E2E8F0; background:#FFFFFF; color:#334155; margin-right:6px; }
.qr-light { display:inline-flex; align-items:center; gap:8px; font-weight:600; font-size:0.85rem; padding:6px 12px; border-radius:999px; }
.qr-light i { width:10px; height:10px; border-radius:50%; display:inline-block; }
.qr-note { background:#FFFFFF; border:1px solid #E2E8F0; border-left:4px solid #2563EB; border-radius:14px; padding:12px 16px; font-size:0.84rem; color:#334155; }
div[data-testid="stPlotlyChart"] { background:#FFFFFF; border:1px solid #E2E8F0; border-radius:14px; padding:4px; }
.stButton>button, .stDownloadButton>button { border-radius:10px; font-weight:600; }
.stButton>button[kind="primary"] { background:#0F172A; border-color:#0F172A; }
.stButton>button[kind="primary"]:hover { background:#2563EB; border-color:#2563EB; }
</style>
"""


def _ok(x):
    return x is not None and isinstance(x, (int, float)) and math.isfinite(x)


def brl(x, dec=0):
    if not _ok(x):
        return "—"
    s = f"{abs(x):,.{dec}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return ("-R$ " if x < 0 else "R$ ") + s


def brl_short(x):
    if not _ok(x):
        return "—"
    a = abs(x)
    sign = "-" if x < 0 else ""
    if a >= 1e6:
        return f"{sign}R$ {a/1e6:.2f} mi".replace(".", ",")
    if a >= 1e3:
        return f"{sign}R$ {a/1e3:.1f} mil".replace(".", ",")
    return brl(x)


def pct(x, dec=1):
    if not _ok(x):
        return "—"
    return f"{x:.{dec}f}%".replace(".", ",")


def months(x):
    if not _ok(x):
        return "Não atinge"
    return f"{x:.1f} meses".replace(".", ",")


def light(p):
    """Semáforo financeiro: >=0,8 verde, >=0,5 âmbar, senão rubi."""
    if p is None or not math.isfinite(p):
        return ("Indeterminado", SLATE, "b")
    if p >= 0.8:
        return ("Viável", GREEN, "g")
    if p >= 0.5:
        return ("Atenção", AMBER, "a")
    return ("Risco elevado", RUBY, "r")


def card(label, value, hint="", tone="b"):
    return f'<div class="qr-card {tone}"><div class="l">{escape(str(label))}</div><div class="v">{escape(str(value))}</div><div class="h">{escape(str(hint))}</div></div>'


def light_badge(p):
    txt, col, _ = light(p)
    return f'<span class="qr-light" style="background:{col}14;color:{col};border:1px solid {col}55"><i style="background:{col}"></i>{txt} · P(VPL&gt;0) = {pct((p or 0)*100)}</span>'
