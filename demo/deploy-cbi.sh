#!/bin/bash
# =====================================================================
# Deploy del BACKEND Conversational_BI come container Docker sul VPS.
#
# Uso (da Putty, sul server):
#     ~/deploy-cbi.sh                # se ~/deploy-cbi.sh e' il symlink a questo file
#     /opt/conversational-bi/demo/deploy-cbi.sh
#
# Cosa fa:
#   1. allinea il repo (e questo script) all'ultima main, poi si ri-esegue
#   2. builda la nuova immagine (il container vecchio resta su: nessun downtime)
#   3. mette in PAUSA l'Agent AEGIS per lo swap del container
#   4. sostituisce il container (rm -f + run, finestra ~1s)
#   5. aspetta l'healthcheck e stampa /health
#   6. riaccende l'Agent AEGIS (anche se qualcosa fallisce, via trap)
#
# Il FRONTEND non e' gestito qui: vedi docs/SERVER.md sezione 2
# (git pull + npm run build + rsync).
# =====================================================================
set -euo pipefail

REPO=/opt/conversational-bi
IMAGE=conversational-bi:latest
NAME=conversational-bi
PUBLISH=127.0.0.1:3005:3005
AGENT=aegis-agent

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

# --- 2. build (container vecchio ancora attivo, zero downtime in questa fase)
docker build -t "$IMAGE" -f "$REPO/demo/Dockerfile" "$REPO/demo"

# --- 3. pausa Agent AEGIS
#     AEGIS sorveglia il container "conversational-bi": se lo vede fermo invia
#     un "docker restart" firmato che farebbe a pugni con lo swap qui sotto
#     (caso peggiore: riavvia il container vecchio e questo script si pianta).
#     Fermare l'Agent per ~30s = niente report = niente incidente = niente heal.
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

# --- 4. swap container: rm -f (SIGKILL immediato) + run
docker rm -f "$NAME" 2>/dev/null || true
docker run -d --name "$NAME" --restart unless-stopped \
  -p "$PUBLISH" --env-file "$REPO/demo/backend/.env" "$IMAGE"

# --- 5. attendi healthcheck
echo "==> attendo healthcheck..."
for _ in $(seq 1 20); do
  status=$(docker inspect -f '{{.State.Health.Status}}' "$NAME" 2>/dev/null || echo unknown)
  [ "$status" = "healthy" ] && break
  sleep 2
done
docker ps --filter "name=$NAME" --format '{{.Names}}  {{.Status}}'
echo "--- health ---"
curl -s http://127.0.0.1:3005/health; echo
echo "--- domande (controllo testo) ---"
curl -s http://127.0.0.1:3005/domande | head -c 200; echo

# --- 6. l'Agent riparte dal trap EXIT
