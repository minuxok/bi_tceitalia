"""Catalogo delle viste ai_bi_* e campioni di righe, per il pannello "Dati della demo".

Sola lettura. Ogni query passa dal validatore e dal runner come quelle del
motore, e il nome della vista è sempre preso dalla whitelist del catalogo (mai
dall'input dell'utente formattato nell'SQL).

Le risposte sono in cache: il dataset demo è congelato; sui verticali MySQL
live la cache breve evita di martellare il DB del cliente.
"""
from __future__ import annotations

import re
import time
from typing import Any

from .config import settings
from .runner import esegui
from .semantic import (
    VIEW_DESCRIPTIONS,
    get_data_riferimento,
    get_views_schema,
)
from .validator import valida_e_normalizza

CAMPIONE_RIGHE = 5
# Colonne con dati di contatto: restano nella vista (il motore le vede), ma non
# vengono mostrate nelle righe di esempio del pannello pubblico. Vale per ogni
# verticale, anche se oggi solo "gest" ne ha.
COLONNE_CONTATTO = {
    "email", "pec", "telefono", "cellulare", "partita_iva", "codice_fiscale",
    "indirizzo", "cap", "iban",
}
_TTL_S = 24 * 3600 if settings.db_engine == "sqlite" else 300

_cache: dict[str, tuple[float, Any]] = {}


def _cached(chiave: str, produci):
    ora = time.monotonic()
    hit = _cache.get(chiave)
    if hit and ora - hit[0] < _TTL_S:
        return hit[1]
    valore = produci()
    _cache[chiave] = (ora, valore)
    return valore


def _scalari(sql: str) -> list:
    ris = esegui(valida_e_normalizza(sql))
    return ris.righe[0] if ris.righe else []


def _n_righe(vista: str) -> int | None:
    try:
        return int(_scalari(f"SELECT COUNT(*) FROM {vista}")[0])
    except Exception:  # noqa: BLE001 - un conteggio mancante non deve rompere il catalogo
        return None


def _periodo() -> dict[str, str] | None:
    """Intervallo coperto, dalla prima vista che espone `anno_mese`."""
    for vista, colonne in get_views_schema().items():
        if any(c == "anno_mese" for c, _ in colonne):
            try:
                da, a = _scalari(f"SELECT MIN(anno_mese), MAX(anno_mese) FROM {vista}")
            except Exception:  # noqa: BLE001
                return None
            if da and a:
                return {"da": str(da), "a": str(a), "vista": vista}
    return None


def _costruisci_catalogo() -> dict:
    viste = []
    for nome, colonne in get_views_schema().items():
        viste.append(
            {
                "nome": nome,
                "descrizione": VIEW_DESCRIPTIONS.get(nome, ""),
                "colonne": [{"nome": c, "tipo": t} for c, t in colonne],
                "n_righe": _n_righe(nome),
            }
        )
    return {
        "verticale": settings.vertical,
        "data_riferimento": get_data_riferimento() if _ha_meta() else "",
        "periodo": _periodo(),
        "viste": viste,
    }


def _ha_meta() -> bool:
    return "ai_bi_meta" in get_views_schema()


def catalogo() -> dict:
    return _cached("catalogo", _costruisci_catalogo)


def campione(vista: str) -> dict | None:
    """Prime righe di una vista. None se la vista non è nel catalogo."""
    if vista not in get_views_schema():
        return None

    def produci() -> dict:
        ris = esegui(valida_e_normalizza(f"SELECT * FROM {vista} LIMIT {CAMPIONE_RIGHE}"))
        tenute = [i for i, c in enumerate(ris.colonne) if c.lower() not in COLONNE_CONTATTO]
        return {
            "vista": vista,
            "colonne": [ris.colonne[i] for i in tenute],
            "righe": [[r[i] for i in tenute] for r in ris.righe],
        }

    return _cached(f"campione:{vista}", produci)


_RE_VISTA = re.compile(r"\bai_bi_[a-z0-9_]+", re.IGNORECASE)


def viste_usate(sql: str) -> list[str]:
    """Viste del catalogo citate nella query, in ordine di comparsa."""
    note = get_views_schema()
    viste: list[str] = []
    for m in _RE_VISTA.finditer(sql or ""):
        v = m.group(0).lower()
        if v in note and v not in viste:
            viste.append(v)
    return viste
