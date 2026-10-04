from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="JUDO_CHAT_", env_file=".env", extra="ignore", frozen=True)

    data_dir: Path = _ROOT / "data"
    guardrail_model: str = "claude-haiku-4-5"
    answer_model: str = "claude-sonnet-5-5"
    answer_effort: Literal["low", "medium", "high"] = "low"
    answer_max_tokens: int = 4000
    guardrail_timeout_s: float = 15.0
    answer_timeout_s: float = 90.0
    cache_ttl: Literal["5m", "1h"] = "1h"
    # Retry server-side num modelo alternativo quando o Sonnet 5.5 recusa por política.
    use_refusal_fallbacks: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
