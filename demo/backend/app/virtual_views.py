"""Viste "virtuali" ai_bi_* per i verticali su DB reale (engine = mysql).

Le viste NON esistono nel database del cliente (utente in sola lettura, nessun
CREATE VIEW). Sono definite in demo/semantic/views_<vert>.sql come
`CREATE OR REPLACE VIEW ai_bi_x AS SELECT ...;` e qui vengono:

  * lette e spezzate in coppie (nome, corpo SELECT);
  * anteposte come CTE (WITH ...) a ogni query generata dall'LLM, così che
    `FROM ai_bi_x` si risolva senza toccare il DB del cliente.

L'ordine nel file è l'ordine nel WITH: una vista che ne referenzia un'altra va
dopo. Al momento tutte partono dalle tabelle base.
"""
from __future__ import annotations

import re
from functools import lru_cache

from .config import settings

_VIEW_RE = re.compile(
    r"CREATE\s+(?:OR\s+REPLACE\s+)?VIEW\s+(\w+)\s+AS\s+(.*?)\s*;",
    re.IGNORECASE | re.DOTALL,
)


@lru_cache(maxsize=1)
def load_view_defs() -> list[tuple[str, str]]:
    """[(nome_vista, corpo_select), ...] nell'ordine del file, commenti '--' rimossi."""
    raw = settings.views_path.read_text(encoding="utf-8")
    no_comments = "\n".join(
        line for line in raw.splitlines() if not line.lstrip().startswith("--")
    )
    defs = [(m.group(1).strip(), m.group(2).strip()) for m in _VIEW_RE.finditer(no_comments)]
    if not defs:
        raise RuntimeError(f"Nessuna vista ai_bi_* trovata in {settings.views_path}")
    return defs


def view_names() -> list[str]:
    return [n for n, _ in load_view_defs()]


@lru_cache(maxsize=1)
def _cte_prefix() -> str:
    parti = ",\n".join(f"{nome} AS (\n{corpo}\n)" for nome, corpo in load_view_defs())
    return f"WITH {parti}\n"


def wrap_with_ctes(user_sql: str) -> str:
    """Antepone le viste ai_bi_* come CTE. Se la query ha già un proprio WITH,
    le CTE delle viste vengono inserite subito dopo `WITH [RECURSIVE]`."""
    s = user_sql.strip()
    m = re.match(r"(?is)^with\s+(recursive\s+)?", s)
    if m:
        head = "WITH " + (m.group(1) or "")
        resto = s[m.end():]
        parti = ",\n".join(f"{nome} AS (\n{corpo}\n)" for nome, corpo in load_view_defs())
        return f"{head}{parti},\n{resto}"
    return _cte_prefix() + s
