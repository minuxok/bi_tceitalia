"""Endpoint del pannello "Dati della demo" (senza LLM).

    cd demo/backend
    VERTICAL=ecom python test_demo_data.py
"""
import sys

from fastapi.testclient import TestClient

from app.main import app

c = TestClient(app)
ko = 0


def check(nome: str, ok: bool) -> None:
    global ko
    print(("ok  " if ok else "KO  ") + nome)
    ko += 0 if ok else 1


schema = c.get("/demo/schema").json()
viste = {v["nome"]: v for v in schema["viste"]}
check("schema: tutte le viste sono ai_bi_*", all(n.startswith("ai_bi_") for n in viste))
check("schema: ogni vista ha descrizione e colonne", all(v["descrizione"] and v["colonne"] for v in viste.values()))

for nome in viste:
    r = c.get(f"/demo/sample/{nome}")
    j = r.json()
    check(f"sample {nome}: 200, <=5 righe", r.status_code == 200 and 0 < len(j["righe"]) <= 5)

from app.demo_data import COLONNE_CONTATTO

for nome in viste:
    cols = c.get(f"/demo/sample/{nome}").json()["colonne"]
    check(f"sample {nome}: nessuna colonna di contatto", not any(x.lower() in COLONNE_CONTATTO for x in cols))

for cattivo in ("sqlite_master", "clienti", "x;drop table y", "ai_bi_inesistente"):
    check(f"sample '{cattivo}' rifiutato (404)", c.get(f"/demo/sample/{cattivo}").status_code == 404)

sys.exit(1 if ko else 0)
