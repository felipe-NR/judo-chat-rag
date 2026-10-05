from datetime import time
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="JUDO_CHAT_", env_file=".env", extra="ignore", frozen=True)

    data_dir: Path = _ROOT / "data"
    guardrail_model: str = "claude-haiku-4-5"
    # Haiku 4.5: o modelo mais barato disponível (US$ 1/M de entrada, metade do Sonnet 5.5) e
    # tokenizador que conta o corpus com ~21% menos tokens. Para mais qualidade, use
    # claude-sonnet-5-5 com JUDO_CHAT_ANSWER_EFFORT=low e JUDO_CHAT_USE_REFUSAL_FALLBACKS=true.
    answer_model: str = "claude-haiku-4-5"
    # O Haiku 4.5 rejeita `effort`; só é enviado quando definido.
    answer_effort: Literal["low", "medium", "high"] | None = None
    answer_max_tokens: int = 4000
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
    # para os modelos da geração 5 (Sonnet 5.5, Opus 5.5); o Haiku 4.5 não aceita.
    use_refusal_fallbacks: bool = False
    # Origens que podem chamar a API pelo navegador (a página no GitHub Pages).
    cors_origins: tuple[str, ...] = ("https://felipe-nr.github.io",)


@lru_cache
def get_settings() -> Settings:
    return Settings()
