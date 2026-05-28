"""Fase 1 reprodutível — descobre COMO o filtro de Perfil é rastreável.

Responsabilidade única: provar, ao vivo, qual método de medição é viável,
classificando entre os 3 níveis do plano:
  1. Event tracking (clique de aba dispara matomo.php com e_c/e_a/e_n)
  2. Navegação para busca (clique navega para buscar?q=<Perfil>)
  3. Transições por serviço (serviços têm URL própria rastreável)

Uso:
    python -m src.discovery.probe_instrumentation

Requer: playwright instalado (`pip install playwright && playwright install chromium`).
Equivale ao que foi executado manualmente em 28/05/2026 (ver docs/estudo-*.md).
"""
from __future__ import annotations

import json
import unicodedata

from playwright.sync_api import sync_playwright

from src.config import PORTAL_HOME_URL

TABS = ["CIDADAO", "SERVIDOR PUBLICO", "EMPRESA", "GESTAO PUBLICA"]
_MATOMO = "matomo.php"


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFD", text or "")
    return "".join(c for c in text if not unicodedata.combining(c)).upper().strip()


def probe() -> dict:
    """Roda a sonda e devolve o veredito do método aplicável."""
    events: list[str] = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.on("request", lambda r: events.append(r.url) if _MATOMO in r.url else None)

        page.goto(PORTAL_HOME_URL, wait_until="networkidle")
        before_events = len(events)
        url_before = page.url

        # clicar a aba "Servidor Público" e observar efeitos colaterais
        page.get_by_role("heading", name="Servidor Público").first.click()
        page.wait_for_timeout(800)
        services = _collect_service_links(page)
        url_after = page.url
        new_events = len(events) - before_events

        browser.close()

    verdict = {
        "matomo_present": bool(events),
        "tab_click_fired_event": new_events > 0,
        "tab_click_changed_url": url_before != url_after,
        "service_links_sample": services[:8],
        "method": _classify(new_events > 0, url_before != url_after, services),
    }
    return verdict


def _collect_service_links(page) -> list[str]:
    return page.eval_on_selector_all(
        "a[href]",
        "els => els.map(e => e.getAttribute('href'))"
        ".filter(h => h && h.includes('/') && !h.startsWith('#') && h.length > 8)",
    )


def _classify(event_fired: bool, url_changed: bool, services: list[str]) -> str:
    if event_fired:
        return "1-event-tracking"
    if url_changed and any("buscar" in (s or "") for s in services):
        return "2-site-search"
    if any("/" in (s or "")[1:] for s in services):
        return "3-transitions-por-servico"
    return "0-nao-mensuravel"


if __name__ == "__main__":
    print(json.dumps(probe(), ensure_ascii=False, indent=2))
