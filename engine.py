"""Motor vetorizado, sem persistência e sem rede. Valores monetários em BRL."""
from time import perf_counter
import numpy as np
import pandas as pd


def _validate(project, horizon, discount):
    for key in ("team", "hourly", "hours", "savings", "capex", "opex",
                "adoption", "volatility", "implementation"):
        value = float(project[key])
        if not np.isfinite(value) or value < 0:
            raise ValueError(f"Premissa inválida: {key}. Use números finitos não negativos.")
    if project["team"] < 1 or project["adoption"] > 100 or project["volatility"] > 100:
        raise ValueError("Equipe deve ser positiva e percentuais devem estar entre 0 e 100.")
    if not 1 <= int(horizon) <= 120 or not np.isfinite(discount) or discount < 0:
        raise ValueError("Horizonte deve estar entre 1 e 120 meses; taxa deve ser não negativa.")


def _curve(months, implementation, adoption, logistic):
    age = months - implementation
    ramp = 1 / (1 + np.exp(-0.85 * (age - 3))) if logistic else np.ones_like(age)
    return np.where(age > 0, adoption * ramp, 0.0)


def _irr(flows):
    """Raiz em log(1+r_mensal); válida para fluxo convencional (-, ..., +)."""
    if flows[0] >= 0 or not np.any(flows > 0):
        return None
    # Cash flow in this model is conventional: ramping benefits, fixed OPEX.
    periods = np.arange(len(flows))
    lo, hi = -5.0, 5.0
    def value(x):
        return float(np.sum(flows * np.exp(np.clip(-x * periods, -700, 700))))
    if np.sign(value(lo)) == np.sign(value(hi)):
        return None
    for _ in range(65):
        mid = (lo + hi) / 2
        if value(mid) > 0:
            lo = mid
        else:
            hi = mid
    return float(np.expm1(12 * ((lo + hi) / 2)) * 100)


def _payback(cumulative):
    crossed = np.flatnonzero(cumulative[1:] >= 0)
    if not len(crossed):
        return None
    month = int(crossed[0] + 1)
    # Require recovery to persist through the horizon.
    if np.any(cumulative[month:] < 0):
        return None
    prior = cumulative[month - 1]
    step = cumulative[month] - prior
    return float(month - 1 + (-prior / step if step > 0 else 1))


def deterministic(project, horizon=36, discount=12.0, logistic=True):
    _validate(project, horizon, discount)
    horizon = int(horizon)
    months = np.arange(1, horizon + 1)
    adoption = _curve(months, float(project["implementation"]),
                      float(project["adoption"]) / 100, logistic)
    potential = float(project["team"]) * float(project["hourly"]) * float(project["hours"]) + float(project["savings"])
    benefits = potential * adoption
    flows = np.r_[-float(project["capex"]), benefits - float(project["opex"])]
    factors = (1 + discount / 100) ** (-np.arange(horizon + 1) / 12)
    cumulative = np.cumsum(flows * factors)
    costs = float(project["capex"]) + float(project["opex"]) * factors[1:].sum()
    return dict(npv=float(cumulative[-1]), irr=_irr(flows),
                payback=_payback(cumulative), roi=float(cumulative[-1] / costs * 100) if costs else 0.0,
                flows=flows, cumulative=cumulative, adoption_curve=adoption)


