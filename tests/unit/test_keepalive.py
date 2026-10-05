from datetime import datetime, time
from zoneinfo import ZoneInfo

from judo_chat.keepalive import CacheKeepAlive, in_window, is_due

BRT = ZoneInfo("America/Sao_Paulo")


def _at(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 10, 5, hour, minute, tzinfo=BRT)


def test_window_07_to_23() -> None:
    start, end = time(7), time(23)
    assert not in_window(_at(6, 59), start, end)
    assert in_window(_at(7), start, end)
    assert in_window(_at(22, 59), start, end)
    assert not in_window(_at(23), start, end)


def test_window_across_midnight() -> None:
    assert in_window(_at(23, 30), time(22), time(2))
    assert in_window(_at(1), time(22), time(2))
    assert not in_window(_at(12), time(22), time(2))


def test_is_due() -> None:
    assert is_due(None, 100.0, 3300)
    assert not is_due(100.0, 100.0 + 3299, 3300)
    assert is_due(100.0, 100.0 + 3300, 3300)


class FakeTarget:
    def __init__(self, last: float | None, fail: bool = False) -> None:
        self.last_cache_touch = last
        self.calls = 0
        self.fail = fail

    async def keep_alive(self) -> tuple[int, int]:
        self.calls += 1
        if self.fail:
            raise RuntimeError("API fora")
        return 34899, 0


def _keepalive(target: FakeTarget, hour: int, now_monotonic: float) -> CacheKeepAlive:
    return CacheKeepAlive(
        target,
        interval_s=3300,
        start=time(7),
        end=time(23),
        timezone="America/Sao_Paulo",
        wall_clock=lambda zone: _at(hour),
        monotonic=lambda: now_monotonic,
    )


async def test_tick_warms_when_idle_inside_window() -> None:
    target = FakeTarget(last=0.0)
    assert await _keepalive(target, hour=10, now_monotonic=3300).tick()
    assert target.calls == 1


async def test_tick_skips_recent_traffic_and_night() -> None:
    recent = FakeTarget(last=1000.0)
    assert not await _keepalive(recent, hour=10, now_monotonic=1000 + 600).tick()
    night = FakeTarget(last=None)
    assert not await _keepalive(night, hour=3, now_monotonic=10_000).tick()
    assert recent.calls == night.calls == 0


async def test_tick_survives_api_errors() -> None:
    target = FakeTarget(last=None, fail=True)
    assert await _keepalive(target, hour=10, now_monotonic=10_000).tick()
