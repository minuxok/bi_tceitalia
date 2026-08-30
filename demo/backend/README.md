# Backend demo — Conversational BI

FastAPI. Traduce una domanda in italiano in una query SQL sulle viste `ai_bi_*`
del DB demo `acme.db`, la **valida**, la esegue in sola lettura e restituisce
testo + tabella + spec grafico + SQL + spiegazione.

```
POST /chiedi    { "domanda": "Fatturato mensile 2025 a barre" }
GET  /domande   → domande d'oro (prompt precompilati del widget)
GET  /health    → stato, modello, viste, data di riferimento
```

## Flusso di una richiesta

```
domanda ──▶ rate limit per IP ──▶ LLM (LiteLLM → Gemini Flash)
                                     │  restituisce JSON:
                                     │  {tipo, sql, spiegazione, viz, ...}
                                     ▼
              tipo = chiarimento ──▶ risposta: domanda di chiarimento
              tipo = non_disponibile ─▶ risposta: motivo
              tipo = query
                                     ▼
                          validator.py  (solo SELECT, solo ai_bi_*,
                          no DDL/DML/PRAGMA/ATTACH, LIMIT forzato)
                                     ▼
                          runner.py  (SQLite mode=ro, PRAGMA query_only,
                          progress handler → timeout)
                                     ▼
                          chart.py  (normalizza viz + sintesi testuale)
                                     ▼
                       risposta JSON + log JSONL dell'interazione
```

L'LLM **non vede il database**: riceve solo schema delle viste, glossario e
5 esempi few-shot (da `eval/golden_questions.yaml`).

## Avvio in locale

```bash
cd demo/backend
python -m venv .venv && .venv\Scripts\activate      # Windows
# source .venv/bin/activate                          # Linux/Mac
pip install -r requirements.txt

cp .env.example .env        # e inserisci GEMINI_API_KEY
uvicorn app.main:app --reload --port 8000
```

Prima genera il DB: `cd ../db && python seed.py`.

### Test senza chiave LLM

```bash
python test_offline.py
```

Valida ed esegue tutte le domande d'oro e verifica che il validatore blocchi
DDL/DML/tabelle grezze/multi-statement/ATTACH/PRAGMA e forzi il `LIMIT`.

## Deploy su VPS OVH (Ubuntu)

```bash
# 1) codice + venv in /opt/acme-bi
sudo mkdir -p /opt/acme-bi && sudo chown $USER /opt/acme-bi
rsync -a demo/ /opt/acme-bi/demo/
cd /opt/acme-bi/demo/backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env      # compila GEMINI_API_KEY, ALLOWED_ORIGINS=https://iltuosito
../db/../.venv/bin/python ../db/seed.py   # oppure: cd ../db && python3 seed.py

# 2) servizio systemd  → /etc/systemd/system/acme-bi.service
```

```ini
[Unit]
Description=Conversational BI demo (Acme)
After=network.target

[Service]
WorkingDirectory=/opt/acme-bi/demo/backend
ExecStart=/opt/acme-bi/demo/backend/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=always
User=www-data

[Install]
WantedBy=multi-user.target
```

```nginx
# blocco nel server{} del sito
location /bi/ {
    proxy_pass http://127.0.0.1:8000/;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
}
```

```bash
sudo systemctl enable --now acme-bi
```

Il widget del sito chiamerà `https://iltuosito/bi/chiedi`.

## Sicurezza (demo pubblica)

- DB **solo dati finti**, aperto in `mode=ro` + `PRAGMA query_only`.
- Validatore: solo `SELECT` su viste `ai_bi_*`, `LIMIT` e `timeout` forzati.
- Rate limit per IP + tetto giornaliero di chiamate LLM (`DAILY_LLM_CAP`).
- Log: domanda, IP con hash (SHA-256 troncato), SQL, esito. Nessun dato personale.
- `GEMINI_API_KEY` solo in `.env` (non committato).
