"""Carica il layer semantico (viste + glossario + few-shot) per il prompt."""
import sqlite3
from functools import lru_cache

import yaml

from .config import settings

# Descrizione curata di ogni vista. Le COLONNE sono lette a runtime dal DB
# (sempre allineate), qui sta solo il "a cosa serve".
VIEW_DESCRIPTIONS: dict[str, str] = {
    "ai_bi_vendite":  "Una riga per riga d'ordine. Base per fatturato, margine e quantita' "
                      "per cliente, prodotto, categoria, agente, area, regione e tempo "
                      "(anno, mese, anno_mese). Esclude ordini in bozza e annullati.",
    "ai_bi_ordini":   "Una riga per ordine (testata) con totale_netto, totale_ivato, n_righe "
                      "e stato_ordine normalizzato. Per numero di ordini e valore medio ordine.",
    "ai_bi_clienti":  "Una riga per cliente con primo_ordine, ultimo_ordine, fatturato_12m, "
                      "num_ordini_12m e flag attivo (1 = ordine negli ultimi 6 mesi).",
    "ai_bi_scaduto":  "Una riga per scadenza NON incassata e gia' scaduta. Ha importo, "
                      "giorni_ritardo e fascia_ritardo ('0-30','31-60','61-90','oltre 90').",
    "ai_bi_prodotti": "Una riga per prodotto con quantita_12m, fatturato_12m, num_ordini_12m, "
                      "ultima_vendita e stato_prodotto. quantita_12m = 0 -> prodotto fermo.",
    "ai_bi_agenti":   "Una riga per agente con num_clienti, fatturato_12m e fatturato_ytd.",
}


_TYPEOF_SQL = {
    "integer": "INTEGER",
    "real": "REAL",
    "text": "TEXT",
    "numeric": "NUMERIC",
    "blob": "BLOB",
}


@lru_cache(maxsize=1)
def get_views_schema() -> dict[str, list[tuple[str, str]]]:
    """{nome_vista: [(colonna, tipo), ...]} letto dal DB demo.

    Le colonne calcolate di una vista spesso non hanno un tipo dichiarato in
    PRAGMA table_info: in quel caso lo deduciamo dai dati con typeof(), così
    il prompt non etichetta come TEXT colonne che sono INTEGER/REAL
    (es. `attivo` 0/1) inducendo il modello a confronti sbagliati (attivo = '1').
    """
    con = sqlite3.connect(f"file:{settings.db_path}?mode=ro", uri=True)
    try:
        views = [r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='view' AND name LIKE 'ai_bi_%' ORDER BY name"
        )]
        out: dict[str, list[tuple[str, str]]] = {}
        for v in views:
            cols = con.execute(f"PRAGMA table_info('{v}')").fetchall()
            tipi: list[tuple[str, str]] = []
            for c in cols:
                nome = c[1]
                dichiarato = (c[2] or "").upper()
                if dichiarato:
                    tipi.append((nome, dichiarato))
                    continue
                riga = con.execute(
                    f'SELECT typeof("{nome}") FROM "{v}" '
                    f'WHERE "{nome}" IS NOT NULL LIMIT 1'
                ).fetchone()
                tipi.append((nome, _TYPEOF_SQL.get(riga[0] if riga else "", "TEXT")))
            out[v] = tipi
        return out
    finally:
        con.close()


@lru_cache(maxsize=1)
def get_data_riferimento() -> str:
    con = sqlite3.connect(f"file:{settings.db_path}?mode=ro", uri=True)
    try:
        row = con.execute("SELECT data_riferimento FROM ai_bi_meta").fetchone()
        return row[0] if row else ""
    finally:
        con.close()


def render_schema_for_prompt() -> str:
    lines: list[str] = []
    for view, cols in get_views_schema().items():
        desc = VIEW_DESCRIPTIONS.get(view, "")
        lines.append(f"VISTA {view} - {desc}")
        col_str = ", ".join(f"{c} {t}" for c, t in cols)
        lines.append(f"  colonne: {col_str}")
    return "\n".join(lines)


@lru_cache(maxsize=1)
def render_glossario_for_prompt() -> str:
    data = yaml.safe_load(settings.glossario_path.read_text(encoding="utf-8"))
    out: list[str] = []
    for termine, definizione in (data.get("termini") or {}).items():
        out.append(f"- {termine}: {' '.join(str(definizione).split())}")
    note = data.get("note_per_il_modello") or []
    if note:
        out.append("")
        out.append("Regole:")
        out.extend(f"- {n}" for n in note)
    return "\n".join(out)


@lru_cache(maxsize=1)
def load_few_shot(n: int = 5) -> list[dict[str, str]]:
    data = yaml.safe_load(settings.golden_path.read_text(encoding="utf-8"))
    shots: list[dict[str, str]] = []
    for q in (data.get("domande") or [])[:n]:
        sql = " ".join(str(q.get("sql_riferimento", "")).split())
        if sql:
            shots.append({"domanda": q["domanda"], "sql": sql})
    return shots


@lru_cache(maxsize=1)
def load_golden_questions() -> list[str]:
    data = yaml.safe_load(settings.golden_path.read_text(encoding="utf-8"))
    return [q["domanda"] for q in (data.get("domande") or [])]
