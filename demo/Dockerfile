# Conversational BI — backend demo (FastAPI + uvicorn)
# Contesto di build: la cartella demo/   ->   docker build -f demo/Dockerfile demo/
FROM python:3.12-slim

# stdout/stderr non bufferizzati: i log escono subito in `docker logs`
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# 1) Dipendenze Python (layer separato: si ricostruisce solo se requirements.txt cambia)
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# 2) Codice + risorse della demo (DB SQLite, layer semantico, golden questions)
COPY backend/ backend/
COPY db/ db/
COPY semantic/ semantic/
COPY eval/ eval/

WORKDIR /app/backend

EXPOSE 3005

# Docker marca il container "unhealthy" se /health non risponde 200
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:3005/health').status==200 else 1)"

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "3005"]
