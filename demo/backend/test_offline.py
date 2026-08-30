"""Prova la pipeline SENZA LLM: valida ed esegue tutte le domande d'oro.

    cd demo/backend
    python test_offline.py
"""
import sys

import yaml

from app.chart import normalizza_viz, sintesi_risultato
from app.config import settings
from app.runner import esegui
from app.semantic import render_glossario_for_prompt, render_schema_for_prompt
from app.validator import QueryRifiutata, valida_e_normalizza

VIZ_HINT = {
    "barre": {"tipo": "barre"}, "linea": {"tipo": "linea"},
    "torta": {"tipo": "torta"}, "tabella": {"tipo": "tabella"},
    "barre_raggruppate": {"tipo": "barre_raggruppate"},
}


def main() -> int:
    print(f"DB           : {settings.db_path}  (esiste: {settings.db_path.exists()})")
    print(f"Schema viste : {len(render_schema_for_prompt().splitlines())} righe di descrizione")
    print(f"Glossario    : {len(render_glossario_for_prompt().splitlines())} righe\n")

    data = yaml.safe_load(settings.golden_path.read_text(encoding="utf-8"))
    domande = data["domande"]
    ko = 0

    for q in domande:
        qid = q["id"]
        sql_rif = q["sql_riferimento"]
        try:
            sql = valida_e_normalizza(sql_rif)
        except QueryRifiutata as e:
            print(f"[{qid}] VALIDATORE KO: {e}")
            ko += 1
            continue
        try:
            ris = esegui(sql)
        except Exception as e:  # noqa: BLE001
            print(f"[{qid}] ESECUZIONE KO: {e}")
            ko += 1
            continue
        viz = normalizza_viz(VIZ_HINT.get(q.get("viz", "")), ris)
        testo = sintesi_risultato(ris, viz)
        print(f"[{qid}] ok  righe={ris.n_righe:<3} viz={viz['tipo']:<17} {testo}")

    # controllo che il validatore BLOCCHI cose vietate
    print("\n-- controlli negativi sul validatore --")
    cattive = [
        ("DDL", "DROP TABLE clienti"),
        ("DML", "DELETE FROM ai_bi_vendite"),
        ("tabella grezza", "SELECT * FROM clienti LIMIT 5"),
        ("multi-statement", "SELECT 1; SELECT 2"),
        ("attach", "ATTACH DATABASE 'x.db' AS x"),
        ("pragma", "PRAGMA table_info('clienti')"),
    ]
    for etichetta, s in cattive:
        try:
            valida_e_normalizza(s)
            print(f"  [{etichetta}] NON bloccata  <-- PROBLEMA")
            ko += 1
        except QueryRifiutata as e:
            print(f"  [{etichetta}] bloccata: {e}")

    # LIMIT forzato
    forzata = valida_e_normalizza("SELECT * FROM ai_bi_vendite")
    print(f"\nLIMIT forzato -> {forzata[-40:]!r}")
    if f"LIMIT {settings.sql_row_limit}" not in forzata.upper().replace('  ', ' '):
        print("  <-- PROBLEMA: LIMIT non applicato")
        ko += 1

    print(f"\n{'TUTTO OK' if ko == 0 else f'{ko} PROBLEMI'}")
    return 1 if ko else 0


if __name__ == "__main__":
    sys.exit(main())
