"""QUANTUM ROI — Terminal Quantitativo de Viabilidade, Risco e Retorno de Projetos de IA."""
import math
import random
import io
import zipfile
from html import escape
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

from data import initial_projects
from engine import simulate, deterministic, sensitivity, optimize, portfolio_summary
import charts
from styles import CSS, logo, brl, brl_short, pct, months, light, card, light_badge

st.set_page_config(page_title="QUANTUM ROI", page_icon=None, layout="wide", initial_sidebar_state="expanded")
st.markdown(CSS, unsafe_allow_html=True)

PARAMS = {
    # chave: (rótulo, tipo, mín, máx, passo, ajuda)
    "team": ("Equipe impactada (pessoas)", int, 1, 100000, 1, "Número de colaboradores cuja rotina é afetada."),
    "hourly": ("Custo-hora carregado (R$)", float, 0.0, 100000.0, 5.0, "Salário + encargos por hora."),
    "hours": ("Horas liberadas por pessoa/mês", float, 0.0, 744.0, 1.0, "Capacidade liberada no regime pleno."),
    "savings": ("Economia direta mensal (R$)", float, 0.0, 1e9, 1000.0, "Redução de custo em caixa (licenças, terceiros)."),
    "capex": ("Investimento inicial CAPEX (R$)", float, 0.0, 1e10, 5000.0, "Desembolso no mês zero."),
    "opex": ("Custo operacional mensal OPEX (R$)", float, 0.0, 1e9, 500.0, "Nuvem, licenças, sustentação."),
    "adoption": ("Adoção-alvo (%)", int, 0, 100, 1, "Percentual da equipe que adota a solução no regime pleno."),
    "volatility": ("Volatilidade dos benefícios (%)", int, 0, 100, 1, "Desvio relativo usado no Monte Carlo."),
    "implementation": ("Implantação (meses)", int, 0, 24, 1, "Meses até o início da captura de valor."),
}
LABELS_SHORT = {"team": "Equipe", "hourly": "Custo-hora", "hours": "Horas/mês", "savings": "Economia direta",
                "capex": "CAPEX", "opex": "OPEX", "adoption": "Adoção", "volatility": "Volatilidade",
                "implementation": "Implantação"}
PAGES = ["Simulador Monte Carlo", "Visão geral", "Sensibilidade", "Otimização", "Portfólio", "Metodologia"]
N_SIM = 10000


# ---------------------------------------------------------------- estado
def _cast(k, v):
    t, lo, hi = PARAMS[k][1], PARAMS[k][2], PARAMS[k][3]
    try:
        v = float(v)
        if not math.isfinite(v):
            v = lo
    except (TypeError, ValueError):
        v = lo
    v = min(max(v, lo), hi)
    return int(round(v)) if t is int else float(v)


def _row(pid):
    df = st.session_state.df
    r = df[df["id"] == pid]
    return r.iloc[0].to_dict() if not r.empty else df.iloc[0].to_dict()


def load_project():
    r = _row(st.session_state.project_id)
    for k in PARAMS:
        st.session_state["param_" + k] = _cast(k, r.get(k))
    st.session_state.opt_results = None


def init_state():
    if "df" not in st.session_state:
        df = pd.DataFrame(initial_projects()).reset_index(drop=True)
        st.session_state.df = df
        st.session_state.project_id = int(df.iloc[0]["id"])
        st.session_state.nav = PAGES[0]
        st.session_state.horizon = 36
        st.session_state.discount = 12.0
        st.session_state.seed = 42
        st.session_state.logistic = True
        st.session_state.save_msg = None
        st.session_state.opt_results = None
        st.session_state.flash = None
        load_project()
    ids = st.session_state.df["id"].astype(int).tolist()
    if st.session_state.project_id not in ids:
        st.session_state.project_id = ids[0]
        load_project()


init_state()


def current_project():
    p = dict(_row(st.session_state.project_id))
    for k in PARAMS:
        p[k] = st.session_state["param_" + k]
    return p


def _key(p):
    return tuple(sorted((k, (float(v) if isinstance(v, (int, float, np.integer, np.floating)) else str(v)))
                        for k, v in p.items()))


