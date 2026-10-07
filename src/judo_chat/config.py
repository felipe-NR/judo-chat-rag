from datetime import time
from functools import lru_cache
from pathlib import Path
from typing import Literal, Self

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="JUDO_CHAT_", env_file=".env", extra="ignore", frozen=True)

    data_dir: Path = _ROOT / "data"
    guardrail_model: str = "claude-haiku-5-5"
    # O pensamento do Haiku 5.5 vem ligado e conta no max_tokens: com 300 a classificação
    # podia acabar antes do JSON.
    guardrail_effort: Literal["low", "medium", "high"] = "low"
    guardrail_max_tokens: int = 1024
    # Haiku 5.5: o modelo mais barato disponível (US$ 0,10/M de entrada e US$ 0,50/M de saída
    # com prompt de até 100 mil tokens). Para mais qualidade, use claude-sonnet-5-5 com
    # JUDO_CHAT_ANSWER_EFFORT=low e JUDO_CHAT_USE_REFUSAL_FALLBACKS=true.
    answer_model: str = "claude-haiku-5-5"
    # O effort faz parte do prefixo cacheado; None não envia o parâmetro (o Haiku 4.5 o rejeita).
    # Sem ele o Haiku 5.5 usa medium.
    answer_effort: Literal["low", "medium", "high"] | None = "low"
    # Cabe o pensamento além da resposta.
    answer_max_tokens: int = 8000
    guardrail_timeout_s: float = 15.0
    answer_timeout_s: float = 90.0
    # 1h combinado com o re-aquecimento: grava 1 vez por dia (2x o preço de entrada) e lê a
    # cada ~55 min parado (0,1x). Com 5 min seriam ~13 re-aquecimentos por hora.
    cache_ttl: Literal["5m", "1h"] = "1h"
    keepalive_enabled: bool = True
    # Abaixo dos 60 min do TTL, com folga para a checagem que roda a cada minuto.
    keepalive_interval_s: float = 55 * 60
    keepalive_window_start: time = time(7, 0)
    keepalive_window_end: time = time(23, 0)
    keepalive_timezone: str = "America/Sao_Paulo"
    # Retry server-side num modelo alternativo quando o modelo recusa por política. Só vale
    # para o Sonnet 5.5 e o Opus 5.5; o Haiku não tem fallback no servidor.
    use_refusal_fallbacks: bool = False
    # Origens que podem chamar a API pelo navegador (a página no GitHub Pages).
    cors_origins: tuple[str, ...] = ("https://felipe-nr.github.io",)

    @model_validator(mode="after")
    def _fallbacks_need_a_supported_model(self) -> Self:
        if self.use_refusal_fallbacks and self.answer_model.startswith("claude-haiku"):
            raise ValueError("JUDO_CHAT_USE_REFUSAL_FALLBACKS não vale para o Haiku, que não tem fallback no servidor")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
