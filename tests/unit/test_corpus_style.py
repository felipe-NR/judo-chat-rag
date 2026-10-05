"""Regressões de estilo pt-BR no corpus (docs/guia-estilo-ptbr.md)."""

import re

from judo_chat.corpus.models import Corpus

_BARE_ROLE = re.compile(
    r"(?<![-\w])(?<!\bo )(?<!\bdo )(?<!\bno )(?<!\bao )(?<!\bpelo )(?<!\bObi )(tori|uke)(?![-\w])", re.I
)
_FORBIDDEN = [
    "puxando e levantando",
    "puxa e levanta",
    "de forma que fica",
    "de modo que fica",
    "para que fica",
]


def _texts(corpus: Corpus) -> dict[str, str]:
    texts = {t.id: " ".join((t.description_pt_br or "").split()) for t in corpus.techniques}
    texts |= {t.id + ":nome": t.name_pt_br or "" for t in corpus.techniques}
    texts |= {d.id: " ".join(d.body.split()) for d in corpus.documents}
    texts |= {p.name: p.note or "" for p in corpus.popular_names}
    return texts


def test_tori_and_uke_always_have_an_article(corpus: Corpus) -> None:
    offenders = {k: m.group(0) for k, v in _texts(corpus).items() for m in [_BARE_ROLE.search(v)] if m}
    assert offenders == {}


def test_no_literal_translation_patterns(corpus: Corpus) -> None:
    offenders = [(k, phrase) for k, v in _texts(corpus).items() for phrase in _FORBIDDEN if phrase in v.lower()]
    assert offenders == []
