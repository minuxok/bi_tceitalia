"""Normalizza lo spec del grafico e produce una sintesi testuale del risultato."""
from __future__ import annotations

import re

from .runner import Risultato

TIPI_VALIDI = {"barre", "barre_raggruppate", "linea", "torta", "tabella", "kpi"}
_DATE_RE = re.compile(r"^\d{4}(-\d{2}(-\d{2})?)?$")


def _is_number(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _col_types(ris: Risultato) -> list[str]:
    """'num' | 'data' | 'testo' per ciascuna colonna, sul primo valore non nullo."""
    tipi = []
    for i, _ in enumerate(ris.colonne):
        tipo = "testo"
        for r in ris.righe:
            v = r[i]
            if v is None:
                continue
            if _is_number(v):
                tipo = "num"
            elif isinstance(v, str) and _DATE_RE.match(v.strip()):
                tipo = "data"
            break
        tipi.append(tipo)
    return tipi


def normalizza_viz(viz: dict | None, ris: Risultato) -> dict:
    viz = dict(viz or {})
    tipi = _col_types(ris)
    col = ris.colonne

    def valida_col(nome):
        return nome if nome in col else None

    x = valida_col(viz.get("x"))
    y = valida_col(viz.get("y"))
    serie = valida_col(viz.get("serie"))
    tipo = viz.get("tipo") if viz.get("tipo") in TIPI_VALIDI else None

    # inferenza di riserva quando il modello non ha dato indicazioni valide
    if x is None:
        for c, t in zip(col, tipi):
            if t in ("data", "testo"):
                x = c
                break
    if y is None:
        for c, t in zip(col, tipi):
            if t == "num" and c != x:
                y = c
                break

    if tipo is None:
        n_num = tipi.count("num")
        if len(col) == 1 or ris.n_righe == 0:
            tipo = "tabella"
        elif ris.n_righe == 1 and n_num >= 1:
            tipo = "kpi"
        elif x and tipi[col.index(x)] == "data":
            tipo = "linea"
        elif serie and n_num >= 1:
            tipo = "barre_raggruppate"
        elif x and y and ris.n_righe <= 8 and n_num == 1:
            tipo = "torta"
        elif x and y:
            tipo = "barre"
        else:
            tipo = "tabella"

    # troppe categorie per una torta -> barre
    if tipo == "torta" and ris.n_righe > 8:
        tipo = "barre"

    return {"tipo": tipo, "x": x, "y": y, "serie": serie}


def _fmt(v) -> str:
    if _is_number(v):
        if float(v).is_integer():
            return f"{int(v):,}".replace(",", ".")
        return f"{v:,.2f}".replace(",", "§").replace(".", ",").replace("§", ".")
    return str(v)


def sintesi_risultato(ris: Risultato, viz: dict) -> str:
    if ris.n_righe == 0:
        return "La query non ha restituito righe."

    x, y = viz.get("x"), viz.get("y")
    if x in ris.colonne and y in ris.colonne and ris.n_righe > 1:
        ix, iy = ris.colonne.index(x), ris.colonne.index(y)
        coppie = [(r[ix], r[iy]) for r in ris.righe if _is_number(r[iy])]
        if coppie:
            tot = sum(v for _, v in coppie)
            top_k, top_v = max(coppie, key=lambda t: t[1])
            parti = [f"{ris.n_righe} righe"]
            yl = (y or "").lower()
            additiva = any(t in yl for t in ("fattur", "importo", "scaduto", "margine", "ricavo", "totale", "quantita", "n_ordini", "num_ordini"))
            non_additiva = any(t in yl for t in ("pct", "perc", "media", "medio", "aov", "%"))
            if additiva and not non_additiva:
                parti.append(f"totale {y} = {_fmt(tot)}")
            parti.append(f"valore piu' alto: {top_k} = {_fmt(top_v)}")
            return ". ".join(parti).capitalize() + "."

    if ris.n_righe == 1:
        celle = ", ".join(f"{c} = {_fmt(v)}" for c, v in zip(ris.colonne, ris.righe[0]))
        return f"Risultato: {celle}."

    return f"{ris.n_righe} righe restituite."
