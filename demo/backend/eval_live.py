"""Valutazione REALE del motore Text-to-SQL contro l'LLM configurato.

Per ogni "domanda d'oro":
  domanda --(LLM)--> interpretazione JSON --> valida_e_normalizza --> esegui
  poi confronta il risultato con quello della sql_riferimento.

Per ogni "controllo negativo": la domanda NON deve produrre una query
(attesa: tipo = non_disponibile | chiarimento, oppure query bloccata dal validatore).

Uso:
    cd demo/backend
    .venv\\Scripts\\python.exe eval_live.py            # tutte
    .venv\\Scripts\\python.exe eval_live.py G06 G11     # solo alcune

Soglia go-live: >= 90% sulle domande d'oro (>= 11 / 12).
Nota: le prime 5 domande (G01-G05) sono anche few-shot nel prompt: contano
meno come test "cieco". Guarda soprattutto G06-G12.
"""
from __future__ import annotations

import json
import sqlite3
import sys
import time
from datetime import datetime, timezone

import yaml

from app.config import settings
from app.llm import LLMError, genera_interpretazione
from app.runner import esegui
from app.semantic import get_data_riferimento
from app.validator import QueryRifiutata, valida_e_normalizza

PAUSA_S = 4.5          # ~13 richieste/minuto: sotto il limite del tier gratuito
MAX_TENTATIVI = 4      # backoff su errori temporanei (rate limit, 5xx)


# ----------------------------- utilità confronto -----------------------------

def _to_float(x):
    if isinstance(x, bool):
        return None
    if isinstance(x, (int, float)):
        return float(x)
    if isinstance(x, str):
        s = x.strip().replace(" ", "").replace("%", "")
        # "1.234,56" -> "1234.56"  |  "1,234.56" -> "1234.56"
        if "," in s and "." in s:
            if s.rfind(",") > s.rfind("."):
                s = s.replace(".", "").replace(",", ".")
            else:
                s = s.replace(",", "")
        elif "," in s:
            s = s.replace(",", ".")
        try:
            return float(s)
        except ValueError:
            return None
    return None


def _riga_map(colonne, righe):
    """dict: etichetta_riga -> lista ordinata dei valori numerici della riga.

    L'etichetta è la PRIMA cella non numerica della riga (di solito la
    dimensione: mese, cliente, categoria...). Usare solo la prima evita falsi
    negativi quando il modello aggiunge colonne testuali extra corrette
    (es. stato_prodotto, ultima_vendita). Il confronto resta indipendente
    dall'ORDER BY.
    """
    out = {}
    for r in righe:
        nums = []
        etichetta = None
        for cella in r:
            f = _to_float(cella)
            if f is None:
                if etichetta is None:
                    etichetta = "" if cella is None else str(cella).strip().lower()
            else:
                nums.append(round(f, 4))
        chiave = etichetta if etichetta is not None else f"__riga_{len(out)}"
        out[chiave] = sorted(nums)
    return out


def _num_vicini(a, b, tol):
    if tol == 0:
        return abs(a - b) < 1e-6
    scala = max(abs(a), abs(b), 1.0)
    return abs(a - b) <= tol * scala


def _liste_num_uguali(la, lb, tol):
    if len(la) != len(lb):
        return False
    return all(_num_vicini(x, y, tol) for x, y in zip(sorted(la), sorted(lb)))


def confronta(atteso_cols, atteso_righe, ott_cols, ott_righe, tol):
    ma = _riga_map(atteso_cols, atteso_righe)
    mo = _riga_map(ott_cols, ott_righe)

    if set(ma) != set(mo):
        mancano = sorted(set(ma) - set(mo))[:4]
        in_piu = sorted(set(mo) - set(ma))[:4]
        return False, f"righe diverse (attese {len(ma)}, ottenute {len(mo)}); mancano {mancano}; in più {in_piu}"

    for chiave, num_a in ma.items():
        num_o = mo[chiave]
        # il modello può aggiungere colonne numeriche extra (es. un COUNT):
        # promuovo a OK se i valori attesi sono un sottoinsieme (con tolleranza)
        if _liste_num_uguali(num_a, num_o, tol):
            continue
        ok_sub = all(any(_num_vicini(x, y, tol) for y in num_o) for x in num_a)
        if not ok_sub:
            return False, f"valori diversi per '{chiave}': attesi {num_a}, ottenuti {num_o}"
    return True, "ok"


