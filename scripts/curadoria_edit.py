"""Troca name_pt_br e description_pt_br de entradas da curadoria sem reformatar o resto.

Uso como módulo: apply({"osoto-gari": {"description_pt_br": "..."}}). Usado nas revisões de
texto em lote; o arquivo YAML continua editável à mão.
"""

import re
import textwrap
from pathlib import Path

CURADORIA = Path(__file__).resolve().parent.parent / "data" / "curadoria"


def _block_span(text: str, technique_id: str) -> tuple[int, int] | None:
    match = re.search(rf"^- id: {re.escape(technique_id)}\n", text, re.M)
    if match is None:
        return None
    following = re.search(r"^(- id: |# -)", text[match.end() :], re.M)
    end = match.end() + following.start() if following else len(text)
    return match.start(), end


def _replace_field(block: str, field: str, value: str) -> str:
    if field == "description_pt_br":
        wrapped = textwrap.fill(" ".join(value.split()), width=88, initial_indent="    ", subsequent_indent="    ")
        new, count = re.subn(r"  description_pt_br: >-\n(?:    .*\n)+", f"  description_pt_br: >-\n{wrapped}\n", block)
    else:
        new, count = re.subn(rf"  {field}: .*\n", f"  {field}: {value}\n", block)
    if count != 1:
        raise ValueError(f"campo {field} não encontrado")
    return new


def apply(changes: dict[str, dict[str, str]]) -> list[str]:
    pending = dict(changes)
    for path in sorted(CURADORIA.glob("*.yaml")):
        text = path.read_text("utf-8")
        for technique_id in list(pending):
            span = _block_span(text, technique_id)
            if span is None:
                continue
            block = text[span[0] : span[1]]
            for field, value in pending.pop(technique_id).items():
                block = _replace_field(block, field, value)
            text = text[: span[0]] + block + text[span[1] :]
        path.write_text(text, "utf-8")
    return sorted(pending)
