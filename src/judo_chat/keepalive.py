"""Mantém o cache do corpus vivo dentro de uma janela de horário.

Com TTL de 1 hora, uma leitura com max_tokens=0 a cada ~55 minutos sem perguntas renova o
cache por ~R$ 0,0023; sem ela, a primeira pergunta depois de 1 hora parado grava o corpus de
novo (~R$ 0,046). Fora da janela o cache expira, e o primeiro re-aquecimento do dia grava.
"""

import asyncio
import logging
import time
from collections.abc import Callable
from datetime import datetime
from datetime import time as clock_time
from typing import Protocol
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)


class KeepAliveTarget(Protocol):
    last_cache_touch: float | None

    async def keep_alive(self) -> tuple[int, int]: ...


def in_window(now: datetime, start: clock_time, end: clock_time) -> bool:
    """Janela [start, end); se end <= start, a janela atravessa a meia-noite."""
    current = now.time()
    if start < end:
        return start <= current < end
    return current >= start or current < end


def is_due(last_touch: float | None, now_monotonic: float, interval_s: float) -> bool:
    return last_touch is None or now_monotonic - last_touch >= interval_s


class CacheKeepAlive:
    def __init__(
        self,
        target: KeepAliveTarget,
        *,
        interval_s: float,
        start: clock_time,
        end: clock_time,
        timezone: str,
        check_every_s: float = 60.0,
        wall_clock: Callable[[ZoneInfo], datetime] = datetime.now,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self._target = target
        self._interval_s = interval_s
        self._start = start
        self._end = end
        self._zone = ZoneInfo(timezone)
        self._check_every_s = check_every_s
        self._wall_clock = wall_clock
        self._monotonic = monotonic

    async def tick(self) -> bool:
        """Re-aquece se estiver na janela e o cache estiver parado há um intervalo inteiro.
        Devolve True quando enviou a requisição."""
        if not in_window(self._wall_clock(self._zone), self._start, self._end):
            return False
        if not is_due(self._target.last_cache_touch, self._monotonic(), self._interval_s):
            return False
        try:
            await self._target.keep_alive()
        except Exception:
            # Sem re-aquecimento a próxima pergunta só paga uma gravação; não derruba a API.
            logger.exception("re-aquecimento falhou")
        return True

    async def run(self) -> None:
        while True:
            await self.tick()
            await asyncio.sleep(self._check_every_s)
