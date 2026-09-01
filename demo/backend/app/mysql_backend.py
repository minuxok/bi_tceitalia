"""Esecuzione query su MySQL/MariaDB REALE, sola lettura, con timeout.

Usato dai verticali con engine = "mysql" (es. "gest" -> c2gest).

Garanzie di sicurezza (a strati):
  * l'utente DB ha solo GRANT SELECT (nessun DDL/DML possibile lato server);
  * ogni connessione apre una transazione READ ONLY;
  * MAX_STATEMENT_TIME (MariaDB) tronca le query troppo lunghe;
  * il validatore a monte accetta solo SELECT sulle viste ai_bi_* e forza il LIMIT;
  * le viste ai_bi_* sono iniettate come CTE (virtual_views.wrap_with_ctes).
"""
from __future__ import annotations

import time
from dataclasses import dataclass

import pymysql
from pymysql.constants import FIELD_TYPE

from .config import settings

# riusa le eccezioni del runner sqlite: main.py cattura quelle
from .runner import QueryErrore, QueryTimeout, Risultato


# tipo colonna (codice pymysql) -> etichetta per il prompt
_INT = {FIELD_TYPE.TINY, FIELD_TYPE.SHORT, FIELD_TYPE.LONG, FIELD_TYPE.LONGLONG,
        FIELD_TYPE.INT24, FIELD_TYPE.YEAR}
_REAL = {FIELD_TYPE.DECIMAL, FIELD_TYPE.NEWDECIMAL, FIELD_TYPE.FLOAT, FIELD_TYPE.DOUBLE}
_DATE = {FIELD_TYPE.DATE, FIELD_TYPE.DATETIME, FIELD_TYPE.TIMESTAMP, FIELD_TYPE.NEWDATE}


def _tipo_sql(codice: int) -> str:
    if codice in _INT:
        return "INTEGER"
    if codice in _REAL:
        return "REAL"
    if codice in _DATE:
        return "DATE"
    return "TEXT"


def _connect() -> pymysql.connections.Connection:
    if not settings.mysql_ready:
        raise QueryErrore(
            "Connessione MySQL non configurata: mancano DB_HOST / DB_NAME / DB_USER nel .env"
        )
    con = pymysql.connect(
        host=settings.mysql_host,
        port=settings.mysql_port,
        user=settings.mysql_user,
        password=settings.mysql_password,
        database=settings.mysql_name,
        connect_timeout=8,
        read_timeout=settings.sql_timeout_s + 5,
        autocommit=True,
        charset="utf8mb4",
    )
    with con.cursor() as cur:
        # difesa in profondità: niente scritture su questa sessione
        try:
            cur.execute("SET SESSION TRANSACTION READ ONLY")
        except pymysql.Error:
            pass
        # MariaDB: tetto di tempo per statement (secondi, può essere frazionario)
        try:
            cur.execute("SET SESSION max_statement_time = %s", (settings.sql_timeout_s,))
        except pymysql.Error:
            pass
    return con


def esegui_mysql(sql: str) -> Risultato:
    """Esegue una SELECT già validata e con le CTE ai_bi_* iniettate."""
    t0 = time.perf_counter()
    try:
        con = _connect()
    except pymysql.Error as e:
        raise QueryErrore(f"Connessione al database non riuscita: {e}") from e

    try:
        with con.cursor() as cur:
            try:
                cur.execute(sql)
            except pymysql.err.OperationalError as e:
                # 1969 = query execution interrotta per max_statement_time (MariaDB)
                if e.args and e.args[0] in (1969, 3024):
                    raise QueryTimeout(
                        f"Query interrotta dopo {settings.sql_timeout_s}s."
                    ) from e
                raise QueryErrore(str(e.args[1] if len(e.args) > 1 else e)) from e
            except pymysql.Error as e:
                raise QueryErrore(str(e.args[1] if len(e.args) > 1 else e)) from e

            colonne = [d[0] for d in cur.description] if cur.description else []
            righe = cur.fetchmany(settings.sql_row_limit + 1)
    finally:
        con.close()

    troncato = len(righe) > settings.sql_row_limit
    if troncato:
        righe = righe[: settings.sql_row_limit]

    return Risultato(
        colonne=colonne,
        righe=[list(r) for r in righe],
        n_righe=len(righe),
        troncato=troncato,
        durata_ms=int((time.perf_counter() - t0) * 1000),
    )


def introspect_views() -> dict[str, list[tuple[str, str]]]:
    """{nome_vista: [(colonna, tipo), ...]} ottenuto eseguendo ogni corpo vista
    con LIMIT 0 e leggendo cursor.description. Sempre allineato ai dati reali."""
    from .virtual_views import load_view_defs

    con = _connect()
    out: dict[str, list[tuple[str, str]]] = {}
    try:
        with con.cursor() as cur:
            for nome, corpo in load_view_defs():
                cur.execute(f"SELECT * FROM (\n{corpo}\n) _v LIMIT 0")
                out[nome] = [(d[0], _tipo_sql(d[1])) for d in cur.description]
    finally:
        con.close()
    return out


def data_riferimento() -> str:
    """Valore di ai_bi_meta.data_riferimento (ultima data presente nei dati)."""
    from .virtual_views import load_view_defs

    corpo = dict(load_view_defs()).get("ai_bi_meta")
    if not corpo:
        return ""
    con = _connect()
    try:
        with con.cursor() as cur:
            cur.execute(f"SELECT data_riferimento FROM (\n{corpo}\n) _m")
            row = cur.fetchone()
            return str(row[0]) if row and row[0] is not None else ""
    finally:
        con.close()
