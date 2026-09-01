"""Validazione della query generata dall'LLM prima dell'esecuzione.

Regole (tutte obbligatorie):
  * un solo statement;
  * deve essere una SELECT (eventualmente con CTE WITH), niente DDL/DML/PRAGMA/ATTACH;
  * ogni tabella referenziata deve iniziare per 'ai_bi_' (le CTE locali sono ammesse);
  * niente funzioni pericolose (load_extension, readfile, writefile, ...);
  * LIMIT forzato: se assente o superiore al massimo, viene riscritto.
"""
from __future__ import annotations

import re

import sqlglot
from sqlglot import exp

from .config import settings


class QueryRifiutata(ValueError):
    """La query non supera i controlli di sicurezza."""


FUNZIONI_VIETATE = {
    # sqlite
    "load_extension", "readfile", "writefile", "fileio", "edit",
    "fts3_tokenizer", "zipfile", "sqlite_compileoption_used",
    # mysql / mariadb
    "load_file", "benchmark", "sleep", "get_lock", "release_lock",
    "master_pos_wait", "sys_eval", "sys_exec", "lines_terminated_by",
}

STATEMENT_VIETATI = (
    exp.Insert, exp.Update, exp.Delete, exp.Create, exp.Drop, exp.Alter,
    exp.Command, exp.Pragma, exp.Set, exp.Merge, exp.TruncateTable,
)


def _is_select_like(tree: exp.Expression) -> bool:
    if isinstance(tree, (exp.Select, exp.Union, exp.Intersect, exp.Except)):
        return True
    if isinstance(tree, exp.Subquery):
        return _is_select_like(tree.this)
    return False


def valida_e_normalizza(sql: str) -> str:
    sql = (sql or "").strip().rstrip(";").strip()
    if not sql:
        raise QueryRifiutata("Query vuota.")

    try:
        statements = sqlglot.parse(sql, read=settings.sql_dialect)
    except Exception as e:  # noqa: BLE001
        raise QueryRifiutata(f"SQL non interpretabile: {e}") from e

    statements = [s for s in statements if s is not None]
    if len(statements) != 1:
        raise QueryRifiutata("È ammesso un solo statement SQL.")

    tree = statements[0]

    for vietato in STATEMENT_VIETATI:
        if isinstance(tree, vietato) or list(tree.find_all(vietato)):
            raise QueryRifiutata("Sono ammesse solo query di lettura (SELECT).")

    if not _is_select_like(tree):
        raise QueryRifiutata("La query deve essere una SELECT.")

    # nomi delle CTE definite nella query stessa (ammessi come "tabelle")
    cte_names = {c.alias_or_name.lower() for c in tree.find_all(exp.CTE)}

    for tbl in tree.find_all(exp.Table):
        nome = (tbl.name or "").lower()
        if nome in cte_names:
            continue
        if not nome.startswith("ai_bi_"):
            raise QueryRifiutata(
                f"Tabella non ammessa: '{tbl.name}'. Sono interrogabili solo le viste ai_bi_*."
            )

    for fn in tree.find_all(exp.Anonymous):
        if (fn.name or "").lower() in FUNZIONI_VIETATE:
            raise QueryRifiutata(f"Funzione non ammessa: {fn.name}")

    # doppio controllo testuale su parole chiave pericolose (paranoia)
    if re.search(r"\b(attach|detach|vacuum|reindex)\b", sql, re.IGNORECASE):
        raise QueryRifiutata("Parola chiave non ammessa nella query.")
    # mysql/mariadb: esfiltrazione su file e lock di sessione
    if re.search(r"\b(into\s+(out|dump)file|load\s+data|load_file)\b", sql, re.IGNORECASE):
        raise QueryRifiutata("Parola chiave non ammessa nella query.")

    return _forza_limit(tree)


def _forza_limit(tree: exp.Expression) -> str:
    limite = settings.sql_row_limit
    target = tree.this if isinstance(tree, exp.Subquery) else tree

    if isinstance(target, exp.Select):
        cur = target.args.get("limit")
        val = None
        if cur is not None:
            try:
                val = int(cur.expression.this)
            except (AttributeError, TypeError, ValueError):
                val = None
        if val is None or val > limite:
            target.set("limit", exp.Limit(expression=exp.Literal.number(limite)))
        return tree.sql(dialect=settings.sql_dialect)

    # UNION/INTERSECT/EXCEPT: avvolgo in una SELECT esterna con LIMIT
    wrapped = exp.select("*").from_(tree.subquery(alias="q")).limit(limite)
    return wrapped.sql(dialect=settings.sql_dialect)