# ----------------------------- esecuzione query -----------------------------

def esegui_riferimento(sql: str):
    con = sqlite3.connect(f"file:{settings.db_path}?mode=ro", uri=True)
    try:
        cur = con.execute(sql.rstrip().rstrip(";"))
        cols = [d[0] for d in cur.description] if cur.description else []
        righe = [list(r) for r in cur.fetchall()]
        return cols, righe
    finally:
        con.close()


class QuotaGiornalieraEsaurita(RuntimeError):
    pass


def chiama_llm(domanda: str) -> dict:
    ultimo = None
    for tentativo in range(1, MAX_TENTATIVI + 1):
        try:
            return genera_interpretazione(domanda)
        except LLMError as e:
            ultimo = e
            msg = str(e).lower()
            # quota GIORNALIERA free tier: inutile ritentare, si ferma tutto
            if "perday" in msg.replace(" ", "") or "requests per day" in msg or "free_tier_requests" in msg:
                raise QuotaGiornalieraEsaurita(
                    "Quota gratuita giornaliera Gemini esaurita (20 richieste/giorno per il modello). "
                    "Attiva la fatturazione sul progetto Google Cloud o riprova domani."
                ) from e
            # credito prepagato esaurito: idem, stop immediato
            if "prepayment credits" in msg or "prepay" in msg:
                raise QuotaGiornalieraEsaurita(
                    "Credito prepagato Gemini esaurito/assente. Carica credito sul progetto "
                    "(AI Studio -> progetto ConversationalBI -> billing) oppure passa alla "
                    "fatturazione posticipata."
                ) from e
            temporaneo = any(k in msg for k in ("rate", "429", "timeout", "503", "500", "overloaded", "unavailable"))
            if tentativo < MAX_TENTATIVI and temporaneo:
                attesa = PAUSA_S * 2 ** tentativo
                print(f"    ...errore temporaneo, ritento tra {attesa:.0f}s ({e})")
                time.sleep(attesa)
                continue
            raise
    raise ultimo  # pragma: no cover


# ----------------------------- casi di test -----------------------------

def valuta_domanda(q: dict) -> dict:
    qid = q["id"]
    tol = float(q.get("tolleranza", 0.01))
    res = {"id": qid, "domanda": q["domanda"]}
    try:
        interp = chiama_llm(q["domanda"])
    except LLMError as e:
        return {**res, "esito": "ERRORE_LLM", "dettaglio": str(e)}

    tipo = interp.get("tipo", "query")
    res["tipo_llm"] = tipo
    res["sql_llm"] = interp.get("sql", "")
    if tipo != "query":
        return {**res, "esito": "FAIL", "dettaglio": f"il modello ha risposto '{tipo}', attesa una query"}

    try:
        sql_ok = valida_e_normalizza(interp.get("sql", ""))
    except QueryRifiutata as e:
        return {**res, "esito": "FAIL", "dettaglio": f"query rifiutata dal validatore: {e}"}
    res["sql_eseguita"] = sql_ok

    try:
        ris = esegui(sql_ok)
    except Exception as e:  # noqa: BLE001
        return {**res, "esito": "FAIL", "dettaglio": f"esecuzione fallita: {e}"}

    try:
        rc, rr = esegui_riferimento(q["sql_riferimento"])
    except Exception as e:  # noqa: BLE001
        return {**res, "esito": "ERRORE_RIF", "dettaglio": f"sql_riferimento non eseguibile: {e}"}

    ok, motivo = confronta(rc, rr, ris.colonne, ris.righe, tol)
    return {**res, "esito": "PASS" if ok else "FAIL", "dettaglio": motivo,
            "n_righe_attese": len(rr), "n_righe_ottenute": ris.n_righe}


def valuta_controllo_negativo(c: dict) -> dict:
    cid = c["id"]
    res = {"id": cid, "domanda": c["domanda"]}
    try:
        interp = chiama_llm(c["domanda"])
    except LLMError as e:
        return {**res, "esito": "ERRORE_LLM", "dettaglio": str(e)}

    tipo = interp.get("tipo", "query")
    res["tipo_llm"] = tipo
    if tipo in ("non_disponibile", "chiarimento"):
        return {**res, "esito": "PASS", "dettaglio": f"il modello ha risposto '{tipo}' (corretto)"}

    # ha comunque prodotto una query: passa solo se il validatore la blocca
    try:
        valida_e_normalizza(interp.get("sql", ""))
    except QueryRifiutata as e:
        return {**res, "esito": "PASS", "dettaglio": f"query prodotta ma bloccata dal validatore: {e}"}
    return {**res, "esito": "FAIL", "dettaglio": "il modello ha prodotto una query eseguibile invece di rifiutare",
            "sql_llm": interp.get("sql", "")}


