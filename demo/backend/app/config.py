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


class Settings:
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
    _db_path_raw: str = os.getenv("DB_PATH", "../db/acme.db")

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
    views_path: Path = DEMO_DIR / "semantic" / "views.sql"
    glossario_path: Path = DEMO_DIR / "semantic" / "glossario.yaml"
    golden_path: Path = DEMO_DIR / "eval" / "golden_questions.yaml"

    @property
    def db_path(self) -> Path:
        p = Path(self._db_path_raw)
        return p if p.is_absolute() else (BASE_DIR / p).resolve()

    @property
    def llm_ready(self) -> bool:
        return bool(self.gemini_api_key)


settings = Settings()

# LiteLLM legge GEMINI_API_KEY dall'ambiente: assicuriamoci sia impostata.
if settings.gemini_api_key:
    os.environ.setdefault("GEMINI_API_KEY", settings.gemini_api_key)
