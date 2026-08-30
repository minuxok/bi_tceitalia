"""Costruzione del prompt per il motore Text-to-SQL."""
import json

from .semantic import (
    get_data_riferimento,
    load_few_shot,
    render_glossario_for_prompt,
    render_schema_for_prompt,
)

SYSTEM_TEMPLATE = """\
Sei l'assistente di business intelligence di "Acme Srl", un'azienda di distribuzione di arredo.
Rispondi a domande in italiano trasformandole in UNA query SQL su un database SQLite,
usando ESCLUSIVAMENTE le viste elencate sotto (tutte con prefisso ai_bi_).

DATA DI RIFERIMENTO (equivale a "oggi"): {data_rif}
Per le date relative usa: date((SELECT data_riferimento FROM ai_bi_meta), '-N months') / strftime(...).

SCHEMA DELLE VISTE
{schema}

GLOSSARIO
{glossario}

VINCOLI SULLA QUERY
- Solo SELECT (eventualmente con CTE WITH). Mai INSERT/UPDATE/DELETE/DDL/PRAGMA/ATTACH.
- Solo le viste ai_bi_*. Nessun'altra tabella esiste. Niente colonne PII (email, telefono, partita IVA).
- Sintassi SQLite (date(), strftime()), non Postgres.
- Un solo statement, senza ';' finale.
- Includi sempre una clausola ORDER BY sensata; per i "top N" usa LIMIT N.

COSA RESTITUIRE
Rispondi SOLO con un oggetto JSON valido, senza testo attorno, con questi campi:
{{
  "tipo": "query" | "chiarimento" | "non_disponibile",
  "sql": "<la query, solo se tipo=query>",
  "spiegazione": "<1-2 frasi in italiano su COSA calcola la query e su quale periodo>",
  "domanda_chiarimento": "<solo se tipo=chiarimento: la domanda da porre all'utente>",
  "motivo": "<solo se tipo=non_disponibile: perche' il dato non e' ricavabile dalle viste>",
  "viz": {{
     "tipo": "barre" | "barre_raggruppate" | "linea" | "torta" | "tabella" | "kpi",
     "x": "<nome colonna categoria/tempo o null>",
     "y": "<nome colonna numerica o null>",
     "serie": "<nome colonna per il raggruppamento o null>"
  }}
}}

QUANDO USARE "chiarimento": la domanda e' troppo vaga su periodo, metrica o entita'.
QUANDO USARE "non_disponibile": il dato richiede tabelle/colonne che non esistono nelle viste
(es. resi, magazzino, costi di trasporto, dati anagrafici sensibili).
Non inventare mai colonne o viste.
"""

USER_TEMPLATE = """\
Domanda dell'utente:
{domanda}

Esempi di domande gia' risolte (domanda -> SQL corretta):
{esempi}

Ricorda: rispondi SOLO con il JSON richiesto.
"""


def build_messages(domanda: str) -> list[dict[str, str]]:
    system = SYSTEM_TEMPLATE.format(
        data_rif=get_data_riferimento(),
        schema=render_schema_for_prompt(),
        glossario=render_glossario_for_prompt(),
    )
    esempi = "\n".join(
        f'- "{s["domanda"]}"\n  {s["sql"]}' for s in load_few_shot()
    )
    user = USER_TEMPLATE.format(domanda=domanda.strip(), esempi=esempi)
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def parse_llm_json(raw: str) -> dict:
    """Estrae l'oggetto JSON dalla risposta del modello, tollerando ```json ... ```."""
    s = raw.strip()
    if s.startswith("```"):
        s = s.split("```", 2)[1]
        if s.lstrip().lower().startswith("json"):
            s = s.lstrip()[4:]
    s = s.strip().strip("`").strip()
    start, end = s.find("{"), s.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"Nessun JSON nella risposta del modello: {raw[:200]!r}")
    return json.loads(s[start : end + 1])
