from pathlib import Path

import pytest

from judo_chat.corpus.loader import load_corpus
from judo_chat.corpus.models import Corpus
from judo_chat.normalizer import Recognizer

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


@pytest.fixture(scope="session")
def corpus() -> Corpus:
    return load_corpus(DATA_DIR)


@pytest.fixture(scope="session")
def recognizer(corpus: Corpus) -> Recognizer:
    return Recognizer(corpus)
