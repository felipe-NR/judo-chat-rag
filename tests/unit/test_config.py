import pytest
from pydantic import ValidationError

from judo_chat.config import Settings


def test_refusal_fallbacks_are_rejected_on_haiku() -> None:
    with pytest.raises(ValidationError, match="Haiku"):
        Settings(answer_model="claude-haiku-5-5", use_refusal_fallbacks=True)


def test_refusal_fallbacks_are_accepted_on_sonnet() -> None:
    assert Settings(answer_model="claude-sonnet-5-5", use_refusal_fallbacks=True).use_refusal_fallbacks
