# Conversational BI — Gestione Server VPS (OVH)

> **VPS:** `193.70.38.117` · Ubuntu · ISPConfig (stesso VPS di tagnest, cultural-invaders, visitnove-api, industriale-3d, poloniato100)
> **Dominio:** `https://bi.tceitalia.com`
> **App:** `/opt/conversational-bi` — backend FastAPI (Python/uvicorn) gestito con **PM2**, frontend build statica Vite
> **Porta backend:** `3005` (3000=tagnest, 3001=cultural-invaders-next, 3002/3003=visitnove-api e un'altra app, 3004=industriale-3d — verifica con `pm2 status` prima di assumerla libera)
> **Database:** SQLite, file `demo/db/acme.db` dentro il repo
> **Accesso SSH:** Putty → `193.70.38.117` porta `22`, utente da definire (stesso utente delle altre app su questo VPS, es. `ubuntu`)
> **Repo:** https://github.com/minuxok/bi_tceitalia — branch `dev` (attivo), `main` (baseline)

A differenza di poloniato100 (SPA statica pura, nessun processo a runtime), questa app **ha un backend Python persistente** (FastAPI + LLM via LiteLLM), quindi il pattern è ibrido:
- **Frontend** (`demo/frontend/dist`) → file statici, serviti da Apache come document root (come poloniato100).
- **Backend** (`demo/backend`) → processo uvicorn su porta locale, gestito da **PM2** (come industriale-3d/cultural-invaders, ma Python invece di Node), esposto solo su `/api` via reverse proxy Apache.

---

## 0. Repo git — fatto ✅

Repo creato e pushato su `https://github.com/minuxok/bi_tceitalia`, branch `main` e `dev` allineati. `.gitignore` esclude `demo/backend/.env` (contiene una vera `GEMINI_API_KEY`) — va sempre ricreato manualmente sul server da `.env.example` (sez. 1.3).

---

## 1. Setup iniziale sul server (da fare una sola volta)

### 1.1 Crea il sito in ISPConfig — farlo per primo

**URL ISPConfig:** `https://193.70.38.117:8080`

1. Crea un nuovo sito web per il dominio `bi.tceitalia.com`.
2. ISPConfig assegna `/var/www/clients/client0/web28` — la cartella pubblica servita da Apache è la sottocartella **`web`** dentro quel percorso: `/var/www/clients/client0/web28/web`.
3. Tab **SSL** → abilita **Let's Encrypt**.

### 1.2 Clona il repo sul server

> ⚠️ Se il repo è privato: prima di clonare, su GitHub → repo → **Settings** → **Danger Zone** → **Change visibility** → **Make public**, clona (30 secondi), rimetti subito **Make private**. Grazie al `.gitignore`, `.env` non è nel repo quindi non c'è rischio anche nella finestra pubblica.

```bash
cd /opt
sudo git clone https://github.com/minuxok/bi_tceitalia conversational-bi
cd conversational-bi
git checkout main
sudo chown -R $USER:$USER /opt/conversational-bi
```

### 1.3 Backend: virtualenv + configurazione

```bash
cd /opt/conversational-bi/demo/backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Crea `.env` (non esiste, escluso dal repo): copia `.env.example` e compila con i valori di produzione.

```bash
cp .env.example .env
nano .env
```

```ini
GEMINI_API_KEY=<la-tua-chiave>
LLM_MODEL=gemini/gemini-3.6-flash
LLM_TEMPERATURE=0
LLM_TIMEOUT_S=30

DB_PATH=../db/acme.db

SQL_ROW_LIMIT=1000
SQL_TIMEOUT_S=8

RATE_MAX_REQ=20
RATE_WINDOW_S=600
DAILY_LLM_CAP=800

# IMPORTANTE: dominio di produzione, non localhost
ALLOWED_ORIGINS=https://bi.tceitalia.com

LOG_DIR=./logs
```

Verifica manuale (poi Ctrl+C, il servizio vero parte con PM2 al passo successivo):

```bash
mkdir -p logs
.venv/bin/python3 -m uvicorn app.main:app --host 127.0.0.1 --port 3005
curl http://localhost:3005/health
```

### 1.4 Build del frontend

```bash
cd /opt/conversational-bi/demo/frontend
npm install
npm run build
```

Verifica che `dist/` sia stata creata con `index.html` dentro.

### 1.5 Avvia il backend con PM2

> Script d'avvio = binario python del venv (non serve `--interpreter`, PM2 lo esegue direttamente); argomenti = modulo uvicorn.

```bash
pm2 start /opt/conversational-bi/demo/backend/.venv/bin/python3 \
  --name "conversational-bi" \
  --cwd /opt/conversational-bi/demo/backend \
  -- -m uvicorn app.main:app --host 127.0.0.1 --port 3005
pm2 save
```

Verifica:
```bash
pm2 status
curl http://localhost:3005/health
```

### 1.6 Pubblica il frontend nel document root

```bash
sudo rsync -a --delete /opt/conversational-bi/demo/frontend/dist/ /var/www/clients/client0/web28/web/
```

### 1.7 Reverse proxy per l'API in ISPConfig

Nel sito `bi.tceitalia.com` → tab **Options** → Apache Directives:

```apache
ProxyPreserveHost On
ProxyPass /api http://localhost:3005/
ProxyPassReverse /api http://localhost:3005/
```

> Il frontend (`demo/frontend/src/api.ts`) chiama di default il path `/api` (`/api/health`, `/api/chiedi`) — coerente con questo proxy, non serve passare `VITE_API_BASE` in build.

Poi tab **SSL** → abilita **Let's Encrypt** se non già fatto.

### 1.8 Verifica finale

```bash
curl -I https://bi.tceitalia.com
curl https://bi.tceitalia.com/api/health
```

Se entrambi rispondono → **il sito è online**. Fai anche una query di test dal widget in browser.

---

## 2. Operazione più comune — Aggiornare il sito

**1. Sul PC (terminale locale):**
```powershell
git add -A
git commit -m "descrizione modifiche"
git push origin dev
```
Quando `dev` è pronto per la produzione, merge su `main` e push anche quello.

**2. Su Putty (server):**
```bash
cd /opt/conversational-bi
git pull origin main

# Backend
cd demo/backend
.venv/bin/pip install -r requirements.txt   # solo se requirements.txt è cambiato
pm2 restart conversational-bi

# Frontend
cd ../frontend
npm install   # solo se package.json è cambiato
npm run build
sudo rsync -a --delete dist/ /var/www/clients/client0/web28/web/
```

---

## Comandi PM2 essenziali

| Comando | Cosa fa |
|---|---|
| `pm2 status` | Vedi se l'app è online/errore/restart |
| `pm2 logs conversational-bi --lines 50` | Ultimi 50 log |
| `pm2 logs conversational-bi --err --lines 30` | Solo errori |
| `pm2 restart conversational-bi` | Riavvia |
| `pm2 stop conversational-bi` | Ferma |
| `pm2 save` | Salva configurazione per riavvio automatico |

---

## File importanti sul server

| Percorso | Cosa contiene |
|---|---|
| `/opt/conversational-bi/` | Sorgente del repo (git), backend gira da qui via PM2 |
| `/opt/conversational-bi/demo/backend/.env` | Config produzione (chiave Gemini, CORS, ecc.) — **non versionato**, va ricreato manualmente ad ogni nuovo clone |
| `/opt/conversational-bi/demo/db/acme.db` | Database SQLite, versionato in git |
| `/opt/conversational-bi/demo/frontend/dist/` | Output build, **non è quello che serve Apache** — va copiato nel document root |
| `/var/www/clients/client0/web28/web/` | Document root reale servito da Apache (richiede `sudo` per scriverci) |
| `~/.pm2/logs/conversational-bi-out.log` | Log output |
| `~/.pm2/logs/conversational-bi-error.log` | Log errori |

---

## ISPConfig — Pannello di controllo

**URL:** `https://193.70.38.117:8080`

Usare ISPConfig per:
- Gestire il sito `bi.tceitalia.com` (DNS, SSL, reverse proxy `/api`)
- Rinnovare/gestire SSL (tab SSL del sito)
- Vedere i log Apache

---

## Se il sito non risponde — Checklist

1. `curl -I https://bi.tceitalia.com` → risponde il frontend?
2. `curl http://localhost:3005/health` → risponde il backend in locale?
3. `pm2 status` → conversational-bi è online?
4. `pm2 logs conversational-bi --err --lines 30` → c'è un errore (es. `GEMINI_API_KEY` mancante, `.env` non creato)?
5. `sudo systemctl status apache2` → Apache è attivo?
6. Verifica che il document root in ISPConfig punti davvero alla cartella dove hai fatto `rsync`

---

## Note specifiche di questo progetto

### `.env` non è nel repo — va ricreato ad ogni deploy da zero
A differenza degli altri progetti su questo VPS (nessun segreto, dati statici), qui il backend richiede una `GEMINI_API_KEY` reale. Il file `.env` è in `.gitignore` per non esporla mai (nemmeno nella finestra "repo temporaneamente pubblico" per il clone). Su un server nuovo va sempre ricreato manualmente da `.env.example` (sez. 1.3).

### Porta 3005 — verificare prima di ogni nuovo setup
Le porte 3000-3004 sono già occupate da altre app Node su questo VPS. Prima di avviare PM2, lancia `pm2 status` per confermare che 3005 sia ancora libera (potrebbe essere cambiato se nel frattempo sono state aggiunte altre app).

### CORS
`ALLOWED_ORIGINS` in `.env` deve includere `https://bi.tceitalia.com` (senza slash finale) — se il widget viene anche embeddato su un altro dominio (es. il sito principale tceitalia.com), aggiungilo alla lista separato da virgola.
