"""Verifica l'endpoint /healthz (schema AEGIS §2), senza rete.

    cd demo/backend
    python test_healthz.py

Copre i tre stati (healthy / degraded / unhealthy) manovrando le env che
`app.config.Settings` legge all'import: ogni caso gira in un sottoprocesso
pulito, perché Settings è valutato una volta sola per processo.
"""
from __future__ import annotations

import json
import subprocess
import sys

_SNIPPET = (
    "import json;"
    "from app.health import build_healthz;"
    "b,c=build_healthz();"
    "print(json.dumps({'http':c,'status':b['status'],"
    "'db':b['checks']['database']['status'],"
    "'llm':b['checks']['llm_provider']['status'],"
    "'keys':sorted(b)}))"
)

# nome caso -> (env aggiuntive, http atteso, status atteso, db atteso, llm atteso)
CASI = {
    "healthy (sqlite ok, llm configurato)": (
        {"VERTICAL": "acme", "GEMINI_API_KEY": "x"}, 200, "healthy", "ok", "ok"),
    "degraded (llm non configurato)": (
        {"VERTICAL": "acme", "GEMINI_API_KEY": ""}, 200, "degraded", "ok", "warn"),
    "unhealthy (file sqlite non apribile)": (
        {"VERTICAL": "acme", "GEMINI_API_KEY": "x", "DB_PATH": "/nope/missing.db"},
        503, "unhealthy", "error", "ok"),
    "degraded (mysql esterno giù, non 503)": (
        {"DB_ENGINE": "mysql", "DB_HOST": "10.255.255.1", "DB_NAME": "x",
         "DB_USER": "x", "DB_PASSWORD": "x", "GEMINI_API_KEY": "x"},
        200, "degraded", "error", "ok"),
}

SCHEMA_KEYS = ["checks", "environment", "service", "status", "timestamp", "version"]


def main() -> int:
    import os

    ko = 0
    for nome, (env, http, status, db, llm) in CASI.items():
        res = subprocess.run(
            [sys.executable, "-c", _SNIPPET],
            capture_output=True, text=True, env={**os.environ, **env},
        )
        if res.returncode != 0:
            print(f"[{nome}] CRASH\n{res.stderr}")
            ko += 1
            continue
        got = json.loads(res.stdout.strip().splitlines()[-1])
        errori = []
        if got["http"] != http:
            errori.append(f"http {got['http']} != {http}")
        if got["status"] != status:
            errori.append(f"status {got['status']!r} != {status!r}")
        if got["db"] != db:
            errori.append(f"db {got['db']!r} != {db!r}")
        if got["llm"] != llm:
            errori.append(f"llm {got['llm']!r} != {llm!r}")
        if got["keys"] != SCHEMA_KEYS:
            errori.append(f"chiavi {got['keys']} != {SCHEMA_KEYS}")
        if errori:
            print(f"[{nome}] KO: {'; '.join(errori)}")
            ko += 1
        else:
            print(f"[{nome}] ok  (http={http}, status={status})")

    print()
    if ko:
        print(f"{ko} caso/i FALLITI")
        return 1
    print("TUTTO OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
