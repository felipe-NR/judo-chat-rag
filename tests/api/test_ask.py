from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from judo_chat.answer import REFUSAL_MESSAGE, UNAVAILABLE_MESSAGE, Answer, Turn
from judo_chat.corpus.models import Corpus
from judo_chat.dependencies import get_answerer, get_corpus, get_guardrail, get_recognizer
from judo_chat.guardrail import Category, GuardrailResult
from judo_chat.main import app
from judo_chat.normalizer import Match, Recognizer


class FakeGuardrail:
    def __init__(self, category: Category, failed: bool = False) -> None:
        self.result = GuardrailResult(category=category, reason="teste", failed=failed)
        self.calls: list[tuple[str, list[str], list[str]]] = []

    async def classify(self, query: str, history: list[str], techniques: list[str]) -> GuardrailResult:
        self.calls.append((query, list(history), list(techniques)))
        return self.result


class FakeAnswerer:
    def __init__(self, text: str = "resposta") -> None:
        self.text = text
        self.calls: list[tuple[str, list[Match], list[Turn]]] = []

    async def answer(self, query: str, matches: list[Match], history: list[Turn]) -> Answer:
        self.calls.append((query, matches, list(history)))
        return Answer(self.text, False, 0, 0)


@pytest.fixture
def answerer() -> FakeAnswerer:
    return FakeAnswerer()


@pytest.fixture
def client(recognizer: Recognizer, answerer: FakeAnswerer, corpus: Corpus) -> Iterator[TestClient]:
    app.dependency_overrides[get_recognizer] = lambda: recognizer
    app.dependency_overrides[get_answerer] = lambda: answerer
    app.dependency_overrides[get_corpus] = lambda: corpus
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
    [(_, matches, _)] = answerer.calls
    assert matches[0].ambiguous
    group = body["video_groups"][0]
    assert group["technique"] == "Deashi-harai" and group["anchor"] is None
    assert group["videos"][0] == {"url": "https://youtu.be/4BUUvqxi_Kk", "kodokan": True}


def test_rejects_empty_and_long_queries(client: TestClient) -> None:
    app.dependency_overrides[get_guardrail] = lambda: FakeGuardrail("tecnica")
    assert client.post("/api/perguntar", json={"query": ""}).status_code == 422
    assert client.post("/api/perguntar", json={"query": "x" * 1001}).status_code == 422


def test_cors_preflight_allows_github_pages(client: TestClient) -> None:
    response = client.options(
        "/api/perguntar",
        headers={
            "Origin": "https://felipe-nr.github.io",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,ngrok-skip-browser-warning",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://felipe-nr.github.io"


def test_page_and_config_are_served(client: TestClient) -> None:
    assert "Judô Chat" in client.get("/").text
    assert 'JUDO_CHAT_API_URL = ""' in client.get("/config.js").text


def test_videos_follow_the_techniques_presented_in_the_answer(client: TestClient, answerer: FakeAnswerer) -> None:
    app.dependency_overrides[get_guardrail] = lambda: FakeGuardrail("tecnica")
    answerer.text = "Contragolpes:\n1. **Uchi-mata-gaeshi**: texto\n2. **Uchi-mata-sukashi**: texto"
    body = client.post("/api/perguntar", json={"query": "contra ataques de uchimata"}).json()
    groups = [(g["technique"], g["anchor"]) for g in body["video_groups"]]
    assert groups[:2] == [("Uchi-mata-gaeshi", "Uchi-mata-gaeshi"), ("Uchi-mata-sukashi", "Uchi-mata-sukashi")]
    assert ("Uchi-mata", None) in groups
    assert all(g["videos"][0]["kodokan"] for g in body["video_groups"])


def test_follow_up_uses_history(client: TestClient, answerer: FakeAnswerer) -> None:
    guardrail = FakeGuardrail("tecnica")
    app.dependency_overrides[get_guardrail] = lambda: guardrail
    history = [
        {"role": "usuario", "text": "contra ataques de uchimata"},
        {"role": "assistente", "text": "O Uchi-mata-sukashi..."},
    ]
    client.post("/api/perguntar", json={"query": "não é esse, liste outros", "history": history})
    [(_, matches, sent_history)] = answerer.calls
    assert [m.technique_ids for m in matches] == [("uchi-mata",)]
    assert [t.role for t in sent_history] == ["usuario", "assistente"]
    [(_, guardrail_history, techniques)] = guardrail.calls
    assert techniques == ["Uchi-mata"] and len(guardrail_history) == 2


def test_history_is_limited(client: TestClient) -> None:
    app.dependency_overrides[get_guardrail] = lambda: FakeGuardrail("tecnica")
    history = [{"role": "usuario", "text": "x"}] * 7
    assert client.post("/api/perguntar", json={"query": "oi", "history": history}).status_code == 422
