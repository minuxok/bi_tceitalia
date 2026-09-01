"""Configurazione letta da variabili d'ambiente / file .env."""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent          # demo/backend
DEMO_DIR = BASE_DIR.parent                                  # demo

load_dotenv(BASE_DIR / ".env")


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


# --- Verticali demo -------------------------------------------------------
# Un "verticale" = un bundle di risorse (motore DB + viste ai_bi_* + glossario
# + domande d'oro). Il motore Text-to-SQL non cambia: si scambiano questi file.
#
# "engine" = quale database interroga il verticale:
#   sqlite -> file .db copiato nell'immagine (demo con dati congelati)
#   mysql  -> connessione a un MySQL/MariaDB REALE, sola lettura. Le viste
#             ai_bi_* NON esistono nel DB del cliente: il backend le inietta
#             come CTE (WITH ...) davanti a ogni query (vedi virtual_views.py).
_VERTICALS: dict[str, dict[str, str]] = {
    "acme": {  # gestionale / distribuzione arredo
        "engine": "sqlite",
        "db": "../db/acme.db",
        "views": "views.sql",
        "glossario": "glossario.yaml",
        "golden": "golden_questions.yaml",
    },
    "ecom": {  # e-commerce "Nuvola Shop" (abbigliamento/calzature)
        "engine": "sqlite",
        "db": "../db/nuvola.db",
        "views": "views_ecom.sql",
        "glossario": "glossario_ecom.yaml",
        "golden": "golden_questions_ecom.yaml",
    },
    "gest": {  # gestionale acquisti + preventivi su MariaDB REALE (c2gest)
        "engine": "mysql",
        "db": "",
        "views": "views_gest.sql",
        "glossario": "glossario_gest.yaml",
        "golden": "golden_questions_gest.yaml",
    },
}

_VERTICAL = (os.getenv("VERTICAL", "acme").strip().lower() or "acme")
if _VERTICAL not in _VERTICALS:
    raise SystemExit(
        f"VERTICAL='{_VERTICAL}' non valido. Valori ammessi: {', '.join(_VERTICALS)}"
    )
_BUNDLE = _VERTICALS[_VERTICAL]


class Settings:
    # verticale attivo (acme | ecom | gest), fissato all'avvio da VERTICAL
    vertical: str = _VERTICAL

    # motore del DB del verticale: "sqlite" | "mysql". DB_ENGINE forza il valore.
    db_engine: str = (os.getenv("DB_ENGINE", "").strip().lower() or _BUNDLE.get("engine", "sqlite"))

    # --- connessione MySQL/MariaDB (solo se db_engine == "mysql") ---
    mysql_host: str = os.getenv("DB_HOST", "").strip()
    mysql_port: int = _int("DB_PORT", 3306)
    mysql_name: str = os.getenv("DB_NAME", "").strip()
    mysql_user: str = os.getenv("DB_USER", "").strip()
    mysql_password: str = os.getenv("DB_PASSWORD", "")

    # --- LLM ---
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    llm_model: str = os.getenv("LLM_MODEL", "gemini/gemini-2.5-flash")
    llm_temperature: float = float(os.getenv("LLM_TEMPERATURE", "0"))
    llm_timeout_s: int = _int("LLM_TIMEOUT_S", 45)
    # tetto ampio: i modelli reasoning consumano budget prima dell'output JSON
    llm_max_tokens: int = _int("LLM_MAX_TOKENS", 4096)
    # "minimal"/"low"/"medium"/"high" — per Text-to-SQL su viste pulite basta poco
    llm_reasoning_effort: str = os.getenv("LLM_REASONING_EFFORT", "low")

    # --- DB ---
    # Vuoto = derivato dal verticale attivo. DB_PATH lo forza a un file custom.
    _db_path_raw: str = os.getenv("DB_PATH", "").strip() or _BUNDLE["db"]

    # --- limiti query ---
    sql_row_limit: int = _int("SQL_ROW_LIMIT", 1000)
    sql_timeout_s: int = _int("SQL_TIMEOUT_S", 8)

    # --- rate limiting ---
    rate_max_req: int = _int("RATE_MAX_REQ", 20)
    rate_window_s: int = _int("RATE_WINDOW_S", 600)
    daily_llm_cap: int = _int("DAILY_LLM_CAP", 800)

    # --- CORS ---
    allowed_origins: list[str] = [
        o.strip() for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",") if o.strip()
    ]

    # --- percorsi risorse ---
    log_dir: Path = (BASE_DIR / os.getenv("LOG_DIR", "./logs")).resolve()
    views_path: Path = DEMO_DIR / "semantic" / _BUNDLE["views"]
    glossario_path: Path = DEMO_DIR / "semantic" / _BUNDLE["glossario"]
    golden_path: Path = DEMO_DIR / "eval" / _BUNDLE["golden"]

    @property
    def db_path(self) -> Path:
        p = Path(self._db_path_raw)
        return p if p.is_absolute() else (BASE_DIR / p).resolve()

    @property
    def sql_dialect(self) -> str:
        """Dialetto sqlglot per validazione/serializzazione della query."""
        return "mysql" if self.db_engine == "mysql" else "sqlite"

    @property
    def mysql_ready(self) -> bool:
        return bool(self.mysql_host and self.mysql_name and self.mysql_user)

    @property
    def llm_ready(self) -> bool:
        return bool(self.gemini_api_key)


settings = Settings()

# LiteLLM legge GEMINI_API_KEY dall'ambiente: assicuriamoci sia impostata.
if settings.gemini_api_key:
    os.environ.setdefault("GEMINI_API_KEY", settings.gemini_api_key)
