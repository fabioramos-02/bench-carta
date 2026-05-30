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
    from src.ga4.queries import build_category_filter, clicks_metrics, screens_metrics

    ga_start, ga_end = start, end
    ga = get_ga4_client()
    telas = screens_metrics(ga, ga_start, ga_end)
    cliques = clicks_metrics(ga, ga_start, ga_end)

    # Passo 1: montar serviços + rótulos GA4 por categoria (sem chamar a API).
    pendentes: list[dict] = []
    for cat, dados in CATALOGO.items():
        cat_key = _norm(dados.get("ga4") or cat)
        servicos: list[dict] = []
        n_nat = n_red = 0
        native_labels: list[str] = [dados["ga4"]] if dados.get("ga4") else []
        redirect_labels: list[str] = []
        for s in dados["servicos"]:
            rotulo = _norm(s.get("ga4") or s["nome"])
            label = s.get("ga4") or s["nome"]
            if s["tipo"] == "nativo":
                n_nat += 1
                native_labels.append(label)
                m = telas.get(rotulo, {})
                servicos.append({
                    "nome": s["nome"], "tipo": "nativo", "url": s["url"],
                    "pessoas": m.get("pessoas", 0),
                    "valor": m.get("acessos", 0), "valor_label": "acessos",
                })
            else:
                n_red += 1
                redirect_labels.append(label)
                m = cliques.get(rotulo, {})
                servicos.append({
                    "nome": s["nome"], "tipo": "redirect", "url": s["url"],
                    "pessoas": m.get("pessoas", 0),
                    "valor": m.get("cliques", 0), "valor_label": "cliques",
                })
        servicos.sort(key=lambda x: x["pessoas"], reverse=True)
        pendentes.append({
            "cat": cat, "dados": dados, "cat_key": cat_key, "servicos": servicos,
            "n_nat": n_nat, "n_red": n_red,
            "filtro": build_category_filter(native_labels, redirect_labels),
        })

    # Passo 2: UNIÃO de únicos por categoria em LOTE (batchRunReports, 5/lote) —
    # troca ~20 round-trips sequenciais por ~4 lotes.
    specs = [{"metrics": ["activeUsers"], "dimension_filter": p["filtro"]}
             for p in pendentes if p["filtro"] is not None]
    batch = ga.run_reports_batch(specs, ga_start, ga_end) if specs else []
    unioes: dict[int, int] = {}
    bi = 0
    for idx, p in enumerate(pendentes):
        if p["filtro"] is None:
            continue
        rows = batch[bi]; bi += 1
        unioes[idx] = sum(int(r.get("activeUsers", 0) or 0) for r in rows)

    # Passo 3: finalizar quantitativo (união → senão cascata tela/clique/maior).
    categorias: list[dict] = []
    for idx, p in enumerate(pendentes):
        servicos, cat_key = p["servicos"], p["cat_key"]
        tela_cat = telas.get(cat_key, {})
        uniao = unioes.get(idx, 0)
        if uniao:
            pessoas, acessos, fonte = uniao, sum(s["valor"] for s in servicos), "uniao"
        elif tela_cat.get("pessoas", 0):
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
            "categoria": p["cat"],
            "icon": p["dados"]["icon"],
            "pessoas": pessoas,
            "acessos": acessos,
            "pessoas_fonte": fonte,
            "n_nativo": p["n_nat"],
            "n_redirect": p["n_red"],
            "servicos": servicos,
        })

    categorias.sort(key=lambda c: c["pessoas"], reverse=True)
    return {"categorias": categorias, "totais": contagem(), "periodo": f"{start}..{end}"}