def simulate(project, horizon=36, discount=12.0, seed=42, logistic=True, n=10000):
    start = perf_counter()
    base = deterministic(project, horizon, discount, logistic)
    if not 1 <= int(n) <= 100000:
        raise ValueError("Número de cenários inválido.")
    horizon, n = int(horizon), int(n)
    rng = np.random.default_rng(int(seed))
    vol = float(project["volatility"]) / 100
    # Persistent technical uncertainty, rather than independent monthly noise.
    # Lognormal benefit/cost factors have expectation exactly 1.
    sigma = np.sqrt(np.log1p(vol ** 2))
    technical = rng.standard_normal(n)
    cost_noise = rng.standard_normal(n)
    benefit_factor = np.exp(sigma * technical - sigma ** 2 / 2)
    cost_factor = np.exp(sigma * 0.5 * cost_noise - (sigma * 0.5) ** 2 / 2)
    adoption = np.clip(float(project["adoption"]) / 100 + vol * 0.30 * technical, 0, 1)
    # Nonnegative technical delays: zero volatility recovers deterministic result.
    delay = np.rint(np.maximum(0, -technical * vol * 4))
    live = float(project["implementation"]) + delay
    months = np.arange(1, horizon + 1)
    curves = _curve(months[None, :], live[:, None], adoption[:, None], logistic)
    potential = float(project["team"]) * float(project["hourly"]) * float(project["hours"]) + float(project["savings"])
    benefits = potential * curves * benefit_factor[:, None]
    cashflows = np.empty((n, horizon + 1))
    cashflows[:, 0] = -float(project["capex"]) * cost_factor
    cashflows[:, 1:] = benefits - float(project["opex"]) * cost_factor[:, None]
    factors = (1 + discount / 100) ** (-np.arange(horizon + 1) / 12)
    cumulative = np.cumsum(cashflows * factors, axis=1)
    npvs = cumulative[:, -1]
    costs = cost_factor * (float(project["capex"]) + float(project["opex"]) * factors[1:].sum())
    mean_cost = float(costs.mean())
    p5, p95 = np.percentile(npvs, [5, 95])
    return dict(npvs=npvs, cumulative=cumulative, months=np.arange(horizon + 1),
                adoption_curve=base["adoption_curve"], cashflows=cashflows,
                mean_npv=float(npvs.mean()), median_npv=float(np.median(npvs)),
                p5=float(p5), p95=float(p95), probability=float(np.mean(npvs > 0)),
                roi=float(npvs.mean() / mean_cost * 100) if mean_cost else 0.0,
                irr=base["irr"], payback=base["payback"],
                elapsed_ms=(perf_counter() - start) * 1000)


def sensitivity(project, horizon=36, discount=12.0, logistic=True):
    labels = {"hours": "Horas economizadas", "adoption": "Adoção da equipe",
              "hourly": "Custo hora", "savings": "Redução de retrabalho",
              "capex": "Investimento inicial", "opex": "Custo mensal",
              "implementation": "Tempo de implantação"}
    rows = []
    for key, label in labels.items():
        values = []
        for factor in (0.8, 1.2):
            changed = dict(project)
            changed[key] = float(project[key]) * factor
            if key == "adoption":
                changed[key] = min(100, changed[key])
            values.append(deterministic(changed, horizon, discount, logistic)["npv"])
        rows.append(dict(variable=label, low=values[0], high=values[1],
                         impact=abs(values[1] - values[0])))
    return pd.DataFrame(rows).sort_values("impact", ascending=True).reset_index(drop=True)


def optimize(project, horizon=36, discount=12.0, logistic=True):
    training = dict(project, adoption=min(100, int(project["adoption"]) + 10),
                    volatility=max(0, int(project["volatility"]) - 5),
                    capex=float(project["capex"]) + 15000)
    negotiated = dict(project, opex=round(float(project["opex"]) * 0.85))
    mvp = dict(project, team=max(1, round(float(project["team"]) * 0.60)),
               savings=round(float(project["savings"]) * 0.60),
               capex=round(float(project["capex"]) * 0.55),
               opex=round(float(project["opex"]) * 0.65),
               implementation=max(0, int(project["implementation"]) - 1))
    combined = dict(training, opex=negotiated["opex"])
    variants = [
        ("Cenário atual", "Premissas atuais, sem intervenção.", dict(project)),
        ("Capacitação", "Treinamento: +R$ 15 mil de CAPEX, +10 p.p. de adoção e −5 p.p. de volatilidade.", training),
        ("Negociação de custos", "Hipótese de redução de 15% no OPEX; depende de negociação real.", negotiated),
        ("MVP faseado", "60% do escopo e benefícios; 55% do CAPEX, 65% do OPEX e implantação um mês menor. Não inclui expansão futura.", mvp),
        ("Capacitação + negociação", "Combina o investimento em capacitação com a hipótese de redução do OPEX.", combined),
    ]
    return [dict(name=name, description=description, project=p,
                 result=simulate(p, horizon, discount, seed=42, logistic=logistic))
            for name, description, p in variants]


def portfolio_summary(df, horizon=36, discount=12.0, seed=42, logistic=True):
    rows = []
    for project in df.to_dict("records"):
        result = simulate(project, horizon, discount, seed, logistic)
        rows.append({**{k: project[k] for k in ("id", "name", "area", "capex")},
                     **{k: result[k] for k in ("mean_npv", "probability", "irr", "payback", "roi")}})
    return pd.DataFrame(rows)
