from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from judo_chat.answer import REFUSAL_MESSAGE, UNAVAILABLE_MESSAGE, Answer
from judo_chat.dependencies import get_answerer, get_guardrail, get_recognizer
from judo_chat.guardrail import Category, GuardrailResult
from judo_chat.main import app
from judo_chat.normalizer import Match, Recognizer


class FakeGuardrail:
    def __init__(self, category: Category, failed: bool = False) -> None:
        self.result = GuardrailResult(category=category, reason="teste", failed=failed)

    async def classify(self, query: str) -> GuardrailResult:
        return self.result


class FakeAnswerer:
    def __init__(self) -> None:
        self.calls: list[tuple[str, list[Match]]] = []

    async def answer(self, query: str, matches: list[Match]) -> Answer:
        self.calls.append((query, matches))
        return Answer("resposta", False, 0, 0)


@pytest.fixture
def answerer() -> FakeAnswerer:
    return FakeAnswerer()


@pytest.fixture
def client(recognizer: Recognizer, answerer: FakeAnswerer) -> Iterator[TestClient]:
    app.dependency_overrides[get_recognizer] = lambda: recognizer
    app.dependency_overrides[get_answerer] = lambda: answerer
    # Sem `with`, o lifespan não roda e nenhum cliente da Anthropic é criado.
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_guardrail_failure_refuses_without_calling_llm(client: TestClient, answerer: FakeAnswerer) -> None:
    app.dependency_overrides[get_guardrail] = lambda: FakeGuardrail("fora", failed=True)
    response = client.post("/api/perguntar", json={"query": "como faço osoto-gari?"})
    assert response.status_code == 200
    body = response.json()
    assert body["refused"] is True
    assert body["answer"] == UNAVAILABLE_MESSAGE
    assert answerer.calls == []


def test_out_of_scope_gets_scope_refusal(client: TestClient, answerer: FakeAnswerer) -> None:
    app.dependency_overrides[get_guardrail] = lambda: FakeGuardrail("fora")
    body = client.post("/api/perguntar", json={"query": "qual a capital da França?"}).json()
    assert body["answer"] == REFUSAL_MESSAGE
    assert answerer.calls == []


def test_ambiguous_name_reaches_answerer_with_candidates(client: TestClient, answerer: FakeAnswerer) -> None:
    app.dependency_overrides[get_guardrail] = lambda: FakeGuardrail("tecnica")
    response = client.post("/api/perguntar", json={"query": "como faço o ashi barai?"})
    body = response.json()
    assert body["category"] == "tecnica"
    assert body["techniques_detected"] == [
        {
            "term": "ashi barai",
            "technique_ids": ["deashi-harai", "okuriashi-harai"],
            "match_type": "popular",
            "ambiguous": True,
        }
    ]
    [(_, matches)] = answerer.calls
    assert matches[0].ambiguous


def test_rejects_empty_and_long_queries(client: TestClient) -> None:
    app.dependency_overrides[get_guardrail] = lambda: FakeGuardrail("tecnica")
    assert client.post("/api/perguntar", json={"query": ""}).status_code == 422
    assert client.post("/api/perguntar", json={"query": "x" * 1001}).status_code == 422
