"""API della demo Conversational BI.

Il verticale attivo (dataset + layer semantico) è scelto da VERTICAL (acme | ecom).

Endpoint:
  GET  /health    stato del servizio
  GET  /domande   elenco delle domande d'oro (prompt precompilati per il widget)
  POST /chiedi    { "domanda": "..." } -> risposta strutturata
"""
from __future__ import annotations

import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .chart import normalizza_viz, sintesi_risultato
from .config import settings
from .llm import LLMError, genera_interpretazione
from .logging_store import (
    budget_llm_disponibile,
    hash_ip,
    incrementa_llm,
    registra,
)
from .ratelimit import consenti
from .runner import QueryErrore, QueryTimeout, esegui
from .semantic import get_data_riferimento, get_views_schema, load_golden_questions
from .validator import QueryRifiutata, valida_e_normalizza

app = FastAPI(
    title=f"Conversational BI - Demo ({settings.vertical})",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class Domanda(BaseModel):
    domanda: str = Field(min_length=3, max_length=500)


def _client_ip(req: Request) -> str:
    fwd = req.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return req.client.host if req.client else "sconosciuto"


@app.get("/health")
def health() -> dict:
    # Il DB reale (mysql) potrebbe non rispondere: /health resta comunque 200,
    # così l'healthcheck Docker non fa flappare il container per un blip di rete.
    try:
        data_rif = get_data_riferimento()
        viste = list(get_views_schema().keys())
        db_ok = True
    except Exception as e:  # noqa: BLE001
        data_rif, viste, db_ok = "", [], False
        _ = e
    return {
        "stato": "ok",
        "verticale": settings.vertical,
        "motore": settings.db_engine,
        "db_raggiungibile": db_ok,
        "llm_configurato": settings.llm_ready,
        "modello": settings.llm_model,
        "data_riferimento": data_rif,
        "viste": viste,
    }


@app.get("/domande")
def domande() -> dict:
    return {"domande": load_golden_questions()}


@app.post("/chiedi")
def chiedi(payload: Domanda, request: Request):
    ip = _client_ip(request)
    ip_hash = hash_ip(ip)
    t0 = time.perf_counter()

    ok, attesa = consenti(ip_hash)
    if not ok:
        return JSONResponse(
            status_code=429,
            content={"tipo": "errore", "errore": f"Troppe richieste. Riprova tra {attesa}s."},
        )

    if not settings.llm_ready:
        return JSONResponse(
            status_code=503,
            content={"tipo": "errore", "errore": "Servizio non configurato (LLM assente)."},
        )
    if not budget_llm_disponibile():
        return JSONResponse(
            status_code=503,
            content={"tipo": "errore", "errore": "Limite giornaliero della demo raggiunto. Riprova domani."},
        )

    log: dict = {"ip": ip_hash, "domanda": payload.domanda}

    # 1) interpretazione LLM
    try:
        incrementa_llm()
        interp = genera_interpretazione(payload.domanda)
    except LLMError as e:
        log.update(esito="llm_error", errore=str(e))
        registra(log)
        return JSONResponse(status_code=502, content={"tipo": "errore", "errore": str(e)})

    tipo = interp.get("tipo", "query")
    log["tipo_llm"] = tipo

    if tipo == "chiarimento":
        msg = interp.get("domanda_chiarimento") or "Puoi precisare periodo e metrica?"
        log.update(esito="chiarimento", dettaglio=msg)
        registra(log)
        return {"tipo": "chiarimento", "messaggio": msg}

    if tipo == "non_disponibile":
        msg = interp.get("motivo") or "Il dato non è ricavabile dalle viste disponibili."
        log.update(esito="non_disponibile", dettaglio=msg)
        registra(log)
        return {"tipo": "non_disponibile", "messaggio": msg}

    sql_llm = interp.get("sql", "")
    log["sql_llm"] = sql_llm

    # 2) validazione + normalizzazione
    try:
        sql = valida_e_normalizza(sql_llm)
    except QueryRifiutata as e:
        log.update(esito="query_rifiutata", errore=str(e))
        registra(log)
        return JSONResponse(
            status_code=422,
            content={"tipo": "errore", "errore": f"Query non ammessa: {e}", "sql": sql_llm},
        )
    log["sql_eseguita"] = sql

    # 3) esecuzione
    try:
        ris = esegui(sql)
    except QueryTimeout as e:
        log.update(esito="timeout", errore=str(e))
        registra(log)
        return JSONResponse(status_code=504, content={"tipo": "errore", "errore": str(e), "sql": sql})
    except QueryErrore as e:
        log.update(esito="sql_error", errore=str(e))
        registra(log)
        return JSONResponse(
            status_code=422,
            content={"tipo": "errore", "errore": f"Errore SQL: {e}", "sql": sql},
        )

    viz = normalizza_viz(interp.get("viz"), ris)
    testo = sintesi_risultato(ris, viz)

    log.update(
        esito="ok",
        n_righe=ris.n_righe,
        troncato=ris.troncato,
        durata_query_ms=ris.durata_ms,
        durata_totale_ms=int((time.perf_counter() - t0) * 1000),
    )
    registra(log)

    return {
        "tipo": "risultato",
        "risposta_testo": testo,
        "spiegazione": interp.get("spiegazione", ""),
        "sql": sql,
        "colonne": ris.colonne,
        "righe": ris.righe,
        "n_righe": ris.n_righe,
        "troncato": ris.troncato,
        "viz": viz,
        "durata_ms": int((time.perf_counter() - t0) * 1000),
    }
