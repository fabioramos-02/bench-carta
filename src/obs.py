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
import sys
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


def _human_bytes(n: int) -> str:
    """Tamanho legível: 230 B, 6.8 MB, ..."""
    size = float(n)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"


# Conjuntos de ícone: emoji (terminais utf-8) ou ASCII (consoles cp1252, ex.: Windows).
_ICONS_UNI = {"ok": "✅", "err": "❌", "warn": "⚠️", "info": "ℹ️", "alert": "⚠"}
_ICONS_ASCII = {"ok": "[OK]", "err": "[ERRO]", "warn": "[!]", "info": "[i]", "alert": "!"}


class ConsoleFormatter(logging.Formatter):
    """Linha humana p/ terminal: ícone + fonte + método + métricas. JSON fica no arquivo."""

    def __init__(self, ascii_only: bool = False) -> None:
        super().__init__()
        self._ic = _ICONS_ASCII if ascii_only else _ICONS_UNI

    def format(self, record: logging.LogRecord) -> str:
        ic = self._ic
        f = getattr(record, "fields", None) or {}
        ts = time.strftime("%H:%M:%S", time.localtime(record.created))
        if "ok" in f:
            icon = ic["ok"] if f["ok"] else ic["err"]
        else:
            icon = {logging.ERROR: ic["err"], logging.WARNING: ic["warn"]}.get(
                record.levelno, ic["info"]
            )
        head = f"{f.get('source', '')} · {f.get('method', '')}".strip(" ·") or record.getMessage()
        parts = [f"{ts}  {icon} {head}"]
        if "duration_ms" in f:
            parts.append(f"{f['duration_ms']:.0f}ms")
        if "status" in f:
            parts.append(str(f["status"]))
        if "n_items" in f:
            parts.append(f"{f['n_items']} itens")
        if "n_bytes" in f:
            parts.append(_human_bytes(int(f["n_bytes"])))
        if f.get("error"):
            parts.append(f"{ic['alert']} {f['error']}")
        line = "  ·  ".join(parts)
        if record.exc_info:
            line += "\n" + self.formatException(record.exc_info)
        return line


def setup_logging() -> logging.Logger:
    """Configura (uma vez) o logger `bench.api`. Idempotente."""
    global _configured
    logger = logging.getLogger(LOGGER_NAME)
    if _configured:
        return logger

    logger.setLevel(logging.INFO)
    logger.propagate = False

    # Tenta utf-8 no console (p/ emoji); cai p/ ícones ASCII se o terminal não suportar.
    stderr = sys.stderr
    ascii_only = True
    try:
        stderr.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        ascii_only = False
    except Exception:  # noqa: BLE001 — stream sem reconfigure (ex.: redirecionado)
        ascii_only = "utf" not in (getattr(stderr, "encoding", "") or "").lower()
    stream = logging.StreamHandler(stderr)
    stream.setFormatter(ConsoleFormatter(ascii_only=ascii_only))  # console: linha humana
    logger.addHandler(stream)

    try:
        _LOG_DIR.mkdir(exist_ok=True)
        file_handler = RotatingFileHandler(
            _LOG_FILE, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
        )
        file_handler.setFormatter(JsonFormatter())  # arquivo: JSON-lines p/ análise
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
