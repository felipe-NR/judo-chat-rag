from pathlib import Path

import yaml
from pydantic import BaseModel

from judo_chat.guardrail import Category

CASES_PATH = Path(__file__).with_name("cases.yaml")


class Case(BaseModel):
    id: str
    pergunta: str
    categoria: Category
    tecnicas: list[str | list[str]]
    incluir: list[str] = []

    def expected_matches(self) -> list[tuple[str, ...]]:
        return [(item,) if isinstance(item, str) else tuple(item) for item in self.tecnicas]


def load_cases() -> list[Case]:
    return [Case.model_validate(item) for item in yaml.safe_load(CASES_PATH.read_text("utf-8"))]
