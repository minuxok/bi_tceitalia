"""Log strutturato JSONL di ogni interazione + contatore giornaliero LLM."""
from __future__ import annotations

import hashlib
import json
import threading
from datetime import date, datetime, timezone

from .config import settings

_lock = threading.Lock()
_contatore = {"giorno": "", "n": 0}


def _oggi() -> str:
    return date.today().isoformat()


def hash_ip(ip: str) -> str:
    return hashlib.sha256(f"acme-demo|{ip}".encode()).hexdigest()[:16]


def incrementa_llm() -> int:
    with _lock:
        if _contatore["giorno"] != _oggi():
            _contatore["giorno"] = _oggi()
            _contatore["n"] = 0
        _contatore["n"] += 1
        return _contatore["n"]


def budget_llm_disponibile() -> bool:
    if settings.daily_llm_cap <= 0:
        return True
    with _lock:
        if _contatore["giorno"] != _oggi():
            return True
        return _contatore["n"] < settings.daily_llm_cap


def registra(evento: dict) -> None:
    settings.log_dir.mkdir(parents=True, exist_ok=True)
    evento = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), **evento}
    path = settings.log_dir / f"interazioni-{_oggi()}.jsonl"
    line = json.dumps(evento, ensure_ascii=False)
    with _lock, open(path, "a", encoding="utf-8") as f:
        f.write(line + "\n")
