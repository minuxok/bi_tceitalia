"""Wrapper LiteLLM: una chiamata, provider sostituibile via config."""
from __future__ import annotations

from .config import settings
from .prompt import build_messages, parse_llm_json


class LLMError(RuntimeError):
    pass


def genera_interpretazione(domanda: str) -> dict:
    """Chiede al modello di interpretare la domanda. Ritorna il dict JSON già parsato."""
    if not settings.llm_ready:
        raise LLMError("LLM non configurato: manca GEMINI_API_KEY nel file .env")

    import litellm  # import ritardato: pesante

    litellm.drop_params = True
    messages = build_messages(domanda)
    try:
        resp = litellm.completion(
            model=settings.llm_model,
            messages=messages,
            temperature=settings.llm_temperature,
            timeout=settings.llm_timeout_s,
            response_format={"type": "json_object"},
            # I modelli "reasoning" (Gemini 3.x) spendono token in ragionamento
            # prima dell'output: serve un tetto ampio o il JSON esce troncato.
            max_tokens=settings.llm_max_tokens,
            reasoning_effort=settings.llm_reasoning_effort,
        )
    except Exception as e:  # noqa: BLE001 - vogliamo un messaggio pulito al client
        raise LLMError(f"Errore nella chiamata al modello: {e}") from e

    raw = (resp["choices"][0]["message"]["content"] or "").strip()
    try:
        data = parse_llm_json(raw)
    except Exception as e:  # noqa: BLE001
        raise LLMError(f"Risposta del modello non in formato JSON valido: {e}") from e

    data.setdefault("tipo", "query")
    data.setdefault("viz", {})
    return data
