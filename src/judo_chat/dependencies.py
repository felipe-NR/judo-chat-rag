from typing import Annotated

from fastapi import Depends, Request

from judo_chat.answer import Answerer
from judo_chat.corpus.models import Corpus
from judo_chat.guardrail import Guardrail
from judo_chat.normalizer import Recognizer


def get_corpus(request: Request) -> Corpus:
    return request.app.state.corpus


def get_recognizer(request: Request) -> Recognizer:
    return request.app.state.recognizer


def get_guardrail(request: Request) -> Guardrail:
    return request.app.state.guardrail


def get_answerer(request: Request) -> Answerer:
    return request.app.state.answerer


CorpusDep = Annotated[Corpus, Depends(get_corpus)]
RecognizerDep = Annotated[Recognizer, Depends(get_recognizer)]
GuardrailDep = Annotated[Guardrail, Depends(get_guardrail)]
AnswererDep = Annotated[Answerer, Depends(get_answerer)]
