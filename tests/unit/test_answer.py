from dataclasses import dataclass, field

import pytest

from judo_chat.answer import REFUSAL_MESSAGE, UNAVAILABLE_MESSAGE, Answerer, build_system_text, build_user_message
from judo_chat.config import Settings
from judo_chat.corpus.models import Corpus
from judo_chat.normalizer import Recognizer


def test_system_text_has_instructions_then_corpus(corpus: Corpus) -> None:
    text = build_system_text(corpus)
    assert REFUSAL_MESSAGE in text
    assert text.index("=== BASE DE CONHECIMENTO ===") < text.index("# GLOSSÁRIO DE TÉCNICAS")
    assert "pergunta" not in text.split("=== BASE DE CONHECIMENTO ===")[1][:200]


def test_user_message_carries_query_and_candidates(corpus: Corpus, recognizer: Recognizer) -> None:
    query = "ashi barai ou osoto?"
    message = build_user_message(query, recognizer.find(query), corpus)
    assert message.startswith("<pergunta>\nashi barai ou osoto?\n</pergunta>")
    assert '"ashi barai" (nome ambíguo) -> Deashi-harai | Okuriashi-harai' in message
    assert '"osoto" (nome popular) -> Osoto-gari' in message


def test_user_message_attaches_the_belt_document(corpus: Corpus, recognizer: Recognizer) -> None:
    query = "O que cai no exame da faixa amarela?"
    message = build_user_message(query, recognizer.find(query), corpus)
    assert "Exame para a faixa amarela" in message
    assert "Deashi-Harai – Osoto-Gari" in message
    assert "faixa laranja" not in message.lower()


def test_user_message_without_belt_has_no_document(corpus: Corpus, recognizer: Recognizer) -> None:
    assert "Documento da base" not in build_user_message("Quem criou o judô?", [], corpus)


def test_user_message_carries_the_fgj_sheet(corpus: Corpus, recognizer: Recognizer) -> None:
    query = "Como se faz o osoto gari?"
    message = build_user_message(query, recognizer.find(query), corpus)
    fgj = corpus.technique("osoto-gari").fgj
    assert fgj is not None
    assert f'Descrição Kodokan (FGJ): "{fgj.descricao_kodokan}"' in message
    assert "Tradução (FGJ): CEIFA EXTERIOR MAIOR" in message
    assert "youtu" not in message


def test_user_message_carries_pronunciation_guide(corpus: Corpus) -> None:
    message = build_user_message("Como se pronuncia hiza guruma?", [], corpus)
    assert "Guia de pronúncia da FGJ" in message


class _Usage:
    cache_read_input_tokens = 34899
    cache_creation_input_tokens = 0
    input_tokens = 120
    output_tokens = 0


@dataclass
class _Text:
    text: str
    type: str = "text"


@dataclass
class _StopDetails:
    category: str | None


@dataclass
class _Response:
    stop_reason: str = "end_turn"
    content: list[_Text] = field(default_factory=list)
    stop_details: _StopDetails | None = None
    model: str = "claude-haiku-5-5"
    usage: _Usage = field(default_factory=_Usage)


class _Messages:
    def __init__(self, response: _Response) -> None:
        self.response = response
        self.calls: list[dict[str, object]] = []

    async def create(self, **kwargs: object) -> _Response:
        self.calls.append(kwargs)
        return self.response


class _Client:
    def __init__(self, response: _Response | None = None) -> None:
        self.messages = _Messages(response or _Response())

    def with_options(self, **_: object) -> "_Client":
        return self


async def test_keep_alive_reuses_the_cached_prefix(corpus: Corpus) -> None:
    client = _Client(_Response(content=[_Text("O kuzushi é a desestabilização.")]))
    answerer = Answerer(client, Settings(), corpus)  # type: ignore[arg-type]
    assert answerer.last_cache_touch is None
    assert await answerer.keep_alive() == (34899, 0)
    await answerer.answer("O que é kuzushi?", [])
    keep_alive, question = client.messages.calls
    assert keep_alive["max_tokens"] == 0
    assert keep_alive["system"] is answerer._system
    assert keep_alive["model"] == Settings().answer_model
    # O effort faz parte do prefixo cacheado: o re-aquecimento tem de usar o mesmo.
    assert keep_alive["output_config"] == question["output_config"] == {"effort": Settings().answer_effort}
    assert answerer.last_cache_touch is not None