# ---------------------------------------------------------------- cache (somente sessão em memória)
@st.cache_data(persist=None, show_spinner=False, max_entries=8)
def c_sim(pk, horizon, discount, seed, logistic):
    return simulate(dict(pk), horizon=horizon, discount=discount, seed=seed, logistic=logistic, n=N_SIM)


@st.cache_data(persist=None, show_spinner=False, max_entries=64)
def c_det(pk, horizon, discount, logistic):
    return deterministic(dict(pk), horizon=horizon, discount=discount, logistic=logistic)


@st.cache_data(persist=None, show_spinner=False, max_entries=32)
def c_sens(pk, horizon, discount, logistic):
    return sensitivity(dict(pk), horizon=horizon, discount=discount, logistic=logistic)


@st.cache_data(persist=None, show_spinner=False, max_entries=16)
def c_opt(pk, horizon, discount, logistic):
    return optimize(dict(pk), horizon=horizon, discount=discount, logistic=logistic)


@st.cache_data(persist=None, show_spinner=False, max_entries=16)
def c_port(records, horizon, discount, seed, logistic):
    df = pd.DataFrame([dict(r) for r in records])
    return portfolio_summary(df, horizon=horizon, discount=discount, seed=seed, logistic=logistic)


def g():
    s = st.session_state
    return int(s.horizon), float(s.discount), int(s.seed), bool(s.logistic)


# ---------------------------------------------------------------- callbacks
def cb_restore():
    load_project()
    st.session_state.logistic = True
    st.session_state.flash = ("info", "Premissas restauradas a partir do portfólio salvo na sessão.")


def cb_new_seed():
    st.session_state.seed = random.randint(1, 999999)


def cb_reset_seed():
    st.session_state.seed = 42


def cb_apply(idx):
    res = st.session_state.opt_results
    if not res or idx >= len(res):
        return
    p = res[idx]["project"]
    for k in PARAMS:
        if k in p:
            st.session_state["param_" + k] = _cast(k, p[k])
    st.session_state.nav = PAGES[0]
    st.session_state.flash = ("success", f"Estratégia \"{res[idx]['name']}\" aplicada aos controles. "
                              "Resultado hipotético: confirme as premissas antes de salvar no portfólio.")


def cb_params_to_portfolio():
    df = st.session_state.df.copy()
    for k, spec in PARAMS.items():
        if spec[1] is float:
            df[k] = df[k].astype(float)
    i = df.index[df["id"] == st.session_state.project_id]
    if len(i):
        for k in PARAMS:
            df.loc[i[0], k] = st.session_state["param_" + k]
        st.session_state.df = df
        st.session_state.flash = ("success", "Premissas atuais gravadas no portfólio desta sessão.")


def cb_save_table():
    ed = st.session_state.get("pending_df")
    if ed is None:
        return
    ed = ed.copy().reset_index(drop=True)
    errs = []
    if ed.empty:
        errs.append("O portfólio precisa ter ao menos um projeto.")
    names = ed["name"].astype(str).str.strip() if "name" in ed else pd.Series(dtype=str)
    if ed["name"].isna().any() or (names == "").any() or (names.str.lower() == "nan").any():
        errs.append("Todos os projetos precisam de nome.")
    for k, (lab, t, lo, hi, *_r) in PARAMS.items():
        col = pd.to_numeric(ed[k], errors="coerce")
        bad = col.isna() | ~np.isfinite(col.astype(float).fillna(np.nan)) | (col < lo) | (col > hi)
        if bad.any():
            linhas = ", ".join(str(x + 1) for x in ed.index[bad][:6])
            errs.append(f"{lab}: valor inválido nas linhas {linhas} (permitido {lo} a {hi:,.0f}).".replace(",", "."))
        else:
            ed[k] = col.round().astype(int) if t is int else col.astype(float)
    if errs:
        st.session_state.save_msg = ("error", errs)
        return
    ids = pd.to_numeric(ed["id"], errors="coerce")
    nxt = int(np.nanmax(ids.values)) + 1 if ids.notna().any() else 1
    for i in ed.index:
        if pd.isna(ids[i]) or (ids[:i] == ids[i]).any():
            ids[i] = nxt
            nxt += 1
    ed["id"] = ids.astype(int)
    for c in ["name", "area", "note"]:
        if c in ed:
            ed[c] = ed[c].fillna("").astype(str)
    ed["name"] = ed["name"].str.strip()
    st.session_state.df = ed
    if st.session_state.project_id in ed["id"].tolist():
        load_project()
    st.session_state.save_msg = ("success", [f"Portfólio salvo na sessão: {len(ed)} projetos."])


