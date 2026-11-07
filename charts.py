"""Gráficos Plotly padronizados do QUANTUM ROI."""
import numpy as np
import plotly.graph_objects as go
from styles import SAPPHIRE, GOLD, GREEN, AMBER, RUBY, MIDNIGHT, SLATE

LEGEND = dict(orientation="h", yanchor="bottom", y=1.10, xanchor="left", x=0)
MARGIN = dict(t=75, b=65, l=50, r=40)


def _base(fig, height=360, xt="", yt=""):
    fig.update_layout(
        height=height, margin=MARGIN, legend=LEGEND, paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF",
        font=dict(family="IBM Plex Sans, sans-serif", size=12, color=MIDNIGHT),
        separators=",.", hovermode="closest",
    )
    fig.update_xaxes(title=xt, tickangle=0, gridcolor="#EEF2F7", zerolinecolor="#CBD5E1", linecolor="#E2E8F0")
    fig.update_yaxes(title=yt, gridcolor="#EEF2F7", zerolinecolor="#CBD5E1", linecolor="#E2E8F0")
    return fig


def histogram(npvs, p5, p95, mean):
    npvs = np.asarray(npvs, dtype=float)
    lo, hi = float(np.min(npvs)), float(np.max(npvs))
    if hi <= lo:
        hi = lo + 1.0
    edges = np.linspace(lo, hi, 61)
    counts, _ = np.histogram(npvs, bins=edges)
    centers = (edges[:-1] + edges[1:]) / 2
    w = edges[1] - edges[0]
    neg = centers < 0
    fig = go.Figure()
    fig.add_bar(x=centers[neg], y=counts[neg], width=w, name="VPL negativo", marker_color=RUBY, opacity=0.85,
                hovertemplate="VPL ≈ R$ %{x:,.0f}<br>Cenários: %{y}<extra></extra>")
    fig.add_bar(x=centers[~neg], y=counts[~neg], width=w, name="VPL positivo", marker_color=SAPPHIRE, opacity=0.85,
                hovertemplate="VPL ≈ R$ %{x:,.0f}<br>Cenários: %{y}<extra></extra>")
    ymax = max(int(counts.max()), 1)
    for x, nm, col, dash in [(p5, "P5", GOLD, "dot"), (mean, "Média", MIDNIGHT, "solid"), (p95, "P95", GOLD, "dot")]:
        fig.add_scatter(x=[x, x], y=[0, ymax * 1.05], mode="lines", name=nm, line=dict(color=col, dash=dash, width=2),
                        hovertemplate=f"{nm}: R$ %{{x:,.0f}}<extra></extra>")
    fig.update_layout(barmode="overlay", bargap=0)
    return _base(fig, 380, "VPL (R$)", "Cenários")


def cumulative_band(months, cum):
    cum = np.asarray(cum, dtype=float)
    p5, p25, p50, p75, p95 = np.percentile(cum, [5, 25, 50, 75, 95], axis=0)
    m = np.asarray(months)
    fig = go.Figure()
    fig.add_scatter(x=m, y=p95, line=dict(width=0), showlegend=False, hoverinfo="skip")
    fig.add_scatter(x=m, y=p5, fill="tonexty", fillcolor="rgba(37,99,235,0.12)", line=dict(width=0), name="Faixa P5–P95",
                    hoverinfo="skip")
    fig.add_scatter(x=m, y=p75, line=dict(width=0), showlegend=False, hoverinfo="skip")
    fig.add_scatter(x=m, y=p25, fill="tonexty", fillcolor="rgba(37,99,235,0.26)", line=dict(width=0), name="Faixa P25–P75",
                    hoverinfo="skip")
    fig.add_scatter(x=m, y=p50, name="Mediana", line=dict(color=SAPPHIRE, width=2.6),
                    hovertemplate="Mês %{x}<br>Mediana: R$ %{y:,.0f}<extra></extra>")
    fig.add_hline(y=0, line=dict(color=RUBY, width=1.2, dash="dash"))
    return _base(fig, 380, "Mês", "Fluxo acumulado descontado (R$)")


