"""Observabilidade: logging estruturado das chamadas às APIs (Matomo / GA4).

Responsabilidade única: configurar logging e emitir 1 registro JSON por chamada
de API, com status, duração, volume e erro. Facilita identificar falhas e
medir latência sem depender de prints soltos.

Formato: JSON-lines (um objeto por linha) em `logs/api.log` (rotativo) + stderr.
Logger dedicado `bench.api` (propagate=False) para não poluir o root logger.
"""
from __future__ import annotations

import json
import logging
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

LOGGER_NAME = "bench.api"
_LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
_LOG_FILE = _LOG_DIR / "api.log"
_configured = False


class JsonFormatter(logging.Formatter):
    """Serializa cada registro como uma linha JSON, incluindo campos extras."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(record.created)),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        fields = getattr(record, "fields", None)
        if isinstance(fields, dict):
            payload.update(fields)
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def setup_logging() -> logging.Logger:
    """Configura (uma vez) o logger `bench.api`. Idempotente."""
    global _configured
    logger = logging.getLogger(LOGGER_NAME)
    if _configured:
        return logger

    logger.setLevel(logging.INFO)
    logger.propagate = False
    fmt = JsonFormatter()

    stream = logging.StreamHandler()
    stream.setFormatter(fmt)
    logger.addHandler(stream)

    try:
        _LOG_DIR.mkdir(exist_ok=True)
        file_handler = RotatingFileHandler(
            _LOG_FILE, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
        )
        file_handler.setFormatter(fmt)
        logger.addHandler(file_handler)
    except OSError:  # ambiente read-only (ex.: alguns hosts) → segue só com stderr
        logger.warning("Sem arquivo de log; usando apenas stderr.")

    _configured = True
    return logger


def log_api_call(
    source: str,
    method: str,
    *,
    ok: bool,
    duration_ms: float,
    status: int | None = None,
    error: str | None = None,
    **extra: Any,
) -> None:
    """Emite um registro estruturado de uma chamada de API.

    Args:
        source: "matomo" ou "ga4".
        method: nome do método/endpoint chamado.
        ok: True se a chamada teve sucesso.
        duration_ms: latência em milissegundos.
        status: código HTTP (quando aplicável).
        error: descrição do erro (tipo: mensagem), quando ok=False.
        **extra: campos adicionais (n_items, n_rows, n_bytes, dimensions, ...).
    """
    logger = setup_logging()
    fields: dict[str, Any] = {
        "source": source,
        "method": method,
        "ok": ok,
        "duration_ms": round(duration_ms, 1),
    }
    if status is not None:
        fields["status"] = status
    if error:
        fields["error"] = error
    fields.update(extra)

    level = logging.INFO if ok else logging.ERROR
    logger.log(level, "api_call", extra={"fields": fields})


class timed:
    """Cronômetro de contexto: `with timed() as t: ...; t.ms`."""

    def __enter__(self) -> "timed":
        self._start = time.perf_counter()
        self.ms = 0.0
        return self

    def __exit__(self, *exc: object) -> None:
        self.ms = (time.perf_counter() - self._start) * 1000.0
