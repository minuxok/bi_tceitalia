"""Esecuzione della query validata su SQLite in sola lettura, con timeout."""
from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass

from .config import settings


class QueryTimeout(RuntimeError):
    pass


class QueryErrore(RuntimeError):
    pass


@dataclass
class Risultato:
    colonne: list[str]
    righe: list[list]
    n_righe: int
    troncato: bool
    durata_ms: int


def _connessione_ro() -> sqlite3.Connection:
    con = sqlite3.connect(f"file:{settings.db_path}?mode=ro", uri=True)
    con.execute("PRAGMA query_only = ON")
    con.execute("PRAGMA trusted_schema = OFF")
    return con


def esegui(sql: str) -> Risultato:
    con = _connessione_ro()
    deadline = time.monotonic() + settings.sql_timeout_s
    scattato = {"timeout": False}

    def _guard() -> int:
        if time.monotonic() > deadline:
            scattato["timeout"] = True
            return 1  # != 0 => SQLite interrompe la query
        return 0

    con.set_progress_handler(_guard, 5000)

    t0 = time.perf_counter()
    try:
        cur = con.execute(sql)
        colonne = [d[0] for d in cur.description] if cur.description else []
        righe = cur.fetchmany(settings.sql_row_limit + 1)
    except sqlite3.OperationalError as e:
        if scattato["timeout"]:
            raise QueryTimeout(
                f"Query interrotta dopo {settings.sql_timeout_s}s."
            ) from e
        raise QueryErrore(str(e)) from e
    except sqlite3.Error as e:
        raise QueryErrore(str(e)) from e
    finally:
        con.close()

    durata_ms = int((time.perf_counter() - t0) * 1000)
    troncato = len(righe) > settings.sql_row_limit
    if troncato:
        righe = righe[: settings.sql_row_limit]

    return Risultato(
        colonne=colonne,
        righe=[list(r) for r in righe],
        n_righe=len(righe),
        troncato=troncato,
        durata_ms=durata_ms,
    )
