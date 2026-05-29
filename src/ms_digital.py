"""Compute do explorador do app MS Digital: cruza o catálogo com o GA4.

Responsabilidade única: coordenar queries GA4 (telas + cliques) e casar com o
`CATALOGO`, devolvendo categorias com quantitativo de pessoas e seus serviços
(nativo → tela; redirect → clique). Sem I/O de arquivo nem UI.
"""
from __future__ import annotations

from src.ga4.queries import _norm
from src.ms_digital_catalog import CATALOGO, contagem


def compute_app(start: str, end: str) -> dict:
    """Retorna {"categorias": [...], "totais": {...}, "periodo": "start..end"}.

    `start`/`end` em YYYY-MM-DD (GA4 aceita qualquer intervalo: dia/mês/ano).
    Cada categoria: {categoria, icon, pessoas, acessos, n_nativo, n_redirect,
    servicos: [{nome, tipo, url, pessoas, valor, valor_label}]}.
    'valor' = acessos (nativo) ou cliques (redirect); 'valor_label' identifica.
    """
    from src.ga4.client import get_ga4_client
    from src.ga4.queries import clicks_metrics, screens_metrics

    ga_start, ga_end = start, end
    ga = get_ga4_client()
    telas = screens_metrics(ga, ga_start, ga_end)
    cliques = clicks_metrics(ga, ga_start, ga_end)

    categorias: list[dict] = []
    for cat, dados in CATALOGO.items():
        cat_key = _norm(dados.get("ga4") or cat)
        tela_cat = telas.get(cat_key, {})
        servicos: list[dict] = []
        n_nat = n_red = 0
        for s in dados["servicos"]:
            rotulo = _norm(s.get("ga4") or s["nome"])
            if s["tipo"] == "nativo":
                n_nat += 1
                m = telas.get(rotulo, {})
                servicos.append({
                    "nome": s["nome"], "tipo": "nativo", "url": s["url"],
                    "pessoas": m.get("pessoas", 0),
                    "valor": m.get("acessos", 0), "valor_label": "acessos",
                })
            else:
                n_red += 1
                m = cliques.get(rotulo, {})
                servicos.append({
                    "nome": s["nome"], "tipo": "redirect", "url": s["url"],
                    "pessoas": m.get("pessoas", 0),
                    "valor": m.get("cliques", 0), "valor_label": "cliques",
                })
        servicos.sort(key=lambda x: x["pessoas"], reverse=True)

        # Quantitativo da categoria em cascata: tela do app → senão clique
        # direto (categorias redirect-only: MS.gov, Diário Oficial, Nota MS
        # Premiada) → senão o maior serviço.
        if tela_cat.get("pessoas", 0):
            pessoas, acessos, fonte = tela_cat["pessoas"], tela_cat.get("acessos", 0), "tela"
        elif cliques.get(cat_key, {}).get("pessoas", 0):
            cc = cliques[cat_key]
            pessoas, acessos, fonte = cc["pessoas"], cc.get("cliques", 0), "clique"
        elif servicos:
            top = max(servicos, key=lambda x: x["pessoas"])
            pessoas, acessos, fonte = top["pessoas"], top["valor"], "servico"
        else:
            pessoas, acessos, fonte = 0, 0, "—"

        categorias.append({
            "categoria": cat,
            "icon": dados["icon"],
            "pessoas": pessoas,
            "acessos": acessos,
            "pessoas_fonte": fonte,
            "n_nativo": n_nat,
            "n_redirect": n_red,
            "servicos": servicos,
        })

    categorias.sort(key=lambda c: c["pessoas"], reverse=True)
    return {"categorias": categorias, "totais": contagem(), "periodo": f"{start}..{end}"}