def cb_reset_portfolio():
    st.session_state.df = pd.DataFrame(initial_projects()).reset_index(drop=True)
    st.session_state.project_id = int(st.session_state.df.iloc[0]["id"])
    load_project()
    st.session_state.save_msg = ("info", ["Portfólio original restaurado."])


def export_project_zip():
    """Exporta somente o código necessário, sem dados de sessão ou credenciais."""
    source_dir = Path(__file__).resolve().parent
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for filename in ("app.py", "data.py", "engine.py", "charts.py", "styles.py"):
            archive.writestr(filename, (source_dir / filename).read_bytes())
        archive.writestr("requirements.txt", "streamlit\npandas\nnumpy\nplotly\n")
        archive.writestr(
            ".streamlit/config.toml",
            '[theme]\n'
            'base = "light"\n'
            'primaryColor = "#2563EB"\n'
            'backgroundColor = "#F8FAFC"\n'
            'secondaryBackgroundColor = "#EFF3F8"\n'
            'textColor = "#0F172A"\n'
            'font = "sans serif"\n',
        )
    buffer.seek(0)
    return buffer


# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.markdown(f'<div class="qr-side">{logo(38)}<div><b>QUANTUM ROI</b><small>Terminal quantitativo</small></div></div>',
                unsafe_allow_html=True)
    st.radio("Navegação", PAGES, key="nav", label_visibility="collapsed")
    st.divider()
    df_s = st.session_state.df
    names = dict(zip(df_s["id"].astype(int), df_s["name"].astype(str)))
    st.selectbox("Projeto em análise", list(names.keys()), format_func=lambda i: names.get(i, str(i)),
                 key="project_id", on_change=load_project)
    with st.expander("Premissas do projeto", expanded=True):
        for k, (lab, t, lo, hi, step, hlp) in PARAMS.items():
            if k in ("adoption", "volatility", "implementation"):
                st.slider(lab, min_value=int(lo), max_value=int(hi), step=int(step), key="param_" + k, help=hlp)
            elif t is int:
                st.number_input(lab, min_value=int(lo), max_value=int(hi), step=int(step), key="param_" + k, help=hlp)
            else:
                st.number_input(lab, min_value=float(lo), max_value=float(hi), step=float(step), format="%.2f",
                                key="param_" + k, help=hlp)
        st.checkbox("Adoção logística (curva S)", key="logistic",
                    help="Desmarcado: adoção-alvo imediata após a implantação.")
        c1, c2 = st.columns(2)
        c1.button("Restaurar", on_click=cb_restore, use_container_width=True)
        c2.button("Gravar", on_click=cb_params_to_portfolio, use_container_width=True,
                  help="Grava estas premissas no portfólio da sessão.")
    with st.expander("Parâmetros do modelo", expanded=False):
        st.slider("Horizonte (meses)", 12, 120, step=6, key="horizon")
        st.number_input("Taxa de desconto anual (%)", 0.0, 100.0, step=0.5, key="discount")
        st.number_input("Semente aleatória", 0, 999999, step=1, key="seed")
        c1, c2 = st.columns(2)
        c1.button("Nova semente", on_click=cb_new_seed, use_container_width=True)
        c2.button("Semente 42", on_click=cb_reset_seed, use_container_width=True)
    st.caption("Sem banco de dados: alterações vivem apenas nesta sessão.")
    st.divider()
    st.download_button(
        "📦 Exportar Código para GitHub (.ZIP)",
        data=export_project_zip(),
        file_name="quantum_roi_github.zip",
        mime="application/zip",
        use_container_width=True,
    )

H, D, SEED, LOG = g()
proj = current_project()
PK = _key(proj)

# ---------------------------------------------------------------- topo
st.markdown(
    f'<div class="qr-top">{logo(50)}<div><div class="t">QUANTUM <span>ROI</span></div>'
    f'<div class="s">Terminal Quantitativo de Viabilidade, Risco (Monte Carlo) e Retorno de Projetos de IA &amp; Automação</div></div>'
    f'<div class="tag">{N_SIM:,} cenários · {H} meses<br>desconto {pct(D)} a.a. · semente {SEED}</div></div>'.replace("10,000", "10.000"),
    unsafe_allow_html=True)

