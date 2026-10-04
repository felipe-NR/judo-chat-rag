from dataclasses import dataclass

import anthropic
import httpx
import pytest

from judo_chat.guardrail import Guardrail, GuardrailOutput


@dataclass
class FakeParsed:
    stop_reason: str
    parsed_output: GuardrailOutput | None


class FakeMessages:
    def __init__(self, result: FakeParsed | Exception) -> None:
        self.result = result
        self.calls: list[dict[str, object]] = []

    async def parse(self, **kwargs: object) -> FakeParsed:
        self.calls.append(kwargs)
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


class FakeClient:
    def __init__(self, result: FakeParsed | Exception) -> None:
        self.messages = FakeMessages(result)

    def with_options(self, **_: object) -> "FakeClient":
        return self


def _guardrail(result: FakeParsed | Exception) -> tuple[Guardrail, FakeClient]:
    client = FakeClient(result)
    return Guardrail(client, "claude-haiku-4-5", 5.0), client  # type: ignore[arg-type]


async def test_allows_in_scope_category() -> None:
    guardrail, client = _guardrail(FakeParsed("end_turn", GuardrailOutput(category="tecnica", reason="técnica")))
    result = await guardrail.classify("como faço osoto-gari?")
    assert result.allowed and result.category == "tecnica" and not result.failed
    sent = client.messages.calls[0]["messages"]
    assert sent == [{"role": "user", "content": "<pergunta>\ncomo faço osoto-gari?\n</pergunta>"}]


@pytest.mark.parametrize(
    "result",
    [
        anthropic.APIConnectionError(request=httpx.Request("POST", "https://api.anthropic.com")),
        anthropic.APITimeoutError(request=httpx.Request("POST", "https://api.anthropic.com")),
        RuntimeError("bug"),
        FakeParsed("max_tokens", None),
        FakeParsed("refusal", None),
        FakeParsed("end_turn", None),
    ],
)
async def test_fails_closed(result: FakeParsed | Exception) -> None:
    guardrail, _ = _guardrail(result)
    verdict = await guardrail.classify("qualquer coisa")
    assert verdict.category == "fora"
    assert verdict.failed
    assert not verdict.allowed
