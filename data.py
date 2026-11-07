"""Premissas de demonstração; nenhum dado é armazenado fora da sessão."""
import pandas as pd


def initial_projects():
    columns = [
        "id", "name", "area", "team", "hourly", "hours", "savings",
        "capex", "opex", "adoption", "volatility", "implementation", "note",
    ]
    rows = [
        (1, "Automação de Triagem Jurídica & Legislativa com IA",
         "Jurídico & Governança", 28, 115, 22, 18000, 145000, 9500, 82, 18, 3, ""),
        (2, "Agente Inteligente de Atendimento & Ouvidoria 24/7",
         "Atendimento & Operações", 45, 58, 26, 14000, 110000, 11200, 88, 15, 2, ""),
        (3, "Auditoria Preditiva de Contratos, Compras & Compliance",
         "Financeiro & Suprimentos", 16, 135, 18, 32000, 190000, 12500, 76, 22, 4, ""),
        (4, "Arquitetura Digital de T&D e Onboarding Acelerado",
         "RH & Educação Corporativa", 60, 78, 12, 16500, 85000, 5800, 90, 12, 2, ""),
        (5, "Copiloto de Análise de Dados & Relatórios Executivos",
         "Controladoria & Estratégia", 18, 125, 20, 11000, 98000, 7200, 80, 20, 3,
         "Volatilidade de 20% e implantação de 3 meses são premissas ilustrativas: o arquivo original termina antes desses valores."),
        (6, "Automação Inteligente de Processos Financeiros",
         "Financeiro & Operações", 24, 85, 18, 12500, 120000, 8500, 78, 20, 3,
         "Projeto inteiramente ilustrativo: o sexto projeto não constava no arquivo recebido."),
    ]
    df = pd.DataFrame(rows, columns=columns)
    for key in ("hourly", "hours", "savings", "capex", "opex"):
        df[key] = df[key].astype(float)
    return df
