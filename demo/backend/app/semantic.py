"""Carica il layer semantico (viste + glossario + few-shot) per il prompt."""
import sqlite3
from functools import lru_cache

import yaml

from .config import settings

# Descrizione curata di ogni vista, per verticale. Le COLONNE sono lette a
# runtime dal DB (sempre allineate), qui sta solo il "a cosa serve".
_VIEW_DESCRIPTIONS: dict[str, dict[str, str]] = {
    "acme": {
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
    },
    "gest": {
        "ai_bi_meta":       "Una sola riga. data_riferimento = ultima data presente nei dati "
                            "('oggi'); n_preventivi e n_ordini_fornitore = totali.",
        "ai_bi_clienti":    "Una riga per cliente. num_preventivi / num_preventivi_accettati, "
                            "valore_accettato(_12m) (imponibile dei preventivi accettati), "
                            "tasso_accettazione_pct, primo/ultimo_preventivo, attivo_recente "
                            "(1 = preventivo negli ultimi 6 mesi). Contiene i contatti "
                            "(email, telefono, indirizzo, partita_iva) - sono dati fittizi.",
        "ai_bi_fornitori":  "Una riga per fornitore. num_ordini, valore_ordinato(_12m) "
                            "(imponibile), consegne_totali / consegne_in_ritardo e "
                            "pct_consegne_in_ritardo (consegna effettiva oltre la prevista). "
                            "Contiene i contatti (dati fittizi).",
        "ai_bi_prodotti":   "Una riga per articolo. prezzo_acquisto, prezzo_vendita, "
                            "margine_unitario, margine_pct, giacenza, giacenza_minima, "
                            "sotto_scorta (1 = giacenza < minima), is_composto, "
                            "quantita_offerta_12m / quantita_ordinata_12m, ultima_offerta, "
                            "ultimo_ordine.",
        "ai_bi_preventivi": "Una riga per preventivo/offerta a cliente (testata). stato "
                            "('bozza','inviata','accettata','rifiutata','scaduta'), accettato "
                            "(1/0), totale_imponibile/iva/generale, n_righe, anno/mese/anno_mese "
                            "di data_offerta. 'accettata' e' l'unico segnale di vendita.",
        "ai_bi_righe_preventivo": "Una riga per riga di preventivo. quantita, prezzo_unitario, "
                            "sconto_percentuale, iva_percentuale, totale_riga (IVA esclusa, "
                            "gia' al netto sconto), categoria prodotto, stato_preventivo, "
                            "accettato. Per analisi per prodotto/categoria/cliente.",
        "ai_bi_ordini_fornitore": "Una riga per ordine d'acquisto a fornitore (testata). stato "
                            "('bozza','inviato','confermato','parzialmente_ricevuto','ricevuto',"
                            "'annullato'), ricevuto/annullato (1/0), totale_imponibile/iva/generale, "
                            "giorni_ritardo_consegna (effettiva - prevista), n_righe.",
        "ai_bi_righe_ordine_fornitore": "Una riga per riga d'ordine d'acquisto. quantita_ordinata, "
                            "quantita_ricevuta, quantita_mancante, prezzo_unitario, totale_riga, "
                            "categoria prodotto, fornitore, stato_ordine. Per acquistato per "
                            "prodotto/categoria/fornitore ed evasione ordini.",
    },
    "ecom": {
        "ai_bi_vendite":  "Una riga per riga d'ordine dell'e-commerce. Base per fatturato, margine "
                          "e quantita' per prodotto, categoria, genere, canale (sorgente), "
                          "dispositivo, regione, provincia e tempo (anno, mese, anno_mese, ora). "
                          "ricavo_lordo = IVA inclusa, ricavo_netto = imponibile. Esclude ordini "
                          "annullati e in attesa di pagamento; i rimborsati restano nel venduto.",
        "ai_bi_ordini":   "Una riga per ordine (testata) con valore_merce_lordo/netto, n_articoli, "
                          "n_righe, sconto_coupon, spedizione_costo, totale_ordine, stato_ordine "
                          "normalizzato, fascia_oraria, con_coupon e tipo_cliente ('Nuovo' al primo "
                          "ordine valido, altrimenti 'Di ritorno'). Per numero ordini, AOV (valore "
                          "medio ordine) e fatturato nuovi vs di ritorno.",
        "ai_bi_clienti":  "Una riga per cliente registrato: canale_acquisizione, newsletter, "
                          "primo_ordine, ultimo_ordine, num_ordini, num_ordini_12m, speso_totale, "
                          "speso_12m (LTV, IVA inclusa, al lordo dei resi), valore_medio_ordine, "
                          "giorni_da_ultimo_ordine, ricorrente (>=2 ordini) e stato_cliente "
                          "('Mai acquistato' | 'Attivo' <=180gg | 'A rischio' 181-365gg | 'Perso' >365gg).",
        "ai_bi_resi":     "Una riga per prodotto reso: importo_rimborsato (lordo) e "
                          "importo_rimborsato_netto, motivo ('Taglia errata', 'Difettoso', ...), "
                          "quantita, categoria/genere prodotto, canale, regione, giorni_dopo_consegna. "
                          "Il venduto sta in ai_bi_vendite: qui c'e' solo il reso.",
        "ai_bi_prodotti": "Una riga per prodotto: prezzo_listino, costo_unitario, margine_pct, "
                          "stato_prodotto, quantita_12m, quantita_resa_12m, tasso_reso_pct, "
                          "fatturato_12m, num_ordini_12m, ultima_vendita. quantita_12m = 0 -> prodotto fermo.",
        "ai_bi_traffico": "Una riga per (giorno, canale) di acquisizione: sessioni, utenti, "
                          "aggiunte_carrello, checkout_avviati, ordini, ricavo_netto, "
                          "conversion_rate_pct (ordini/sessioni*100) e ricavo_per_sessione. "
                          "UNICA fonte per conversion rate e funnel di traffico.",
    },
}

VIEW_DESCRIPTIONS: dict[str, str] = _VIEW_DESCRIPTIONS.get(settings.vertical, {})


_TYPEOF_SQL = {
    "integer": "INTEGER",
    "real": "REAL",
    "text": "TEXT",
    "numeric": "NUMERIC",
    "blob": "BLOB",
}


@lru_cache(maxsize=1)
def get_views_schema() -> dict[str, list[tuple[str, str]]]:
    """{nome_vista: [(colonna, tipo), ...]}.

    sqlite: letto dal file .db (le viste ai_bi_* esistono davvero).
    mysql : ottenuto eseguendo il corpo di ogni vista virtuale con LIMIT 0.
    """
    if settings.db_engine == "mysql":
        from .mysql_backend import introspect_views
        return introspect_views()

    # Le colonne calcolate di una vista spesso non hanno un tipo dichiarato in
    # PRAGMA table_info: in quel caso lo deduciamo dai dati con typeof(), così
    # il prompt non etichetta come TEXT colonne che sono INTEGER/REAL
    # (es. `attivo` 0/1) inducendo il modello a confronti sbagliati (attivo = '1').
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
    if settings.db_engine == "mysql":
        from .mysql_backend import data_riferimento
        return data_riferimento()

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
