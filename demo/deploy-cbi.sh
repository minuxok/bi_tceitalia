#!/bin/bash
# =====================================================================
# Deploy del BACKEND Conversational_BI come container Docker sul VPS.
#
# Tre verticali = TRE container dalla STESSA immagine (stesso codice,
# env VERTICAL diverso):
#     conversational-bi        VERTICAL=acme  127.0.0.1:3005 -> :3005  (SQLite)
#     conversational-bi-ecom   VERTICAL=ecom  127.0.0.1:3006 -> :3005  (SQLite)
#     conversational-bi-gest   VERTICAL=gest  127.0.0.1:3007 -> :3005  (MySQL reale)
# La porta INTERNA resta 3005 per tutti (Dockerfile invariato); cambia solo
# la porta pubblicata sull'host. Il reverse proxy Apache instrada
# /api/ -> 3005, /api-ecom/ -> 3006, /api-gest/ -> 3007 (vedi docs/SERVER.md).
#
# Uso (da Putty, sul server):
#     ~/deploy-cbi.sh                # symlink a questo file
#     /opt/conversational-bi/demo/deploy-cbi.sh
#
# Cosa fa:
#   1. allinea il repo (e questo script) all'ultima main, poi si ri-esegue
#   2. builda la nuova immagine (i container vecchi restano su: nessun downtime)
#   3. mette in PAUSA l'Agent AEGIS per lo swap dei container
#   4. sostituisce OGNI container (rm -f + run, finestra ~1s ciascuno)
#   5. aspetta l'healthcheck e stampa /healthz di ogni istanza
#   6. riaccende l'Agent AEGIS (anche se qualcosa fallisce, via trap)
#
# Il FRONTEND non e' gestito qui: vedi docs/SERVER.md sezione 2
# (git pull + npm run build + rsync). Build con:
#   VITE_API_BASE_GESTIONALE=/api VITE_API_BASE_ECOMMERCE=/api-ecom npm run build
# (sono gia' i default in src/verticals.ts: senza variabili funziona comunque,
#  purche' Apache proxi /api/ e /api-ecom/).
# =====================================================================
set -euo pipefail

REPO=/opt/conversational-bi
IMAGE=conversational-bi:latest
ENV_FILE="$REPO/demo/backend/.env"
AGENT=aegis-agent
INTERNAL_PORT=3005

# verticale -> "nome_container porta_host [env-extra separati da virgola]"
# L'env-extra e' iniettato con -e su QUEL solo container (es. gest -> mysql
# reale). Le credenziali DB_HOST/DB_NAME/DB_USER/DB_PASSWORD stanno nel
# --env-file comune: acme/ecom (sqlite) le ignorano.
INSTANCES=(
  "acme conversational-bi 3005"
  "ecom conversational-bi-ecom 3006"
  "gest conversational-bi-gest 3007 DB_ENGINE=mysql"
)

cd "$REPO"

# --- 1. aggiorna repo + script, poi ri-esegui la versione fresca una volta sola
if [ "${CBI_DEPLOY_REEXEC:-}" != "1" ]; then
  git fetch origin main
  git checkout main
  git reset --hard origin/main
  export CBI_DEPLOY_REEXEC=1
  exec bash "$REPO/demo/deploy-cbi.sh" "$@"
fi

echo "==> commit in deploy: $(git log --oneline -1)"

[ -f "$ENV_FILE" ] || { echo "ERRORE: manca $ENV_FILE (vedi docs/SERVER.md 1.3)"; exit 1; }
if grep -Eq '^[[:space:]]*DB_PATH[[:space:]]*=[[:space:]]*\.\./db/' "$ENV_FILE"; then
  echo "ERRORE: $ENV_FILE fissa DB_PATH a un file specifico."
  echo "        Con due verticali DB_PATH deve essere VUOTO (lo sceglie VERTICAL)."
  echo "        Correggi la riga in:  DB_PATH="
  exit 1
fi

# --- 2. build (container vecchi ancora attivi, zero downtime in questa fase)
docker build -t "$IMAGE" -f "$REPO/demo/Dockerfile" "$REPO/demo"

# --- 3. pausa Agent AEGIS
#     AEGIS sorveglia i container CBI: se ne vede uno fermo invia un
#     "docker restart" firmato che farebbe a pugni con lo swap qui sotto.
#     Fermare l'Agent per la durata del deploy = niente heal spurio.
AGENT_WAS_ACTIVE=0
if systemctl is-active --quiet "$AGENT"; then
  AGENT_WAS_ACTIVE=1
  echo "==> pausa $AGENT (deploy in corso)"
  sudo systemctl stop "$AGENT"
fi
restart_agent() {
  if [ "$AGENT_WAS_ACTIVE" = "1" ]; then
    echo "==> riavvio $AGENT"
    sudo systemctl start "$AGENT" || true
  fi
}
trap restart_agent EXIT

# --- 4. swap di ogni container: rm -f (SIGKILL immediato) + run
for row in "${INSTANCES[@]}"; do
  read -r VERT NAME HOST_PORT EXTRA <<< "$row"
  extra_env=()
  if [ -n "${EXTRA:-}" ]; then
    IFS=',' read -ra _kv <<< "$EXTRA"
    for kv in "${_kv[@]}"; do extra_env+=(-e "$kv"); done
  fi
  echo "==> swap $NAME (VERTICAL=$VERT, 127.0.0.1:$HOST_PORT${EXTRA:+, $EXTRA})"
  docker rm -f "$NAME" 2>/dev/null || true
  docker run -d --name "$NAME" --restart unless-stopped \
    -e "VERTICAL=$VERT" "${extra_env[@]}" \
    -p "127.0.0.1:$HOST_PORT:$INTERNAL_PORT" \
    --env-file "$ENV_FILE" "$IMAGE"
done

# --- 5. attendi healthcheck di tutti
echo "==> attendo healthcheck..."
for row in "${INSTANCES[@]}"; do
  read -r VERT NAME HOST_PORT <<< "$row"
  for _ in $(seq 1 20); do
    status=$(docker inspect -f '{{.State.Health.Status}}' "$NAME" 2>/dev/null || echo unknown)
    [ "$status" = "healthy" ] && break
    sleep 2
  done
  docker ps --filter "name=$NAME" --format '{{.Names}}  {{.Status}}'
  echo "--- health $NAME (VERTICAL=$VERT) ---"
  curl -s "http://127.0.0.1:$HOST_PORT/healthz"; echo
done

# --- 6. l'Agent riparte dal trap EXIT
