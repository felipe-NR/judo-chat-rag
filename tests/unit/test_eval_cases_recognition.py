"""Camada sem rede do conjunto de avaliação: o reconhecedor contra cada pergunta."""

import pytest

from judo_chat.normalizer import Recognizer

from ..eval.cases import Case, load_cases

CASES = load_cases()


def test_case_ids_are_unique() -> None:
    ids = [case.id for case in CASES]
    assert len(ids) == len(set(ids))


@pytest.mark.parametrize("case", CASES, ids=[case.id for case in CASES])
def test_recognizer_on_eval_case(recognizer: Recognizer, case: Case) -> None:
    assert [m.technique_ids for m in recognizer.find(case.pergunta)] == case.expected_matches()
