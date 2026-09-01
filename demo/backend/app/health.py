"""Endpoint /healthz — AEGIS Standard Contract.

Implementa lo schema descritto in `../AEGIS/PIANO_OPERATIVO_AEGIS.md` §2 e
tipizzato in `AEGIS/shared/types/healthz.ts`:

    { service, version, status, timestamp, environment, checks }

  * status            : "healthy" | "degraded" | "unhealthy"
  * checks[*].status  : "ok" | "warn" | "error"

AEGIS Core legge `status` dal corpo JSON; noi lo rispecchiamo anche sul codice
HTTP (unhealthy -> 503) così che pure un check "solo status code" — l'HEALTHCHECK
Docker o il worker HTTP di AEGIS — veda il problema. Un blip di rete verso il DB
non fa flappare il container: l'HEALTHCHECK ha --retries=3 e AEGIS ritenta con
backoff prima di aprire un incidente.

La sonda del DB è volutamente NON cachata (a differenza di
`semantic.get_data_riferimento`, che dopo il primo giro risponde da lru_cache e
non toccherebbe più il datastore).
"""
from __future__ import annotations

import platform
import sqlite3
import time
from datetime import datetime, timezone

import fastapi

from .config import settings

# tenuto allineato a FastAPI(title=..., version=...) in main.py
SERVICE_VERSION = "0.1.0"


def _now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )


def _check_database() -> dict:
    """Probe leggero del datastore del verticale attivo: una `SELECT 1`."""
    t0 = time.perf_counter()
    try:
        if settings.db_engine == "mysql":
            import pymysql

            con = pymysql.connect(
                host=settings.mysql_host,
                port=settings.mysql_port,
                user=settings.mysql_user,
                password=settings.mysql_password,
                database=settings.mysql_name,
                connect_timeout=4,
                read_timeout=4,
            )
            try:
                with con.cursor() as cur:
                    cur.execute("SELECT 1")
                    cur.fetchone()
            finally:
                con.close()
        else:
            con = sqlite3.connect(f"file:{settings.db_path}?mode=ro", uri=True)
            try:
                con.execute("SELECT 1").fetchone()
            finally:
                con.close()
    except Exception as e:  # noqa: BLE001
        return {
            "status": "error",
            "latency_ms": int((time.perf_counter() - t0) * 1000),
            "message": f"{type(e).__name__}: {e}"[:200],
        }
    return {"status": "ok", "latency_ms": int((time.perf_counter() - t0) * 1000)}


def _check_llm_provider() -> dict:
    """Solo presenza della configurazione: nessuna chiamata reale all'API del
    provider (costo, latenza e rate-limit non hanno posto su un liveness check)."""
    if settings.llm_ready:
        return {"status": "ok", "message": f"configurato: {settings.llm_model}"}
    return {"status": "warn", "message": "GEMINI_API_KEY assente: /chiedi risponde 503"}


def build_healthz() -> tuple[dict, int]:
    """Ritorna (corpo JSON conforme allo schema §2, codice HTTP)."""
    checks = {
        "database": _check_database(),
        "llm_provider": _check_llm_provider(),
    }

    db_broken = checks["database"]["status"] == "error"
    # sqlite: DB è un file dentro l'immagine — se non si apre il container è
    #   davvero rotto, un restart può rimetterlo a posto -> unhealthy (503).
    # mysql: DB è un server ESTERNO (es. c2gest) — se è giù il restart non
    #   serve a niente e farebbe solo flappare il container -> degraded (200),
    #   il guasto resta visibile in checks.database.status = "error".
    if db_broken and settings.db_engine != "mysql":
        status = "unhealthy"
    elif any(c["status"] in ("warn", "error") for c in checks.values()):
        status = "degraded"           # risponde, ma con capacità ridotta
    else:
        status = "healthy"

    body = {
        "service": f"conversational-bi-{settings.vertical}",
        "version": SERVICE_VERSION,
        "status": status,
        "timestamp": _now_iso(),
        "environment": {
            "runtime": f"python@{platform.python_version()}",
            "framework": f"fastapi@{fastapi.__version__}",
        },
        "checks": checks,
    }
    return body, (503 if status == "unhealthy" else 200)