# ----------------------------- main -----------------------------

def main() -> int:
    if not settings.llm_ready:
        print("LLM non configurato: manca GEMINI_API_KEY in demo/backend/.env")
        return 2

    data = yaml.safe_load(settings.golden_path.read_text(encoding="utf-8"))
    domande = data.get("domande") or []
    negativi = data.get("controlli_negativi") or []

    filtro = {a.upper() for a in sys.argv[1:]}
    if filtro:
        domande = [q for q in domande if q["id"].upper() in filtro]
        negativi = [c for c in negativi if c["id"].upper() in filtro]

    print(f"Modello         : {settings.llm_model}")
    print(f"Data riferimento: {get_data_riferimento()}")
    print(f"Domande d'oro    : {len(domande)}   Controlli negativi: {len(negativi)}")
    print("=" * 78)

    risultati = []
    tot = len(domande) + len(negativi)
    i = 0
    quota_finita = False

    try:
        for q in domande:
            i += 1
            r = valuta_domanda(q)
            risultati.append(r)
            marca = {"PASS": "PASS ", "FAIL": "FAIL ", "ERRORE_LLM": "ERR! ", "ERRORE_RIF": "ERR? "}.get(r["esito"], "???? ")
            print(f"[{r['id']}] {marca} {r['domanda']}")
            if r["esito"] != "PASS":
                print(f"        -> {r.get('dettaglio','')}")
                if r.get("sql_llm"):
                    print(f"        SQL modello: {' '.join(r['sql_llm'].split())[:300]}")
            if i < tot:
                time.sleep(PAUSA_S)

        if negativi:
            print("-" * 78)
            print("Controlli negativi (il modello NON deve inventare):")
        for c in negativi:
            i += 1
            r = valuta_controllo_negativo(c)
            risultati.append(r)
            marca = {"PASS": "PASS ", "FAIL": "FAIL "}.get(r["esito"], "ERR! ")
            print(f"[{r['id']}] {marca} {r['domanda']}")
            if r["esito"] != "PASS":
                print(f"        -> {r.get('dettaglio','')}")
            if i < tot:
                time.sleep(PAUSA_S)
    except QuotaGiornalieraEsaurita as e:
        quota_finita = True
        print("-" * 78)
        print(f"STOP: {e}")
        print(f"Completate {len(risultati)}/{tot} prima dello stop.")

    # ---- riepilogo ----
    d_pass = sum(1 for r in risultati if r["id"].startswith("G") and r["esito"] == "PASS")
    d_tot = sum(1 for r in risultati if r["id"].startswith("G"))
    n_pass = sum(1 for r in risultati if r["id"].startswith("N") and r["esito"] == "PASS")
    n_tot = sum(1 for r in risultati if r["id"].startswith("N"))
    cieche = [r for r in risultati if r["id"].startswith("G") and r["id"] not in ("G01", "G02", "G03", "G04", "G05")]
    c_pass = sum(1 for r in cieche if r["esito"] == "PASS")

    print("=" * 78)
    if d_tot:
        pct = 100 * d_pass / d_tot
        print(f"Domande d'oro     : {d_pass}/{d_tot}  ({pct:.0f}%)   soglia go-live: 90%")
        if cieche:
            print(f"  di cui \"cieche\" (G06-G12): {c_pass}/{len(cieche)}  ({100*c_pass/len(cieche):.0f}%)")
    if n_tot:
        print(f"Controlli negativi: {n_pass}/{n_tot}")

    out = {
        "quando": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "modello": settings.llm_model,
        "domande_pass": d_pass, "domande_tot": d_tot,
        "cieche_pass": c_pass, "cieche_tot": len(cieche),
        "negativi_pass": n_pass, "negativi_tot": n_tot,
        "dettaglio": risultati,
    }
    out["interrotto_per_quota"] = quota_finita
    dest = settings.golden_path.parent / "last_run.json"
    dest.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nDettaglio salvato in {dest}")

    if quota_finita:
        return 2
    return 0 if (d_tot and d_pass / d_tot >= 0.90) else 1


if __name__ == "__main__":
    sys.exit(main())
