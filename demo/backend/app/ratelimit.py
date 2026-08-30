"""Rate limiting in memoria per IP (finestra scorrevole semplice)."""
from __future__ import annotations

import threading
import time
from collections import deque

from .config import settings

_lock = threading.Lock()
_hits: dict[str, deque] = {}


def consenti(chiave: str) -> tuple[bool, int]:
    """Ritorna (ammesso, secondi_di_attesa_se_bloccato)."""
    ora = time.monotonic()
    finestra = settings.rate_window_s
    with _lock:
        dq = _hits.setdefault(chiave, deque())
        while dq and dq[0] <= ora - finestra:
            dq.popleft()
        if len(dq) >= settings.rate_max_req:
            attesa = int(dq[0] + finestra - ora) + 1
            return False, attesa
        dq.append(ora)
        return True, 0