def adoption(curve, logistic):
    c = np.asarray(curve, dtype=float) * 100
    m = np.arange(1, len(c) + 1)
    fig = go.Figure()
    fig.add_scatter(x=m, y=c, name="Logística (curva S)" if logistic else "Adoção imediata", fill="tozeroy",
                    fillcolor="rgba(217,119,6,0.12)", line=dict(color=GOLD, width=2.6),
                    hovertemplate="Mês %{x}<br>Adoção: %{y:.1f}%<extra></extra>")
    fig.update_yaxes(range=[0, 105])
    return _base(fig, 320, "Mês", "Adoção (%)")


def tornado(df, base):
    d = df.sort_values("impact", ascending=True)
    fig = go.Figure()
    fig.add_bar(y=d["variable"], x=d["low"] - base, base=base, orientation="h", name="Parâmetro −20%",
                marker_color=RUBY, customdata=d["low"], hovertemplate="%{y}<br>VPL: R$ %{customdata:,.0f}<extra></extra>")
    fig.add_bar(y=d["variable"], x=d["high"] - base, base=base, orientation="h", name="Parâmetro +20%",
                marker_color=SAPPHIRE, customdata=d["high"], hovertemplate="%{y}<br>VPL: R$ %{customdata:,.0f}<extra></extra>")
    fig.add_vline(x=base, line=dict(color=MIDNIGHT, width=1.5, dash="dot"))
    fig.update_layout(barmode="overlay")
    return _base(fig, max(360, 46 * len(d) + 140), "VPL determinístico (R$)", "")


def strategies(names, means, p5s, p95s, probs):
    cols = [GREEN if p >= 0.8 else (AMBER if p >= 0.5 else RUBY) for p in probs]
    m = np.asarray(means, float)
    fig = go.Figure()
    fig.add_bar(x=names, y=m, name="VPL médio", marker_color=cols,
                error_y=dict(type="data", symmetric=False, array=np.asarray(p95s) - m, arrayminus=m - np.asarray(p5s),
                             color=SLATE, thickness=1.2),
                hovertemplate="%{x}<br>VPL médio: R$ %{y:,.0f}<extra></extra>")
    fig.add_scatter(x=[None], y=[None], mode="lines", name="Intervalo P5–P95", line=dict(color=SLATE))
    return _base(fig, 380, "", "VPL (R$)")


def portfolio_bubble(df):
    fig = go.Figure()
    for lo, hi, col, nm in [(0.8, 2, GREEN, "P ≥ 80%"), (0.5, 0.8, AMBER, "50% ≤ P < 80%"), (-1, 0.5, RUBY, "P < 50%")]:
        s = df[(df["probability"] >= lo) & (df["probability"] < hi)]
        if s.empty:
            continue
        size = np.clip(np.sqrt(s["capex"].clip(lower=1).astype(float)) / 8, 12, 60)
        fig.add_scatter(x=s["probability"] * 100, y=s["mean_npv"], mode="markers+text", text=s["name"],
                        textposition="top center", name=nm, marker=dict(size=size, color=col, opacity=0.75,
                                                                      line=dict(color="#FFFFFF", width=1.5)),
                        customdata=s["capex"],
                        hovertemplate="%{text}<br>P(VPL>0): %{x:.1f}%<br>VPL médio: R$ %{y:,.0f}<br>CAPEX: R$ %{customdata:,.0f}<extra></extra>")
    fig.add_hline(y=0, line=dict(color=RUBY, width=1, dash="dash"))
    fig.update_xaxes(range=[-5, 105])
    return _base(fig, 420, "Probabilidade de VPL positivo (%)", "VPL médio (R$)")


def portfolio_bars(df):
    d = df.sort_values("mean_npv")
    fig = go.Figure()
    fig.add_bar(y=d["name"], x=d["capex"], orientation="h", name="CAPEX", marker_color=GOLD,
                hovertemplate="%{y}<br>CAPEX: R$ %{x:,.0f}<extra></extra>")
    fig.add_bar(y=d["name"], x=d["mean_npv"], orientation="h", name="VPL médio", marker_color=SAPPHIRE,
                hovertemplate="%{y}<br>VPL médio: R$ %{x:,.0f}<extra></extra>")
    fig.update_layout(barmode="group")
    return _base(fig, 420, "R$", "")