if st.session_state.flash:
    kind, msg = st.session_state.flash
    getattr(st, kind)(msg)
    st.session_state.flash = None


def sec(title, sub=""):
    st.markdown(f'<div class="qr-sec">{title}</div>' + (f'<div class="qr-sub">{sub}</div>' if sub else ""),
                unsafe_allow_html=True)


def capacity_note():
    st.markdown('<div class="qr-note"><b>Leitura correta das horas:</b> horas liberadas da equipe são <b>capacidade valorizada</b> '
                'ao custo-hora, não economia de caixa garantida. Só viram caixa se houver realocação, redução de horas extras, '
                'contratações evitadas ou aumento de receita. A economia direta mensal é o único componente tratado como caixa.</div>',
                unsafe_allow_html=True)


def kpis(r):
    txt, col, tone = light(r["probability"])
    items = [
        ("VPL médio", brl_short(r["mean_npv"]), f"Mediana {brl_short(r['median_npv'])}", "g" if r["mean_npv"] > 0 else "r"),
        ("P(VPL > 0)", pct(r["probability"] * 100), txt, tone),
        ("Intervalo P5 – P95", f"{brl_short(r['p5'])} | {brl_short(r['p95'])}", "90% dos cenários", "b"),
        ("ROI descontado", pct(r["roi"]), "VPL líquido / custos descontados", "g" if (r["roi"] or 0) > 0 else "r"),
        ("TIR anual", pct(r["irr"]) if r["irr"] is not None else "—", "Fluxo determinístico", "b"),
        ("Payback descontado", months(r["payback"]), "Fluxo determinístico", "a" if r["payback"] is None else "b"),
    ]
    for start in (0, 3):
        cols = st.columns(3)
        for c, (l, v, h, t) in zip(cols, items[start:start + 3]):
            c.markdown(card(l, v, h, t), unsafe_allow_html=True)


# ================================================================ páginas
page = st.session_state.nav

if page == "Simulador Monte Carlo":
    with st.spinner("Simulando 10.000 cenários..."):
        r = c_sim(PK, H, D, SEED, LOG)
    head_l, head_r = st.columns([3, 2])
    with head_l:
        st.markdown(f"### {proj['name']}")
        st.markdown(f'<span class="qr-pill">{escape(str(proj.get("area", "")))}</span><span class="qr-pill">ID {proj["id"]}</span>'
                    f'<span class="qr-pill">{"Logística" if LOG else "Adoção imediata"}</span>', unsafe_allow_html=True)
        if str(proj.get("note", "")).strip():
            st.caption(str(proj["note"]))
    with head_r:
        st.markdown(f'<div style="text-align:right;margin-top:14px">{light_badge(r["probability"])}</div>',
                    unsafe_allow_html=True)
        st.markdown(f'<div style="text-align:right;margin-top:8px"><span class="qr-pill">{len(r["npvs"]):,} simulações</span>'
                    f'<span class="qr-pill">{float(r["elapsed_ms"]):.0f} ms</span><span class="qr-pill">horizonte {H} m</span>'
                    f'<span class="qr-pill">semente {SEED}</span></div>'.replace(",", "."), unsafe_allow_html=True)
    kpis(r)

    c1, c2 = st.columns(2)
    with c1:
        sec("Distribuição do VPL", "Rubi: cenários com perda. Safira: cenários com ganho. Linhas: P5, média e P95.")
        st.plotly_chart(charts.histogram(r["npvs"], r["p5"], r["p95"], r["mean_npv"]), use_container_width=True)
    with c2:
        sec("Fluxo de caixa acumulado descontado", "Mediana e faixas percentílicas; CAPEX negativo no mês zero.")
        st.plotly_chart(charts.cumulative_band(r["months"], r["cumulative"]), use_container_width=True)

    c3, c4 = st.columns([3, 2])
    with c3:
        sec("Curva de adoção", "Percentual da equipe que adota a solução mês a mês, após a implantação.")
        st.plotly_chart(charts.adoption(r["adoption_curve"], LOG), use_container_width=True)
    with c4:
        sec("Percentis da distribuição do VPL")
        qs = [1, 5, 10, 25, 50, 75, 90, 95, 99]
        vals = np.percentile(r["npvs"], qs)
        st.dataframe(pd.DataFrame({"Percentil": [f"P{q}" for q in qs], "VPL": [brl(v) for v in vals]}),
                     hide_index=True, use_container_width=True, height=360)
    capacity_note()
    st.caption(f"Tempo real de cálculo da simulação: {float(r['elapsed_ms']):.1f} ms (resultado reutilizado do cache da sessão "
               "quando as premissas não mudam). Semáforo: verde P ≥ 80%, âmbar P ≥ 50%, rubi abaixo de 50%.".replace(".", ",", 1))

