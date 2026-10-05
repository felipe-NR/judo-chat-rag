"""Relações entre técnicas, derivadas dos dados que o corpus já tem.

Tipos:
- contragolpe: `counter` contra-ataca `attack`. Vem dos textos da FGJ ("Contragolpe de uma
  tentativa de X", "sua tentativa de X"), dos nomes "X-gaeshi"/"X-sukashi" e da série de
  kaeshi-waza do Projeto Budô ("Uchi Mata – Tai Otoshi");
- variacao: `variant` é uma forma derivada de `base`. Vem dos nomes ("Kuzure-X", "Ippon-X",
  "X-makikomi") e dos princípios da FGJ ("A ação como de um X");
- combinacao: `second` emenda depois de `first`, nas séries de renraku-henka-waza.
"""

import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

from judo_chat.corpus.models import Corpus, Technique
from judo_chat.normalizer import Recognizer

Kind = Literal["contragolpe", "variacao", "combinacao"]

_FGJ_COUNTER = re.compile(
    r"(?:Contragolpe de uma|Contraposição a uma|sua|repelir a|desviar da) tentativa de ([A-Za-zÀ-ú-]+(?: \([^)]*\))?)"
)
_FGJ_LIKE = re.compile(r"como de um ([A-Za-zÀ-ú-]+)")
_SERIES_LINE = re.compile(r"^- \d+ – (.+)$")
_COUNTER_SUFFIXES = ("gaeshi", "sukashi")


@dataclass(frozen=True, order=True)
class Relation:
    # Para contragolpe: source = golpe atacado, target = contragolpe.
    # Para variacao: source = técnica base, target = variação.
    # Para combinacao: source = primeiro golpe, target = o que emenda depois.
    source: str
    target: str
    kind: Kind
    origin: str


def _ids(recognizer: Recognizer, text: str) -> list[str]:
    entry = recognizer.lookup(text)
    if entry is not None:
        return list(entry.technique_ids)
    return [tid for match in recognizer.find(text) for tid in match.technique_ids]


def _from_fgj(technique: Technique, recognizer: Recognizer) -> Iterable[Relation]:
    if technique.fgj is None:
        return
    text = f"{technique.fgj.principio} {technique.fgj.descricao_kodokan}"
    for fragment in _FGJ_COUNTER.findall(text):
        for attack in _ids(recognizer, fragment):
            if attack != technique.id:
                yield Relation(attack, technique.id, "contragolpe", "FGJ")
    for fragment in _FGJ_LIKE.findall(technique.fgj.principio):
        for base in _ids(recognizer, fragment):
            if base != technique.id:
                yield Relation(base, technique.id, "variacao", "FGJ")


def _official_ids(corpus: Corpus, recognizer: Recognizer, name: str, exclude: str) -> list[str]:
    """Só nomes oficiais (ou grafias) de técnicas: "Hikikomi" é nome popular do próprio
    Hikikomi-gaeshi, e "gake" casaria com o conceito kake."""
    entry = recognizer.lookup(name)
    if entry is None or entry.match_type not in ("oficial", "ijf", "grafia"):
        return []
    return [tid for tid in entry.technique_ids if tid != exclude and corpus.technique(tid).kind == "technique"]


def _from_name(technique: Technique, corpus: Corpus, recognizer: Recognizer) -> Iterable[Relation]:
    parts = technique.name.split("-")
    if len(parts) < 2:
        return
    if parts[-1] in _COUNTER_SUFFIXES:
        for attack in _official_ids(corpus, recognizer, "-".join(parts[:-1]), technique.id):
            yield Relation(attack, technique.id, "contragolpe", "nome")
        return
    candidates = ["-".join(parts[1:])]
    if parts[-1] == "makikomi":
        candidates.append("-".join(parts[:-1]))
    for candidate in candidates:
        for base in _official_ids(corpus, recognizer, candidate, technique.id):
            yield Relation(base, technique.id, "variacao", "nome")


def _from_series(corpus: Corpus, recognizer: Recognizer) -> Iterable[Relation]:
    for document in corpus.documents:
        if document.id == "graduacao/kaeshi-waza":
            kind: Kind = "contragolpe"
        elif document.id == "graduacao/renraku-henka-waza":
            kind = "combinacao"
        else:
            continue
        for line in document.body.splitlines():
            match = _SERIES_LINE.match(line.strip())
            if not match:
                continue
            steps = [_ids(recognizer, name.strip()) for name in match.group(1).split(" – ")]
            for first, second in zip(steps, steps[1:], strict=False):
                for source in first:
                    for target in second:
                        if source != target:
                            yield Relation(source, target, kind, "Projeto Budô")


class Relations:
    def __init__(self, corpus: Corpus, recognizer: Recognizer) -> None:
        found: dict[tuple[str, str, Kind], set[str]] = {}
        sources: list[Iterable[Relation]] = [_from_series(corpus, recognizer)]
        for technique in corpus.techniques:
            if technique.kind == "technique":
                sources += [_from_fgj(technique, recognizer), _from_name(technique, corpus, recognizer)]
        for relations in sources:
            for relation in relations:
                found.setdefault((relation.source, relation.target, relation.kind), set()).add(relation.origin)
        self._all = sorted(
            Relation(source, target, kind, ", ".join(sorted(origins)))
            for (source, target, kind), origins in found.items()
        )

    def all(self) -> list[Relation]:
        return list(self._all)

    def of(self, technique_id: str, kinds: Iterable[Kind]) -> list[Relation]:
        """Relações em que a técnica aparece, nos dois sentidos."""
        wanted = set(kinds)
        return [r for r in self._all if r.kind in wanted and technique_id in (r.source, r.target)]
