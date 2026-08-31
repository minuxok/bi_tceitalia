# Conversational BI — Gestione Server VPS (OVH)

> **VPS:** `193.70.38.117` · Ubuntu · ISPConfig (stesso VPS di tagnest, cultural-invaders, visitnove-api, industriale-3d, poloniato100)
> **Dominio:** `https://bi.tceitalia.com`
> **App:** `/opt/conversational-bi` — backend FastAPI (Python/uvicorn) in **container Docker** dal 31/08/2026 (prima era PM2 — vedi §"Procedura per Docker"), frontend build statica Vite
> **Porta backend:** `3005` (3000=tagnest, 3001=cultural-invaders-next, 3002/3003=visitnove-api e un'altra app, 3004=industriale-3d — verifica con `pm2 status` prima di assumerla libera)
> **Database:** SQLite, file `demo/db/acme.db` dentro il repo
> **Accesso SSH:** Putty → `193.70.38.117` porta `22`, utente da definire (stesso utente delle altre app su questo VPS, es. `ubuntu`)
> **Repo:** https://github.com/minuxok/bi_tceitalia — branch `dev` (attivo), `main` (baseline)

A differenza di poloniato100 (SPA statica pura, nessun processo a runtime), questa app **ha un backend Python persistente** (FastAPI + LLM via LiteLLM), quindi il pattern è ibrido:
- **Frontend** (`demo/frontend/dist`) → file statici, serviti da Apache come document root (come poloniato100). Deploy manuale: `git pull` + `npm run build` + `rsync` (§2).
- **Backend** (`demo/backend`) → **container Docker** su `127.0.0.1:3005` (dal 31/08/2026; prima era PM2), esposto solo su `/api` via reverse proxy Apache. Deploy con `~/deploy-cbi.sh` (§"Procedura per Docker"). Sorvegliato da AEGIS.

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
ProxyPass /api/ http://localhost:3005/
ProxyPassReverse /api/ http://localhost:3005/
```

> ⚠️ Slash finale obbligatorio e coerente su entrambi i lati (`/api/` non `/api`): senza, Apache non strippa il prefisso e il backend riceve `/api/health` invece di `/health`, rispondendo 404 `{"detail":"Not Found"}` (visto in produzione il 30/08/2026).

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

> ⚠️ Il **backend** ora si aggiorna con Docker, non con `pm2 restart` — vedi §"Procedura per Docker".
> Questa sezione resta valida per il **frontend**.

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

# Backend  → NON più così: usa ~/deploy-cbi.sh (§"Procedura per Docker")

# Frontend
cd demo/frontend
npm install   # solo se package.json è cambiato
npm run build
sudo rsync -a --delete dist/ /var/www/clients/client0/web28/web/
```

---

## Procedura per Docker

> Dal **31/08/2026** il **backend** non gira più con PM2 ma dentro un **container Docker**.
> Motivo: così **AEGIS** (sistema di monitoraggio sullo stesso VPS, `/opt/aegis`) può
> sorvegliarlo e riavviarlo da solo se cade. Il **frontend** è invariato (build statica
> Vite servita da Apache). Anche il reverse proxy ISPConfig `/api/` → `http://localhost:3005/`
> non cambia: il container pubblica sulla stessa porta `127.0.0.1:3005`.

### Cosa c'è nel repo

| File | Ruolo |
|---|---|
| `demo/Dockerfile` | Ricetta immagine: `python:3.12-slim` → `pip install -r backend/requirements.txt` → copia `backend/` + `db/` + `semantic/` + `eval/` → avvia `uvicorn app.main:app` su `:3005`. Con `HEALTHCHECK` su `/health`. |
| `demo/.dockerignore` | Esclude dall'immagine `.venv`, `logs/`, `__pycache__`, e soprattutto il **`.env`** — il segreto NON entra nell'immagine |
| `demo/deploy-cbi.sh` | **Script di deploy versionato**: allinea main → build immagine → pausa Agent AEGIS → swap container → healthcheck → riaccende l'Agent. Sul server `~/deploy-cbi.sh` è un symlink a questo file. |

`GEMINI_API_KEY` e le altre variabili arrivano a runtime da
`/opt/conversational-bi/demo/backend/.env` via `--env-file`. Quel file va comunque
creato a mano sul server (come prima, §1.3) e non passa da git.

### AEGIS sorveglia questo container

Il servizio è registrato in AEGIS (tabella `services` del DB `aegis`) con
`container_name = 'conversational-bi'`. Conseguenze operative:

- L'**Agent** (`systemd: aegis-agent`) manda lo stato dei container al Core ogni **15s**.
- Se vede il container in stato `≠ running`, il Core apre un incidente `critical` e
  invia all'Agent un comando firmato `restart_container` → `docker restart conversational-bi`.
- **Circuit breaker**: 3 remediation automatiche in 60 min → il servizio va in
  `quarantined` per un'ora (stop auto-restart, solo alert).

Perciò lo swap del container durante un deploy **non va fatto a mano con
`docker stop/rm/run`** mentre l'Agent è attivo: un tick a metà swap fa partire un
`docker restart` che entra in conflitto (caso peggiore: riavvia il container
vecchio, il tuo `rm` fallisce, resti sull'immagine vecchia). Lo script
`deploy-cbi.sh` **mette in pausa l'Agent per la durata dello swap** e lo riaccende
alla fine (anche in caso di errore, via `trap`).

Verificare che il servizio sia quello atteso:

```bash
sudo -u postgres psql -d aegis -c \
  "SELECT name, container_name, quarantined_until FROM services;"
```

### Prima volta sul server (una tantum)

```bash
cd /opt/conversational-bi
git fetch --prune && git checkout main && git branch --set-upstream-to=origin/main
git pull

# togli il vecchio processo PM2 (lo sostituisce il container), se ancora presente
pm2 delete conversational-bi 2>/dev/null && pm2 save || true

# lo script di deploy è versionato nel repo: basta il symlink in home
ln -sf /opt/conversational-bi/demo/deploy-cbi.sh ~/deploy-cbi.sh

# prima esecuzione
~/deploy-cbi.sh
```

> `deploy-cbi.sh` usa `sudo systemctl stop/start aegis-agent`: se `sudo` chiede la
> password è normale, digitala. (Per evitarlo si può aggiungere una regola
> `NOPASSWD` limitata a quei due comandi in `/etc/sudoers.d/`.)

### Aggiornare il backend (ogni volta che hai novità)

```bash
# 1. sul PC (dopo aver portato le modifiche su main)
git push origin main

# 2. su Putty
~/deploy-cbi.sh
```

Lo script fa da solo: `git fetch/checkout/reset` su `origin/main` → si ri-esegue nella
versione aggiornata → `docker build` → pausa `aegis-agent` → `docker rm -f` + `docker run`
→ attende `healthy` → stampa `/health` e `/domande` → riaccende `aegis-agent`.

Il **frontend** si aggiorna a parte come nella §2 (`git pull` + `npm run build` + `rsync`):
Docker riguarda **solo il backend**.

> ⚠️ **Non incollare blocchi multi-riga con `sudo` dentro** direttamente in Putty: se
> `sudo` apre il prompt della password, "mangia" le righe incollate dopo e alcuni
> comandi (es. `git pull`) non partono, senza errori evidenti. Usa `deploy-cbi.sh`,
> oppure incolla **un comando alla volta**.

### Comandi Docker essenziali

| Comando | Cosa fa |
|---|---|
| `docker ps` | Container attivi — cerca `conversational-bi`, stato `Up (healthy)` |
| `docker logs conversational-bi --tail 50` | Ultimi log del backend |
| `docker logs -f conversational-bi` | Log in tempo reale (Ctrl-C per uscire) |
| `docker inspect -f '{{.Config.Image}} {{.Created}}' conversational-bi` | Da quale immagine e quando è nato il container attivo |
| `docker restart conversational-bi` | Riavvio manuale (l'Agent AEGIS non se ne lamenta: torna `running` subito) |
| `docker image prune -f` | Cancella le immagini vecchie senza nome (ogni tanto, libera spazio) |

### Rollback a PM2 (emergenza)

```bash
sudo systemctl stop aegis-agent          # evita che AEGIS tenti di risollevare il container
docker rm -f conversational-bi
cd /opt/conversational-bi/demo/backend
pm2 start .venv/bin/python3 --name conversational-bi --cwd "$(pwd)" \
  -- -m uvicorn app.main:app --host 127.0.0.1 --port 3005
pm2 save
# lasciare aegis-agent fermo finché non si tolge la riga da `services` o si aggiorna
# `container_name`, altrimenti apre incidenti su un container che non esiste più
```

### Note

- **Non modificare il codice sulla VPS**: `deploy-cbi.sh` fa `git reset --hard origin/main` e sovrascrive tutto. Sempre locale → push su `main` → `~/deploy-cbi.sh`.
- **Nuove variabili d'ambiente**: se le aggiungi in `.env.example`, aggiungile anche a
  `/opt/conversational-bi/demo/backend/.env` sul server (non è nell'immagine).
- **`acme.db`** e i file `eval/` / `semantic/` sono dentro l'immagine: ogni modifica
  richiede un nuovo `docker build` (lo fa già `deploy-cbi.sh`).
- **Se in futuro AEGIS monitora più container su questo VPS**, invece di fermare tutto
  l'Agent conviene quarantenare il solo servizio CBI per pochi minuti
  (`UPDATE services SET quarantined_until = now() + interval '5 min' WHERE container_name = 'conversational-bi';`).

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
| `/opt/conversational-bi/` | Sorgente del repo (git). Da qui `deploy-cbi.sh` fa `docker build` del backend |
| `/opt/conversational-bi/demo/Dockerfile` · `demo/.dockerignore` | Ricetta immagine del backend (versionati) |
| `/opt/conversational-bi/demo/backend/.env` | Config produzione (chiave Gemini, CORS, ecc.) — **non versionato**, passato al container con `--env-file`, va ricreato manualmente ad ogni nuovo clone |
| `/opt/conversational-bi/demo/db/acme.db` | Database SQLite, versionato in git, copiato dentro l'immagine |
| `/opt/conversational-bi/demo/frontend/dist/` | Output build frontend, **non è quello che serve Apache** — va copiato nel document root |
| `/var/www/clients/client0/web28/web/` | Document root reale servito da Apache (richiede `sudo` per scriverci) |
| `~/deploy-cbi.sh` | Symlink a `/opt/conversational-bi/demo/deploy-cbi.sh` (script di deploy versionato: build + pausa AEGIS + swap container) |
| `docker logs conversational-bi` | Log del backend (sostituisce i vecchi `~/.pm2/logs/conversational-bi-*.log`) |
| `/opt/aegis`, `/opt/aegis-agent` | AEGIS: Core (PM2 `aegis-core`) e Agent (`systemd: aegis-agent`) che sorveglia il container. Vedi `AEGIS/docs/SERVER.md` |

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
3. `docker ps` → il container `conversational-bi` è `Up (healthy)`?
4. `docker logs conversational-bi --tail 40` → c'è un errore (es. `GEMINI_API_KEY` mancante, `.env` non passato)?
5. `sudo systemctl is-active aegis-agent` → se `inactive` (es. un deploy interrotto prima del riavvio), `sudo systemctl start aegis-agent`
6. `sudo -u postgres psql -d aegis -c "SELECT name, quarantined_until FROM services WHERE container_name='conversational-bi';"` → se `quarantined_until` è nel futuro, l'auto-heal è sospeso: `... SET quarantined_until = NULL ...` per riattivarlo
7. `sudo systemctl status apache2` → Apache è attivo?
8. Verifica che il document root in ISPConfig punti davvero alla cartella dove hai fatto `rsync`

---

## Note specifiche di questo progetto

### `.env` non è nel repo — va ricreato ad ogni deploy da zero
A differenza degli altri progetti su questo VPS (nessun segreto, dati statici), qui il backend richiede una `GEMINI_API_KEY` reale. Il file `.env` è in `.gitignore` per non esporla mai (nemmeno nella finestra "repo temporaneamente pubblico" per il clone). Su un server nuovo va sempre ricreato manualmente da `.env.example` (sez. 1.3).

### Porta 3005 — verificare prima di ogni nuovo setup
Le porte 3000-3004 sono già occupate da altre app Node su questo VPS. Prima di avviare PM2, lancia `pm2 status` per confermare che 3005 sia ancora libera (potrebbe essere cambiato se nel frattempo sono state aggiunte altre app).

### CORS
`ALLOWED_ORIGINS` in `.env` deve includere `https://bi.tceitalia.com` (senza slash finale) — se il widget viene anche embeddato su un altro dominio (es. il sito principale tceitalia.com), aggiungilo alla lista separato da virgola.