elif page == "Visão geral":
    st.markdown("### Visão geral do portfólio")
    st.caption("Cada projeto é simulado com 10.000 cenários sob os mesmos parâmetros de modelo.")
    with st.spinner("Calculando portfólio..."):
        recs = tuple(_key(r) for r in st.session_state.df.to_dict("records"))
        ps = c_port(recs, H, D, SEED, LOG).copy()
    tot_capex = float(ps["capex"].sum())
    tot_npv = float(ps["mean_npv"].sum())
    n_g = int((ps["probability"] >= 0.8).sum())
    best = ps.loc[ps["mean_npv"].idxmax()]
    cols = st.columns(4)
    cols[0].markdown(card("Projetos", str(len(ps)), f"{n_g} com P ≥ 80%", "b"), unsafe_allow_html=True)
    cols[1].markdown(card("CAPEX total", brl_short(tot_capex), "Investimento inicial agregado", "a"), unsafe_allow_html=True)
    cols[2].markdown(card("Soma dos VPLs médios", brl_short(tot_npv), "Soma de expectativas; não é risco agregado",
                          "g" if tot_npv > 0 else "r"), unsafe_allow_html=True)
    cols[3].markdown(card("Maior VPL médio", str(best["name"]), brl_short(float(best["mean_npv"])), "g"),
                     unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        sec("Risco x retorno", "Tamanho da bolha proporcional ao CAPEX; cor pelo semáforo financeiro.")
        st.plotly_chart(charts.portfolio_bubble(ps), use_container_width=True)
    with c2:
        sec("CAPEX versus VPL médio")
        st.plotly_chart(charts.portfolio_bars(ps), use_container_width=True)
    sec("Ranking comparativo")
    rk = ps.sort_values("mean_npv", ascending=False)
    st.dataframe(pd.DataFrame({
        "Semáforo": [light(p)[0] for p in rk["probability"]],
        "Projeto": rk["name"], "Área": rk["area"], "CAPEX": [brl(v) for v in rk["capex"]],
        "VPL médio": [brl(v) for v in rk["mean_npv"]], "P(VPL>0)": [pct(p * 100) for p in rk["probability"]],
        "TIR a.a.": [pct(v) if v is not None and not (isinstance(v, float) and math.isnan(v)) else "—" for v in rk["irr"]],
        "Payback": [months(v) if v is not None and not (isinstance(v, float) and math.isnan(v)) else "Não atinge" for v in rk["payback"]],
        "ROI": [pct(v) for v in rk["roi"]],
    }), hide_index=True, use_container_width=True)
    capacity_note()

elif page == "Sensibilidade":
    st.markdown(f"### Sensibilidade — {proj['name']}")
    st.caption("Cada premissa é variada em ±20% (respeitando limites válidos) mantendo as demais fixas. VPL determinístico.")
    det = c_det(PK, H, D, LOG)
    sd = c_sens(PK, H, D, LOG).copy()
    sd["variable"] = sd["variable"].map(lambda v: LABELS_SHORT.get(v, v))
    top = sd.sort_values("impact", ascending=False).iloc[0]
    cols = st.columns(3)
    cols[0].markdown(card("VPL determinístico base", brl_short(det["npv"]), "Sem incerteza", "b"), unsafe_allow_html=True)
    cols[1].markdown(card("Premissa mais crítica", str(top["variable"]), f"Amplitude {brl_short(float(top['impact']))}", "a"),
                     unsafe_allow_html=True)
    flips = sd[(np.sign(sd["low"]) != np.sign(sd["high"]))]
    cols[2].markdown(card("Premissas que invertem o sinal", str(len(flips)),
                          ", ".join(flips["variable"]) if len(flips) else "Nenhuma", "r" if len(flips) else "g"),
                     unsafe_allow_html=True)
    sec("Gráfico tornado", "Barras partem do VPL base; rubi = premissa −20%, safira = premissa +20%.")
    st.plotly_chart(charts.tornado(sd, float(det["npv"])), use_container_width=True)
    sec("Tabela de impacto")
    t = sd.sort_values("impact", ascending=False)
    st.dataframe(pd.DataFrame({"Premissa": t["variable"], "VPL com −20%": [brl(v) for v in t["low"]],
                               "VPL com +20%": [brl(v) for v in t["high"]], "Amplitude": [brl(v) for v in t["impact"]]}),
                 hide_index=True, use_container_width=True)

elif page == "Otimização":
    st.markdown(f"### Otimização — {proj['name']}")
    st.warning("Estratégias são cenários hipotéticos. Exigem confirmação das premissas (orçamento de treinamento, "
               "poder de negociação, escopo do MVP) antes de qualquer decisão. Não há retorno garantido.")
    with st.spinner("Simulando estratégias candidatas..."):
        res = c_opt(PK, H, D, LOG)
    st.session_state.opt_results = res
    base = res[0]["result"]
    best_i = max(range(len(res)), key=lambda i: (res[i]["result"]["probability"], res[i]["result"]["mean_npv"]))
    sec("Comparação de estratégias", "Barra = VPL médio; haste = intervalo P5–P95; cor = semáforo de probabilidade.")
    st.plotly_chart(charts.strategies([x["name"] for x in res], [x["result"]["mean_npv"] for x in res],
                                      [x["result"]["p5"] for x in res], [x["result"]["p95"] for x in res],
                                      [x["result"]["probability"] for x in res]), use_container_width=True)
    sec("Estratégias candidatas")
    for i, s in enumerate(res):
        rr = s["result"]
        with st.container(border=True):
            a, b, c, d, e = st.columns([3, 1.3, 1.3, 1.3, 1.4])
            tag = "  ·  RECOMENDADA" if i == best_i else ""
            a.markdown(f"**{s['name']}**{tag}")
            a.caption(s["description"])
            changes = [f"{LABELS_SHORT[k]}: {proj[k]} → {s['project'][k]}" for k in PARAMS
                       if k in s["project"] and _cast(k, s["project"][k]) != _cast(k, proj[k])]
            if changes:
                a.caption("Alterações: " + "; ".join(changes))
            b.metric("VPL médio", brl_short(rr["mean_npv"]), delta=brl_short(rr["mean_npv"] - base["mean_npv"]) if i else None)
            c.metric("P(VPL>0)", pct(rr["probability"] * 100),
                     delta=f"{(rr['probability'] - base['probability']) * 100:+.1f} p.p.".replace(".", ",") if i else None)
            d.metric("Payback", months(rr["payback"]))
            if i:
                e.button("Aplicar recomendada" if i == best_i else "Aplicar", key=f"apply_{i}", on_click=cb_apply,
                         args=(i,), type="primary" if i == best_i else "secondary", use_container_width=True)
            else:
                e.caption("Cenário atual")
    st.caption("Aplicar altera apenas os controles da barra lateral. Use Gravar para persistir no portfólio da sessão.")

elif page == "Portfólio":
    st.markdown("### Portfólio de projetos")
    st.info("Sem banco de dados: alterações salvas valem apenas para esta sessão e serão perdidas quando ela terminar. "
            "Exporte o CSV para guardar uma cópia.")
    cfg = {
        "id": st.column_config.NumberColumn("ID", disabled=True),
        "name": st.column_config.TextColumn("Projeto", required=True),
        "area": st.column_config.TextColumn("Área"),
        "team": st.column_config.NumberColumn("Equipe", min_value=1, step=1),
        "hourly": st.column_config.NumberColumn("Custo-hora R$", min_value=0.0, format="%.2f"),
        "hours": st.column_config.NumberColumn("Horas/mês", min_value=0.0),
        "savings": st.column_config.NumberColumn("Economia R$/mês", min_value=0.0, format="%.0f"),
        "capex": st.column_config.NumberColumn("CAPEX R$", min_value=0.0, format="%.0f"),
        "opex": st.column_config.NumberColumn("OPEX R$/mês", min_value=0.0, format="%.0f"),
        "adoption": st.column_config.NumberColumn("Adoção %", min_value=0, max_value=100, step=1),
        "volatility": st.column_config.NumberColumn("Volatilidade %", min_value=0, max_value=100, step=1),
        "implementation": st.column_config.NumberColumn("Implantação (m)", min_value=0, max_value=24, step=1),
        "note": st.column_config.TextColumn("Observação"),
    }
    st.session_state.pending_df = st.data_editor(st.session_state.df, key="editor", num_rows="dynamic",
                                                 column_config=cfg, hide_index=True, use_container_width=True)
    c1, c2, c3, _ = st.columns([1.2, 1.4, 1.4, 3])
    c1.button("Salvar alterações", type="primary", on_click=cb_save_table, use_container_width=True)
    c2.download_button("Baixar CSV", st.session_state.df.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"),
                       file_name="quantum_roi_portfolio.csv", mime="text/csv", use_container_width=True)
    c3.button("Restaurar originais", on_click=cb_reset_portfolio, use_container_width=True)
    if st.session_state.save_msg:
        kind, msgs = st.session_state.save_msg
        getattr(st, kind)("\n\n".join(msgs))
        if kind != "error":
            st.session_state.save_msg = None
    st.caption("O CSV exporta a versão salva (separador ponto e vírgula, decimal vírgula). Edições não salvas não entram no "
               "cálculo nem no arquivo. Validação: valores numéricos finitos e não negativos, equipe ≥ 1, adoção e volatilidade "
               "entre 0 e 100, implantação entre 0 e 24 meses, nome obrigatório.")

else:
    st.markdown("### Metodologia")
    c1, c2 = st.columns(2)
    with c1:
        sec("Benefício mensal")
        st.markdown("Benefício(t) = [Equipe × Horas × Custo-hora + Economia direta] × Adoção-alvo × a(t) − OPEX")
        st.markdown("- **a(t)** é a curva de adoção: zero durante a implantação; o benefício começa no mês seguinte, em curva logística (ponto médio no 3º mês após a implantação, inclinação 0,85) ou adoção-alvo imediata, quando a curva S está desativada.\n"
                    "- O CAPEX é lançado como fluxo negativo no mês zero; o OPEX começa no mês 1, inclusive durante a implantação.\n"
                    "- Horas liberadas representam **capacidade valorizada**, não caixa garantido.")
        sec("Monte Carlo")
        st.markdown(f"- {N_SIM:,} cenários independentes com semente reprodutível.\n".replace(",", ".") +
                    "- Cada cenário sorteia um fator técnico persistente: benefício lognormal (média 1, CV = volatilidade), custos com CV de cerca da metade, adoção ±0,3 × volatilidade atrelada ao mesmo fator; cenários técnicos ruins podem atrasar a implantação.\n"
                    "- P5–P95 é o intervalo que contém 90% dos cenários, não um intervalo de confiança da média.\n"
                    "- Fluxos descontados mensalmente pela taxa anual equivalente.\n"
                    "- Resultados: VPL médio, mediana, P5, P95 e probabilidade de VPL positivo.")
    with c2:
        sec("Indicadores determinísticos")
        st.markdown("- **TIR**: taxa anual equivalente que zera o VPL do fluxo determinístico.\n"
                    "- **Payback descontado**: primeiro mês em que o acumulado descontado fica ≥ 0.\n"
                    "- **ROI**: benefício líquido descontado dividido pelo custo total descontado.")
        sec("Semáforo financeiro")
        st.markdown("- **Verde**: P(VPL > 0) ≥ 80%\n- **Âmbar**: 50% ≤ P < 80%\n- **Rubi**: P < 50%")
        sec("Sensibilidade e otimização")
        st.markdown("- Tornado: cada premissa a ±20%, limitada a valores válidos; VPL absoluto em cada extremo.\n"
                    "- Otimização: estratégias hipotéticas (treinamento, negociação de custos, MVP, combinada) "
                    "re-simuladas com o mesmo motor. Exigem validação das premissas.")
    capacity_note()
