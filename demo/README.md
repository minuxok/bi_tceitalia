# Demo "Acme Srl" — Conversational BI

Primo mattone del progetto: **database demo + layer semantico + domande d'oro**.
Serve sia per lo spike Text-to-SQL sia, subito dopo, per il widget da mettere sul sito.

```
demo/
├── db/
│   ├── schema.sql          tabelle grezze (clienti, ordini, righe, pagamenti, prodotti, agenti)
│   ├── seed.py             generatore deterministico (seed=42) → acme.db
│   └── acme.db             SQLite generato (rigenerabile: python seed.py)
├── semantic/
│   ├── views.sql           viste curate ai_bi_* (gli UNICI oggetti interrogabili dal motore)
│   └── glossario.yaml      termini di business → definizioni operative sulle viste
└── eval/
    └── golden_questions.yaml   12 domande d'oro + 3 controlli negativi
```

## Rigenerare il database

```bash
cd demo/db
python seed.py            # crea demo/db/acme.db
```

Nessuna dipendenza esterna: solo Python 3 standard library. Il dataset è
**deterministico** (stesso seed → stesso DB) e **congelato al 2026-08-27**
(`ai_bi_meta.data_riferimento`), così gli screenshot della demo restano validi.

Contenuto: 6 agenti, 90 clienti, 60 prodotti, ~1.900 ordini, ~5.000 righe,
~2.900 scadenze, su 2024 → agosto 2026. Include stagionalità (picco set/ott,
calo agosto), ~28 clienti dormienti, ~9% di scaduto sul fatturato, 6 prodotti fermi.

## Layer semantico

Il motore Text-to-SQL vede **solo** le viste `ai_bi_*`, mai le tabelle grezze.
Il validatore del backend accetterà solo query `SELECT` che toccano nomi con
prefisso `ai_bi_`.

| Vista | Grana | A cosa serve |
|---|---|---|
| `ai_bi_vendite` | riga d'ordine | fatturato, margine, quantità per cliente/prodotto/agente/area/tempo |
| `ai_bi_ordini` | ordine | numero ordini, valore medio, stato, totali |
| `ai_bi_clienti` | cliente | attivi/dormienti, fatturato 12m, primo/ultimo ordine |
| `ai_bi_scaduto` | scadenza non incassata | insoluto per cliente/agente, fasce di ritardo |
| `ai_bi_prodotti` | prodotto | best seller, prodotti fermi, venduto 12m |
| `ai_bi_agenti` | agente | classifiche fatturato YTD / 12m, portafoglio clienti |

Nessuna PII nelle viste: email, telefono e partita IVA restano nelle tabelle grezze.

## Domande d'oro

`eval/golden_questions.yaml` contiene 12 domande con SQL di riferimento e sintesi
del risultato atteso (valori calcolati su `seed=42`), più 3 controlli negativi in
cui il modello **non deve inventare** (dato assente, PII, domanda vaga).

## Prossimo passo

Backend FastAPI: endpoint `/chiedi` → schema viste + glossario + few-shot al LLM
(via LiteLLM) → validazione query → esecuzione su `acme.db` → risposta con
testo + tabella + spec grafico + SQL + spiegazione. Poi il widget React embeddabile.