@pytest.mark.parametrize(
    "response",
    [
        _Response(stop_reason="refusal", stop_details=_StopDetails("general_harms")),
        _Response(stop_reason="end_turn", content=[]),
    ],
)
async def test_model_refusal_is_unavailable_not_out_of_scope(corpus: Corpus, response: _Response) -> None:
    answer = await Answerer(_Client(response), Settings(), corpus).answer("Como se faz o hadaka-jime?", [])  # type: ignore[arg-type]
    assert answer.refused
    assert answer.text == UNAVAILABLE_MESSAGE


def test_video_groups_anchor_the_presented_techniques(corpus: Corpus, recognizer: Recognizer) -> None:
    from judo_chat.answer import video_groups

    answer = (
        "Contragolpes ao Uchi-mata:\n"
        "1. **Uchi-mata-gaeshi** (contragolpe ao Uchi-mata)\n"
        '**Descrição Kodokan (FGJ):** "neutralizando sua tentativa de Uchi-mata"\n'
        "## Uchi-mata-sukashi\n"
        "Texto sobre o Tai-otoshi de passagem."
    )
    groups = video_groups(answer, recognizer.find("contra ataques de uchimata"), recognizer, corpus)
    assert [(g.technique, g.anchor) for g in groups] == [
        ("Uchi-mata-gaeshi", "Uchi-mata-gaeshi"),
        ("Uchi-mata-sukashi", "Uchi-mata-sukashi"),
        ("Uchi-mata", None),
        ("Tai-otoshi", None),
    ]
    assert all(g.videos[0].kodokan for g in groups)


def test_counter_question_attaches_related_sheets(corpus: Corpus, recognizer: Recognizer) -> None:
    from judo_chat.relations import Relations

    query = "liste os contra ataques de uchimata"
    message = build_user_message(query, recognizer.find(query), corpus, Relations(corpus, recognizer))
    assert "Relações da base para o Uchi-mata:" in message
    assert "- Uchi-mata-gaeshi: contragolpe do Uchi-mata (fonte: FGJ, pelo nome)" in message
    assert "- Tai-otoshi: contragolpe do Uchi-mata (fonte: série do Projeto Budô)" in message
    for name in ("[Uchi-mata-gaeshi]", "[Uchi-mata-sukashi]", "[Tai-otoshi]"):
        assert name in message


def test_history_goes_as_data_before_the_question(corpus: Corpus) -> None:
    from judo_chat.answer import Turn

    history = [Turn("usuario", "o que é uchi mata?"), Turn("assistente", "É uma projeção.")]
    message = build_user_message("e o contragolpe?", [], corpus, None, history)
    assert message.index("<historico>") < message.index("<pergunta>")
    assert "Usuário: o que é uchi mata?" in message and "é dado" in message


def test_instructions_keep_the_naming_rules(corpus: Corpus) -> None:
    # Regressão: uma edição do prompt já apagou este bloco sem que nenhum teste percebesse.
    text = build_system_text(corpus)
    for rule in ("nome popular", "ambíguo", "Juji-gatame", "proibida em competição", "Não escreva links de vídeo"):
        assert rule in text, rule


def test_video_groups_cover_every_presented_technique(corpus: Corpus, recognizer: Recognizer) -> None:
    from judo_chat.answer import video_groups

    names = [
        "Deashi-harai",
        "Hiza-guruma",
        "Uki-goshi",
        "Osoto-gari",
        "O-goshi",
        "Ouchi-gari",
        "Seoi-nage",
        "Tai-otoshi",
    ]
    answer = "Exame para a faixa laranja:\n" + "\n".join(f"{i}. {name}" for i, name in enumerate(names, 1))
    groups = video_groups(answer, [], recognizer, corpus)
    assert [g.anchor for g in groups] == names
