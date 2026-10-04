from judo_chat.answer import REFUSAL_MESSAGE, build_system_text, build_user_message
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
